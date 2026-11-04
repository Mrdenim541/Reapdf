import pytest,pymupdf as f
from backend.layers import model,apply
from backend.engine import DocumentError
from tests.test_extended_workflows import layered


def test_native_print_export_rules_are_independent_of_screen_and_preserve_streams():
    base,a,b=layered();before=model(base,[]);values=[{'id':r['id'],'print':'OFF' if r['id']==a else 'ON','export':'ON' if r['id']==a else None} for r in before['layers']]
    out=apply(base,[],[a,b],usage=values);after=model(out,[])
    assert after['usage']['supported'] and after['usage']['layers']==values
    with f.open(stream=base) as d,f.open(stream=out) as e:
        assert d[0].read_contents()==e[0].read_contents() and set(d.get_ocgs())==set(e.get_ocgs())
        n=f.mupdf;config=n.pdf_dict_getp(n.pdf_trailer(f._as_pdf_document(e)),'Root/OCProperties/D');rules=n.pdf_dict_gets(config,'AS')
        assert n.pdf_array_len(rules)==2
        assert n.pdf_to_name(n.pdf_dict_gets(n.pdf_array_get(rules,0),'Event'))=='Print'
        assert 'ONLY A' in e[0].get_text() and 'ONLY B' in e[0].get_text()
    cleared=apply(out,[],[a,b],usage=[{**r,'print':None,'export':None} for r in values]);assert all(r['print'] is None and r['export'] is None for r in model(cleared,[])['usage']['layers'])


def test_unknown_automatic_rules_are_retained_and_not_replaced():
    base,a,b=layered()
    with f.open(stream=base) as d:
        d.xref_set_key(d.pdf_catalog(),'OCProperties/D/AS',f'[<< /Event/View /Category[/Zoom] /OCGs[{a} 0 R] >>]');base=d.tobytes()
    assert not model(base,[])['usage']['supported']
    with pytest.raises(DocumentError,match='especializada'):apply(base,[],[a,b],usage=[{'id':i,'print':'OFF','export':None} for i in [a,b]])


@pytest.mark.parametrize('bad',['missing','duplicate','invalid','unknown','boolean'])
def test_invalid_usage_plans_fail_before_publication(bad):
    base,a,b=layered();values=[{'id':i,'print':None,'export':None} for i in [a,b]]
    if bad=='missing':values.pop()
    if bad=='duplicate':values[1]=values[0]
    if bad=='invalid':values[0]['print']='YES'
    if bad=='unknown':values[0]['id']=10000
    if bad=='boolean':values[0]['export']=True
    with pytest.raises(DocumentError):apply(base,[],[a,b],usage=values)


def test_print_snapshot_uses_print_state_and_keeps_original_view():
    from backend.layer_usage import for_print
    base,a,b=layered();configured=apply(base,[],[a,b],usage=[{'id':a,'print':'OFF','export':None},{'id':b,'print':'ON','export':None}])
    printed=for_print(configured)
    with f.open(stream=configured) as view,f.open(stream=printed) as printing:
        assert 'ONLY A' in view[0].get_text() and 'ONLY B' in view[0].get_text()
        assert 'ONLY A' not in printing[0].get_text() and 'ONLY B' in printing[0].get_text()
        assert view[0].read_contents()==printing[0].read_contents()
    assert for_print(base)==base


def test_locked_layer_usage_is_not_modified():
    base,a,b=layered()
    with f.open(stream=base) as d:d.set_layer(-1,locked=[a]);base=d.tobytes()
    with pytest.raises(DocumentError,match='bloqueada'):apply(base,[],[a,b],usage=[{'id':a,'print':'OFF','export':None},{'id':b,'print':None,'export':None}])
