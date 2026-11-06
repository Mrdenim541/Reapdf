import json
import pytest
import pymupdf as f
from backend.engine import DocumentError
from backend.native_text import native_model
from backend.styled_text import inspect_styled,replace_styled,replace_styled_regions
from scripts.create_semantic_text_sample import source,form_source


def selected(base,text='HELLO',page=0):
    with f.open(stream=base) as d:
        d[page].set_rotation(0);r=next(r for r in native_model(d,page,d[page].rect)[1] if r['text']==text)
    b=r['bbox'];return r,[b[0],b[1],b[2]-b[0],b[3]-b[1]]


def change(base,*,text='HOLA Ω',family='sans',style='regular',size=12,accessible='New reading'):
    r,box=selected(base)
    update={'id':r['id'],'text':text,'format':{'family':family,'style':style,'size':size}}
    if r.get('has_actual_text'):update['accessible_text']=accessible
    return replace_styled(base,[],0,box,[update])


@pytest.mark.parametrize('family',['sans','serif','mono'])
@pytest.mark.parametrize('style',['regular','bold','italic','bold-italic'])
def test_all_included_faces_embed_unicode_and_remain_natively_editable(family,style):
    base=source('HELLO',tagged=True);out=change(base,family=family,style=style)
    r,box=selected(out,'HOLA Ω');assert r['editable'] and r['format_editable'] and r['size']==pytest.approx(12)
    again=replace_styled(out,[],0,box,[{'id':r['id'],'text':'HOLA','accessible_text':'Reading after reopen'}])
    with f.open(stream=base) as a,f.open(stream=again) as d:
        assert d.xref_get_key(d.pdf_catalog(),'StructTreeRoot')[0]=='xref'
        assert 'HOLA Ω' not in d[0].get_text(flags=f.TEXTFLAGS_TEXT|f.TEXT_IGNORE_ACTUALTEXT)
        assert a[0].search_for('UNCHANGED')==d[0].search_for('UNCHANGED')


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('nested',[False,True])
@pytest.mark.parametrize('stream_owned',[False,True])
def test_form_format_preserves_owner_rotation_other_pages_and_other_occurrence(rotation,nested,stream_owned):
    from backend.semantic_text import capture
    base=form_source(stream_owned=stream_owned,actual='Reading',rotation=rotation,nested=nested,shared=not stream_owned)
    out=change(base,accessible='Reading')
    with f.open(stream=base) as a,f.open(stream=out) as d:
        assert d[0].rotation==rotation and a[1].get_pixmap().samples==d[1].get_pixmap().samples
        d[0].set_rotation(0);a[0].set_rotation(0)
        r=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HOLA Ω');assert r['editable'] and bool(r.get('has_actual_text'))==stream_owned
        assert capture(a,0)==capture(d,0)
        if not stream_owned:assert a[0].search_for('HELLO')[-1]==d[0].search_for('HELLO')[-1]


def test_original_font_size_changes_without_adding_a_font_and_can_change_again():
    base=source('HELLO',tagged=True);out=change(base,text='HELLO',family='original',style='original',size=18,accessible='HELLO')
    r,box=selected(out);assert r['size']==pytest.approx(18) and r['font']=='Helvetica'
    with f.open(stream=base) as a,f.open(stream=out) as b:assert len(a[0].get_fonts(full=True))==len(b[0].get_fonts(full=True))
    again=replace_styled(out,[],0,box,[{'id':r['id'],'text':'HOLA','format':{'family':'original','style':'original','size':10}}]);assert selected(again,'HOLA')[0]['size']==pytest.approx(10)


@pytest.mark.parametrize('options',[None,{}, {'family':'sans','style':'regular','size':True},{'family':'sans','style':'regular','size':None},{'family':'sans','style':'regular','size':145},{'family':'bad','style':'regular','size':12},{'family':'original','style':'bold','size':12},{'family':[],'style':'regular','size':12}])
def test_invalid_format_rejected_without_mutating_input(options):
    base=source();r,box=selected(base)
    with pytest.raises(DocumentError):replace_styled(base,[],0,box,[{'id':r['id'],'text':'HOLA','format':options}])
    assert selected(base)[0]['font']=='Helvetica'


