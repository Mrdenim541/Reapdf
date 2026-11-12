"""Native OCG dictionaries, saved copies and context preview without content loss."""
import pymupdf as f
import pytest
from backend.layers import model,apply
from backend.layer_screen import resolve
from backend.layer_usage import for_print
from backend.engine import DocumentError
from tests.test_extended_workflows import layered


def values(base):return model(base,[])['screen']['layers']
def text(data):
    with f.open(stream=data) as doc:return doc[0].get_text()


def test_native_preferences_roundtrip_and_content_preservation():
    base,a,b=layered();v=values(base);v[0].update(view='ON',zoom={'min':1.1,'max':2},language={'lang':'es-MX','preferred':True})
    output=apply(base,[],[a,b],screen=v)
    assert model(output,[])['screen']['layers']==v
    with f.open(stream=base) as before,f.open(stream=output) as after:
        assert before[0].read_contents()==after[0].read_contents()
        assert before[0].get_fonts()==after[0].get_fonts()
        assert after.xref_get_key(a,'Usage/Language/Preferred')==('name','/ON')
        assert after.xref_get_key(a,'Usage/Language/Lang')==('string','es-MX')
    assert 'ONLY A' in text(resolve(output,{'zoom':1.1,'language':'es-MX'}))
    assert 'ONLY A' not in text(resolve(output,{'zoom':2,'language':'es-MX'}))


@pytest.mark.parametrize('zoom,shown',[(.5,False),(1,True),(1.5,True),(2,False),(4,False)])
def test_zoom_range_includes_minimum_and_excludes_maximum(zoom,shown):
    base,a,b=layered();v=values(base);v[0]['zoom']={'min':1,'max':2};output=apply(base,[],[a,b],screen=v)
    assert ('ONLY A' in text(resolve(output,{'zoom':zoom,'language':'es'}))) is shown
    assert 'ONLY B' in text(resolve(output,{'zoom':zoom,'language':'es'}))


@pytest.mark.parametrize('view',['ON','OFF'])
def test_view_condition_is_applied_in_simulation_and_initial_native_view(view):
    base,a,b=layered();v=values(base);v[0]['view']=view;output=apply(base,[],[a,b],screen=v)
    assert ('ONLY A' in text(resolve(output,{'zoom':1,'language':'es'})))==(view=='ON')
    assert ('ONLY A' in text(output))==(view=='ON')


@pytest.mark.parametrize('lang,visible',[('es-MX','A'),('ES-mx','A'),('en-US','B'),('fr','')])
def test_exact_language_matching(lang,visible):
    base,a,b=layered();v=values(base);v[0]['language']={'lang':'es-MX','preferred':False};v[1]['language']={'lang':'en-US','preferred':False};output=apply(base,[],[a,b],screen=v)
    got=text(resolve(output,{'zoom':1,'language':lang}))
    assert ('ONLY A' in got)==(visible=='A') and ('ONLY B' in got)==(visible=='B')


def test_preferred_partial_language_and_exact_priority_across_separate_rules():
    base,a,b=layered();v=values(base);v[0]['language']={'lang':'es-MX','preferred':True};output=apply(base,[],[a,b],screen=v)
    v=values(output);v[1]['language']={'lang':'es-PE','preferred':False};output=apply(output,[],[a,b],screen=v)
    assert 'ONLY A' in text(resolve(output,{'zoom':1,'language':'es-CL'}))
    exact=text(resolve(output,{'zoom':1,'language':'es-PE'}));assert 'ONLY B' in exact and 'ONLY A' not in exact


def test_ambiguous_partial_language_is_explicit_and_never_silently_chosen():
    base,a,b=layered();v=values(base)
    for row,lang in zip(v,['es-MX','es-PE']):row['language']={'lang':lang,'preferred':False}
    output=apply(base,[],[a,b],screen=v)
    with pytest.raises(DocumentError,match='idioma exacto'):resolve(output,{'zoom':1,'language':'es-CL'})


