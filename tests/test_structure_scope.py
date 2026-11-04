import pytest,pymupdf as f
from backend.basic_tagging import candidates,create
from backend.structure_editing import model,properties
from backend.engine import DocumentError
from tests.test_four_blocks import table_pdf,table_entries


def source():
    base=table_pdf();return create(base,[],table_entries(candidates(base,[])),reviewed=True)[0]


@pytest.mark.parametrize('scope',['Row','Column','Both'])
@pytest.mark.parametrize('kind',['missing','direct','shared','array','other_owner'])
def test_scope_repair_preserves_rendering_tree_and_unselected_headers(scope,kind):
    base=source();rows=model(base,[])['nodes'];heads=[r for r in rows if r['role']=='TH'];selected=heads[0]['id'];other=heads[1]['id']
    with f.open(stream=base) as d:
        if kind=='missing':d.xref_set_key(selected,'A','null')
        elif kind=='shared':
            x=d.get_new_xref();d.update_object(x,'<< /O/Table /Scope/Column /ColSpan 1 >>');d.xref_set_key(selected,'A',f'{x} 0 R');d.xref_set_key(other,'A',f'{x} 0 R')
        elif kind=='array':d.xref_set_key(selected,'A','[<< /O/Layout /Placement/Block >> 0 << /O/Table /Scope/Column /ColSpan 1 >> 0]')
        elif kind=='other_owner':d.xref_set_key(selected,'A','<< /O/Layout /Placement/Block >>')
        base=d.tobytes()
    out=properties(base,[],selected,scope=scope);a=model(base,[])['nodes'];b=model(out,[])['nodes'];assert [(r['role'],r['depth']) for r in a]==[(r['role'],r['depth']) for r in b]
    heads=[r for r in b if r['role']=='TH'];assert heads[0]['scope']==scope and heads[1]['scope']=='Column'
    with f.open(stream=base) as a,f.open(stream=out) as b:assert a[0].get_pixmap().samples==b[0].get_pixmap().samples


@pytest.mark.parametrize('attributes',['[<< /O/Table >> << /O/Table >>]','[5 << /O/Table >>]','<< /Scope/Column >>','<< /O/Table /Scope/Unknown >>'])
def test_ambiguous_attributes_are_protected(attributes):
    with f.open(stream=source()) as d:
        identity=next(r['id'] for r in model(d.tobytes(),[])['nodes'] if r['role']=='TH');d.xref_set_key(identity,'A',attributes);base=d.tobytes()
    assert not next(r for r in model(base,[])['nodes'] if r['id']==identity)['can_scope']
    with pytest.raises(DocumentError):properties(base,[],identity,scope='Both')


def test_td_and_multiple_property_changes_are_rejected():
    base=source();identity=next(r['id'] for r in model(base,[])['nodes'] if r['role']=='TD')
    with pytest.raises(DocumentError):properties(base,[],identity,scope='Both')
    with pytest.raises(DocumentError):properties(base,[],identity,language='es',scope='Both')
