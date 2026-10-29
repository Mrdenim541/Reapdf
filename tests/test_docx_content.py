"""Word media/table interoperability, fallback behavior and resource budgets."""
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import shutil,subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.docx_export import export_docx,W,R,A
from backend.engine import DocumentError


def illustrated(rotation=0,crop=False,alpha=False,table=True,image=True,text=True):
    with f.open() as d:
        p=d.new_page(width=500,height=650)
        if text:p.insert_text((40,60),'Informe de prueba',fontsize=14)
        if image:
            pix=f.Pixmap(f.csRGB,(0,0,60,40),alpha);pix.clear_with(180)
            if alpha:pix.set_alpha(bytes([128])*(pix.width*pix.height))
            p.insert_image(f.Rect(50,100,200,200),stream=pix.tobytes('png'),keep_proportion=False)
        if table:
            for x in [50,200,350]:p.draw_line((x,260),(x,350))
            for y in [260,290,320,350]:p.draw_line((50,y),(350,y))
            for y,row in zip([280,310,340],[['Concepto','Importe'],['Material','125'],['Mano de obra','250']]):
                for x,t in zip([60,210],row):p.insert_text((x,y),t,fontsize=10)
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation);d.new_page().insert_text((40,60),'Segunda pagina');return d.tobytes()


def inspect(data):
    with ZipFile(BytesIO(data)) as z:
        for name in z.namelist():
            if name.endswith(('.xml','.rels')):ET.fromstring(z.read(name))
        return ET.fromstring(z.read('word/document.xml')),{n:z.read(n) for n in z.namelist()}


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_images_and_tables_are_real_word_objects_without_duplicate_cell_text(rotation,crop):
    base=illustrated(rotation,crop);out,report=export_docx(base,[],[0,1],include_images=True,include_tables=True);root,files=inspect(out)
    assert report['images']==1 and report['tables']==1 and report['cells']==6
    assert not report['pages'][0]['images_skipped'] and not report['pages'][0]['tables_skipped']
    assert len(root.findall('.//{'+W+'}tbl'))==1 and len(root.findall('.//{'+W+'}tc'))==6
    texts=[n.text for n in root.findall('.//{'+W+'}t')];assert texts.count('Material')==1 and texts.count('250')==1
    assert 'Informe de prueba' in texts and 'Segunda pagina' in texts
    blip=root.find('.//{'+A+'}blip');assert blip.attrib['{'+R+'}embed']=='rIdImage1'
    assert len([n for n in files if n.startswith('word/media/')])==1
    assert b'rIdImage1' in files['word/_rels/document.xml.rels']
    with f.open(stream=base) as d:assert d[0].rotation==rotation


def test_native_jpeg_is_kept_without_reencoding_and_repeated_images_have_unique_relationships():
    pix=f.Pixmap(f.csRGB,(0,0,30,20),False);pix.clear_with(140);jpeg=pix.tobytes('jpeg')
    with f.open() as d:
        p=d.new_page();p.insert_text((40,60),'Fotografias')
        ref=p.insert_image(f.Rect(40,100,200,200),stream=jpeg)
        p.insert_image(f.Rect(40,250,200,350),xref=ref);base=d.tobytes()
    out,r=export_docx(base,[],[0],include_images=True);root,files=inspect(out)
    assert r['images']==2 and files['word/media/image1.jpeg']==jpeg and files['word/media/image2.jpeg']==jpeg
    assert {n.attrib['{'+R+'}embed'] for n in root.findall('.//{'+A+'}blip')}=={'rIdImage1','rIdImage2'}


def test_alpha_mask_is_retained_in_png_and_image_only_export_is_possible():
    base=illustrated(alpha=True,table=False,text=False);out,r=export_docx(base,[],[0],include_images=True);_,files=inspect(out)
    pix=f.Pixmap(files['word/media/image1.png']);assert pix.alpha and pix.samples[3]==128
    assert r['characters']==0 and r['images']==1
    with pytest.raises(DocumentError,match='OCR'):export_docx(base,[],[0])


