import pytest,pymupdf as f
from backend.affine_reflow import reflow
from backend.engine import DocumentError
from tests.test_affine_mixed_reflow import source as single,model


def source(matrix=(1,.25,.15,1),rotation=0,form=False):
    with f.open(stream=single(matrix,rotation,form)) as d:
        for x in range(1,d.xref_length()):
            if d.xref_is_stream(x):
                data=d.xref_stream(x)
                if b'(HELLO ) Tj /heit' in data:d.update_stream(x,data.replace(b'(HELLO ) Tj /heit',b'(HELLO ) Tj ET BT /heit'))
        return d.tobytes()


@pytest.mark.parametrize('matrix',[(1,.25,.15,1),(0,1,-1,0),(-1,.1,.1,1),(1.4,.3,.2,.7)])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('form',[False,True])
def test_native_reflow_across_objects_preserves_other_content(matrix,rotation,form):
    from backend.native_text import native_model
    base=source(matrix,rotation,form);m=model(base);assert m['mixed'] and len(m['runs'])==2
    with f.open(stream=base) as d:
        d[0].set_rotation(0);_,rows=native_model(d,0,d[0].rect);assert len({r['_text_object'] for r in rows if r['id'] in m['ids']})==2
    runs=[{'id':r['id'],'text':'HELLO HELLO ' if i==0 else 'TEXT TEXT'} for i,r in enumerate(m['runs'])]
    out,report=reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),130,180,False,m['ids'],runs)
    assert report['mixed'] and report['source_objects']==2
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].get_text().count('HELLO')==(3 if form else 2) and b[0].get_text().count('TEXT')==(3 if form else 2)
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples and a[0].rotation==b[0].rotation
        a[0].set_rotation(0);b[0].set_rotation(0);assert a[0].search_for('NEIGHBOR UNCHANGED')==b[0].search_for('NEIGHBOR UNCHANGED')
        styles=lambda d:{(s['font'],round(s['size'],3),s['color']) for block in d[0].get_text('dict')['blocks'] for line in block.get('lines',[]) for s in line['spans'] if s['font'] in ['Helvetica-Bold','Helvetica-Oblique']}
        assert styles(a)==styles(b)


def test_partial_object_is_still_rejected():
    # First object has an additional style outside the requested selection.
    from tests.test_affine_mixed_reflow import source,model
    base=source();m=model(base);runs=[{'id':m['ids'][0],'text':'HELLO'}]
    with pytest.raises(DocumentError):reflow(base,[],0,m['box'],m['ids'][0],'HELLO',130,180,False,m['ids'][:1],runs)


def test_horizontal_shared_form_crosses_objects():
    base=source((1,0,0,1),form=True);m=model(base);assert len(m['runs'])==2 and m['affine']
    runs=[{'id':r['id'],'text':r['text']} for r in m['runs']];out,r=reflow(base,[],0,m['box'],m['ids'][0],''.join(v['text'] for v in runs),130,180,False,m['ids'],runs);assert r['source_objects']==2


def test_gap_does_not_automatically_join_unrelated_labels():
    from backend.pdf_content import operations,patch
    with f.open(stream=source()) as d:
        x=d[0].get_contents()[-1];data=d.xref_stream(x);args=[a for op,a,_ in operations(data) if op=='Tm'][1];arg=args[4];d.update_stream(x,patch(data,[(arg.start,arg.end,str(arg.value+70).encode())]));base=d.tobytes()
    m=model(base);assert len(m['ids'])==1