@pytest.mark.parametrize('text',['العربية','e\u0301','A\u200dB','\ud800','\U0010ffff'])
def test_unshaped_or_missing_characters_are_rejected(text):
    with pytest.raises(DocumentError):change(source(),text=text)


def test_shared_stream_remains_protected_and_typography_attributes_are_reported():
    with pytest.raises(DocumentError):change(form_source(stream_owned=True,shared=True))
    base=source(tagged=True)
    with f.open(stream=base) as d:
        from backend.semantic_text import tree
        leaf=next(iter(tree(d).records));d.xref_set_key(leaf,'A','<</O/Layout /BBox [0 0 200 200]>>');base=d.tobytes()
    r,box=selected(base);assert r['editable'] and not r['format_editable'] and 'atributos' in r['format_reason']
    with pytest.raises(DocumentError,match='atributos'):change(base)


def test_format_cannot_expand_across_neighbor_text_or_page_edges():
    with pytest.raises(DocumentError):change(source(),size=144,text='HOLA HOLA HOLA HOLA HOLA HOLA')


def test_format_cannot_cross_table_edge_but_can_keep_background():
    base=source(tagged=True)
    with f.open(stream=base) as d:
        r=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HELLO');x=r['bbox'][2]+2
        d[0].draw_line((x,40),(x,130));edge=d.tobytes()
    with pytest.raises(DocumentError,match='borde'):change(edge,text='HELLOHELLO',accessible='HELLOHELLO')
    with f.open(stream=base) as d:
        d[0].draw_rect(d[0].rect,fill=(.98,.98,.98),color=None,overlay=False);background=d.tobytes()
    assert selected(change(background),'HOLA Ω')[0]['editable']


def test_generated_font_alias_collision_does_not_replace_existing_resource():
    base=source(tagged=True)
    with f.open(stream=base) as d:
        d[0].insert_font(fontname='ReapdfFormat',fontfile='resources/fonts/DejaVuSansMono.ttf');base=d.tobytes()
    assert selected(change(base),'HOLA Ω')[0]['editable']


@pytest.mark.parametrize('mode',['tm','form'])
@pytest.mark.parametrize('linear',[(0,1,-1,0),(0,-1,1,0),(-1,0,0,-1),(-1,0,0,1),(1,0,0,-1),(1,.3,.2,1),(.7,.3,.2,1.4),(.70710678,.70710678,-.70710678,.70710678),(1,0,.6,1)])
def test_font_change_retains_affine_frame_and_unselected_occurrences(linear,mode):
    from tests.test_affine_text_editing import source as affine_source
    base=affine_source(linear=linear,mode=mode);r,box=selected(base,'HELLO TEXT')
    out=replace_styled(base,[],0,box,[{'id':r['id'],'text':'HOLA Ω','format':{'family':'sans','style':'bold','size':13}}])
    with f.open(stream=base) as a,f.open(stream=out) as d:
        after=next(s for s in native_model(d,0,d[0].rect)[1] if s['text']=='HOLA Ω')
        assert after['editable'] and after['_geometry']['matrix']==pytest.approx(r['_geometry']['matrix'],abs=.00001)
        assert a[1].get_pixmap().samples==d[1].get_pixmap().samples


@pytest.mark.parametrize('char,word,kerning',[(0,2,50),(1,1,-80),(.5,1,0),(0,0,-60)])
def test_cid_font_preserves_character_word_and_matching_tj_gaps(char,word,kerning):
    from tests.test_revision_quick_spacing import spaced_source
    base=spaced_source(char,word,kerning);r,box=selected(base,'AVATAR TEST')
    out=replace_styled(base,[],0,box,[{'id':r['id'],'text':'AVATAR TEST','format':{'family':'serif','style':'regular','size':18}}])
    a,_=selected(out,'AVATAR TEST');assert a['editable']
    assert a['_spacing']['state']==r['_spacing']['state']
    expected=list(r['_spacing']['kern']);expected[6]-=word/18*1000
    assert a['_spacing']['kern']==pytest.approx(expected)


