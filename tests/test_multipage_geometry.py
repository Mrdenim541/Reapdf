"""Continuation geometry is page-local, reeditable, and preserves the logical P."""
import pytest
import pymupdf as f
from backend.semantic_text import tree
from backend.text_typography import declarations
from backend.text_geometry import validate
from backend.native_text import native_model
from backend.original_reflow import inspect
from backend.affine_reflow import reflow
from tests.test_paragraph_geometry import sample,change


def check(data):
    with f.open(stream=data) as d:
        for page in d:page.set_rotation(0)
        t=tree(d);n=f.mupdf;all_rows=[(p.number,row) for p in d if p.get_text().strip() for row in native_model(d,p.number,p.rect)[1]];found=0
        for owner,rec in t.records.items():
            for _,_,_,attr in declarations(d,rec['object']):
                if n.pdf_to_name(n.pdf_dict_gets(attr,'O'))!='Layout':continue
                box=validate(attr)
                if box is None:continue
                covered=[(page,row) for page,row in all_rows if owner in t.records[row['_semantic_identity']]['chain']+[row['_semantic_identity']]]
                assert covered and len({page for page,_ in covered})==1
                page=covered[0][0];assert {pg for pg,_,_ in t.refs[owner]}=={d[page].xref}
                actual=f.Rect()
                for _,row in covered:
                    assert row['editable'];actual|=f.Rect(row['bbox'])*~d[page].transformation_matrix
                assert list(box)==pytest.approx(list(actual),abs=.05)
                for key,value in [('Width',box.width),('Height',box.height)]:
                    raw=n.pdf_dict_gets(attr,key)
                    if n.pdf_is_number(raw):assert n.pdf_to_real(raw)==pytest.approx(value,abs=.05)
                found+=1
        assert found>=2
        return found


@pytest.mark.parametrize('classes',[False,True])
@pytest.mark.parametrize('container',[False,True])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('automatic',[False,True])
def test_continuation_keeps_exact_local_geometry_styles_and_unrelated_pages(classes,container,rotation,automatic):
    base=sample(classes,container,rotation)
    kwargs={'paginate':True} if automatic else {'continuations':[{'page':1,'box':[30,100,300,400]}]}
    out,report=change(base,words=15,width=130,height=30,**kwargs);assert report['page_local_geometry']>=2;check(out)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert sum(p.get_text().count('HELLO') for p in b)==15 and sum(p.get_text().count('TEXT') for p in b)==15
        assert a[0].search_for('NEIGHBOR UNCHANGED')==b[0].search_for('NEIGHBOR UNCHANGED')
        if automatic:assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        else:assert a[2].get_pixmap().samples==b[2].get_pixmap().samples
        ta,tb=tree(a),tree(b);roles=lambda t:sum(f.mupdf.pdf_to_name(f.mupdf.pdf_dict_gets(r['object'],'S'))=='P' for r in t.records.values())
        assert roles(ta)==roles(tb)
        if classes:assert a.xref_get_key(f.mupdf.pdf_to_num(ta.root),'ClassMap/Shared0')==b.xref_get_key(f.mupdf.pdf_to_num(tb.root),'ClassMap/Shared0')


