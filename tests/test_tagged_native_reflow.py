import pytest,pymupdf as f
from backend.engine import DocumentError
from backend.native_text import native_model
from backend.original_reflow import inspect
from backend.affine_reflow import reflow
from backend.styled_text import replace_styled
from backend.tagged_text_integrity import snapshot
from backend.structure_editing import model
from tests.test_structure_scope import source


def payload(base):
    with f.open(stream=base) as d:
        _,rows=native_model(d,0,d[0].rect,context=True);anchor=next(r for r in rows if r['editable'] and len(r['text'])>3)
    return anchor,inspect(base,[],0,anchor['origin'],anchor['text'])


def test_single_tagged_fragment_reflows_with_same_tree_and_marked_content():
    base=source();row,m=payload(base);assert m['affine'] and m['tagged_native'] and not m['complete_object_selection']
    text=row['text'][:-1];out,r=reflow(base,[],0,m['box'],m['ids'][0],text,m['local_width'],m['local_height'])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert snapshot(a,0)==snapshot(b,0)
        assert b[0].search_for(text)
    assert len(model(base,[])['nodes'])==len(model(out,[])['nodes'])


def test_native_line_edit_also_verifies_the_tag_graph():
    base=source();row,_=payload(base);b=row['bbox'];box=[b[0],b[1],b[2]-b[0],b[3]-b[1]]
    with f.open(stream=base) as d:
        # Route the legacy simple page into verified native editing.
        x=d[0].get_contents()[0];d.update_stream(x,b'0 Tc '+d.xref_stream(x));base=d.tobytes()
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':row['text'][:-1]}])
    with f.open(stream=base) as a,f.open(stream=out) as b:assert snapshot(a,0)==snapshot(b,0)


@pytest.mark.parametrize('kind',['actualtext','stream'])
def test_alternative_text_and_stream_bound_structure_are_not_silently_changed(kind):
    with f.open(stream=source()) as d:
        leaf=next(r for r in model(d.tobytes(),[])['nodes'] if r['role']=='TH')
        if kind=='actualtext':d.xref_set_key(leaf['id'],'ActualText',f.get_pdf_str('Alternative'))
        else:d.xref_set_key(leaf['id'],'K',f'<< /Type/MCR /Pg {d[0].xref} 0 R /MCID 0 /Stm {d[0].get_contents()[0]} 0 R >>')
        base=d.tobytes()
    with f.open(stream=base) as d:
        with pytest.raises(DocumentError,match='estructura etiquetada'):snapshot(d,0)


def test_canonical_graph_survives_xref_compaction_but_detects_role_changes():
    base=source()
    with f.open(stream=base) as d:
        expected=snapshot(d,0);unused=d.get_new_xref();d.update_object(unused,'<< /Unused true >>');compacted=d.tobytes(garbage=2)
    with f.open(stream=compacted) as d:
        assert snapshot(d,0)==expected
        leaf=next(r for r in model(compacted,[])['nodes'] if r['role']=='TH');d.xref_set_key(leaf['id'],'S','/TD')
        assert snapshot(d,0)!=expected