def test_api_format_metadata_and_preview_are_non_destructive(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import app
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path));base=source(tagged=True);r,box=selected(base)
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('Source.pdf',base,'application/pdf')})
        assert doc.status_code==200,doc.text
        identifier=doc.json()['id'];prefix=f'/api/documents/{identifier}'
        inspect=client.post(prefix+'/inspect-styled-text',json={'operations':[],'page':0,'box':box});assert inspect.status_code==200 and inspect.json()['runs'][0]['format_editable']
        payload={'operations':[],'page':0,'box':box,'changes':[{'id':r['id'],'text':'HOLA Ω','accessible_text':'New reading','format':{'family':'sans','style':'regular','size':12}}]}
        response=client.post(prefix+'/replace-styled-text',json={**payload,'preview':True});assert response.status_code==200 and response.headers['content-type']=='image/png'
        response=client.post(prefix+'/replace-styled-text',json=payload);assert response.status_code==200
        original=client.post(prefix+'/export',json={'operations':[]});assert selected(original.content)[0]['font']=='Helvetica'


def test_layout_bbox_and_table_metadata_remain_intact_when_new_font_stays_inside():
    from backend.semantic_text import tree,capture
    base=source(tagged=True)
    with f.open(stream=base) as d:
        leaf=next(iter(tree(d).records));d.xref_set_key(leaf,'A','[<</O/Layout /BBox [40 380 160 435] /WritingMode/LrTb>> <</O/Table /RowSpan 1 /ColSpan 1>>]');base=d.tobytes()
        before=capture(d,0)
    r,_=selected(base);assert r['format_editable'],r['format_reason']
    out=change(base,accessible='HELLO')
    with f.open(stream=out) as d:assert capture(d,0)==before
    with pytest.raises(DocumentError,match='caja declarada'):change(base,text='HOLA',size=60)


def test_declared_font_family_does_not_silently_contradict_new_font():
    from backend.semantic_text import tree
    base=source(tagged=True)
    with f.open(stream=base) as d:
        leaf=next(iter(tree(d).records));d.xref_set_key(leaf,'A','<</O/Layout /FontFamily (Helvetica)>>');base=d.tobytes()
    r,_=selected(base);assert r['editable'] and r['format_editable']
    out=change(base)
    with f.open(stream=out) as d:
        leaf=next(iter(tree(d).records));assert d.xref_get_key(leaf,'A/FontFamily')==('string','DejaVu Sans')


def test_multi_page_font_change_is_atomic_and_uses_each_page_resources():
    with f.open(stream=source('First',tagged=True,node=True)) as d,f.open(stream=source('Second')) as other:
        d.insert_pdf(other);root=int(d.xref_get_key(d.pdf_catalog(),'StructTreeRoot')[1].split()[0]);first=int(d.xref_get_key(root,'K')[1].strip('[]').split()[0]);leaf=d.get_new_xref();d.update_object(leaf,f'<</Type/StructElem /S/P /P {root} 0 R /Pg {d[1].xref} 0 R /K 0>>');d.xref_set_key(root,'K',f'[{first} 0 R {leaf} 0 R]');d.xref_set_key(root,'ParentTree',f'<</Nums [0 [{first} 0 R] 1 [{leaf} 0 R]]>>');d.xref_set_key(d[1].xref,'StructParents','1');base=d.tobytes()
    regions=[]
    for page in [0,1]:
        r,box=selected(base,page=page);regions.append({'page':page,'box':box,'changes':[{'id':r['id'],'text':'HOLA Ω','accessible_text':'Reading '+str(page),'format':{'family':'serif' if page else 'sans','style':'bold','size':12}}]})
    out=replace_styled_regions(base,[],regions)
    for page in [0,1]:assert selected(out,'HOLA Ω',page)[0]['editable']
    regions[1]['changes'][0]['format']['size']=10000
    with pytest.raises(DocumentError,match='No se aplicó'):replace_styled_regions(base,[],regions)
    for page in [0,1]:assert selected(base,page=page)[0]['font']=='Helvetica'
