import pytest
import pymupdf as f
from scripts.create_tagged_paragraph_sample import create
from scripts.create_semantic_text_sample import source
from tests.test_native_format import selected,change
from backend.semantic_text import tree
from backend.native_text import native_model
from backend.original_reflow import inspect
from backend.affine_reflow import reflow
from backend.engine import DocumentError,spans


def apply(base,options,words=2,width=200,height=150,paginate=False,preview=False):
    with f.open(stream=base) as d:
        d[0].set_rotation(0);r=next(r for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text'])
    m=inspect(base,[],0,r['origin'],r['text']);runs=[{'id':r['id'],'text':((('HELLO ' if options.get('family')=='original' else 'HELLO Ω ')*words) if i==0 else 'TEXT '*words)} for i,r in enumerate(m['runs'])]
    return reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),width,height,preview,m['ids'],runs,paginate=paginate,formatting=options)


def declared(base,classes=False):
    with f.open(stream=base) as d:
        t=tree(d);root=nroot=f.mupdf.pdf_to_num(t.root)
        for key,record in t.records.items():
            if f.mupdf.pdf_to_name(f.mupdf.pdf_dict_gets(record['object'],'S'))!='Span':continue
            value='<</O/Layout /FontFamily (Helvetica) /FontSize 18 /FontWeight 400 /FontStyle/Normal>>'
            if classes:
                d.xref_set_key(root,'ClassMap','<</Shared '+value+'>>');d.xref_set_key(key,'C','/Shared')
            else:d.xref_set_key(key,'A',value)
        return d.tobytes()


