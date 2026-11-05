from functools import lru_cache
import pytest
import pymupdf as f
from backend.engine import DocumentError
from backend.basic_tagging import candidates,create
from backend.original_reflow import inspect
from backend.affine_reflow import reflow
from backend.native_text import native_model
from backend.tagged_paragraph import Paragraph
from backend.tagged_text_integrity import snapshot
from backend.structure_editing import reading_preview
from scripts.create_sheared_paragraph_sample import create as plain


@lru_cache(maxsize=4)
def source(rotation=0):
    base=plain();entries=candidates(base,[])['entries']
    base=create(base,[],[{'id':r['id'],'role':'P'} for r in entries],reviewed=True)[0]
    with f.open(stream=base) as d:
        d[0].set_rotation(rotation);return d.tobytes()


def model(base,number=0):
    with f.open(stream=base) as d:
        d[number].set_rotation(0)
        row=next(r for r in native_model(d,number,d[number].rect)[1] if 'HELLO' in r['text'])
    return inspect(base,[],number,row['origin'],row['text'])


def apply(base,*,number=0,hello=2,tail=2,**kw):
    m=model(base,number);runs=[{'id':r['id'],'text':('HELLO '*hello if 'HELLO' in r['text'] else 'TEXT '*tail)} for r in m['runs']]
    return reflow(base,[],number,m['box'],m['ids'][0],''.join(r['text'] for r in runs),kw.pop('width',160),kw.pop('height',150),False,m['ids'],runs,**kw)


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_tagged_styles_discovered_from_mouse_anchor_reflow_and_reedit(rotation):
    base=source(rotation);m=model(base)
    assert m.get('tagged_paragraph') and m['mixed'] and m['complete_object_selection'] and len(m['runs'])==2
    out,report=apply(base)
    assert report['tagged_native'] and report['variable_shear']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert snapshot(a,0)==snapshot(b,0)
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert b[0].rotation==rotation
    m2=model(out);assert m2['tagged_paragraph'] and len(m2['runs'])>=2
    again,_=apply(out,hello=1,tail=1)
    assert reading_preview(again,[],0)['untagged_blocks']==0


@pytest.mark.parametrize('paginate',[False,True])
def test_continuation_keeps_logical_parent_and_new_page_mcid(paginate):
    base=source()
    kwargs={'paginate':True} if paginate else {'continuations':[{'page':2,'box':[30,30,570,700]}]}
    out,report=apply(base,hello=10,tail=8,width=160,height=40,**kwargs)
    assert report['tagged_native']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        for number in report['pages']:
            b[number].set_rotation(0);rows=native_model(b,number,b[number].rect)[1]
            row=next(r for r in rows if 'HELLO' in r['text'] or 'TEXT' in r['text'])
            group=Paragraph(b,number,rows,row);assert len(group.rows)>0
            assert reading_preview(out,[],number)['untagged_blocks']==0
    assert (len(report['pages'])>1)


def test_partial_selection_does_not_erase_other_style():
    base=source();m=model(base);r=m['runs'][0]
    with pytest.raises(DocumentError,match='completo'):
        reflow(base,[],0,m['box'],m['ids'][0],'HELLO',160,150,False,m['ids'][:1],[{'id':r['id'],'text':'HELLO'}])


def split_source(kind='same_leaf'):
    """Separate native objects and MCIDs; tags retain the association."""
    from backend.tagged_image_integrity import context
    from backend.pdf_content import set_content
    with f.open(stream=source()) as d:
        ctx=context(d,0);n=f.mupdf;scope=ctx['scopes'][1];content=d[0].read_contents()
        middle=content.index(b'/heit ',scope['open_end'])
        content=content[:middle]+b'ET EMC /Span <</MCID 2>> BDC BT '+content[middle:]
        set_content(d,d[0],content)
        leaf=n.pdf_to_num(n.pdf_array_get(ctx['parent_row'][3],1));pg=d[0].xref
        if kind=='same_leaf':
            d.xref_set_key(leaf,'K','[1 2]');owners=[leaf,leaf]
        else:
            children=[]
            for code in [1,2]:
                child=d.get_new_xref();d.update_object(child,f'<< /Type/StructElem /S/Span /P {leaf} 0 R /Pg {pg} 0 R /K {code} >>');children.append(child)
            d.xref_set_key(leaf,'K','['+' '.join(f'{c} 0 R' for c in children)+']');owners=children
        arr=ctx['parent_row'][3];pdf=f._as_pdf_document(d)
        n.pdf_array_put(arr,1,n.pdf_new_indirect(pdf,owners[0],0));n.pdf_array_push(arr,n.pdf_new_indirect(pdf,owners[1],0))
        return d.tobytes()


