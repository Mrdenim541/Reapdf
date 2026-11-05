import pytest
import pymupdf as f
from backend.engine import DocumentError
from backend.native_text import native_model
from backend.styled_text import replace_styled,replace_styled_regions,inspect_styled
from scripts.create_semantic_text_sample import source,form_source




def row(base):
    with f.open(stream=base) as d:
        _,rows=native_model(d,0,d[0].rect);r=next(r for r in rows if r['text']=='HELLO')
    b=r['bbox'];return r,[b[0],b[1],b[2]-b[0],b[3]-b[1]]


@pytest.mark.parametrize('tagged,node',[(False,False),(True,False),(True,True)])
@pytest.mark.parametrize('actual',['HELLO','Accessible reading','', 'Lectura con acentos áé y Ω'])
def test_visible_and_accessible_text_are_saved_together_without_touching_neighbor(tagged,node,actual):
    base=source(actual,tagged,node);r,box=row(base);assert r['editable'],r['reason'];assert r['has_actual_text'] and r['accessible_text']==actual
    out=replace_styled(base,[],0,box,[{'id':r['id'],'text':'HOLA','accessible_text':'Nueva lectura Ω'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert 'HOLA' in b[0].get_text(flags=f.TEXTFLAGS_TEXT|f.TEXT_IGNORE_ACTUALTEXT)
        rows=native_model(b,0,b[0].rect)[1];changed=next(r for r in rows if r['text']=='HOLA');assert changed['editable'] and changed['accessible_text']=='Nueva lectura Ω'
        assert a[0].search_for('UNCHANGED')==b[0].search_for('UNCHANGED')
        if not node:assert 'Nueva lectura Ω' in b[0].get_text()


def test_matching_alternative_follows_visible_text_without_extra_request_properties():
    base=source();r,box=row(base);out=replace_styled(base,[],0,box,[{'id':r['id'],'text':'HOLA'}])
    with f.open(stream=out) as d:assert 'HOLA' in d[0].get_text() and 'HELLO' not in d[0].get_text()


def test_different_alternative_requires_an_explicit_choice():
    base=source('Meaning');r,box=row(base)
    with pytest.raises(DocumentError,match='lectura accesible'):replace_styled(base,[],0,box,[{'id':r['id'],'text':'HOLA'}])


def test_accessible_only_edit_preserves_pixels_and_visible_glyphs():
    base=source('Meaning');r,box=row(base);out=replace_styled(base,[],0,box,[{'id':r['id'],'text':'HELLO','accessible_text':'Other meaning'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:assert a[0].get_pixmap().samples==b[0].get_pixmap().samples and 'Other meaning' in b[0].get_text()




@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('nested',[False,True])
@pytest.mark.parametrize('actual',[None,'Accessible meaning'])
def test_unique_stream_owned_form_keeps_mcr_and_original_stream_identity(rotation,nested,actual):
    from backend.semantic_text import capture
    base=form_source(rotation=rotation,nested=nested,actual=actual)
    with f.open(stream=base) as d:
        d[0].set_rotation(0);rows=native_model(d,0,d[0].rect)[1];r=next(r for r in rows if r['text']=='HELLO');assert r['editable'],r['reason'];assert r['stream_tagged']
        b=r['bbox'];box=[b[0],b[1],b[2]-b[0],b[3]-b[1]]
    change={'id':r['id'],'text':'HOLA',**({'accessible_text':'Nueva lectura'} if actual is not None else {})}
    out=replace_styled(base,[],0,box,[change])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples and b[0].rotation==rotation
        b[0].set_rotation(0);rows=native_model(b,0,b[0].rect)[1];changed=next(r for r in rows if r['text']=='HOLA');assert changed['editable'] and changed['stream_tagged']
        if actual is None:assert capture(a,0)==capture(b,0)
        else:assert changed['accessible_text']=='Nueva lectura'


@pytest.mark.parametrize('nested',[False,True])
def test_page_owned_reused_form_isolated_without_dropping_outer_tags(nested):
    from backend.semantic_text import capture
    base=form_source(stream_owned=False,nested=nested,shared=True)
    with f.open(stream=base) as d:
        rows=native_model(d,0,d[0].rect)[1];chosen=min([r for r in rows if r['text']=='HELLO'],key=lambda r:r['origin'][0]);assert chosen['editable'],chosen['reason'];b=chosen['bbox'];box=[b[0],b[1],b[2]-b[0],b[3]-b[1]]
    out=replace_styled(base,[],0,box,[{'id':chosen['id'],'text':'HOLA'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].get_text().count('HOLA')==1 and b[0].get_text().count('HELLO')==1
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert capture(a,0)==capture(b,0)


def test_shared_stream_owned_form_is_not_mutated_for_other_appearances():
    base=form_source(shared=True)
    with f.open(stream=base) as d:
        rows=native_model(d,0,d[0].rect)[1];chosen=next(r for r in rows if r['text']=='HELLO');assert not chosen['editable']


@pytest.mark.parametrize('nested',[False,True])
@pytest.mark.parametrize('continuation',[False,True])
def test_page_owned_form_paragraph_can_reflow_continue_and_reopen(nested,continuation):
    from backend.original_reflow import inspect
    from backend.affine_reflow import reflow
    from backend.structure_editing import reading_preview
    base=form_source(stream_owned=False,nested=nested,shared=True)
    with f.open(stream=base) as d:
        chosen=min([r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HELLO'],key=lambda r:r['origin'][0]);m=inspect(base,[],0,chosen['origin'],chosen['text'])
    assert m['tagged_paragraph'] and m['mixed'] and m['complete_object_selection']
    text='HOLA '*20 if continuation else 'HOLA HOLA'
    kwargs={'continuations':[{'page':1,'box':[40,150,400,300]}]} if continuation else {}
    out,report=reflow(base,[],0,m['box'],m['ids'][0],text,120,30 if continuation else 80,False,m['ids'],[{'id':m['ids'][0],'text':text}],**kwargs)
    with f.open(stream=out) as d:
        assert d[0].get_text().count('HELLO')==1
        assert sum(p.get_text().count('HOLA') for p in d)==(20 if continuation else 2)
        changed=next(r for r in native_model(d,0,d[0].rect)[1] if 'HOLA' in r['text']);again=inspect(out,[],0,changed['origin'],changed['text']);assert again['tagged_paragraph']
    blocks=reading_preview(out,[],1 if continuation else 0)['blocks'];assert all(b['tagged'] for b in blocks if 'HOLA' in b['text'])


@pytest.mark.parametrize('kind',['parenttree','duplicate_index','missing_stream','shared_other_page','bad_parent','overflow_mcid'])
def test_stream_associations_cannot_be_guessed_or_edited_in_place_when_ambiguous(kind):
    base=form_source()
    with f.open(stream=base) as d:
        target=next(x[0] for x in d[0].get_xobjects() if d.xref_get_key(x[0],'StructParents')[0]=='int');root=int(d.xref_get_key(d.pdf_catalog(),'StructTreeRoot')[1].split()[0]);leaf=int(d.xref_get_key(root,'K')[1].strip('[]').split()[0])
        if kind=='parenttree':d.xref_set_key(root,'ParentTree','<</Nums [10 [null]]>>')
        elif kind=='duplicate_index':d.xref_set_key(d[0].xref,'StructParents','10')
        elif kind=='missing_stream':d.xref_set_key(leaf,'K',f'<</Type/MCR /Pg {d[0].xref} 0 R /MCID 0>>')
        elif kind=='bad_parent':d.xref_set_key(leaf,'P',f'{d.pdf_catalog()} 0 R')
        elif kind=='overflow_mcid':d.xref_set_key(leaf,'K',d.xref_get_key(leaf,'K')[1].replace('/MCID 0','/MCID 4294967296'))
        else:
            from backend.form_text import clone_dictionary
            r=clone_dictionary(d,d[1].xref,'Resources');d.xref_set_key(r,'XObject',f'<</F {target} 0 R>>');x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'q 1 0 0 1 50 300 cm /F Do Q');d.xref_set_key(d[1].xref,'Contents','['+' '.join(f'{v} 0 R' for v in d[1].get_contents()+[x])+']')
        broken=d.tobytes()
    with f.open(stream=broken) as d:
        rows=native_model(d,0,d[0].rect)[1];chosen=next(r for r in rows if r['text']=='HELLO');assert not chosen['editable']


@pytest.mark.parametrize('kind',['two_groups','two_alternatives','invalid_unicode','paint','ancestor_many'])
def test_partial_or_conflicting_alternative_is_readonly(kind):
    base=source('Meaning',tagged=True,node=kind=='ancestor_many')
    with f.open(stream=base) as d:
        x=d[0].get_contents()[0];data=d.xref_stream(x)
        if kind=='two_groups':data=data.replace(b'EMC',b'BT /helv 16 Tf 1 0 0 1 50 350 Tm (MORE) Tj ET EMC')
        elif kind=='two_alternatives':data=b'/Span <</ActualText (Other)>> BDC '+data+b' EMC'
        elif kind=='invalid_unicode':data=data.replace(b'(Meaning)',b'<feffd800>')
        elif kind=='paint':data=data.replace(b'EMC',b'0 0 50 50 re S EMC')
        else:
            root=int(d.xref_get_key(d.pdf_catalog(),'StructTreeRoot')[1].split()[0]);leaf=int(d.xref_get_key(root,'K')[1].strip('[]').split()[0]);d.xref_set_key(leaf,'K','[0 1]')
        d.update_stream(x,data);broken=d.tobytes()
    try:
        r,_=row(broken);assert not r['editable']
    except DocumentError:assert kind=='invalid_unicode'


def test_atomic_edit_of_node_and_inline_alternatives_on_two_pages():
    with f.open(stream=source('First',tagged=True,node=True)) as d,f.open(stream=source('Second')) as second:
        d.insert_pdf(second);root=int(d.xref_get_key(d.pdf_catalog(),'StructTreeRoot')[1].split()[0]);first=int(d.xref_get_key(root,'K')[1].strip('[]').split()[0]);leaf=d.get_new_xref();d.update_object(leaf,f'<</Type/StructElem /S/P /P {root} 0 R /Pg {d[1].xref} 0 R /K 0>>');d.xref_set_key(root,'K',f'[{first} 0 R {leaf} 0 R]');d.xref_set_key(root,'ParentTree',f'<</Nums [0 [{first} 0 R] 1 [{leaf} 0 R]]>>');d.xref_set_key(d[1].xref,'StructParents','1');base=d.tobytes()
    regions=[]
    with f.open(stream=base) as d:
        for number in range(2):
            r=next(r for r in native_model(d,number,d[number].rect)[1] if r['text']=='HELLO');b=r['bbox'];regions.append({'page':number,'box':[b[0],b[1],b[2]-b[0],b[3]-b[1]],'changes':[{'id':r['id'],'text':'HOLA','accessible_text':'Reading '+str(number)}]})
    out=replace_styled_regions(base,[],regions)
    with f.open(stream=out) as d:
        r=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HOLA');assert r['accessible_text']=='Reading 0' and 'Reading 1' in d[1].get_text()
    regions[1]['changes'][0]['text']='NO CABE '*100
    with pytest.raises(DocumentError):replace_styled_regions(base,[],regions)


def test_api_returns_visible_and_reading_values_and_keeps_source_version():
    from fastapi.testclient import TestClient
    from backend.app import app
    from backend.engine import spans
    base=source('Meaning');r,box=row(base)
    with f.open(stream=base) as d:assert next(s for s in spans(d[0]) if s['text']=='HELLO')['semantic_protected']
    with TestClient(app) as c:
        original=c.post('/api/documents',files={'file':('Alternatives.pdf',base,'application/pdf')}).json();url='/api/documents/'+original['id']
        inspected=c.post(url+'/inspect-styled-text',json={'page':0,'box':box});assert inspected.status_code==200 and inspected.json()['runs'][0]['accessible_text']=='Meaning'
        response=c.post(url+'/replace-styled-text',json={'page':0,'box':box,'changes':[{'id':r['id'],'text':'HOLA','accessible_text':'Other reading'}]});assert response.status_code==200 and response.json()['id']!=original['id']
        again=c.post(url+'/inspect-styled-text',json={'page':0,'box':box});assert again.json()['runs'][0]['text']=='HELLO' and again.json()['runs'][0]['accessible_text']=='Meaning'


@pytest.mark.parametrize('actual',['HELLO','Other reading'])
def test_stream_mcr_with_node_alternative_is_updated_without_changing_ownership(actual):
    base=form_source(actual=actual,node_actual=True);r,box=row(base);assert r['stream_tagged'] and r['accessible_text']==actual
    out=replace_styled(base,[],0,box,[{'id':r['id'],'text':'HOLA','accessible_text':'Updated reading'}])
    with f.open(stream=out) as d:
        r=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HOLA');assert r['stream_tagged'] and r['accessible_text']=='Updated reading'
