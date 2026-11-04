from copy import deepcopy
import pytest,pymupdf as f
from backend.structure_editing import model
from backend.table_structure_repair import inspect,repair
from backend.engine import DocumentError
from tests.test_structure_scope import source


def payload(base):
    identity=next(r['id'] for r in model(base,[])['nodes'] if r['role']=='Table');table=inspect(base,[],identity)
    return identity,[c for r in table['rows'] for c in r['cells']]


def test_repair_cell_roles_scope_and_shared_attributes_preserves_pixels_and_mcids():
    base=source();identity,cells=payload(base)
    with f.open(stream=base) as d:
        x=d.get_new_xref();d.update_object(x,'<< /O/Table /RowSpan 1 /ColSpan 1 /Scope/Column /CustomFlag (KEEP) >>')
        for c in cells:d.xref_set_key(c['id'],'A',f'{x} 0 R')
        base=d.tobytes();before={c['id']:d.xref_get_key(c['id'],'K') for c in cells}
    cells[0]['role']='TD';cells[0]['scope']='';cells[2]['role']='TH';cells[2]['scope']='Row'
    out,r=repair(base,[],identity,cells,True);assert r['columns']==2 and not r['visible_content_changed']
    assert inspect(out,[],identity)['rows'][1]['cells'][0]['scope']=='Row'
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
        assert all(b.xref_get_key(c['id'],'K')==before[c['id']] for c in cells)
        assert all(b.xref_get_key(c['id'],'A/CustomFlag')==('string','KEEP') for c in cells)
        assert b.xref_get_key(cells[1]['id'],'A/Scope')==('name','/Column') and b.xref_get_key(cells[0]['id'],'A/Scope')[0]=='null'


def test_inconsistent_existing_spans_can_be_repaired_as_one_transaction():
    base=source();identity,cells=payload(base)
    with f.open(stream=base) as d:
        d.xref_set_key(cells[0]['id'],'A/ColSpan','3');base=d.tobytes()
    assert inspect(base,[],identity)['grid_issue']
    out,_=repair(base,[],identity,cells,True);assert inspect(out,[],identity)['columns']==2


@pytest.mark.parametrize('bad',['overflow','hole','bool','missing','repeat','scope','role','unreviewed'])
def test_invalid_repairs_never_publish_a_partial_structure(bad):
    base=source();identity,cells=payload(base);reviewed=True
    if bad=='overflow':cells[-1]['rowspan']=2
    if bad=='hole':cells[0]['colspan']=2
    if bad=='bool':cells[0]['rowspan']=True
    if bad=='missing':cells.pop()
    if bad=='repeat':cells[-1]=deepcopy(cells[0])
    if bad=='scope':cells[0]['scope']='Unknown'
    if bad=='role':cells[0]['role']='P'
    if bad=='unreviewed':reviewed=False
    with pytest.raises(DocumentError):repair(base,[],identity,cells,reviewed)


def test_id_associated_header_cannot_be_changed_to_data():
    base=source();identity,cells=payload(base)
    with f.open(stream=base) as d:d.xref_set_key(cells[0]['id'],'ID',f.get_pdf_str('HeaderOne'));base=d.tobytes()
    cells[0]['role']='TD';cells[0]['scope']=''
    with pytest.raises(DocumentError,match='asociaciones'):repair(base,[],identity,cells,True)
