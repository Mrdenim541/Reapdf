from collections import Counter
import pytest,pymupdf as f
from backend.engine import DocumentError
from backend.native_text import native_model
from backend.styled_text import replace_styled
from backend.affine_mixed_reflow import stable_key


def source(relative=False):
    with f.open() as d:
        p=d.new_page();p.insert_text((50,100),'ORIGINAL',fontsize=14)
        if relative:
            x=p.get_contents()[0];d.update_stream(x,d.xref_stream(x).replace(b'ET',b'[(NEIGHBOR)] TJ ET'))
        else:p.insert_text((50,111),'NEIGHBOR',fontsize=14)
        return d.tobytes()


def payload(base):
    with f.open(stream=base) as d:
        _,rows=native_model(d,0,d[0].rect,context=True);r=next(r for r in rows if r['text']=='ORIGINAL');b=f.Rect(r['bbox']);return r,[b.x0,b.y0,b.width,b.height],rows


def test_native_edit_within_existing_overlapping_boxes_preserves_neighbor_geometry():
    base=source();row,box,before=payload(base);out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'ORIGINA'}])
    with f.open(stream=out) as d:
        _,after=native_model(d,0,d[0].rect,context=True)
        assert any(r['text']=='ORIGINA' for r in after)
        assert not (Counter(stable_key(r) for r in before if r['id']!=row['id'])-Counter(stable_key(r) for r in after))


def test_expansion_into_an_existing_overlapping_neighbor_is_still_rejected():
    base=source();row,box,_=payload(base);box[2]+=200
    with pytest.raises(DocumentError,match='cruza'):replace_styled(base,[],0,box,[{'id':row['id'],'text':'ORIGINAL ORIGINAL'}],True)


def test_inline_paragraph_falls_back_to_native_edit_on_dense_overlapping_boxes():
    from backend.original_reflow import inspect
    from backend.affine_reflow import reflow
    with f.open(stream=source()) as d:
        x=d[0].get_contents()[0];d.update_stream(x,b'/Span BMC '+d.xref_stream(x)+b' EMC');base=d.tobytes()
    row,box,before=payload(base);m=inspect(base,[],0,row['origin'],row['text'])
    assert m['affine'] and m['original_available']
    out,_=reflow(base,[],0,m['box'],m['ids'][0],'ORIGINA',m['local_width'],m['local_height'])
    with f.open(stream=out) as d:assert d[0].search_for('NEIGHBOR') and d[0].search_for('ORIGINA')
