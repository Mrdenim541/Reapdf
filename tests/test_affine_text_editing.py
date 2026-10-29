from pathlib import Path
import math,re
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError,spans
from backend.styled_text import inspect_styled,replace_styled,replace_styled_regions
from backend.affine_text import frame,contains,overlap,rectangle,bounds
from backend.paragraphs import replace_paragraph
from tests.test_cff_forms_mixed import cff_pdf

MATRICES=[(0,1,-1,0),(0,-1,1,0),(-1,0,0,-1),(-1,0,0,1),(1,0,0,-1),(1,.3,.2,1),(.7,.3,.2,1.4),(.70710678,.70710678,-.70710678,.70710678),(1,0,.6,1)]
FONT=Path(__file__).resolve().parents[1]/'resources/fonts/DejaVuSans.ttf'


def original(kind):
    if kind in ['cff','cid']:return cff_pdf('cid' if kind=='cid' else 'open')
    with f.open() as d:
        p=d.new_page()
        if kind=='ttf':p.insert_font(fontname='Original',fontfile=str(FONT))
        p.insert_text((40,100),'HELLO TEXT',fontname='Original' if kind=='ttf' else 'helv',fontsize=18);p.insert_text((40,300),'UNCHANGED');return d.tobytes()


def source(linear=MATRICES[5],kind='base',mode='form',rotation=0,crop=False,clipped=False):
    a,b,c,d=linear
    with f.open(stream=original(kind)) as src:
        sp=src[0];origin=next(s['origin'] for bl in sp.get_text('dict')['blocks'] for l in bl.get('lines',[]) for s in l['spans'] if s['text']=='HELLO TEXT');ox,oy=f.Point(origin)*~sp.transformation_matrix
        e=200-a*ox-c*oy;g=800-b*ox-d*oy
        if mode=='form':
            with f.open() as out:
                page=out.new_page(width=800,height=1000);page.show_pdf_page(sp.rect,src,0)
                wrapper=next(x for x in page.get_xobjects() if x[2]==0)[0];out.xref_set_key(wrapper,'Matrix',f'[{a} {b} {c} {d} {e} {g}]')
                if clipped:out.xref_set_key(wrapper,'BBox',f'[0 {oy-3} {sp.rect.width} {sp.rect.height}]')
                page.show_pdf_page(f.Rect(450,700,450+sp.rect.width*.4,700+sp.rect.height*.4),src,0)
                other=out.new_page();other.show_pdf_page(other.rect,src,0)
                if crop:page=out[0];page.set_cropbox(f.Rect(10,15,790,985))
                out[0].set_rotation(rotation);return out.tobytes()
        sp.set_mediabox(f.Rect(0,0,800,1000));stream=sp.get_contents()[0];content=src.xref_stream(stream)
        if mode=='tm':
            content,count=re.subn(rb'1 0 0 1 [-.0-9]+ [-.0-9]+ Tm',f'{a} {b} {c} {d} 200 800 Tm'.encode(),content,count=1);assert count==1
        else:content=f'q {a} {b} {c} {d} {e} {g} cm '.encode()+content+b' Q'
        src.update_stream(stream,content);src.new_page().insert_text((40,80),'OTHER PAGE')
        if crop:src[0].set_cropbox(f.Rect(10,15,790,985))
        src[0].set_rotation(rotation);return src.tobytes()


