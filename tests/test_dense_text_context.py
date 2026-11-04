from collections import Counter
import pytest,pymupdf as f
from backend.engine import DocumentError
from backend.native_text import native_model,matching_traces,trace_index
from backend.affine_reflow import inspect,reflow
from backend.affine_mixed_reflow import inspect_selection


def source():
    with f.open() as d:
        p=d.new_page(width=600,height=800)
        for n in range(240):p.insert_text((30+(n//60)*140,30+(n%60)*12),f'ITEM-{n:03d}',fontsize=7)
        return d.tobytes()


def test_dense_context_retains_every_neighbor_without_relaxing_selection_limit():
    with f.open(stream=source()) as d:
        with pytest.raises(DocumentError,match='100 fragmentos'):native_model(d,0,d[0].rect)
        _,rows=native_model(d,0,d[0].rect,context=True);assert len(rows)==240 and all(r['editable'] for r in rows)
        anchor=rows[100];model=inspect(d,0,anchor['origin'],anchor['text']);assert 1<=len(model['ids'])<=100


def test_affine_reflow_on_a_dense_page_keeps_all_unselected_text_positions():
    base=source()
    with f.open(stream=base) as d:
        _,before=native_model(d,0,d[0].rect,context=True);row=before[100];rect=f.Rect(row['bbox']);box=[rect.x0,rect.y0,rect.width,rect.height]
    out,r=reflow(base,[],0,box,row['id'],'ITEM-001',80,20)
    with f.open(stream=out) as d:
        _,after=native_model(d,0,d[0].rect,context=True)
        stable=lambda x:(x['text'],tuple(round(v,2) for v in x['origin']))
        assert not (Counter(stable(v) for v in before if v['id']!=row['id'])-Counter(stable(v) for v in after))
    selected=inspect_selection(base,[],0,[{'origin':row['origin'],'text':row['text']}]);assert selected['explicit_selection']


@pytest.mark.parametrize('origin',[[1.019,2.019],[1.001,2.001],[-1.001,-2.001]])
def test_indexed_trace_lookup_matches_original_search_near_bucket_edges(origin):
    trace={'chars':[(ord('A'),1,tuple(origin),(0,0,1,1)),(ord('B'),2,(origin[0]+10,origin[1]),(0,0,1,1))]}
    for delta in [0,.019,-.019,.021]:
        point=[origin[0]+delta,origin[1]];assert matching_traces([trace],'AB',point,trace_index([trace]))==matching_traces([trace],'AB',point)


def test_a_discontinuous_large_text_object_opens_only_the_clicked_block():
    with f.open() as d:
        p=d.new_page();p.insert_font(fontname='helv');x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'BT /helv 14 Tf 1 0 0 1 50 700 Tm (ORIGINAL) Tj 1 0 0 1 300 400 Tm (NEIGHBOR) Tj ET');p.set_contents(x);base=d.tobytes()
        _,rows=native_model(d,0,p.rect,context=True);anchor=next(r for r in rows if r['text']=='ORIGINAL');m=inspect(d,0,anchor['origin'],anchor['text'])
    assert len(m['ids'])==1 and m['text']=='ORIGINAL' and m['complete_object_selection'] is False
    out,_=reflow(base,[],0,m['box'],m['ids'][0],'ORIGINA',m['local_width'],m['local_height'])
    with f.open(stream=out) as d:
        assert 'ORIGINA' in d[0].get_text() and d[0].search_for('NEIGHBOR')
