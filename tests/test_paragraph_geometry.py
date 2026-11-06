"""Saved geometry must describe exact selected owners, not nearby text."""
import pytest
import pymupdf as f
from backend.semantic_text import tree
from backend.text_typography import declarations
from backend.native_text import native_model
from backend.original_reflow import inspect
from backend.affine_reflow import reflow
from backend.engine import DocumentError
from scripts.create_tagged_paragraph_sample import create


def sample(classes=False,container=False,rotation=0):
    with f.open(stream=create()) as d:
        t=tree(d);n=f.mupdf;rows=[r for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']]
        owners={t.owners[(d[0].xref,0,code)][0]:[row] for code,row in zip([1,2],rows)}
        if container:owners={next(k for k in t.records if len(t.refs[k])==2):rows}
        for i,(owner,group) in enumerate(owners.items()):
            box=f.Rect(group[0]['bbox'])
            for row in group[1:]:box|=f.Rect(row['bbox'])
            box=(box+(-1,-1,1,1))*~d[0].transformation_matrix
            attr='<</O/Layout /BBox ['+' '.join(str(v) for v in box)+f'] /Width {box.width} /Height {box.height} /FontFamily(Helvetica)>>'
            if classes:
                root=n.pdf_to_num(t.root)
                if i==0:d.xref_set_key(root,'ClassMap','<<>>')
                d.xref_set_key(root,f'ClassMap/Shared{i}',attr);d.xref_set_key(owner,'C',f'/Shared{i}')
            else:d.xref_set_key(owner,'A',attr)
        d[0].set_rotation(rotation);return d.tobytes()


def change(base,formatting=None,words=3,width=130,height=160,continuations=None,paginate=False,preview=False):
    with f.open(stream=base) as d:
        d[0].set_rotation(0);row=next(r for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text'])
    m=inspect(base,[],0,row['origin'],row['text']);assert m['original_available']
    runs=[{'id':r['id'],'text':('HELLO '*words if i==0 else 'TEXT '*words)} for i,r in enumerate(m['runs'])]
    return reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),width,height,preview,m['ids'],runs,continuations=continuations,paginate=paginate,formatting=formatting)


def check_boxes(data):
    with f.open(stream=data) as d:
        d[0].set_rotation(0);n=f.mupdf;t=tree(d);rows=native_model(d,0,d[0].rect)[1]
        for owner,record in t.records.items():
            for _,_,_,attr in declarations(d,record['object']):
                box=n.pdf_dict_gets(attr,'BBox')
                if n.pdf_is_null(box):continue
                actual=f.Rect([n.pdf_to_real(n.pdf_array_get(box,i)) for i in range(4)])
                covered=[]
                for row in rows:
                    leaf=row['_semantic_identity']
                    if owner in t.records[leaf]['chain']+[leaf]:covered.append(row)
                assert covered
                expected=f.Rect()
                for row in covered:expected|=f.Rect(row['bbox'])*~d[0].transformation_matrix
                assert list(actual)==pytest.approx(list(expected),abs=.05)
                assert n.pdf_to_real(n.pdf_dict_gets(attr,'Width'))==pytest.approx(actual.width,abs=.02)
                assert n.pdf_to_real(n.pdf_dict_gets(attr,'Height'))==pytest.approx(actual.height,abs=.02)
                assert all(row['editable'] for row in covered)


@pytest.mark.parametrize('classes',[False,True])
@pytest.mark.parametrize('container',[False,True])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_saved_boxes_follow_reflow_and_isolate_classes(classes,container,rotation):
    base=sample(classes,container,rotation);out,report=change(base);assert report['tagged_native'];check_boxes(out)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert a[0].search_for('NEIGHBOR UNCHANGED')==b[0].search_for('NEIGHBOR UNCHANGED')
        if classes:assert a.xref_get_key(f.mupdf.pdf_to_num(tree(a).root),'ClassMap/Shared0')==b.xref_get_key(f.mupdf.pdf_to_num(tree(b).root),'ClassMap/Shared0')


@pytest.mark.parametrize('classes',[False,True])
@pytest.mark.parametrize('family',['sans','serif','mono'])
def test_format_and_geometry_are_updated_together(classes,family):
    out,_=change(sample(classes),{'family':family,'style':'keep','size':22},words=2,width=200,height=170);check_boxes(out)
    with f.open(stream=out) as d:
        for rec in tree(d).records.values():
            for _,_,_,attr in declarations(d,rec['object']):
                if not f.mupdf.pdf_is_null(f.mupdf.pdf_dict_gets(attr,'BBox')):assert f.mupdf.pdf_to_text_string(f.mupdf.pdf_dict_gets(attr,'FontFamily')).startswith('DejaVu')


def test_saved_geometry_can_reflow_again():
    out,_=change(sample(),words=1,width=200);again,_=change(out,words=4,width=140);check_boxes(again)


def test_geometric_continuation_preview_matches_saved_distribution():
    base=sample();args={'words':15,'width':130,'height':30,'continuations':[{'page':1,'box':[30,100,300,400]}]}
    preview=change(base,preview=True,**args);out,report=change(base,**args)
    assert preview==report and report['page_local_geometry']>0
    with f.open(stream=out) as d:assert sum(p.get_text().count('HELLO') for p in d)==15


@pytest.mark.parametrize('bad',['[0 0 1]','[0 0 1 (bad)]','[50 0 10 100]','[0 0 1e30 100]'])
def test_bad_geometry_is_protected(bad):
    with f.open(stream=sample()) as d:
        t=tree(d);owner=t.owners[(d[0].xref,0,1)][0];d.xref_set_key(owner,'A/BBox',bad);base=d.tobytes()
    with pytest.raises(DocumentError):change(base)


def test_ancestor_with_other_content_cannot_be_resized():
    with f.open(stream=sample(container=True)) as d:
        t=tree(d);document=next(k for k,r in t.records.items() if f.mupdf.pdf_to_name(f.mupdf.pdf_dict_gets(r['object'],'S'))=='Document');d.xref_set_key(document,'A','<</O/Layout /BBox [0 0 650 800]>>');base=d.tobytes()
    with pytest.raises(DocumentError):change(base)


def test_formatted_manual_continuation_and_preview_match():
    fmt={'family':'serif','style':'keep','size':12};dest=[{'page':1,'box':[30,100,300,400]}]
    preview=change(create(),fmt,words=15,width=130,height=30,continuations=dest,preview=True)
    out,report=change(create(),fmt,words=15,width=130,height=30,continuations=dest);assert preview==report and len(report['regions'])==2
    with f.open(stream=out) as d:
        assert sum(p.get_text().count('HELLO') for p in d)==15
        for number in [0,1]:
            rows=[r for r in native_model(d,number,d[number].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']]
            assert rows and all(r['editable'] and r['size']==pytest.approx(12) and r['font'].startswith('DejaVuSerif') for r in rows)