@pytest.mark.parametrize('kind',['rotated','cropped','clip','layer'])
def test_incompatible_images_are_reported_and_source_text_survives(kind):
    with f.open(stream=illustrated(table=False)) as d:
        p=d[0]
        if kind=='rotated':
            p.delete_image(p.get_images()[0][0]);pix=f.Pixmap(f.csRGB,(0,0,20,40),False);pix.clear_with(100);p.insert_image(f.Rect(40,100,140,200),stream=pix.tobytes('png'),rotate=90)
        elif kind=='cropped':p.set_cropbox(f.Rect(100,0,500,650))
        elif kind=='clip':
            streams=p.get_contents();ref=streams[1];d.update_stream(ref,b'q 40 40 20 20 re W n '+d.xref_stream(ref)+b' Q')
        else:
            x=p.get_images()[0][0];d.xref_set_key(x,'OC','<< /Type /OCG /Name (Layer) >>')
        base=d.tobytes()
    out,r=export_docx(base,[],[0],include_images=True);root,_=inspect(out)
    assert r['images']==0 and r['pages'][0]['images_skipped'] and not root.findall('.//{'+W+'}drawing')


def test_merged_table_stays_plain_text_with_explicit_reason():
    with f.open() as d:
        p=d.new_page();p.insert_text((40,60),'Tabla irregular')
        for y in [100,140,180]:p.draw_line((40,y),(300,y))
        for x in [40,300]:p.draw_line((x,100),(x,180))
        p.draw_line((170,140),(170,180))
        for x,y,t in [(50,125,'Cabecera combinada'),(50,165,'A'),(180,165,'B')]:p.insert_text((x,y),t)
        base=d.tobytes()
    out,r=export_docx(base,[],[0],include_tables=True);root,_=inspect(out)
    assert r['tables']==0 and r['pages'][0]['tables_skipped'] and 'Cabecera combinada' in ''.join(root.itertext())


@pytest.mark.parametrize('budget,value,flag',[('MAX_IMAGES',0,'include_images'),('MAX_MEDIA_BYTES',1,'include_images'),('MAX_TABLES',0,'include_tables'),('MAX_CELLS',1,'include_tables')])
def test_content_limits_are_atomic(budget,value,flag,monkeypatch):
    monkeypatch.setattr('backend.docx_content.'+budget,value)
    with pytest.raises(DocumentError):export_docx(illustrated(),[],[0],**{flag:True})


def test_option_validation_permissions_and_tables_page_limit():
    base=illustrated()
    for opts in [{'include_images':1},{'include_tables':'yes'}]:
        with pytest.raises(DocumentError):export_docx(base,[],[0],**opts)
    with f.open() as d:
        for _ in range(21):d.new_page()
        many=d.tobytes()
    with pytest.raises(DocumentError,match='20 páginas'):export_docx(many,[],list(range(21)),include_tables=True)
    with f.open(stream=base) as d:restricted=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_PRINT)
    with pytest.raises(DocumentError):export_docx(restricted,[],[0],include_images=True,include_tables=True)


def test_independent_reader_opens_images_tables_and_sections(tmp_path):
    python=shutil.which('python')
    if not python or subprocess.run([python,'-c','import docx'],capture_output=True).returncode:pytest.skip('python-docx independiente no disponible')
    path=tmp_path/'illustrated.docx';path.write_bytes(export_docx(illustrated(),[],[0,1],include_images=True,include_tables=True)[0])
    subprocess.run([python,'-c',"from docx import Document;import sys;d=Document(sys.argv[1]);assert len(d.inline_shapes)==1 and len(d.tables)==1 and len(d.sections)==2;assert d.tables[0].cell(1,0).text=='Material';assert d.tables[0].cell(2,1).text=='250'",str(path)],check=True,capture_output=True)


def test_api_reports_cells_and_honors_download_options_without_changing_source():
    base=illustrated()
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('table.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        opts={'pages':[0],'include_images':True,'include_tables':True}
        review=client.post(url+'/export-docx',json=opts|{'review':True});assert review.status_code==200
        r=review.json();assert r['images']==1 and r['tables']==1 and r['pages'][0]['tables'][0]['rows'][1]==['Material','125']
        out=client.post(url+'/export-docx',json=opts);assert out.status_code==200;inspect(out.content)
        plain=client.post(url+'/export-docx',json={'pages':[0],'review':True}).json();assert plain['images']==0 and plain['tables']==0