def test_print_export_and_screen_changes_preserve_each_other():
    base,a,b=layered();v=values(base);v[0]['zoom']={'min':1,'max':2}
    output=apply(base,[],[a,b],screen=v);u=[{'id':a,'print':'OFF','export':'ON'},{'id':b,'print':'ON','export':None}]
    output=apply(output,[],[a,b],usage=u);assert values(output)==v
    v[1]['view']='ON';output=apply(output,[],[a,b],screen=v)
    assert model(output,[])['usage']['layers']==u
    assert 'ONLY A' not in text(for_print(output)) and 'ONLY B' in text(for_print(output))
    assert 'ONLY A' not in text(resolve(output,{'zoom':2,'language':'es'}))


@pytest.mark.parametrize('event',['View','Print'])
def test_missing_ocgs_means_no_affected_groups(event):
    base,a,b=layered()
    with f.open(stream=base) as d:
        d.xref_set_key(a,'Usage',f'<< /{event} << /{event}State /OFF >> >>');d.xref_set_key(d.pdf_catalog(),'OCProperties/D/AS',f'[<< /Event /{event} /Category[/{event}] >>]');output=d.tobytes()
    got=resolve(output,{'zoom':1,'language':'es'}) if event=='View' else for_print(output)
    if event=='View':assert 'ONLY A' in text(got)
    else:assert got==output


@pytest.mark.parametrize('bad',[
 {'min':2,'max':1},{'min':0,'max':0},{'min':None,'max':None},{'min':True,'max':2},{'min':float('nan'),'max':2},{'min':1,'max':float('inf')},{'min':-1,'max':2},{'min':0,'max':1e100},
])
def test_invalid_zoom_never_publishes(bad):
    base,a,b=layered();v=values(base);v[0]['zoom']=bad
    with pytest.raises(DocumentError):apply(base,[],[a,b],screen=v)


@pytest.mark.parametrize('bad',[{'lang':'','preferred':False},{'lang':'es_MX','preferred':False},{'lang':'es','preferred':'ON'},{'lang':'es','preferred':True,'extra':1}])
def test_invalid_language_never_publishes(bad):
    base,a,b=layered();v=values(base);v[0]['language']=bad
    with pytest.raises(DocumentError):apply(base,[],[a,b],screen=v)


@pytest.mark.parametrize('bad',[None,{},[],{'zoom':True,'language':'es'},{'zoom':0,'language':'es'},{'zoom':1,'language':'es_MX'},{'zoom':1,'language':'es','extra':1}])
def test_invalid_simulation_context(bad):
    with pytest.raises(DocumentError):resolve(layered()[0],bad)


def test_locked_rows_and_shared_usage_are_preserved():
    base,a,b=layered()
    with f.open(stream=base) as d:
        shared=d.get_new_xref();d.update_object(shared,'<< /View << /ViewState /ON >> >>');d.xref_set_key(a,'Usage',f'{shared} 0 R');d.xref_set_key(b,'Usage',f'{shared} 0 R');d.set_layer(-1,locked=[a]);base=d.tobytes()
    v=values(base);v[1]['view']='OFF';output=apply(base,[],[a,b],screen=v)
    assert values(output)[0]==v[0] and values(output)[1]['view']=='OFF'
    with f.open(stream=base) as x,f.open(stream=output) as y:assert x.xref_object(a)==y.xref_object(a)
    v[0]['view']='OFF'
    with pytest.raises(DocumentError,match='bloqueada'):apply(base,[],[a,b],screen=v)


def test_removing_preferences_keeps_other_usage_metadata_and_original_unchanged():
    base,a,b=layered();v=values(base);v[0]['view']='OFF';v[0]['zoom']={'min':1,'max':None};configured=apply(base,[],[a,b],screen=v)
    with f.open(stream=configured) as d:d.xref_set_key(a,'Usage/CreatorInfo','<< /Creator (Example) /Subtype /Technical >>');configured=d.tobytes()
    cleared=apply(configured,[],[a,b],screen=values(base));assert values(cleared)==values(base)
    with f.open(stream=cleared) as d:assert d.xref_get_key(a,'Usage/CreatorInfo/Creator')==('string','Example')
    assert values(configured)[0]['view']=='OFF'


