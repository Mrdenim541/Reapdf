from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_headers import fixture as base,p,field,W,R,P


def properties(*,landscape=False,start=None,fmt=None,header=None,kind='nextPage',title=False):
    width,height=(16838,11906) if landscape else (11906,16838)
    refs=f'<w:headerReference w:type="default" r:id="{header}"/>' if header else ''
    number='' if start is None and fmt is None else '<w:pgNumType '+(f'w:start="{start}" ' if start is not None else '')+(f'w:fmt="{fmt}"' if fmt else '')+'/>'
    return f'<w:sectPr>{refs}<w:type w:val="{kind}"/><w:pgSz w:w="{width}" w:h="{height}"/><w:pgMar w:left="1440" w:right="720" w:top="1080" w:bottom="720"/>{number}'+('<w:titlePg/>' if title else '')+'</w:sectPr>'


def fixture(*,kind='nextPage',long=False):
    first=properties(header='h',start=3,fmt='lowerRoman')
    middle=properties(landscape=True,header='h2',kind=kind)
    last=properties(start=1,fmt='decimal')
    def ending(content,props):return '<w:p><w:pPr>'+props+'</w:pPr><w:r><w:t>'+content+'</w:t></w:r></w:p>'
    from tests.test_docx_merged_tables import combined_table
    content=ending('Portada original. '+('Cuerpo de portada. '*400 if long else ''),first)+combined_table()+ending('Tabla horizontal. '+('Cuerpo horizontal. '*400 if long else ''),middle)+p('Anexo independiente. '+('Cuerpo anexo. '*400 if long else ''))+last
    files={'word/document.xml':f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>{content}</w:body></w:document>',
      'word/_rels/document.xml.rels':f'<Relationships xmlns="{P}"><Relationship Id="h" Type="{R}/header" Target="header1.xml"/><Relationship Id="h2" Type="{R}/header" Target="header2.xml"/></Relationships>'}
    for part,title in [('header1.xml','Cabecera portada'),('header2.xml','Cabecera horizontal')]:
        files['word/'+part]=f'<w:hdr xmlns:w="{W}" xmlns:r="{R}"><w:p><w:r><w:t>{title} </w:t></w:r>{field("PAGE")}<w:r><w:t> de </w:t></w:r>{field("NUMPAGES")}<w:hyperlink r:id="web"><w:r><w:t> Enlace externo</w:t></w:r></w:hyperlink></w:p></w:hdr>'
        files['word/_rels/'+part+'.rels']=f'<Relationships xmlns="{P}"><Relationship Id="web" Type="{R}/hyperlink" Target="https://example.com/{part}" TargetMode="External"/></Relationships>'
    return rewrite(base(),files)


def rewrite(data,files):
    out=BytesIO()
    with ZipFile(BytesIO(data)) as old,ZipFile(out,'w',ZIP_DEFLATED) as z:
        for name in old.namelist():z.writestr(name,files.pop(name,old.read(name)))
        for name,value in files.items():z.writestr(name,value)
    return out.getvalue()


def test_portrait_landscape_annex_restart_inherited_headers_links_and_native_labels():
    pdf,r=import_docx(fixture())
    assert r['section_count']==3 and r['text_check_passed'] and r['pages']==3
    assert [s['number_start'] for s in r['sections']]==[3,4,1]
    with f.open(stream=pdf) as d:
        assert [p.get_label() for p in d]==['iii','iv','1']
        for index,(page,title,num) in enumerate(zip(d,['portada','horizontal','horizontal'],['iii','iv','1'])):
            assert f'Cabecera {title} {num} de 3' in page.get_text()
            assert page.get_links() and all(('header1' if index==0 else 'header2') in link['uri'] for link in page.get_links())
            assert (page.rect.width>page.rect.height)==(index==1)
            assert all(page.rect.contains(f.Rect(word[:4])) for word in page.get_text('words'))
            assert not page.get_xobjects() and not page.get_images()
        assert all(value in d[1].get_text() for value in ['Titulo combinado','Vertical','SuperiorA','SuperiorB','Inferior combinada'])
        assert d[0].search_for('Portada')[0].x0>=72
    assert not any('última sección' in w or 'tamaño de página común' in w or 'reinicios internos' in w for w in r['warnings'])


def test_global_total_and_continuation_with_multiple_pages_per_section():
    pdf,r=import_docx(fixture(long=True));assert r['text_check_passed']
    with f.open(stream=pdf) as d:
        assert len(d)>3
        for s in r['sections']:
            start=s['first_page']-1
            for offset in range(s['pages']):
                page=d[start+offset];assert f' de {len(d)}' in page.get_text()
                from backend.docx_fields import number_label
                assert page.get_label()==number_label(s['number_start']+offset,s['number_format'])
        assert r['sections'][1]['number_start']==3+r['sections'][0]['pages']


@pytest.mark.parametrize('paper',['A4','Letter'])
def test_explicit_paper_applies_consistently_to_all_sections(paper):
    pdf,r=import_docx(fixture(),paper)
    with f.open(stream=pdf) as d:
        assert all(abs(page.rect.width-f.paper_size(paper)[0])<.1 for page in d)
    assert r['section_count']==3 and r['text_check_passed']


