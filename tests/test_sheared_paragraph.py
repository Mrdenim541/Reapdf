import pymupdf as f
import pytest
from backend.original_reflow import inspect
from backend.affine_reflow import reflow
from backend.affine_mixed_reflow import inspect_selection
from backend.engine import DocumentError
from backend.native_text import native_model
from backend.affine_text import polygon,overlap
from tests.test_affine_mixed_reflow import source as original
from backend.pdf_content import operations,patch


def source(matrix=(1,0,0,1),rotation=0,form=False,shear=.35,scale=1):
    base=original(matrix,rotation,form)
    with f.open(stream=base) as doc:
        for x in range(1,doc.xref_length()):
            if not doc.xref_is_stream(x):continue
            data=doc.xref_stream(x)
            if b'(HELLO )' not in data:continue
            current=None;second=None
            for op,args,_ in operations(data):
                if op=='Tm':current=args
                if op=='Tj' and args and args[0].value==b'TEXT':second=current
            assert second is not None
            first=f.Matrix(*matrix,0,0);changed=f.Matrix(scale,0,shear,1,0,0)*first
            doc.update_stream(x,patch(data,[(second[i].start,second[i].end,format(changed[i],'.8f').encode()) for i in range(4)]))
        return doc.tobytes()


def model(base):
    with f.open(stream=base) as doc:
        p=doc[0];p.set_rotation(0);_,rows=native_model(doc,0,p.rect)
        row=next(r for r in rows if r['text']=='HELLO ')
        return inspect(base,[],0,row['origin'],row['text'])


def apply(base,continuation=False,paginate=False,width=150,height=200,texts=('HELLO HELLO ','TEXT TEXT')):
    m=model(base);assert m['variable_shear'] and m['mixed']
    with f.open(stream=base) as doc:destination=len(doc)-1
    runs=[{'id':r['id'],'text':texts[i]} for i,r in enumerate(m['runs'])]
    return reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),width,height,False,m['ids'],runs,False,[{'page':destination,'box':[40,100,520,600]}] if continuation else None,paginate)


@pytest.mark.parametrize('matrix',[(1,0,0,1),(1,.25,.15,1),(0,1,-1,0),(-1,.1,.1,1)])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('form',[False,True])
def test_reflow_retains_distinct_style_transforms_fonts_and_unselected_appearances(matrix,rotation,form):
    base=source(matrix,rotation,form);out,report=apply(base);assert report['variable_shear'] and report['preserves_run_transforms']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].rotation==rotation and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        a[0].set_rotation(0);b[0].set_rotation(0)
        assert a[0].search_for('NEIGHBOR UNCHANGED')==b[0].search_for('NEIGHBOR UNCHANGED')
        _,before=native_model(a,0,a[0].rect);_,after=native_model(b,0,b[0].rect)
        selected=set(model(base)['ids'])
        expected={(r['font'],r['color'],round(r['display_size'],3),tuple(round(v,4) for v in r['_geometry']['matrix'][:4])) for r in before if r['id'] in selected}
        edited=[r for r in after if r['text'].startswith('HELLO HELLO') or r['text'].startswith('TEXT TEXT')]
        assert len(edited)>=2
        assert {(r['font'],r['color'],round(r['display_size'],3),tuple(round(v,4) for v in r['_geometry']['matrix'][:4])) for r in edited}==expected
        assert all(overlap(polygon(x['_geometry']),polygon(y['_geometry']))<.05 for i,x in enumerate(edited) for y in edited[i+1:])
        if form:
            # A reused smaller Form instance stays intact at the bottom/right.
            clip=f.Rect(550,700,875,1100)
            assert a[0].get_pixmap(clip=clip).samples==b[0].get_pixmap(clip=clip).samples


@pytest.mark.parametrize('shear,scale',[(-.5,1),(.7,1.4),(-.4,.65)])
def test_original_horizontal_scale_and_shear_survive(shear,scale):
    base=source(shear=shear,scale=scale);out,report=apply(base);assert report['complete']


@pytest.mark.parametrize('paginate',[False,True])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('form',[False,True])
def test_continuation_or_automatic_pages_keeps_style_transforms(paginate,rotation,form):
    base=source(rotation=rotation,form=form)
    with f.open(stream=base) as d:d.new_page(width=650,height=800);base=d.tobytes();original_pages=len(d)
    out,report=apply(base,continuation=not paginate,paginate=paginate,height=30,texts=('HELLO '*15,'TEXT '*12))
    assert len(report['regions'])>1 and report['complete']
    with f.open(stream=out) as doc:
        texts=''.join(p.get_text() for p in doc)
        assert texts.count('HELLO')==15+2*int(form) and texts.count('TEXT')==12+2*int(form)
        assert len(doc)>original_pages if paginate else len(doc)==original_pages


def test_overflow_unsupported_glyph_and_incompatible_baseline_do_not_publish():
    base=source()
    with pytest.raises(DocumentError):apply(base,height=10,texts=('HELLO '*30,'TEXT '*30))
    with pytest.raises(DocumentError):apply(base,texts=('漢','TEXT'))
    with f.open(stream=base) as d:
        x=d[0].get_contents()[-1];data=d.xref_stream(x);second=[a for op,a,_ in operations(data) if op=='Tm'][1];d.update_stream(x,patch(data,[(second[1].start,second[1].end,b'.5')]));bad=d.tobytes()
        p=d[0];_,rows=native_model(d,0,p.rect);refs=[{'origin':r['origin'],'text':r['text']} for r in rows if r['text'] in ['HELLO ','TEXT']]
    with pytest.raises(DocumentError):inspect_selection(bad,[],0,refs)


