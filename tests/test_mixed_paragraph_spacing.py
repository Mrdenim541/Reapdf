import pytest,pymupdf as f
from backend.affine_mixed_reflow import inspect_selection
from backend.affine_reflow import reflow
from backend.native_text import native_model
from backend.engine import DocumentError
from tests.test_cross_path_reflow import source as original,refs


def source(matrix=(1,.25,.15,1),rotation=0,nested=False,char=1.2,word=3,kern=False):
    with f.open(stream=original(matrix,rotation,nested)) as d:
        for x in range(1,d.xref_length()):
            if not d.xref_is_stream(x):continue
            data=d.xref_stream(x)
            if b'(HELLO )' not in data and b'(TEXT)' not in data:continue
            data=data.replace(b'BT ',f'BT {char} Tc {word} Tw '.encode())
            if kern:data=data.replace(b'(HELLO ) Tj',b'[(HE) -60 (LLO )] TJ')
            d.update_stream(x,data)
        d.new_page(width=650,height=800);return d.tobytes()


def apply(base,continuation=False):
    m=inspect_selection(base,[],0,refs(base));runs=[{'id':r['id'],'text':'HELLO HELLO HELLO ' if i==0 else 'TEXT TEXT TEXT'} for i,r in enumerate(m['runs'])]
    return reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),140,40 if continuation else 200,False,m['ids'],runs,True,[{'page':2,'box':[30,80,530,600]}] if continuation else None)


@pytest.mark.parametrize('matrix',[(1,.25,.15,1),(0,1,-1,0),(-1,.1,.1,1)])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('nested',[False,True])
@pytest.mark.parametrize('char,word,kern',[(1.2,3,False),(-.3,2,False),(0,0,True)])
def test_reflow_preserves_tracking_word_spacing_and_adjacent_kerning(matrix,rotation,nested,char,word,kern):
    base=source(matrix,rotation,nested,char,word,kern);out,report=apply(base);assert report['preserves_spacing']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        a[0].set_rotation(0);b[0].set_rotation(0);assert a[0].search_for('NEIGHBOR UNCHANGED')==b[0].search_for('NEIGHBOR UNCHANGED')
        text=''.join(b[0].get_text().split());assert text.count('HELLO')==(4 if nested else 3) and text.count('TEXT')==(6 if nested else 4)
        _,rows=native_model(b,0,b[0].rect);edited=[r for r in rows if r['origin'][1]<650 and (r['text'].startswith('HELLO HELLO') or r['text'].startswith('TEXT TEXT'))]
        assert edited
        if kern:assert any(any(r['_spacing']['kern']) for r in rows if r['text'].startswith('HELLO'))


@pytest.mark.parametrize('char,word,kern',[(1.2,3,False),(-.3,2,False),(0,0,True)])
def test_continuation_uses_source_spacing_in_the_new_page(char,word,kern):
    base=source(char=char,word=word,kern=kern)
    m=inspect_selection(base,[],0,refs(base))
    with f.open(stream=base) as original:
        _,src=native_model(original,0,original[0].rect);expected={v['font']:v['_spacing']['state'] for v in src if v['id'] in m['ids']}
    out,r=apply(base,True);assert r['pages']==[0,2]
    with f.open(stream=out) as d:
        _,rows=native_model(d,2,d[2].rect);assert rows
        for row in rows:
            state=row['_spacing']['state'];assert state['char']==pytest.approx(expected[row['font']]['char'],abs=.001) and state['word']==pytest.approx(expected[row['font']]['word'],abs=.001)


def test_extreme_negative_tracking_refuses_inverted_advances():
    from backend.mixed_spacing import Layout
    base=source();m=inspect_selection(base,[],0,refs(base))
    with f.open(stream=base) as d:
        _,rows=native_model(d,0,d[0].rect);row=next(r for r in rows if r['id']==m['ids'][0]);row['_spacing']['state']['char']=-100
        with pytest.raises(DocumentError,match='avances'):Layout([row],[{'id':row['id'],'text':'HELLO'}])


def test_selected_first_fragment_retains_its_actual_tj_pair():
    import math
    base=source(char=0,word=0,kern=True);anchor=refs(base)[0]['origin'];out,_=apply(base)
    with f.open(stream=out) as d:
        _,rows=native_model(d,0,d[0].rect);first=next(r for r in rows if math.dist(r['origin'],anchor)<.02)
        assert first['text'].startswith('HELLO') and first['_spacing']['kern'][1]==pytest.approx(-60)


def test_large_kerning_comparison_is_bounded_before_sequence_matching():
    from backend.text_spacing import retained_kern
    row={'text':'AB'*2000,'_spacing':{'kern':[1.]*3999}}
    with pytest.raises(DocumentError,match='presupuesto'):retained_kern(row,'AB'*2000)
