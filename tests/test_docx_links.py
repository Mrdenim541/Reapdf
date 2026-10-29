from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import shutil,subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.docx_export import export_docx,W,R,RPKG
from backend.engine import DocumentError


def source(rotation=0,crop=False,kind='web'):
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((60,100),'Sitio oficial',fontsize=14,fontname='hebo',color=(.2,.4,.6));p.insert_text((60,160),'Texto ajeno')
        box=p.search_for('Sitio oficial')[0]
        if kind=='partial':box.x1=(box.x0+box.x1)/2
        link={'kind':f.LINK_URI,'from':box,'uri':'https://example.com/ruta?a=1&b=2'}
        if kind=='unsafe':link['uri']='file:///secret/file.txt'
        elif kind=='internal':link={'kind':f.LINK_GOTO,'from':box,'page':0}
        p.insert_link(link)
        if kind=='ambiguous':p.insert_link({'kind':f.LINK_URI,'from':box,'uri':'https://other.example.com'})
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation);return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_web_hyperlinks_keep_native_text_styles_xml_and_exact_external_target(rotation,crop):
    out,r=export_docx(source(rotation,crop),[],[0],include_links=True)
    assert r['links']==1 and not r['pages'][0]['links_skipped']
    with ZipFile(BytesIO(out)) as z:
        root=ET.fromstring(z.read('word/document.xml'));links=root.findall('.//{'+W+'}hyperlink');assert len(links)==1
        assert ''.join(links[0].itertext())=='Sitio oficial'
        assert links[0].find('.//{'+W+'}b') is not None
        rels=ET.fromstring(z.read('word/_rels/document.xml.rels'));rel=next(x for x in rels if x.attrib['Id']==links[0].attrib['{'+R+'}id'])
        assert rel.attrib['Target']=='https://example.com/ruta?a=1&b=2' and rel.attrib['TargetMode']=='External'
    # Independent OOXML reader must open and resolve the exported hyperlink.
    executable=shutil.which('python')
    if executable and subprocess.run([executable,'-c','import docx'],capture_output=True).returncode==0:
        check="from docx import Document;import sys;d=Document(sys.stdin.buffer);p=d.paragraphs[0];assert p.hyperlinks[0].url=='https://example.com/ruta?a=1&b=2';assert 'Sitio oficial' in p.text"
        # A seekable BytesIO is required by independent ZIP readers.
        check=check.replace('Document(sys.stdin.buffer)','Document(__import__("io").BytesIO(sys.stdin.buffer.read()))')
        subprocess.run([executable,'-c',check],input=out,check=True,capture_output=True)



@pytest.mark.parametrize('kind',['partial','unsafe','internal','ambiguous'])
def test_partial_unsafe_and_non_web_links_do_not_get_guessed(kind):
    out,r=export_docx(source(kind=kind),[],[0],include_links=True)
    assert r['links']==0 and r['pages'][0]['links_skipped']
    with ZipFile(BytesIO(out)) as z:assert not ET.fromstring(z.read('word/document.xml')).findall('.//{'+W+'}hyperlink')


def test_hyperlinks_remain_optional_and_boolean_option_is_validated():
    out,r=export_docx(source(),[],[0]);assert not r['links_enabled'] and r['links']==0
    with pytest.raises(DocumentError):export_docx(source(),[],[0],include_links=1)


def test_word_link_api_review_and_download():
    with TestClient(app) as c:
        d=c.post('/api/documents',files={'file':('links.pdf',source(),'application/pdf')}).json();url='/api/documents/'+d['id']+'/export-docx'
        payload={'pages':[0],'include_links':True}
        r=c.post(url,json=payload|{'review':True});assert r.status_code==200 and r.json()['links']==1
        r=c.post(url,json=payload);assert r.status_code==200 and r.content.startswith(b'PK')