def test_variable_shear_across_separate_form_paths_is_copy_on_write():
    from tests.test_cross_path_reflow import source as cross,refs
    base=cross()
    with f.open(stream=base) as d:
        for x in range(1,d.xref_length()):
            if not d.xref_is_stream(x):continue
            data=d.xref_stream(x)
            if b'(TEXT)' not in data:continue
            tm=next(args for op,args,_ in operations(data) if op=='Tm');matrix=f.Matrix(1,0,.4,1,0,0)*f.Matrix(1,.25,.15,1,0,0)
            d.update_stream(x,patch(data,[(tm[i].start,tm[i].end,format(matrix[i],'.8f').encode()) for i in range(4)]))
        base=d.tobytes()
    m=inspect_selection(base,[],0,refs(base));assert m['variable_shear'] and m['source_paths']==2
    runs=[{'id':r['id'],'text':'HELLO HELLO ' if i==0 else 'TEXT TEXT'} for i,r in enumerate(m['runs'])]
    result,report=reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),150,100,False,m['ids'],runs,True)
    with f.open(stream=base) as a,f.open(stream=result) as b:
        clip=f.Rect(0,580,650,800);assert a[0].get_pixmap(clip=clip).samples==b[0].get_pixmap(clip=clip).samples
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples


@pytest.mark.parametrize('char,word,kern',[(1.2,3,False),(-.3,2,False),(0,0,True)])
@pytest.mark.parametrize('form',[False,True])
def test_variable_shear_retains_native_tracking_word_spacing_and_kern(char,word,kern,form):
    base=source(form=form)
    with f.open(stream=base) as d:
        for x in range(1,d.xref_length()):
            if not d.xref_is_stream(x):continue
            data=d.xref_stream(x)
            if b'(HELLO )' not in data:continue
            data=data.replace(b'BT ',f'BT {char} Tc {word} Tw '.encode())
            if kern:data=data.replace(b'(HELLO ) Tj',b'[(HE) -60 (LLO )] TJ')
            d.update_stream(x,data)
        base=d.tobytes();_,rows=native_model(d,0,d[0].rect)
        refs=[{'origin':r['origin'],'text':r['text']} for r in rows if r['text'] in ['HELLO ','TEXT']][:2]
    m=inspect_selection(base,[],0,refs);assert m['variable_shear'];runs=[{'id':r['id'],'text':'HELLO HELLO ' if i==0 else 'TEXT TEXT'} for i,r in enumerate(m['runs'])]
    result,_=reflow(base,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),170,150,False,m['ids'],runs,True)
    with f.open(stream=result) as d:
        _,after=native_model(d,0,d[0].rect)
        if kern:assert any(any(r['_spacing']['kern']) for r in after if r['text'].startswith('HELLO'))


def test_saved_variable_shear_paragraph_can_be_opened_and_edited_again():
    base=source();result,_=apply(base)
    with f.open(stream=result) as d:
        _,rows=native_model(d,0,d[0].rect);anchor=next(r for r in rows if r['text'].startswith('HELLO'))
    m=inspect(result,[],0,anchor['origin'],anchor['text']);assert m['variable_shear'] and m['mixed'] and len(m['ids'])==2
    runs=[{'id':r['id'],'text':'HELLO ' if i==0 else 'TEXT'} for i,r in enumerate(m['runs'])]
    again,_=reflow(result,[],0,m['box'],m['ids'][0],''.join(r['text'] for r in runs),160,100,False,m['ids'],runs)
    with f.open(stream=again) as d:assert d[0].get_text().count('HELLO')==d[0].get_text().count('TEXT')==1


@pytest.mark.parametrize('paginate',[False,True])
def test_inline_api_discovers_previews_and_applies_variable_shear_without_mutating_source(paginate):
    from fastapi.testclient import TestClient
    from backend.app import app,document_path
    from scripts.create_sheared_paragraph_sample import create
    base=create()
    with f.open(stream=base) as d:anchor=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HELLO ')
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('sheared.pdf',base,'application/pdf')}).json()
        response=client.post(f"/api/documents/{doc['id']}/inline-block",json={'operations':[],'page':0,'origin':anchor['origin'],'text':anchor['text']});assert response.status_code==200,response.text
        m=response.json();assert m['variable_shear'] and len(m['runs'])==2
        runs=[{'id':r['id'],'text':'HELLO '*8 if i==0 else 'TEXT '*6} for i,r in enumerate(m['runs'])]
        plan={'operations':[],'page':0,'box':m['box'],'id':m['ids'][0],'ids':m['ids'],'runs':runs,'text':''.join(r['text'] for r in runs),'width':160,'height':30 if paginate else 250,'paginate':paginate}
        url=f"/api/documents/{doc['id']}/reflow-affine";preview=client.post(url,json={**plan,'preview':True});assert preview.status_code==200,preview.text;assert preview.json()['variable_shear']
        applied=client.post(url,json=plan);assert applied.status_code==200,applied.text
        output=client.post(f"/api/documents/{applied.json()['id']}/export",json={'operations':[]}).content
        with f.open(stream=output) as d:
            text=''.join(p.get_text() for p in d);assert text.count('HELLO')==8 and text.count('TEXT')==6
        assert document_path(doc['id']).read_bytes()==base