def box_for(data,text='HELLO TEXT',index=0):
    with f.open(stream=data) as doc:
        p=doc[0];p.set_rotation(0);span=[s for b in p.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'] if s['text']==text][index];r=f.Rect(span['bbox']);return [r.x0,r.y0,r.width,r.height]


@pytest.mark.parametrize('linear',MATRICES)
@pytest.mark.parametrize('mode',['form','direct','tm'])
@pytest.mark.parametrize('kind',['base','ttf','cff','cid'])
def test_affine_original_program_codes_matrix_neighbors_and_other_page(linear,mode,kind):
    base=source(linear,kind,mode);box=box_for(base);row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason'];assert row['transformed']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEX'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert 'HELLO TEX' in b[0].get_text() and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert b[0].get_text().count('HELLO TEXT')==(1 if mode=='form' else 0)
        assert a[0].search_for('UNCHANGED')==b[0].search_for('UNCHANGED')
        left={v[3]:a.extract_font(v[0])[3] for v in a[0].get_fonts()};right={v[3]:b.extract_font(v[0])[3] for v in b[0].get_fonts()};assert left==right
        # The matrices themselves stay in the original streams/objects. Editing
        # replaces only selected show operands and the isolated invocation path.
        if mode!='form':
            from backend.pdf_content import operations
            left=[(op,[t.value for t in args]) for op,args,_ in operations(a[0].read_contents()) if op in ['cm','Tm']];right=[(op,[t.value for t in args]) for op,args,_ in operations(b[0].read_contents()) if op in ['cm','Tm']];assert left==right


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
@pytest.mark.parametrize('linear',[MATRICES[3],MATRICES[5],MATRICES[7]])
def test_affine_page_rotations_crop_targets_and_export(rotation,crop,linear):
    base=source(linear,rotation=rotation,crop=crop);box=box_for(base);row=inspect_styled(base,[],0,box)['runs'][0];out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEX'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].rotation==b[0].rotation and a[0].cropbox==b[0].cropbox
        selected=[s for s in spans(a[0]) if s['text']=='HELLO TEXT'][0];assert selected['transformed'] and len(selected['quad'])==4
        assert a[0].rotation==rotation


def test_original_cells_respect_tilted_form_clip_and_partial_source_is_readonly():
    base=source(MATRICES[7],clipped=True);box=box_for(base);row=inspect_styled(base,[],0,box)['runs'][0];assert not row['editable'] and 'recorte' in row['reason']
    with pytest.raises(DocumentError):replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEX'}])


def test_small_neighbor_in_empty_bbox_corner_does_not_block_native_edit():
    base=source(MATRICES[7],mode='direct')
    with f.open(stream=base) as doc:
        p=doc[0];p.insert_text((187,116),'I',fontsize=4);base=doc.tobytes()
    box=box_for(base);row=next(r for r in inspect_styled(base,[],0,box)['runs'] if r['text']=='HELLO TEXT');assert row['editable']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEX'}])
    with f.open(stream=out) as d:assert 'I' in d[0].get_text()


def test_actual_neighbor_collision_growth_and_paragraph_substitution_rejected():
    base=source(MATRICES[-1],mode='direct');box=box_for(base);row=inspect_styled(base,[],0,box)['runs'][0]
    with pytest.raises(DocumentError,match='ancho'):replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEXT LONG'}])
    with pytest.raises(DocumentError,match='geometría'):replace_paragraph(base,[],0,box,'NEW TEXT')
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':''}])
    with f.open(stream=out) as d:assert 'HELLO TEXT' not in d[0].get_text()


def test_singular_matrices_and_convex_corner_checks():
    for values in [(1,0,0,0,0,0),(1,0,1000,1,0,0),(1e-8,0,0,1e-8,0,0)]:
        with pytest.raises(DocumentError):frame(f.Matrix(*values),f.Point(0,0))
    assert not contains([[0,0]]*4,[[1,1]])
    diamond=[[0,5],[5,0],[10,5],[5,10]];corner=rectangle(f.Rect(0,0,1,1));assert not contains(diamond,corner) and overlap(diamond,corner)==0


def test_affine_api_inspect_apply_preview_and_base_unchanged():
    base=source(MATRICES[5]);box=box_for(base)
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('affine.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id'];rows=c.post(url+'/inspect-styled-text',json={'page':0,'box':box}).json()['runs'];payload={'page':0,'box':box,'changes':[{'id':rows[0]['id'],'text':'HELLO TEX'}]}
        assert c.post(url+'/replace-styled-text',json={**payload,'preview':True}).status_code==200
        assert c.post(url+'/replace-styled-text',json=payload).status_code==200
        assert c.post(url+'/export',json={'operations':[]}).content==base


def test_expansion_along_reflected_baseline_and_new_image_collision():
    base=source(MATRICES[3],mode='direct');area=[0,100,400,200];row=next(r for r in inspect_styled(base,[],0,area)['runs'] if r['text']=='HELLO TEXT')
    out=replace_styled(base,[],0,area,[{'id':row['id'],'text':'HELLO TEXT TEXT'}],True)
    with f.open(stream=out) as doc:assert 'HELLO TEXT TEXT' in doc[0].get_text()
    with f.open(stream=base) as doc:
        p=doc[0];pix=f.Pixmap(f.csRGB,f.IRect(0,0,10,10),False);pix.clear_with(100);p.insert_image(f.Rect(45,185,75,205),pixmap=pix);blocked=doc.tobytes()
    row=next(r for r in inspect_styled(blocked,[],0,area)['runs'] if r['text']=='HELLO TEXT');assert row['editable']
    with pytest.raises(DocumentError,match='imagen'):replace_styled(blocked,[],0,area,[{'id':row['id'],'text':'HELLO TEXT TEXT'}],True)


def test_overlap_with_actual_neighbor_rejected():
    base=source(MATRICES[5],mode='direct')
    with f.open(stream=base) as doc:
        p=doc[0];p.insert_text((220,190),'COLLISION',fontsize=10);base=doc.tobytes()
    box=box_for(base);rows=inspect_styled(base,[],0,box)['runs'];row=next(r for r in rows if r['text']=='HELLO TEXT')
    with pytest.raises(DocumentError,match='otro fragmento'):replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEX'}])


def test_batch_two_affine_occurrences_is_atomic_and_isolated():
    base=source(MATRICES[5]);regions=[]
    for index,text in [(0,'HELLO TEX'),(1,'HELLO TE')]:
        box=box_for(base,index=index);row=inspect_styled(base,[],0,box)['runs'][0];regions.append({'page':0,'box':box,'changes':[{'id':row['id'],'text':text}]})
    out=replace_styled_regions(base,[],regions)
    with f.open(stream=out) as doc,f.open(stream=base) as old:
        assert 'HELLO TEX' in doc[0].get_text() and 'HELLO TE' in doc[0].get_text();assert doc[1].get_pixmap().samples==old[1].get_pixmap().samples
    regions[-1]['changes'][0]['text']='W'*100
    with pytest.raises(DocumentError):replace_styled_regions(base,[],regions)


def test_unparsed_inline_image_does_not_enable_untransformed_redaction_fallback():
    base=source(MATRICES[4],mode='direct')
    with f.open(stream=base) as doc:
        page=doc[0];xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,b'q 10 0 0 10 600 800 cm BI /W 1 /H 1 /BPC 8 /CS /RGB ID \xff\x00\x00 EI Q');doc.xref_set_key(page.xref,'Contents','['+' '.join(f'{n} 0 R' for n in page.get_contents()+[xref])+']');base=doc.tobytes()
    box=box_for(base)
    with pytest.raises(DocumentError):inspect_styled(base,[],0,box)
    with pytest.raises(DocumentError,match='geometría'):replace_paragraph(base,[],0,box,'NEW TEXT')