@pytest.mark.parametrize('raw',['/OFF','<< /View << /ViewState /MAYBE >> >>','<< /Zoom << /min (bad) >> >>','<< /Language << /Lang (es) /Preferred true >> >>'])
def test_malformed_native_conditions_are_protected(raw):
    base,a,b=layered()
    with f.open(stream=base) as d:d.xref_set_key(a,'Usage',raw);base=d.tobytes()
    assert not model(base,[])['screen']['supported']
    with pytest.raises(DocumentError):apply(base,[],[a,b],screen=values(base))


def test_preview_api_is_temporary_and_saved_preferences_are_reopenable():
    from fastapi.testclient import TestClient
    from backend.app import app
    base,a,b=layered();v=values(base);v[0]['zoom']={'min':1,'max':2}
    with TestClient(app) as client:
        source=client.post('/api/documents',files={'file':('Layers.pdf',base,'application/pdf')}).json()['id'];path=f'/api/documents/{source}'
        payload={'operations':[],'visible':[a,b],'screen':v,'preview':True,'screen_context':{'zoom':2,'language':'es'}}
        preview=client.post(path+'/set-layers',json=payload);assert preview.status_code==200 and preview.headers['content-type']=='image/png'
        assert client.post(path+'/layers',json={'operations':[]}).json()['screen']['layers']==values(base)
        payload.pop('preview');saved=client.post(path+'/set-layers',json=payload);assert saved.status_code==200,saved.text
        exported=client.post('/api/documents/'+saved.json()['id']+'/export',json={'operations':[]});assert values(exported.content)==v
        with f.open(stream=base) as before,f.open(stream=exported.content) as after:assert before[0].read_contents()==after[0].read_contents()


@pytest.mark.parametrize('rule',[
 '<< /Event /View /Category [/User] >>',
 '<< /Event /View /Category [/Zoom /Zoom] >>',
 '<< /Event /View /Category [/Zoom] /OCGs [5] >>',
 '<< /Event /View /Category [/Zoom] /OCGs [5 0 R 5 0 R] >>',
 '<< /Event /View /Category [/Zoom] /OCGs [99 0 R] >>',
 '<< /Event /View /Category [/Zoom] /Unknown true >>',
])
def test_unsupported_automatic_rules_cannot_be_overwritten(rule):
    base,a,b=layered()
    with f.open(stream=base) as doc:doc.xref_set_key(doc.pdf_catalog(),'OCProperties/D/AS','['+rule+']');base=doc.tobytes()
    assert not model(base,[])['screen']['supported']
    with pytest.raises(DocumentError):apply(base,[],[a,b],screen=values(base))


def test_combined_view_zoom_rule_uses_all_conditions():
    base,a,b=layered()
    with f.open(stream=base) as doc:
        doc.xref_set_key(a,'Usage','<< /View << /ViewState /OFF >> /Zoom << /min 1 /max 2 >> >>')
        doc.xref_set_key(doc.pdf_catalog(),'OCProperties/D/AS',f'[<< /Event /View /Category [/View /Zoom] /OCGs [{a} 0 R] >>]');base=doc.tobytes()
    assert 'ONLY A' not in text(resolve(base,{'zoom':1.5,'language':'es'}))


def test_temporary_snapshot_matches_direct_layer_toggle_pixels_and_preserves_streams():
    base,a,b=layered();v=values(base);v[0]['zoom']={'min':1,'max':2};configured=apply(base,[],[a,b],screen=v)
    resolved=resolve(configured,{'zoom':2,'language':'es'})
    with f.open(stream=base) as expected,f.open(stream=resolved) as actual:
        expected.set_layer(-1,on=[b],off=[a])
        with f.open(stream=expected.tobytes()) as reopened:
            assert reopened[0].get_pixmap().samples==actual[0].get_pixmap().samples
        assert expected[0].read_contents()==actual[0].read_contents()


