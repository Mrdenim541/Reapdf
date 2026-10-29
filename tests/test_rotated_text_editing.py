"""Text editing keeps page rotation, CropBox, native geometry and other pages."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend.paragraphs import inspect_paragraph,replace_paragraph,paragraph_blocks,paragraph_preview
from backend.styled_text import inspect_styled,replace_styled

BOX=[10,20,440,140]
FONT=Path(__file__).resolve().parent.parent/'resources/fonts/DejaVuSans.ttf'


def source(rotation=0,crop=False,embedded=False):
    with f.open() as d:
        p=d.new_page(width=500,height=650)
        if embedded:p.insert_font(fontname='Original',fontfile=str(FONT))
        p.insert_text((40,80),'Texto digital original largo',fontname='Original' if embedded else 'hebo',fontsize=14,color=(.2,.4,.6))
        p.insert_text((40,400),'Fuera del bloque',fontname='tiro',fontsize=12)
        p.draw_rect(f.Rect(30,350,400,450),color=(.2,.5,.4))
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation)
        d.new_page(width=500,height=650).insert_text((40,80),'Otra pagina',fontname='hebo')
        if embedded:d.subset_fonts()
        return d.tobytes()


def change(data,mode):
    if mode=='paragraph':return replace_paragraph(data,[],0,BOX,'Edición áñ αβ',size=13,family='serif',style='bold-italic',color=[.2,.4,.6])
    row=inspect_styled(data,[],0,BOX)['runs'][0]
    assert row['editable']
    return replace_styled(data,[],0,BOX,[{'id':row['id'],'text':'Texto original'}])


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
@pytest.mark.parametrize('mode',['paragraph','styled','embedded'])
def test_rotation_crop_and_pixels_match_an_independently_rotated_edit(rotation,crop,mode):
    base=source(rotation,crop,mode=='embedded');out=change(base,mode)
    reference=change(source(0,crop,mode=='embedded'),mode)
    with f.open(stream=base) as before,f.open(stream=out) as after,f.open(stream=reference) as expected:
        expected[0].set_rotation(rotation)
        assert after[0].rotation==rotation and after[0].cropbox==before[0].cropbox and after[0].mediabox==before[0].mediabox
        assert after[0].get_pixmap(matrix=f.Matrix(1.5,1.5)).samples==expected[0].get_pixmap(matrix=f.Matrix(1.5,1.5)).samples
        assert after[1].get_pixmap().samples==before[1].get_pixmap().samples
        assert after[1].get_text()==before[1].get_text()
        assert 'Fuera del bloque' in after[0].get_text() and 'Texto digital original largo' not in after[0].get_text()
        if mode!='paragraph':
            a=inspect_styled(base,[],0,BOX)['runs'][0];b=inspect_styled(out,[],0,BOX)['runs'][0]
            assert all(a[key]==b[key] for key in ['font','size','color','origin'])
            fonts=lambda d:{hashlib.sha256(d.extract_font(row[0])[3]).hexdigest() for row in d[0].get_fonts() if row[1]=='ttf'}
            assert fonts(before)==fonts(after)


@pytest.mark.parametrize('rotation',[90,180,270])
def test_detection_and_normalized_preview_share_original_coordinates(rotation):
    zero=source();rotated=source(rotation)
    assert paragraph_blocks(zero,[],0)==paragraph_blocks(rotated,[],0)
    a,ha=paragraph_preview(zero,[],0);b,hb=paragraph_preview(rotated,[],0)
    assert a==b and hb['X-Page-Rotation']==str(rotation) and ha['X-Page-Rotation']=='0'
    for block in paragraph_blocks(rotated,[],0)['blocks']:
        assert inspect_paragraph(rotated,[],0,block['box'])['text'].startswith(block['text'])


def test_inferred_format_reports_first_span_and_mixed_styles():
    base=source(90)
    model=inspect_paragraph(base,[],0,BOX)
    assert model['format']=={'size':14.0,'family':'sans','style':'bold','color':'#336699','mixed':False}
    assert model['rotation']==90
    model=inspect_paragraph(base,[],0,[10,20,440,430])
    assert model['format']['mixed'] and model['format']['style']=='bold'


@pytest.mark.parametrize('page',[True,-1,2,None,'0'])
def test_normalized_preview_validates_page(page):
    with pytest.raises(DocumentError):paragraph_preview(source(),[],page)


@pytest.mark.parametrize('mode',['paragraph','styled'])
def test_rotated_page_cannot_bypass_overlap_or_unsupported_content(mode):
    with f.open(stream=source(270)) as d:
        p=d[0];p.add_text_annot((50,75),'Nota en el bloque');data=d.tobytes()
    with pytest.raises(DocumentError,match='anotaciones'):change(data,mode)


def test_api_previews_enderezadas_and_applied_rotation_is_retained():
    with TestClient(app) as client:
        base=source(270,True)
        doc=client.post('/api/documents',files={'file':('rotated.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        initial=client.post(url+'/paragraph-preview',json={'page':0})
        assert initial.status_code==200 and initial.headers['X-Page-Rotation']=='270'
        rows=client.post(url+'/inspect-styled-text',json={'page':0,'box':BOX}).json()['runs']
        for route,payload in [('replace-paragraph',{'text':'Nuevo texto','size':14}),('replace-styled-text',{'changes':[{'id':rows[0]['id'],'text':'Texto original'}]})]:
            request={'page':0,'box':BOX}|payload
            preview=client.post(url+'/'+route,json=request|{'preview':True})
            assert preview.status_code==200 and preview.headers['X-Page-Rotation']=='270'
            result=client.post(url+'/'+route,json=request)
            assert result.status_code==200 and result.json()['pages'][0]['rotation']==270
        assert client.post(url+'/inspect-paragraph',json={'page':0,'box':BOX}).json()['text']=='Texto digital original largo'


@pytest.mark.parametrize('rotation',[90,180,270])
def test_poppler_sees_rotated_edits_and_preserves_other_page(rotation,tmp_path):
    if not shutil.which('pdftoppm') or not shutil.which('pdftotext'):pytest.skip('Poppler no disponible')
    base=source(rotation,True,True);out=change(base,'embedded')
    before=tmp_path/'before.pdf';after=tmp_path/'after.pdf';before.write_bytes(base);after.write_bytes(out)
    text=subprocess.check_output(['pdftotext','-layout',str(after),'-']).decode()
    assert 'Texto original' in text and 'Texto digital original largo' not in text and 'Otra pagina' in text
    pixels=[]
    for p in [before,after]:
        prefix=str(p)+'.render'
        subprocess.run(['pdftoppm','-f','2','-l','2','-scale-to','700','-singlefile','-png',str(p),prefix],check=True,capture_output=True)
        pixels.append(Path(prefix+'.png').read_bytes())
    assert pixels[0]==pixels[1]
