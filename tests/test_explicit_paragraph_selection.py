import pytest,pymupdf as f
from backend.affine_mixed_reflow import inspect_selection
from backend.affine_reflow import reflow
from backend.native_text import native_model
from backend.engine import DocumentError
from tests.test_multi_object_reflow import source as continuous
from backend.pdf_content import operations,patch


def source(rotation=0,form=False):
    with f.open(stream=continuous(rotation=rotation,form=form)) as d:
        for x in range(1,d.xref_length()):
            if d.xref_is_stream(x) and b'(HELLO )' in d.xref_stream(x):
                data=d.xref_stream(x);args=[a for op,a,_ in operations(data) if op=='Tm'][1];arg=args[4];d.update_stream(x,patch(data,[(arg.start,arg.end,str(arg.value+70).encode())]))
        return d.tobytes()


def refs(base):
    with f.open(stream=base) as d:
        d[0].set_rotation(0);_,rows=native_model(d,0,d[0].rect)
        rows=[r for r in rows if r['text'].strip() in ['HELLO','TEXT']];path=rows[0]['_native_path'];return [{'origin':r['origin'],'text':r['text']} for r in rows if r['_native_path']==path]


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('form',[False,True])
def test_explicit_gap_selection_and_apply_preserves_other_content(rotation,form):
    base=source(rotation,form);selection=refs(base);m=inspect_selection(base,[],0,selection);assert m['explicit_selection'] and len(m['ids'])==2
    runs=[{'id':r['id'],'text':r['text']} for r in m['runs']];out,_=reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),130,180,False,m['ids'],runs,True)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        a[0].set_rotation(0);b[0].set_rotation(0);assert a[0].search_for('NEIGHBOR UNCHANGED')==b[0].search_for('NEIGHBOR UNCHANGED')


def test_duplicates_stale_and_partial_objects_rejected():
    b=source();r=refs(b)
    for bad in [[],r+r,[{'origin':r[0]['origin'],'text':'STALE'}]]:
        with pytest.raises(DocumentError):inspect_selection(b,[],0,bad)
    from tests.test_affine_mixed_reflow import source as single
    b=single();r=refs(b)
    with pytest.raises(DocumentError,match='otros fragmentos'):inspect_selection(b,[],0,r[:1])


def test_selection_order_is_explicit_and_retained():
    base=source();s=refs(base);m=inspect_selection(base,[],0,list(reversed(s)))
    assert m['runs'][0]['text'].strip()==s[-1]['text'].strip()


def test_api_selection_references_are_validated():
    from fastapi.testclient import TestClient
    from backend.app import app
    b=source()
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('Original.pdf',b,'application/pdf')}).json();url='/api/documents/'+doc['id']+'/inline-block'
        r=c.post(url,json={'page':0,'selection':refs(b)});assert r.status_code==200 and r.json()['explicit_selection']
        assert c.post(url,json={'page':0,'selection':refs(b)*2}).status_code==422
