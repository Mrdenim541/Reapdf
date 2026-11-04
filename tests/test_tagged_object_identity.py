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