@pytest.mark.parametrize('family',['sans','serif','mono'])
@pytest.mark.parametrize('container',[False,True])
def test_font_and_size_are_coordinated_with_migrated_boxes(family,container):
    fmt={'family':family,'style':'keep','size':12};out,report=change(sample(classes=True,container=container),fmt,words=15,width=130,height=30,continuations=[{'page':1,'box':[30,100,300,400]}]);assert report['formatted'];check(out)
    with f.open(stream=out) as d:
        rows=[r for p in d if p.get_text().strip() for r in native_model(d,p.number,p.rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']]
        assert all(r['size']==pytest.approx(12) and r['font'].startswith('DejaVu') and r['editable'] for r in rows)


def edit_page(base,page):
    with f.open(stream=base) as d:
        d[page].set_rotation(0);row=next(r for r in native_model(d,page,d[page].rect)[1] if 'HELLO' in r['text'])
    m=inspect(base,[],page,row['origin'],row['text']);assert m['original_available']
    runs=[{'id':r['id'],'text':r['text'].replace('HELLO','HOLA')} for r in m['runs']]
    return reflow(base,[],page,m['box'],m['ids'][0],''.join(r['text'] for r in runs),m['local_width']+2,m['local_height']+20,False,m['ids'],runs)


@pytest.mark.parametrize('page',[0,1])
def test_saved_page_fragment_is_editable_without_touching_the_other_fragment(page):
    first,_=change(sample(container=True),words=15,width=130,height=30,continuations=[{'page':1,'box':[30,100,300,400]}]);out,_=edit_page(first,page);check(out)
    with f.open(stream=first) as a,f.open(stream=out) as b:
        assert 'HOLA' in b[page].get_text()
        assert a[1-page].get_pixmap().samples==b[1-page].get_pixmap().samples
        assert a[1-page].get_text()==b[1-page].get_text()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_destination_geometry_uses_its_own_default_user_space(rotation,crop):
    with f.open(stream=sample(container=True)) as d:
        d[1].set_rotation(rotation)
        if crop:
            d[0].set_cropbox(f.Rect(10,10,630,780));d[1].set_cropbox(f.Rect(20,20,620,770))
        base=d.tobytes()
    out,_=change(base,words=15,width=130,height=30,continuations=[{'page':1,'box':[30,100,300,400]}]);check(out)
    with f.open(stream=base) as a,f.open(stream=out) as b:assert a[1].rotation==b[1].rotation and a[1].cropbox==b[1].cropbox


@pytest.mark.parametrize('dimension',['Auto','missing'])
def test_optional_dimensions_keep_auto_or_absence_in_migrated_leaves(dimension):
    with f.open(stream=sample()) as d:
        t=tree(d)
        for code in [1,2]:
            owner=t.owners[(d[0].xref,0,code)][0]
            for key in ['Width','Height']:d.xref_set_key(owner,'A/'+key,'/Auto' if dimension=='Auto' else 'null')
        base=d.tobytes()
    out,_=change(base,words=15,width=130,height=30,continuations=[{'page':1,'box':[30,100,300,400]}]);check(out)
    with f.open(stream=out) as d:
        for rec in tree(d).records.values():
            for _,_,_,attr in declarations(d,rec['object']):
                if validate(attr) is None:continue
                for key in ['Width','Height']:
                    v=f.mupdf.pdf_dict_gets(attr,key)
                    assert f.mupdf.pdf_is_null(v) if dimension=='missing' else f.mupdf.pdf_to_name(v)=='Auto'


def test_overlapping_auto_and_numeric_declarations_cannot_silently_override_each_other():
    from backend.engine import DocumentError
    with f.open(stream=sample()) as d:
        t=tree(d);owner=next(k for k,r in t.records.items() if len(t.refs[k])==2 and f.mupdf.pdf_to_name(f.mupdf.pdf_dict_gets(r['object'],'S'))=='P')
        d.xref_set_key(owner,'A','<</O/Layout /BBox[150 350 400 450]/Width/Auto/Height/Auto>>');base=d.tobytes()
    with pytest.raises(DocumentError,match='dimensiones incompatibles'):change(base,words=15,width=130,height=30,continuations=[{'page':1,'box':[30,100,300,400]}])


@pytest.mark.parametrize('erased',[0,1])
@pytest.mark.parametrize('continued',[False,True])
def test_erasing_a_whole_style_clears_its_stale_box_and_retains_the_paragraph(erased,continued):
    base=sample()
    with f.open(stream=base) as d:row=next(r for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text'])
    m=inspect(base,[],0,row['origin'],row['text']);runs=[{'id':r['id'],'text':'' if i==erased else ('HELLO ' if i==0 else 'TEXT ')*15} for i,r in enumerate(m['runs'])]
    kwargs={'continuations':[{'page':1,'box':[30,100,300,400]}]} if continued else {}
    out,report=reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),130,30 if continued else 400,False,m['ids'],runs,**kwargs)
    if continued:check(out)
    with f.open(stream=out) as d:
        assert sum(p.get_text().count('TEXT' if erased==0 else 'HELLO') for p in d)==15
        t=tree(d)
        for owner,rec in t.records.items():
            for _,_,_,attr in declarations(d,rec['object']):
                if validate(attr) is not None:assert t.refs[owner]
