"""Paragraph layout, independent page preservation, and public API contracts."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend.paragraphs import replace_paragraph, paragraph_blocks, inspect_paragraph

BOX=[30,50,430,130]

@pytest.fixture
def source():
    with f.open() as d:
        p=d.new_page(width=500,height=650)
        p.insert_text((40,80),'Texto original primera linea',fontsize=12)
        p.insert_text((40,100),'Segunda linea de prueba',fontsize=12)
        p.insert_text((40,400),'Conservar fuera del bloque',fontsize=12,fontname='tiro')
        d.new_page(width=500,height=650).insert_text((40,80),'Otra pagina intacta',fontsize=12)
        # Exercise font dictionaries and page resources shared across pages.
        kind,raw=d.xref_get_key(d[0].xref,'Resources')
        d.xref_set_key(d[1].xref,'Resources',raw)
        return d.tobytes()

@pytest.mark.parametrize('family',['sans','serif','mono'])
@pytest.mark.parametrize('style',['regular','bold','italic','bold-italic'])
def test_twelve_fonts_preserve_unicode_color_styles_and_other_page(source,family,style):
    out,report=replace_paragraph(source,[],0,BOX,'Edición: áñ αβ Привет',family=family,style=style,color=[.2,.4,.6],return_report=True)
    with f.open(stream=source) as before,f.open(stream=out) as after:
        assert before[1].get_pixmap().samples==after[1].get_pixmap().samples
        assert before[1].get_text()==after[1].get_text()
        assert 'Texto original' not in after[0].get_text()
        assert 'Conservar fuera del bloque' in after[0].get_text()
        spans=[s for b in after[0].get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'] if 'Edición' in s['text']]
        assert len(spans)==1
        span=spans[0];assert span['color']==0x336699 and span['size']==12
        assert bool(span['flags']&16)==('bold' in style)
        assert bool(span['flags']&2)==('italic' in style)
        assert (f.Rect(span['bbox'])&f.Rect(30,50,460,180)).get_area()>0
    assert report['size']==12 and not report['adjusted']


def test_auto_fit_reports_actual_size_never_enlarges_and_obeys_minimum(source):
    text='Un párrafo extenso que necesita redistribución. '*12
    with pytest.raises(DocumentError,match='cabe'):replace_paragraph(source,[],0,BOX,text,size=24)
    out,report=replace_paragraph(source,[],0,BOX,text,size=24,auto_fit=True,min_size=8,return_report=True)
    assert 8<=report['size']<24 and report['adjusted']
    with f.open(stream=out) as d:
        assert 'Un párrafo' in d[0].get_text()
        spans=[s for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['font'].startswith('DejaVu')]
        assert spans and all(abs(s['size']-report['size'])<.01 for s in spans)
        assert all(f.Rect(30,50,460,180).contains(f.Rect(s['bbox'])) for s in spans)
    with pytest.raises(DocumentError,match='cabe'):replace_paragraph(source,[],0,BOX,text,size=24,auto_fit=True,min_size=22)
    _,small=replace_paragraph(source,[],0,BOX,'Breve',size=10,auto_fit=True,return_report=True)
    assert small['size']==10


def test_interline_spacing_changes_geometry_and_preserves_explicit_paragraphs(source):
    outputs=[replace_paragraph(source,[],0,BOX,'Primera\nSegunda\n\nTercera',line_height=v) for v in [1,1.8]]
    origins=[]
    for data in outputs:
        with f.open(stream=data) as d:
            spans={s['text']:s for b in d[0].get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans']}
            assert all(t in spans for t in ['Primera','Segunda','Tercera'])
            origins.append([spans[t]['origin'][1] for t in ['Primera','Segunda','Tercera']])
    assert origins[1][1]-origins[1][0]>origins[0][1]-origins[0][0]
    assert origins[1][2]-origins[1][1]>origins[1][1]-origins[1][0]

@pytest.mark.parametrize('kwargs',[
 {'family':'../DejaVuSans'},{'family':[]},{'style':'unknown'},{'style':{}},
 {'line_height':0},{'line_height':2.6},{'line_height':True},{'line_height':float('nan')},
 {'auto_fit':1},{'auto_fit':'true'},{'min_size':5},{'min_size':True},{'size':12,'auto_fit':True,'min_size':13},
 {'text':'bad\x7f'},{'text':'bad\t'},{'text':'漢字'},{'color':[1,0,3]},
])
def test_invalid_options_fail_without_mutating_source(source,kwargs):
    before=hashlib.sha256(source).digest()
    with pytest.raises(DocumentError):replace_paragraph(source,[],0,BOX,**({'text':'Nuevo'}|kwargs))
    assert hashlib.sha256(source).digest()==before


def test_detection_returns_complete_selectable_boxes_and_respects_operations(source):
    result=paragraph_blocks(source,[],0)
    assert len(result['blocks'])>=2
    for b in result['blocks']:
        model=inspect_paragraph(source,[],0,b['box']);assert model['text'].startswith(b['text'])
    assert any('Conservar fuera' in b['text'] for b in result['blocks'])
    with f.open(stream=source) as d:
        p=d[0];p.set_rotation(90);rotated=d.tobytes()
    assert paragraph_blocks(rotated,[],0)==paragraph_blocks(source,[],0)
    with pytest.raises(DocumentError):paragraph_blocks(source,[],True)


def test_empty_text_removes_only_region(source):
    out=replace_paragraph(source,[],0,BOX,'',family='serif',style='bold')
    with f.open(stream=out) as d:
        assert 'Texto original' not in d[0].get_text() and 'Conservar fuera' in d[0].get_text()
        assert 'Otra pagina' in d[1].get_text()


def test_api_preview_is_read_only_and_replays_identical_layout(source):
    with TestClient(app) as client:
        uploaded=client.post('/api/documents',files={'file':('paragraph.pdf',source,'application/pdf')})
        assert uploaded.status_code==200,uploaded.text
        doc=uploaded.json();url='/api/documents/'+doc['id']
        detected=client.post(url+'/paragraph-blocks',json={'page':0,'operations':[]})
        assert detected.status_code==200 and detected.json()['blocks']
        payload={'page':0,'box':BOX,'text':'Nuevo párrafo de prueba. '*20,'family':'serif','style':'bold-italic','size':28,'auto_fit':True,'min_size':7,'line_height':1.4,'color':[.1,.2,.3]}
        preview=client.post(url+'/replace-paragraph',json=payload|{'preview':True})
        assert preview.status_code==200,preview.text[:500]
        report=json.loads(preview.headers['X-Reapdf-Layout']);assert report['adjusted']
        assert preview.content.startswith(b'\x89PNG')
        unchanged=client.post(url+'/inspect-paragraph',json={'page':0,'box':BOX})
        assert 'Texto original' in unchanged.json()['text']
        applied=client.post(url+'/replace-paragraph',json=payload)
        assert applied.status_code==200 and applied.json()['id']!=doc['id']


def test_poppler_sees_unicode_and_preserves_other_page(source,tmp_path):
    if not shutil.which('pdftotext') or not shutil.which('pdftoppm'):pytest.skip('Poppler no disponible')
    new=replace_paragraph(source,[],0,BOX,'Edición áñ αβ Привет',family='serif',style='bold-italic')
    a=tmp_path/'before.pdf';b=tmp_path/'after.pdf';a.write_bytes(source);b.write_bytes(new)
    text=subprocess.check_output(['pdftotext',str(b),'-']).decode()
    assert 'Edición áñ αβ Привет' in text and 'Texto original' not in text and 'Otra pagina intacta' in text
    pixels=[]
    for path in [a,b]:
        prefix=str(path)+'.render'
        subprocess.run(['pdftoppm','-f','2','-l','2','-scale-to','700','-singlefile','-png',str(path),prefix],check=True,capture_output=True)
        pixels.append(Path(prefix+'.png').read_bytes())
    assert pixels[0]==pixels[1]


def test_bundled_font_manifest_hashes_and_license():
    root=Path(__file__).resolve().parent.parent/'resources/fonts'
    manifest=json.loads((root/'manifest.json').read_text());assert len(manifest['files'])==12
    assert (root/manifest['license']).is_file()
    for row in manifest['files']:assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest()==row['sha256']