@pytest.mark.parametrize('kind',['same_leaf','span_children'])
@pytest.mark.parametrize('paginate',[None,False,True])
def test_distinct_mcids_and_span_siblings_keep_order_through_save(kind,paginate):
    base=split_source(kind);m=model(base);assert m['tagged_paragraph'] and len(m['ids'])==2
    kwargs={} if paginate is None else {'paginate':True} if paginate else {'continuations':[{'page':2,'box':[30,30,570,700]}]}
    out,report=apply(base,hello=6,tail=4,height=150 if paginate is None else 40,**kwargs)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        if paginate is None:assert snapshot(a,0)==snapshot(b,0)
        for number in report['pages']:
            assert reading_preview(out,[],number)['untagged_blocks']==0
            m2=model(out,number);assert m2['tagged_paragraph']
    if paginate is not None:
        destination=report['pages'][-1]
        again,_=apply(out,number=destination,hello=1,tail=1,width=500,height=400)
        assert reading_preview(again,[],destination)['untagged_blocks']==0


@pytest.mark.parametrize('kind',['actualtext','alt','bbox','class','namespace','parent','parenttree','duplicate_mcid','reverse_order','unowned_show','figure'])
def test_ambiguous_or_stale_semantics_are_refused_atomically(kind):
    from backend.tagged_image_integrity import context
    from backend.pdf_content import set_content
    original=split_source();m=model(original)
    with f.open(stream=original) as d:
        ctx=context(d,0);n=f.mupdf;leaf=n.pdf_to_num(n.pdf_array_get(ctx['parent_row'][3],1))
        if kind=='actualtext':d.xref_set_key(leaf,'ActualText','(Alternative)')
        elif kind=='alt':d.xref_set_key(leaf,'Alt','(Alternative)')
        elif kind=='bbox':d.xref_set_key(leaf,'A','<< /O/Layout /BBox [0 0 100 100] >>')
        elif kind=='class':d.xref_set_key(leaf,'C','/Unknown')
        elif kind=='namespace':d.xref_set_key(leaf,'NS','<< /NS (http://example.invalid) >>')
        elif kind=='parent':d.xref_set_key(leaf,'P',f'{d.pdf_catalog()} 0 R')
        elif kind=='parenttree':n.pdf_array_put(ctx['parent_row'][3],2,n.PdfObj())
        elif kind=='duplicate_mcid':set_content(d,d[0],d[0].read_contents().replace(b'/MCID 2',b'/MCID 1'))
        elif kind=='reverse_order':d.xref_set_key(leaf,'K','[2 1]')
        elif kind=='unowned_show':set_content(d,d[0],d[0].read_contents().replace(b'/MCID 2',b'/MCID 9'))
        else:d.xref_set_key(leaf,'S','/Figure')
        base=d.tobytes()
    runs=[{'id':r['id'],'text':r['text']} for r in m['runs']]
    with pytest.raises(DocumentError):reflow(base,[],0,m['box'],m['ids'][0],m['text'],160,150,False,m['ids'],runs)
    with f.open(stream=base) as d:assert d[0].get_text()


