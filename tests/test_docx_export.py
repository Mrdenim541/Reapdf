"""OOXML structure, styled text, limits and independent python-docx interoperability."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import shutil,subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.docx_export import export_docx,W
from backend.engine import DocumentError


def source():
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((40,80),'Texto en negrita & <editable>',fontname='hebo',fontsize=16,color=(.2,.4,.6));p.insert_text((40,100),'Segunda linea',fontname='heit',fontsize=12)
        p=d.new_page(width=650,height=500);p.insert_text((40,80),'Pagina dos',fontname='tiro',fontsize=14)
        d.new_page();return d.tobytes()


def parse(data):
    with ZipFile(BytesIO(data)) as z:
        assert set(z.namelist())=={'[Content_Types].xml','_rels/.rels','word/document.xml','word/styles.xml','word/_rels/document.xml.rels'}
        for name in z.namelist():ET.fromstring(z.read(name))
        return ET.fromstring(z.read('word/document.xml'))


def test_docx_contains_editable_styled_text_and_sections_in_requested_order():
    out,report=export_docx(source(),[],[1,0,2]);tree=parse(out);ns={'w':W};text=''.join(tree.itertext())
    assert 'Pagina dos' in text and 'Texto en negrita & <editable>' in text and text.index('Pagina dos')<text.index('Texto en negrita')
    assert len(tree.findall('.//w:sectPr',ns))==3 and tree.find('.//w:b',ns) is not None and tree.find('.//w:i',ns) is not None
    assert tree.find('.//w:color[@w:val="336699"]',ns) is not None
    assert report['pages'][2]['characters']==0 and report['characters']>0 and not report['layout_preserved'] and not report['images_included']
    assert all(c.tag!='{http://schemas.openxmlformats.org/drawingml/2006/main}blip' for c in tree.iter())


@pytest.mark.parametrize('keep',[True,False])
def test_line_break_option_is_honored(keep):
    with f.open() as d:
        p=d.new_page();p.insert_text((40,80),'Primera\nSegunda',fontsize=12);base=d.tobytes()
    out,_=export_docx(base,[],[0],keep);tree=parse(out)
    assert bool(tree.findall('.//{'+W+'}br'))==keep


def test_blank_or_image_only_document_requires_ocr():
    with f.open() as d:d.new_page();base=d.tobytes()
    with pytest.raises(DocumentError,match='OCR'):export_docx(base,[],[0])


@pytest.mark.parametrize('pages,keep',[([],True),([True],True),([3],True),([0,0],True),([0],'yes')])
def test_invalid_selection_or_option_rejected(pages,keep):
    with pytest.raises(DocumentError):export_docx(source(),[],pages,keep)


def test_permission_and_character_page_limits(monkeypatch):
    with f.open(stream=source()) as d:restricted=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_PRINT)
    with pytest.raises(DocumentError):export_docx(restricted,[],[0])
    monkeypatch.setattr('backend.docx_export.MAX_CHARACTERS',5)
    with pytest.raises(DocumentError,match='100000'):export_docx(source(),[],[0])
    with f.open() as d:
        for i in range(51):d.new_page()
        base=d.tobytes()
    with pytest.raises(DocumentError,match='50 páginas'):export_docx(base,[],list(range(51)))


def test_oversized_page_is_scaled_and_native_rotation_reported():
    with f.open() as d:
        p=d.new_page(width=2500,height=2000);p.insert_text((40,80),'Plano con texto');p.set_rotation(90);base=d.tobytes()
    out,report=export_docx(base,[],[0]);tree=parse(out)
    assert report['pages'][0]['word_size_scaled'] and report['pages'][0]['rotation']==90
    size=tree.find('.//{'+W+'}pgSz');assert max(int(size.attrib['{'+W+'}w']),int(size.attrib['{'+W+'}h']))<=31680


def test_independent_python_docx_reader_opens_package_and_reads_styles(tmp_path):
    executable=shutil.which('python')
    if not executable:pytest.skip('Lector independiente no disponible')
    probe=subprocess.run([executable,'-c','import docx'],capture_output=True)
    if probe.returncode:pytest.skip('python-docx independiente no instalado')
    path=tmp_path/'editable.docx';path.write_bytes(export_docx(source(),[],[0,1])[0])
    subprocess.run([executable,'-c',"from docx import Document;import sys;d=Document(sys.argv[1]);assert len(d.sections)==2;assert any('Texto en negrita' in p.text for p in d.paragraphs);assert any(r.bold and r.font.size.pt==16 for p in d.paragraphs for r in p.runs);assert any(r.italic for p in d.paragraphs for r in p.runs)",str(path)],check=True,capture_output=True)


def test_api_review_and_download_are_read_only():
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('text.pdf',source(),'application/pdf')}).json();url='/api/documents/'+doc['id']
        review=client.post(url+'/export-docx',json={'pages':[0,1],'review':True});assert review.status_code==200 and review.json()['characters']>0
        result=client.post(url+'/export-docx',json={'pages':[0,1]});assert result.status_code==200 and 'wordprocessingml' in result.headers['content-type'];parse(result.content)
        assert client.post(url+'/comments',json={}).json()['comments']==[]
