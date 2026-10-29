from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import re,shutil,subprocess,unicodedata
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.docx_import import import_docx
from backend.docx_export import export_docx
from backend.engine import DocumentError
from tests.test_docx_content import illustrated


def source():return export_docx(illustrated(),[],[0,1],include_images=True,include_tables=True)[0]


def changed(base,name,data,extra=None):
    out=BytesIO()
    with ZipFile(BytesIO(base)) as old,ZipFile(out,'w',ZIP_DEFLATED) as z:
        for path in old.namelist():z.writestr(path,data if path==name else old.read(path))
        if extra:z.writestr(*extra)
    return out.getvalue()


def document_xml(text='Prueba importada',extra=''):
    return f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p>{extra}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:body></w:document>'.encode()


def test_import_styled_text_images_tables_and_editable_pdf_with_independent_extraction(tmp_path):
    data=source();out,r=import_docx(data)
    assert r['tables']==1 and r['images']==1 and r['text_check_passed'] and not r['layout_preserved']
    assert r['warnings'] and r['source_sha256'] and r['pdf_sha256']
    with f.open(stream=out) as d:
        text=''.join(p.get_text() for p in d);assert 'Material' in text and '250' in text
        assert any(p.get_images() for p in d)
        spans=[s for p in d for b in p.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans']]
        assert any(s['font'].startswith('DejaVu') for s in spans)
    if shutil.which('pdftotext'):
        path=tmp_path/'imported.pdf';path.write_bytes(out);assert 'Material' in subprocess.check_output(['pdftotext',str(path),'-']).decode()


@pytest.mark.parametrize('paper',['source','A4','Letter'])
def test_pagination_paper_and_all_text_remains_available(paper):
    base=changed(source(),'word/document.xml',document_xml('Contenido largo. '*2000))
    out,r=import_docx(base,paper);assert 1<r['pages']<=50 and r['text_check_passed']
    with f.open(stream=out) as d:
        assert ''.join(p.get_text() for p in d).count('Contenido')==2000
        if paper=='Letter':assert d[0].rect.width==612


def test_web_hyperlink_survives_import_and_font_changes_are_reported():
    from tests.test_docx_links import source as linked_pdf
    docx=export_docx(linked_pdf(),[],[0],include_links=True)[0];out,r=import_docx(docx)
    with f.open(stream=out) as d:assert any(link.get('uri')=='https://example.com/ruta?a=1&b=2' for p in d for link in p.get_links())
    assert 'Arial' in r['fonts_replaced']


@pytest.mark.parametrize('xml',[
 b'<!DOCTYPE x [<!ENTITY z "boom">]><w:document/>',b'<broken>',b'<x/>',
 document_xml('漢字'),document_xml('Texto','<w:ins><w:p/></w:ins>'),document_xml('Texto','<w:object/>'),
])
def test_invalid_and_unsafe_content_rejected(xml):
    with pytest.raises(DocumentError):import_docx(changed(source(),'word/document.xml',xml))


@pytest.mark.parametrize('name',['../escape.xml','/absolute.xml','word/vbaProject.bin','word/embeddings/oleObject1.bin','word\\escape.xml'])
def test_package_paths_macros_and_objects_rejected(name):
    with pytest.raises(DocumentError):import_docx(changed(source(),'unused',b'',extra=(name,b'unsafe')))


def test_omitted_headers_lists_fields_and_styles_are_visible_in_report():
    xml=document_xml('Texto visible','<w:p><w:pPr><w:numPr/></w:pPr><w:r><w:fldChar/><w:t>Resultado fijo</w:t></w:r></w:p>')
    base=changed(source(),'word/document.xml',xml,extra=('word/header1.xml',b'<header/>'))
    out,r=import_docx(base)
    assert any('Encabezados' in v for v in r['warnings']) and any('numeración/listas' in v for v in r['warnings']) and any('campos automáticos' in v for v in r['warnings'])
    with f.open(stream=out) as d:assert 'Resultado fijo' in unicodedata.normalize('NFKC',d[0].get_text())


def test_expansion_characters_and_page_limits(monkeypatch):
    monkeypatch.setattr('backend.docx_import.MAX_EXPANDED',20)
    with pytest.raises(DocumentError,match='40 MB'):import_docx(source())
    monkeypatch.setattr('backend.docx_import.MAX_EXPANDED',40*1024*1024)
    with pytest.raises(DocumentError,match='100000'):import_docx(changed(source(),'word/document.xml',document_xml('abc '*30000)))
    with pytest.raises(DocumentError):import_docx(b'not zip')
    with pytest.raises(DocumentError):import_docx(source(),paper='unknown')


def test_api_import_creates_editable_document_and_invalid_upload_is_not_stored():
    with TestClient(app) as c:
        r=c.post('/api/import/docx',files={'file':('Mi trabajo.docx',source(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
        assert r.status_code==200,r.text
        info=r.json();assert info['name']=='Mi trabajo.pdf' and info['report']['images']==1
        url='/api/documents/'+info['document']['id'];assert c.post(url+'/export',json={'operations':[]}).status_code==200
        assert c.post('/api/import/docx',files={'file':('bad.docx',b'bad','application/zip')}).status_code==422
        assert c.delete(url).status_code==200


def test_direct_bold_italic_size_and_color_survive_import():
    from tests.test_docx_export import source as styled
    out,r=import_docx(export_docx(styled(),[],[0])[0])
    with f.open(stream=out) as d:
        spans=[s for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']]
        assert any(s['flags']&16 and abs(s['size']-16)<.01 and s['color']==0x336699 for s in spans)
        assert any(s['flags']&2 for s in spans)


def test_cropped_images_are_omitted_instead_of_exposing_hidden_areas():
    base=source()
    with ZipFile(BytesIO(base)) as z:
        xml=z.read('word/document.xml').replace(b'<a:stretch>',b'<a:srcRect l="20000"/><a:stretch>')
    out,r=import_docx(changed(base,'word/document.xml',xml))
    assert r['images']==0 and any('Imagen recortada' in v for v in r['warnings'])
    with f.open(stream=out) as d:assert not any(p.get_images() for p in d)


def test_simple_fields_preserve_cached_text_without_executing_instructions():
    xml=document_xml('Inicio').replace(b'</w:p>',b'<w:fldSimple w:instr="DATE"><w:r><w:t>20/10/2026</w:t></w:r></w:fldSimple></w:p>',1)
    out,r=import_docx(changed(source(),'word/document.xml',xml))
    with f.open(stream=out) as d:assert '20/10/2026' in d[0].get_text()
    assert any('campos automáticos' in v for v in r['warnings'])


def test_imported_pdf_can_be_edited_as_text_not_only_viewed():
    from tests.test_docx_export import source as styled
    from backend.paragraphs import paragraph_blocks,replace_paragraph
    pdf,_=import_docx(export_docx(styled(),[],[0])[0])
    boxes=paragraph_blocks(pdf,[],0)['blocks'];assert boxes
    result=replace_paragraph(pdf,[],0,boxes[0]['box'],'Edición importada',auto_fit=True,min_size=6)
    with f.open(stream=result) as d:assert 'Edición importada' in d[0].get_text()