@pytest.mark.parametrize('kind',['continuous','oddPage','evenPage','nextColumn','invalid'])
def test_unsupported_section_break_is_explicit_and_atomic(kind):
    with pytest.raises(DocumentError,match='página siguiente'):import_docx(fixture(kind=kind))
    with TestClient(app) as client:
        response=client.post('/api/import/docx',files={'file':('secciones.docx',fixture(kind=kind),'application/zip')})
        assert response.status_code==422 and 'página siguiente' in response.json()['detail']


def test_numbering_without_dynamic_fields_still_preserves_native_labels():
    data=fixture()
    files={}
    with ZipFile(BytesIO(data)) as z:
        for name in ['word/header1.xml','word/header2.xml']:
            files[name]=f'<w:hdr xmlns:w="{W}">{p("Cabecera sin campos")}</w:hdr>'
    pdf,r=import_docx(rewrite(data,files))
    with f.open(stream=pdf) as d:assert [p.get_label() for p in d]==['iii','iv','1']
    assert r['page_fields']==0 and r['page_labels_preserved']


def test_section_limit_rejects_many_empty_sections():
    body=''.join('<w:p><w:pPr>'+properties()+'</w:pPr></w:p>' for _ in range(51))
    data=rewrite(base(),{'word/document.xml':f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'})
    with pytest.raises(DocumentError,match='50 secciones'):import_docx(data)


@pytest.mark.parametrize('before',['<w:pageBreakBefore/>','<w:pageBreakBefore w:val="1"/>'])
def test_page_break_before_creates_native_new_page_with_correct_total(before):
    xml=f'<w:document xmlns:w="{W}"><w:body>{p("Primera pagina")}<w:p><w:pPr>{before}</w:pPr><w:r><w:t>Segunda pagina</w:t></w:r></w:p>{properties()}</w:body></w:document>'
    pdf,r=import_docx(rewrite(base(),{'word/document.xml':xml}))
    with f.open(stream=pdf) as d:
        assert len(d)==2 and 'Primera' in d[0].get_text() and 'Segunda' not in d[0].get_text() and 'Segunda' in d[1].get_text()
    assert r['manual_page_breaks']==1 and r['text_check_passed']


def test_inline_page_break_preserves_direct_run_style_and_selectable_text():
    xml=f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:rPr><w:b/><w:color w:val="14642F"/></w:rPr><w:t>Antes del salto</w:t><w:br w:type="page"/><w:t>Despues del salto</w:t></w:r></w:p>{properties()}</w:body></w:document>'
    pdf,r=import_docx(rewrite(base(),{'word/document.xml':xml}))
    with f.open(stream=pdf) as d:
        assert len(d)==2 and 'Antes del salto' in d[0].get_text() and 'Despues del salto' in d[1].get_text()
        for page in d:
            spans=[s for b in page.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans']]
            assert any(s['flags']&16 and s['color']==0x14642F for s in spans)
    assert r['manual_page_breaks']==1 and r['text_check_passed']


def test_page_break_false_does_not_add_page():
    xml=f'<w:document xmlns:w="{W}"><w:body>{p("Primera")}<w:p><w:pPr><w:pageBreakBefore w:val="false"/></w:pPr><w:r><w:t>Segunda</w:t></w:r></w:p>{properties()}</w:body></w:document>'
    pdf,r=import_docx(rewrite(base(),{'word/document.xml':xml}))
    with f.open(stream=pdf) as d:assert len(d)==1
    assert r['manual_page_breaks']==0


def test_sectionpages_counts_only_current_section_while_numpages_counts_document():
    data=fixture(long=True)
    files={}
    with ZipFile(BytesIO(data)) as z:
        for name in ['word/header1.xml','word/header2.xml']:
            xml=z.read(name).decode().replace(field('NUMPAGES'),field('NUMPAGES')+'<w:r><w:t> Seccion </w:t></w:r>'+field('SECTIONPAGES'))
            files[name]=xml
    pdf,r=import_docx(rewrite(data,files))
    with f.open(stream=pdf) as d:
        for section in r['sections']:
            for index in range(section['first_page']-1,section['first_page']-1+section['pages']):
                assert f'de {len(d)} Seccion {section["pages"]}' in d[index].get_text()
    assert r['text_check_passed']


def test_complex_sectionpages_with_roman_switch_and_global_total():
    from tests.test_docx_complex_fields import complex_field
    data=fixture();files={}
    with ZipFile(BytesIO(data)) as z:
        for name in ['word/header1.xml','word/header2.xml']:
            files[name]=z.read(name).decode().replace(field('NUMPAGES'),complex_field('SECTIONPAGES \\* ROMAN'))
    pdf,r=import_docx(rewrite(data,files))
    with f.open(stream=pdf) as d:assert all(' de I' in page.get_text() for page in d)
    assert r['complex_page_fields']==3 and r['text_check_passed']