def test_explicit_selection_obeys_semantic_order_and_api_preview_is_immutable():
    from backend.affine_mixed_reflow import inspect_selection
    from fastapi.testclient import TestClient
    from backend.app import app
    base=split_source('span_children');m=model(base)
    with f.open(stream=base) as d:
        rows=native_model(d,0,d[0].rect)[1];refs=[{'origin':r['origin'],'text':r['text']} for i in m['ids'] for r in rows if r['id']==i]
    selected=inspect_selection(base,[],0,refs);assert selected['tagged_paragraph'] and selected['explicit_selection']
    with pytest.raises(DocumentError):inspect_selection(base,[],0,list(reversed(refs)))
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('Tagged.pdf',base,'application/pdf')}).json()
        url='/api/documents/'+doc['id']+'/reflow-affine';runs=[{'id':r['id'],'text':r['text']} for r in m['runs']]
        payload={'page':0,'box':m['box'],'id':m['ids'][0],'ids':m['ids'],'text':m['text'],'runs':runs,'width':160,'height':150}
        response=c.post(url,json={**payload,'preview':True});assert response.status_code==200 and response.json()['tagged_native']
        applied=c.post(url,json=payload);assert applied.status_code==200 and applied.json()['reflow_report']['tagged_native'] and applied.json()['id']!=doc['id']


def test_overflow_glyph_and_obstacle_are_refused_without_partial_pdf():
    base=source()
    with pytest.raises(DocumentError):apply(base,hello=30,tail=30,width=10,height=10)
    m=model(base);runs=[{'id':r['id'],'text':'漢'} for r in m['runs']]
    with pytest.raises(DocumentError):reflow(base,[],0,m['box'],m['ids'][0],'漢漢',160,150,False,m['ids'],runs)
    with f.open(stream=base) as d:
        d[0].draw_rect(f.Rect(190,390,500,490));blocked=d.tobytes()
    with pytest.raises(DocumentError):apply(blocked)


def test_large_42_page_tag_graph_can_edit_a_verified_paragraph_without_losing_other_nodes():
    from scripts.create_tagged_paragraph_sample import create as sample
    from backend.tagged_image_integrity import context
    with f.open(stream=sample()) as d:
        ctx=context(d,0);n=f.mupdf;document=n.pdf_to_num(n.pdf_array_get(n.pdf_dict_gets(ctx['root'],'K'),0));extra=[]
        for _ in range(39):
            pg=d.new_page(width=650,height=800).xref
            for _ in range(110):
                identity=d.get_new_xref();d.update_object(identity,f'<< /Type/StructElem /S/P /P {document} 0 R /Pg {pg} 0 R /K [] >>');extra.append(identity)
        old=d.xref_get_key(document,'K')[1];d.xref_set_key(document,'K',old[:-1]+' '+' '.join(f'{x} 0 R' for x in extra)+']');base=d.tobytes()
    out,r=apply(base)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert len(a)==len(b)==42 and snapshot(a,0)==snapshot(b,0)
        assert snapshot(b,0)['nodes']>4200


def test_existing_metric_overlap_allows_edit_within_original_footprint_only():
    from collections import Counter
    from backend.affine_mixed_reflow import stable_key
    with f.open() as d:
        p=d.new_page(width=400,height=400)
        for i in range(5):p.insert_text((40,80+i*8),f'ITEM-{i:03d}',fontsize=7)
        plain=d.tobytes()
    entries=candidates(plain,[])['entries'];base=create(plain,[],[{'id':r['id'],'role':'P'} for r in entries],reviewed=True)[0]
    with f.open(stream=base) as d:
        _,before=native_model(d,0,d[0].rect,context=True);row=next(r for r in before if r['text']=='ITEM-002')
    m=inspect(base,[],0,row['origin'],row['text']);assert m['tagged_paragraph']
    out,_=reflow(base,[],0,m['box'],m['ids'][0],'ITEM-902',m['local_width'],m['local_height'],False,m['ids'],[{'id':m['ids'][0],'text':'ITEM-902'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert snapshot(a,0)==snapshot(b,0)
        after=native_model(b,0,b[0].rect,context=True)[1]
        assert not (Counter(stable_key(r) for r in before if r['id']!=row['id'])-Counter(stable_key(r) for r in after))
    with pytest.raises(DocumentError):reflow(base,[],0,m['box'],m['ids'][0],'ITEM-902\nITEM-903',100,100,False,m['ids'],[{'id':m['ids'][0],'text':'ITEM-902\nITEM-903'}])
