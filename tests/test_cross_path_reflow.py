"""Explicit edits across separate Form appearances, with copy-on-write checks."""
import pytest,pymupdf as f
from backend.affine_mixed_reflow import inspect_selection
from backend.affine_reflow import reflow
from backend.native_text import native_model
from backend.engine import DocumentError


def source(matrix=(1,.25,.15,1),rotation=0,nested=False,partial=False,clip=False):
    with f.open() as d:
        p=d.new_page(width=650,height=800);p.insert_font(fontname='hebo');p.insert_font(fontname='heit');p.insert_text((30,740),'NEIGHBOR UNCHANGED')
        resource=d.xref_get_key(p.xref,'Resources')[1];m=f.Matrix(*matrix,300,400);point=f.Point(130,0)*m
        forms=[]
        for i,(font,size,text,color,pos) in enumerate([('hebo',18,'HELLO ','.8 0 0',m),('heit',14,'TEXT','0 0 .8',f.Matrix(*matrix,point.x,point.y))]):
            box='[400 300 600 500]' if clip and i==1 else '[0 0 650 800]'
            x=d.get_new_xref();d.update_object(x,f'<< /Type/XObject /Subtype/Form /BBox {box} /Resources {resource} >>')
            extra=' 1 0 0 1 200 300 Tm (EXTRA) Tj' if partial and i==1 else ''
            d.update_stream(x,(f'q BT /{font} {size} Tf {color} rg '+' '.join(map(str,pos))+' Tm ('+text+') Tj'+extra+' ET Q').encode());forms.append(x)
        d.xref_set_key(int(resource.split()[0]),'XObject',f'<< /A {forms[0]} 0 R /B {forms[1]} 0 R >>')
        x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'q /A Do /B Do 1 0 0 1 0 -250 cm /B Do Q');d.xref_set_key(p.xref,'Contents','['+' '.join(f'{r} 0 R' for r in p.get_contents()+[x])+']')
        p.set_rotation(rotation);d.new_page().insert_text((30,40),'OTHER PAGE UNCHANGED');base=d.tobytes()
    if not nested:return base
    with f.open(stream=base) as a,f.open() as d:
        a[0].set_rotation(0);p=d.new_page(width=1000,height=1300);p.show_pdf_page(f.Rect(0,0,650,800),a,0);p.show_pdf_page(f.Rect(550,700,875,1100),a,0);d.new_page().show_pdf_page(f.Rect(0,0,650,800),a,0);d[0].set_rotation(rotation);return d.tobytes()


def refs(base):
    with f.open(stream=base) as d:
        d[0].set_rotation(0);_,rows=native_model(d,0,d[0].rect)
        a=next(r for r in rows if r['text']=='HELLO ');b=next(r for r in rows if r['text']=='TEXT')
        return [{'origin':r['origin'],'text':r['text']} for r in [a,b]]


def apply(base,preview=False):
    m=inspect_selection(base,[],0,refs(base));assert m['source_paths']==2 and m['explicit_selection']
    runs=[{'id':r['id'],'text':'HELLO HELLO ' if i==0 else 'TEXT TEXT'} for i,r in enumerate(m['runs'])]
    return reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),130,180,preview,m['ids'],runs,True)


@pytest.mark.parametrize('matrix',[(1,.25,.15,1),(0,1,-1,0),(-1,.1,.1,1),(1.4,.3,.2,.7)])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('nested',[False,True])
def test_separate_paths_reflow_preserves_shared_appearances_and_styles(matrix,rotation,nested):
    base=source(matrix,rotation,nested);out,report=apply(base);assert report['source_paths']==2 and report['source_objects']==2
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].rotation==b[0].rotation and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        a[0].set_rotation(0);b[0].set_rotation(0)
        for label in ['NEIGHBOR UNCHANGED','TEXT']:
            # Existing unselected TEXT appearances remain at their exact origins.
            for rect in a[0].search_for(label)[1 if label=='TEXT' else 0:]:assert rect in b[0].search_for(label)
        expected={(s['font'],round(s['size'],3),s['color']) for block in a[0].get_text('dict')['blocks'] for l in block.get('lines',[]) for s in l['spans'] if s['font'] in ['Helvetica-Bold','Helvetica-Oblique']}
        actual={(s['font'],round(s['size'],3),s['color']) for block in b[0].get_text('dict')['blocks'] for l in block.get('lines',[]) for s in l['spans'] if s['font'] in ['Helvetica-Bold','Helvetica-Oblique']};assert expected==actual
        text=''.join(b[0].get_text().split());assert text.count('HELLO')==(3 if nested else 2) and text.count('TEXT')==(5 if nested else 3)


def test_explicit_path_order_and_preview():
    base=source();m=inspect_selection(base,[],0,list(reversed(refs(base))));assert m['runs'][0]['text'].startswith('TEXT')
    assert apply(base,True)['source_paths']==2


def test_partial_second_form_object_is_not_implicitly_selected():
    base=source(partial=True)
    with pytest.raises(DocumentError,match='otros fragmentos'):inspect_selection(base,[],0,refs(base))


def test_different_paths_require_explicit_apply():
    base=source();m=inspect_selection(base,[],0,refs(base));runs=[{'id':r['id'],'text':r['text']} for r in m['runs']]
    with pytest.raises(DocumentError,match='selección explícita'):reflow(base,[],0,m['box'],m['ids'][0],m['text'],130,180,False,m['ids'],runs)


def test_cross_path_api_roundtrip():
    from fastapi.testclient import TestClient
    from backend.app import app
    base=source()
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('forms.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id'];m=c.post(url+'/inline-block',json={'page':0,'selection':refs(base)}).json()
        payload={'page':0,'box':m['box'],'id':m['ids'][0],'ids':m['ids'],'text':m['text'],'runs':[{'id':r['id'],'text':r['text']} for r in m['runs']],'width':130,'height':180,'explicit_order':True}
        edited=c.post(url+'/reflow-affine',json=payload);assert edited.status_code==200 and edited.json()['reflow_report']['source_paths']==2
        export=c.post('/api/documents/'+edited.json()['id']+'/export',json={'operations':[]});assert export.status_code==200
        with f.open(stream=export.content) as d:assert len(d)==2


@pytest.mark.parametrize('nested',[False,True])
def test_page_and_form_or_ancestor_and_descendant_paths(nested):
    with f.open(stream=source(matrix=(1,0,0,1))) as d:
        p=d[0];x=p.get_contents()[-1];data=d.xref_stream(x);form=int(d.xref_get_key(p.xref,'Resources/XObject/A')[1].split()[0]);d.update_stream(x,data.replace(b'/A Do',d.xref_stream(form)));base=d.tobytes()
    if nested:
        with f.open(stream=base) as a,f.open() as d:
            p=d.new_page(width=650,height=800);p.show_pdf_page(p.rect,a,0);d.new_page().insert_text((30,40),'OTHER PAGE UNCHANGED');base=d.tobytes()
    out,report=apply(base);assert report['source_paths']==2
    with f.open(stream=out) as d:assert d[0].get_text().count('HELLO')==2 and d[0].get_text().count('TEXT')==3


def test_cross_path_reflow_keeps_each_original_clip():
    with f.open(stream=source(matrix=(1,0,0,1))) as d:
        target=int(d.xref_get_key(d[0].xref,'Resources/XObject/B')[1].split()[0]);d.xref_set_key(target,'BBox','[400 0 650 800]');base=d.tobytes()
    with pytest.raises(DocumentError,match='recorte'):apply(base)
