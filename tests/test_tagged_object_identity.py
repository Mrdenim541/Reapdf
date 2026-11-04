import pytest,pymupdf as f
from backend.basic_tagging import candidates,create
from backend.structure_editing import model
from backend.document_tools import optimize_pdf,metadata_pdf,protect_pdf
from backend.engine import export_pdf,pdf_garbage
from tests.test_four_blocks import table_pdf,table_entries


def source():
    base=table_pdf();entries=table_entries(candidates(base,[]))
    return create(base,[],entries,reviewed=True,empty_cells=[{'page':0,'table':1,'row':4,'column':1},{'page':0,'table':1,'row':4,'column':2}])[0]


def empty_cells(data,password=''):
    with f.open(stream=data) as d:
        if d.needs_pass:assert d.authenticate(password)
        assert pdf_garbage(d)==2
        return [x for x in range(1,d.xref_length()) if d.xref_get_key(x,'S')==('name','/TD') and d.xref_get_key(x,'K')==('array','[]')]


def test_equal_empty_cell_dictionaries_keep_distinct_structural_identities():
    base=source();assert len(empty_cells(base))==2
    nodes=model(base,[])['nodes'];assert len({r['id'] for r in nodes})==len(nodes)


@pytest.mark.parametrize('action',['optimize','metadata','protect','annotation'])
def test_core_saves_preserve_distinct_empty_cells_and_valid_parents(action):
    base=source()
    if action=='optimize':out=optimize_pdf(base,[])[0]
    elif action=='metadata':out=metadata_pdf(base,[],{'title':'Preserved','author':'','subject':'','keywords':'','creator':''},False)
    elif action=='protect':out=protect_pdf(base,[],'read-2026','owner-2026')
    else:out=export_pdf(base,[{'id':'new-note','type':'note','page':0,'point':[300,250],'content':'Review','color':[1,1,0]}])
    assert len(empty_cells(out,'read-2026'))==2
    if action!='protect':assert all(r['parent_valid'] for r in model(out,[])['nodes'])
def test_edit_on_untagged_page_preserves_equal_tagged_cells_on_another_page():
    from backend.tagged_text_integrity import snapshot
    from backend.styled_text import inspect_styled,replace_styled
    with f.open(stream=source()) as d:
        d.new_page().insert_text((50,100),'OTHER TEXT',fontsize=12);base=d.tobytes(garbage=2)
    with f.open(stream=base) as d:
        expected=snapshot(d,1);r=next(s for b in d[1].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text']=='OTHER TEXT');b=f.Rect(r['bbox']);box=[b.x0,b.y0,b.width,b.height]
    row=inspect_styled(base,[],1,box)['runs'][0]
    result=replace_styled(base,[],1,box,[{'id':row['id'],'text':'OTHER TEX'}])
    with f.open(stream=result) as d,f.open(stream=base) as original:
        assert snapshot(d,1)==expected and d[1].search_for('OTHER TEX')
        assert original[0].get_pixmap().samples==d[0].get_pixmap().samples