def test_conflicting_exclusive_group_is_explicitly_rejected_in_simulation():
    base,a,b=layered()
    with f.open(stream=base) as doc:doc.set_layer(-1,on=[a],off=[b],rbgroups=[[a,b]]);base=doc.tobytes()
    v=values(base)
    for row in v:row['view']='ON'
    configured=apply(base,[],[a],screen=v)
    with pytest.raises(DocumentError,match='exclusivo'):resolve(configured,{'zoom':1,'language':'es'})


def test_canonical_rule_combines_all_categories_once_per_group():
    base,a,b=layered();v=values(base);v[0].update(view='ON',zoom={'min':1,'max':2},language={'lang':'es','preferred':False});out=apply(base,[],[a,b],screen=v)
    with f.open(stream=out) as doc:
        n=f.mupdf;cfg=n.pdf_dict_getp(n.pdf_trailer(f._as_pdf_document(doc)),'Root/OCProperties/D');rules=n.pdf_dict_gets(cfg,'AS');assert n.pdf_array_len(rules)==1
        cats=n.pdf_dict_gets(n.pdf_array_get(rules,0),'Category');assert [n.pdf_to_name(n.pdf_array_get(cats,i)) for i in range(n.pdf_array_len(cats))]==['View','Zoom','Language']


def test_overlapping_foreign_view_rules_remain_protected():
    base,a,b=layered()
    with f.open(stream=base) as doc:
        doc.xref_set_key(doc.pdf_catalog(),'OCProperties/D/AS',f'[<< /Event /View /Category[/View] /OCGs[{a} 0 R] >> << /Event /View /Category[/Zoom] /OCGs[{a} 0 R] >>]');base=doc.tobytes()
    assert not model(base,[])['screen']['supported']
    with pytest.raises(DocumentError):apply(base,[],[a,b],screen=values(base))


def test_frozen_context_is_editable_by_layer_controls_and_preserves_print_export():
    base,a,b=layered();v=values(base);v[0]['zoom']={'min':1,'max':2};v[1]['language']={'lang':'es','preferred':False}
    u=[{'id':a,'print':'ON','export':'OFF'},{'id':b,'print':'OFF','export':'ON'}];configured=apply(base,[],[a,b],usage=u,screen=v)
    frozen=resolve(configured,{'zoom':2,'language':'es'},freeze=True)
    assert 'ONLY B' in text(frozen) and 'ONLY A' not in text(frozen)
    assert all(r['view'] is None and r['zoom'] is None and r['language'] is None for r in values(frozen))
    assert model(frozen,[])['usage']['layers']==u
    assert 'ONLY A' in text(for_print(frozen)) and 'ONLY B' not in text(for_print(frozen))
    restored=apply(frozen,[],[a,b]);assert 'ONLY A' in text(restored) and 'ONLY B' in text(restored)
    with f.open(stream=configured) as before,f.open(stream=frozen) as after:assert before[0].read_contents()==after[0].read_contents()


def test_copy_context_api_preserves_source_and_preview_pixels():
    from fastapi.testclient import TestClient
    from backend.app import app
    base,a,b=layered();v=values(base);v[0]['zoom']={'min':1,'max':2}
    with TestClient(app) as client:
        source=client.post('/api/documents',files={'file':('Layers.pdf',base,'application/pdf')}).json()['id'];url=f'/api/documents/{source}/set-layers'
        payload={'operations':[],'visible':[a,b],'screen':v,'screen_context':{'zoom':2,'language':'es'}}
        preview=client.post(url,json={**payload,'preview':True});copy=client.post(url,json={**payload,'apply_context':True});assert preview.status_code==200 and copy.status_code==200,copy.text
        assert copy.json().get('working_copy') is True
        out=client.post('/api/documents/'+copy.json()['id']+'/export',json={'operations':[]}).content
        with f.open(stream=out) as doc:assert doc[0].get_pixmap().samples==f.Pixmap(preview.content).samples
        assert 'ONLY B' in text(out) and 'ONLY A' not in text(out)
        assert client.post('/api/documents/'+source+'/layers',json={'operations':[]}).json()['screen']['layers']==values(base)
        assert client.post(url,json={**payload,'apply_context':True,'preview':True}).status_code==422