@pytest.mark.parametrize('family',['sans','serif','mono'])
@pytest.mark.parametrize('style',['keep','regular','bold','italic','bold-italic'])
def test_common_font_reflows_paragraph_and_preserves_color_transform_and_emphasis(family,style):
    base=create();out,report=apply(base,{'family':family,'style':style,'size':12})
    assert report['formatted'] and report['complete']
    with f.open(stream=base) as a,f.open(stream=out) as d:
        rows=[r for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']]
        assert rows and all(r['editable'] and r['size']==pytest.approx(12) for r in rows)
        if style=='keep':assert any('Bold' in r['font'] for r in rows) and any('Italic' in r['font'] or 'Oblique' in r['font'] for r in rows)
        assert {r['color'] for r in rows}=={0xcc0000,0x0000cc}
        assert a[0].search_for('NEIGHBOR UNCHANGED')==d[0].search_for('NEIGHBOR UNCHANGED') and a[1].get_pixmap().samples==d[1].get_pixmap().samples


@pytest.mark.parametrize('classes',[False,True])
def test_declarations_are_updated_without_rewriting_original_shared_class(classes):
    base=declared(create(),classes);out,_=apply(base,{'family':'serif','style':'regular','size':12})
    with f.open(stream=out) as d:
        t=tree(d)
        for record in t.records.values():
            obj=record['object']
            if f.mupdf.pdf_to_name(f.mupdf.pdf_dict_gets(obj,'S'))!='Span':continue
            from backend.text_typography import declarations
            for _,_,_,attr in declarations(d,obj):
                assert f.mupdf.pdf_to_text_string(f.mupdf.pdf_dict_gets(attr,'FontFamily'))=='DejaVu Serif'
                assert f.mupdf.pdf_to_real(f.mupdf.pdf_dict_gets(attr,'FontSize'))==12
        if classes:
            old=f.mupdf.pdf_dict_gets(f.mupdf.pdf_dict_gets(t.root,'ClassMap'),'Shared');assert f.mupdf.pdf_to_text_string(f.mupdf.pdf_dict_gets(old,'FontFamily'))=='Helvetica'


def test_original_font_size_can_be_shared_without_replacing_faces():
    out,_=apply(create(),{'family':'original','style':'keep','size':13},words=1)
    with f.open(stream=out) as d:
        rows=[r for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']];assert {r['font'] for r in rows}=={'Helvetica-Bold','Helvetica-Oblique'}


def test_merged_uniform_style_source_groups_stay_individually_selectable():
    with f.open(stream=create()) as d:
        for x in d[0].get_contents():d.update_stream(x,d.xref_stream(x).replace(b'.8 0 0 rg',b'0 g').replace(b'0 0 .8 rg',b'0 g').replace(b'1 0 .35 1',b'1 0 0 1'))
        base=d.tobytes()
    out,_=apply(base,{'family':'sans','style':'regular','size':12},words=1)
    with f.open(stream=out) as d:
        rows=[r for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']];targets=spans(d[0]);assert len(rows)==2 and all(r['editable'] for r in rows);assert any(t['text']==rows[0]['text'] for t in targets)


@pytest.mark.parametrize('classes',[False,True])
def test_single_line_declaration_and_actualtext_are_coordinated(classes):
    with f.open(stream=source(tagged=True)) as d:
        t=tree(d);leaf=next(iter(t.records));root=f.mupdf.pdf_to_num(t.root);value='<</O/Layout /FontFamily (Helvetica) /FontSize 16 /FontWeight 400 /FontStyle(normal)>>'
        if classes:d.xref_set_key(root,'ClassMap','<</Shared '+value+'>>');d.xref_set_key(leaf,'C','/Shared')
        else:d.xref_set_key(leaf,'A',value)
        base=d.tobytes()
    out=change(base);assert selected(out,'HOLA Ω')[0]['editable']


@pytest.mark.parametrize('options',[{}, {'family':'sans','style':'bad','size':12},{'family':'sans','style':'regular','size':False},{'family':'original','style':'bold','size':12}])
def test_bad_options_never_publish_partial_format(options):
    with pytest.raises(DocumentError):apply(create(),options)


def test_preview_and_automatic_pagination_use_the_same_format():
    options={'family':'mono','style':'keep','size':12};report=apply(create(),options,words=20,width=130,height=30,paginate=True,preview=True);assert report['formatted'] and report['added_pages']>0
    out,actual=apply(create(),options,words=20,width=130,height=30,paginate=True)
    with f.open(stream=out) as d:assert len(d)==3+actual['added_pages'] and sum(p.get_text().count('Ω') for p in d)==20


@pytest.mark.parametrize('classes',[False,True])
def test_reformatting_a_saved_declared_line_updates_again(classes):
    with f.open(stream=source(tagged=True)) as d:
        t=tree(d);leaf=next(iter(t.records));root=f.mupdf.pdf_to_num(t.root)
        if classes:d.xref_set_key(root,'ClassMap','<</Shared <</O/Layout /FontFamily (Helvetica) /FontSize 16>>>>');d.xref_set_key(leaf,'C','/Shared')
        else:d.xref_set_key(leaf,'A','<</O/Layout /FontFamily (Helvetica) /FontSize 16>>')
        base=d.tobytes()
    out=change(base,text='HELLO');again=change(out,text='HOLA Ω',family='mono');assert selected(again,'HOLA Ω')[0]['editable']


def test_inherited_declaration_cannot_change_unselected_children():
    with f.open(stream=create()) as d:
        t=tree(d);paragraph=next(k for k,r in t.records.items() if len(t.refs[k])==2);d.xref_set_key(paragraph,'A','<</O/Layout /FontFamily (Helvetica)>>');base=d.tobytes()
    with f.open(stream=base) as d:r=next(r for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text']);b=r['bbox'];box=[b[0],b[1],b[2]-b[0],b[3]-b[1]]
    from backend.styled_text import replace_styled
    with pytest.raises(DocumentError,match='no seleccionado'):replace_styled(base,[],0,box,[{'id':r['id'],'text':'HOLA Ω','format':{'family':'sans','style':'bold','size':12}}])
    out,_=apply(base,{'family':'mono','style':'keep','size':12});assert out


@pytest.mark.parametrize('classes',[False,True])
@pytest.mark.parametrize('bad',['/FontFamily []','/FontSize -1','/FontWeight 55','/FontStyle/Sideways'])
def test_malformed_declarations_are_protected(classes,bad):
    with f.open(stream=source(tagged=True)) as d:
        t=tree(d);leaf=next(iter(t.records));root=f.mupdf.pdf_to_num(t.root);value='<</O/Layout '+bad+'>>'
        if classes:d.xref_set_key(root,'ClassMap','<</Shared '+value+'>>');d.xref_set_key(leaf,'C','/Shared')
        else:d.xref_set_key(leaf,'A',value)
        base=d.tobytes()
    r,_=selected(base);assert not r['format_editable']
    with pytest.raises(DocumentError):change(base)


def test_shared_attribute_dictionary_is_cloned_for_selected_node_only():
    with f.open(stream=create()) as d:
        t=tree(d);spans=[k for k,r in t.records.items() if f.mupdf.pdf_to_name(f.mupdf.pdf_dict_gets(r['object'],'S'))=='Span'];attr=d.get_new_xref();d.update_object(attr,'<</O/Layout /FontFamily (Helvetica)>>')
        for node in spans:d.xref_set_key(node,'A',f'{attr} 0 R')
        base=d.tobytes()
    # Edit only the first Span; the second one must retain the shared declaration.
    with f.open(stream=base) as d:r=next(r for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text']);b=r['bbox'];box=[b[0],b[1],b[2]-b[0],b[3]-b[1]]
    from backend.styled_text import replace_styled
    out=replace_styled(base,[],0,box,[{'id':r['id'],'text':'HI','format':{'family':'sans','style':'bold','size':12}}])
    with f.open(stream=out) as d:
        t=tree(d);a=t.owners[(d[0].xref,0,1)][0];b=t.owners[(d[0].xref,0,2)][0];assert d.xref_get_key(a,'A/FontFamily')==('string','DejaVu Sans') and d.xref_get_key(b,'A/FontFamily')==('string','Helvetica')


@pytest.mark.parametrize('rotation',[90,180,270])
def test_formatted_paragraph_keeps_page_rotation(rotation):
    with f.open(stream=create()) as d:d[0].set_rotation(rotation);base=d.tobytes()
    out,_=apply(base,{'family':'sans','style':'keep','size':12})
    with f.open(stream=out) as d:assert d[0].rotation==rotation
