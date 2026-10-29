from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import unicodedata,shutil,subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_styles import fixture as styled,W

R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
def p(text):return '<w:p><w:r><w:t>'+text+'</w:t></w:r></w:p>'
def field(name):return f'<w:fldSimple w:instr="{name}"><w:r><w:t>777</w:t></w:r></w:fldSimple>'
def fixture(*,variants=False,first=True,even=True,body='Texto central. '*400,overrides=None):
    xml=f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>{p(body)}<w:sectPr><w:headerReference w:type="default" r:id="h"/><w:footerReference w:type="default" r:id="f"/>'
    rels=f'<Relationships xmlns="{P}"><Relationship Id="h" Type="{R}/header" Target="header1.xml"/><Relationship Id="f" Type="{R}/footer" Target="footer1.xml"/>'
    files={'word/header1.xml':f'<w:hdr xmlns:w="{W}">{p("Cabecera general")}</w:hdr>',
      'word/footer1.xml':f'<w:ftr xmlns:w="{W}"><w:p><w:r><w:t>Pagina </w:t></w:r>{field("PAGE")}<w:r><w:t> de </w:t></w:r>{field("NUMPAGES")}</w:p></w:ftr>'}
    if variants:
        for kind,name,part in [('header','first','header2.xml'),('header','even','header3.xml')]:
            xml+=f'<w:{kind}Reference w:type="{name}" r:id="{name}"/>';rels+=f'<Relationship Id="{name}" Type="{R}/{kind}" Target="{part}"/>'
            files['word/'+part]=f'<w:hdr xmlns:w="{W}">{p("Portada especial" if name=="first" else "Cabecera par")}</w:hdr>'
    if first:xml+='<w:titlePg/>' if variants else ''
    xml+='<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:left="720" w:right="720" w:top="720" w:bottom="720" w:header="240" w:footer="240"/></w:sectPr></w:body></w:document>'
    files.update({'word/document.xml':xml,'word/_rels/document.xml.rels':rels+'</Relationships>','word/settings.xml':f'<w:settings xmlns:w="{W}">'+('<w:evenAndOddHeaders/>' if even and variants else '')+'</w:settings>'})
    files.update(overrides or {});out=BytesIO()
    with ZipFile(BytesIO(styled())) as old,ZipFile(out,'w',ZIP_DEFLATED) as z:
        for name in old.namelist():z.writestr(name,files.pop(name,old.read(name)))
        for name,data in files.items():z.writestr(name,data)
    return out.getvalue()

def texts(pdf):
    with f.open(stream=pdf) as d:return [unicodedata.normalize('NFKC',p.get_text()) for p in d]

@pytest.mark.parametrize('paper',['source','A4','Letter'])
def test_repeated_running_matter_page_counts_selectable_and_unclipped(paper,tmp_path):
    pdf,r=import_docx(fixture(),paper);pages=texts(pdf)
    assert len(pages)>=2 and r['header_footer_templates']==2 and r['header_footer_instances']==2*len(pages) and r['page_fields']==2 and r['text_check_passed']
    for index,text in enumerate(pages):assert 'Cabecera general' in text and f'Pagina {index+1} de {len(pages)}' in text and '777' not in text
    with f.open(stream=pdf) as d:
        for page in d:
            blocks=page.get_text('blocks');header=next(b for b in blocks if 'Cabecera' in b[4]);footer=next(b for b in blocks if 'Pagina' in b[4]);central=next(b for b in blocks if 'Texto central' in b[4])
            assert header[3]<central[1] and central[3]<footer[1] and footer[3]<page.rect.height
            assert not page.get_xobjects()  # Direct native text, no page overlay Form.
    if shutil.which('pdftotext'):
        path=tmp_path/'running.pdf';path.write_bytes(pdf);assert f'Pagina {len(pages)} de {len(pages)}' in subprocess.check_output(['pdftotext',str(path),'-']).decode()

@pytest.mark.parametrize('first,even',[(True,True),(False,True),(True,False),(False,False)])
def test_first_even_and_default_variants_follow_settings_without_false_text_loss(first,even):
    pdf,r=import_docx(fixture(variants=True,first=first,even=even,body='Texto central. '*800));pages=texts(pdf);assert len(pages)>=3 and r['text_check_passed']
    assert ('Portada especial' if first else 'Cabecera general') in pages[0]
    assert ('Cabecera par' if even else 'Cabecera general') in pages[1]
    assert 'Cabecera general' in pages[2]
    # titlePg/even headers without a corresponding footer mean a blank footer.
    assert ('Pagina 1 de' in pages[0]) is (not first)
    assert ('Pagina 2 de' in pages[1]) is (not even)


def test_running_links_use_the_part_relationships_and_survive_on_every_page():
    header=f'<w:hdr xmlns:w="{W}" xmlns:r="{R}"><w:p><w:hyperlink r:id="link"><w:r><w:t>Enlace de cabecera</w:t></w:r></w:hyperlink></w:p></w:hdr>'
    rels=f'<Relationships xmlns="{P}"><Relationship Id="link" Type="{R}/hyperlink" Target="https://example.com/reapdf" TargetMode="External"/></Relationships>'
    pdf,r=import_docx(fixture(overrides={'word/header1.xml':header,'word/_rels/header1.xml.rels':rels}))
    with f.open(stream=pdf) as d:assert all(any(l.get('uri')=='https://example.com/reapdf' for l in page.get_links()) for page in d)
    assert r['text_check_passed']

@pytest.mark.parametrize('change',['external','missing','badtype','dtd','revision','object','overflow','wrongroot','duplicate','wide'])
def test_invalid_or_overflowing_running_matter_fails_without_partial_pdf(change):
    overrides={}
    if change in ['external','missing','badtype','duplicate']:
        rel=f'<Relationship Id="h" Type="{R}/header" Target="header1.xml"/>'
        if change=='external':rel=f'<Relationship Id="h" Type="{R}/header" Target="https://example.com/remote.xml" TargetMode="External"/>'
        elif change=='missing':rel=rel.replace('header1.xml','not-here.xml')
        elif change=='badtype':rel=rel.replace('/header','/image')
        else:rel+=rel
        overrides['word/_rels/document.xml.rels']=f'<Relationships xmlns="{P}">{rel}<Relationship Id="f" Type="{R}/footer" Target="footer1.xml"/></Relationships>'
    elif change=='dtd':overrides['word/header1.xml']='<!DOCTYPE x [<!ENTITY attack "bad">]><x/>'
    elif change in ['revision','object']:overrides['word/header1.xml']=f'<w:hdr xmlns:w="{W}"><w:{"ins" if change=="revision" else "object"}/></w:hdr>'
    elif change=='overflow':overrides['word/header1.xml']=f'<w:hdr xmlns:w="{W}">'+p('Muy largo. '*400)+'</w:hdr>'
    elif change=='wide':overrides['word/header1.xml']=f'<w:hdr xmlns:w="{W}">'+p('X'*500)+'</w:hdr>'
    else:overrides['word/header1.xml']='<wrong/>'
    with pytest.raises(DocumentError):import_docx(fixture(overrides=overrides))


def test_body_editing_remains_possible_after_header_import():
    from backend.paragraphs import paragraph_blocks,replace_paragraph
    pdf,_=import_docx(fixture(body='Contenido para editar.'))
    blocks=paragraph_blocks(pdf,[],0)['blocks'];block=next(b for b in blocks if 'Contenido' in b['text'])
    edited=replace_paragraph(pdf,[],0,block['box'],'Contenido corregido.',auto_fit=True,min_size=6)
    text=texts(edited)[0];assert 'Contenido corregido.' in text and 'Cabecera general' in text and 'Pagina 1 de 1' in text


def test_api_import_includes_running_matter_report():
    with TestClient(app) as c:
        r=c.post('/api/import/docx',files={'file':('encabezados.docx',fixture(),'application/zip')});assert r.status_code==200,r.text
        assert r.json()['report']['header_footer_templates']==2 and r.json()['report']['page_fields']==2


@pytest.mark.parametrize('distance',['-1','999999','bad'])
def test_invalid_header_footer_distances_rejected(distance):
    base=fixture();out=BytesIO()
    with ZipFile(BytesIO(base)) as old,ZipFile(out,'w',ZIP_DEFLATED) as z:
        for name in old.namelist():
            data=old.read(name)
            if name=='word/document.xml':data=data.replace(b'w:header="240"',f'w:header="{distance}"'.encode())
            z.writestr(name,data)
    with pytest.raises(DocumentError):import_docx(out.getvalue())


def test_images_in_headers_resolve_their_own_local_relationships():
    from tests.test_docx_import import source
    from xml.etree import ElementTree as E
    from copy import deepcopy
    with ZipFile(BytesIO(source())) as original:
        doc=E.fromstring(original.read('word/document.xml'));drawing=next(doc.iter('{'+W+'}drawing'))
        hdr=E.Element('{'+W+'}hdr');paragraph=E.SubElement(hdr,'{'+W+'}p');run=E.SubElement(paragraph,'{'+W+'}r');run.append(deepcopy(drawing))
        extra={name:original.read(name) for name in original.namelist() if name.startswith('word/media/')}
        extra['word/header1.xml']=E.tostring(hdr);extra['word/_rels/header1.xml.rels']=original.read('word/_rels/document.xml.rels')
    pdf,report=import_docx(fixture(overrides=extra))
    with f.open(stream=pdf) as d:assert all(page.get_images() for page in d)
    assert report['images']==1 and report['text_check_passed']


def test_unsupported_field_instructions_use_saved_results_and_are_not_executed():
    footer=f'<w:ftr xmlns:w="{W}"><w:p><w:fldSimple w:instr="INCLUDETEXT &quot;https://example.com/private&quot;"><w:r><w:t>Resultado guardado</w:t></w:r></w:fldSimple></w:p></w:ftr>'
    pdf,report=import_docx(fixture(overrides={'word/footer1.xml':footer}));assert all('Resultado guardado' in text for text in texts(pdf))
    assert any('sin actualización' in warning for warning in report['warnings'])


def test_page_fields_keep_compatible_inherited_and_direct_text_style():
    footer=f'<w:ftr xmlns:w="{W}"><w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:fldSimple w:instr="PAGE"><w:r><w:rPr><w:sz w:val="18"/><w:i/></w:rPr><w:t>777</w:t></w:r></w:fldSimple></w:p></w:ftr>'
    pdf,r=import_docx(fixture(body='Contenido',overrides={'word/footer1.xml':footer}))
    with f.open(stream=pdf) as d:
        spans=[s for b in d[0].get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans']]
        number=next(s for s in spans if s['text']=='1');assert number['size']==9 and number['flags']&2 and number['flags']&16 and number['color']==0x245588
    assert r['page_fields']==1 and r['text_check_passed']
