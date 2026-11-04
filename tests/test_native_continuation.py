"""Original-font atomic continuations from transformed shared Form paragraphs."""
import re,pytest,pymupdf as f
from backend.affine_mixed_reflow import inspect_selection
from backend.affine_reflow import reflow
from backend.engine import DocumentError
from tests.test_cross_path_reflow import source as cross_source,refs


def source(matrix=(1,.25,.15,1),rotation=0,nested=False,crop=False):
    with f.open(stream=cross_source(matrix,rotation,nested)) as d:
        p=d.new_page(pno=1,width=650,height=800);p.insert_text((30,40),'OTHER PAGE UNCHANGED');p.set_rotation(rotation)
        if crop:p.set_cropbox(f.Rect(10,10,p.mediabox.width-10,p.mediabox.height-10))
        d.new_page(width=650,height=800).insert_text((30,40),'UNTOUCHED FINAL PAGE');return d.tobytes()


def payload(base):
    m=inspect_selection(base,[],0,refs(base));runs=[{'id':r['id'],'text':'HELLO '*18 if i==0 else 'TEXT '*12} for i,r in enumerate(m['runs'])]
    return {'number':0,'box':m['box'],'identifier':m['ids'][0],'text':''.join(r['text'] for r in runs),'width':150,'height':40,'identifiers':m['ids'],'runs':runs,'explicit_order':True,'continuations':[{'page':1,'box':[40,150,480,450]}]}


@pytest.mark.parametrize('matrix',[(1,.25,.15,1),(0,1,-1,0),(-1,.1,.1,1),(1.4,.3,.2,.7)])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('nested',[False,True])
def test_transformed_cross_path_paragraph_continues_with_original_fonts(matrix,rotation,nested):
    base=source(matrix,rotation,nested);p=payload(base);out,report=reflow(base,[],preview=False,**p)
    assert report['complete'] and report['pages']==[0,1] and len(report['regions'])==2 and all(r['characters']>0 for r in report['regions'])
    assert sum(r['characters'] for r in report['regions'])==len(p['text'])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[2].get_pixmap().samples==b[2].get_pixmap().samples
        for i in range(2):assert a[i].rotation==b[i].rotation;a[i].set_rotation(0);b[i].set_rotation(0)
        assert a[0].search_for('NEIGHBOR UNCHANGED')==b[0].search_for('NEIGHBOR UNCHANGED') and a[1].search_for('OTHER PAGE UNCHANGED')==b[1].search_for('OTHER PAGE UNCHANGED')
        assert 'HELLO' in b[1].get_text() and 'TEXT' in b[1].get_text()
        actual=''.join(b[0].get_text().split())+''.join(b[1].get_text().split());assert actual.count('HELLO')==(19 if nested else 18) and actual.count('TEXT')==(15 if nested else 13)
        before={(s['font'],round(s['size'],3),s['color']) for bl in a[0].get_text('dict')['blocks'] for l in bl.get('lines',[]) for s in l['spans'] if s['font'] in ['Helvetica-Bold','Helvetica-Oblique']}
        after={(s['font'],round(s['size'],3),s['color']) for bl in b[1].get_text('dict')['blocks'] for l in bl.get('lines',[]) for s in l['spans']};assert after<=before|{('Helvetica',11,0)}
        assert len(b[1].get_images())==0


def test_multiple_destinations_and_cropped_rotated_page():
    base=source(rotation=90,crop=True);p=payload(base);p['continuations']=[{'page':1,'box':[40,150,300,70]},{'page':1,'box':[40,300,350,400]}];out,r=reflow(base,[],preview=False,**p)
    assert len(r['regions'])==3 and all(v['characters']>0 for v in r['regions'])
    with f.open(stream=base) as a,f.open(stream=out) as b:assert a[1].cropbox==b[1].cropbox and a[1].rotation==b[1].rotation


@pytest.mark.parametrize('bad',[[],[{'page':0,'box':[30,150,200,200]}],[{'page':True,'box':[30,150,200,200]}],[{'page':99,'box':[30,150,200,200]}],[{'page':1,'box':[30,150,9,50]}],[{'page':1,'box':[30,150,9000,50]}],[{'page':1,'box':[30,150,200,200],'replace':True}],[{'page':1,'box':[30,150,200,200]}]*2])
def test_invalid_regions_fail_without_a_document(bad):
    base=source();p=payload(base);p['continuations']=bad
    with pytest.raises(DocumentError):reflow(base,[],preview=False,**p)


@pytest.mark.parametrize('kind',['text','drawing','image','annotation','link','widget','redact','tagged','layer'])
def test_destination_is_not_allowed_to_replace_other_content(kind):
    with f.open(stream=source()) as d:
        p=d[1]
        if kind=='text':p.insert_text((100,200),'COLLISION')
        if kind=='drawing':p.draw_line((50,200),(250,200))
        if kind=='image':
            pix=f.Pixmap(f.csRGB,f.IRect(0,0,2,2),False);pix.clear_with(0);p.insert_image(f.Rect(70,180,110,210),pixmap=pix)
        if kind=='annotation':p.add_text_annot((100,200),'Collision')
        if kind=='link':p.insert_link({'kind':f.LINK_URI,'from':f.Rect(70,180,110,210),'uri':'https://example.com/'})
        if kind=='widget':
            w=f.Widget();w.field_name='Field';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(70,180,110,210);p.add_widget(w)
        if kind=='redact':p.add_redact_annot(f.Rect(5,5,15,15))
        if kind=='tagged':d.xref_set_key(d.pdf_catalog(),'StructTreeRoot','<< /Type/StructTreeRoot >>')
        if kind=='layer':d.add_ocg('Layer')
        base=d.tobytes()
    with pytest.raises(DocumentError):reflow(base,[],preview=False,**payload(base))


def test_overflow_and_unsupported_glyph_do_not_publish_partial_text():
    base=source();p=payload(base);p['continuations']=[{'page':1,'box':[40,150,40,20]}]
    with pytest.raises(DocumentError,match='no cabe'):reflow(base,[],preview=False,**p)
    p=payload(base);p['runs'][0]['text']+='漢';p['text']=''.join(r['text'] for r in p['runs'])
    with pytest.raises(DocumentError):reflow(base,[],preview=False,**p)


def test_api_preview_apply_export_then_edit_continued_text_again():
    from fastapi.testclient import TestClient
    from backend.app import app
    from backend.native_text import native_model
    base=source();p=payload(base);p['page']=p.pop('number');p['id']=p.pop('identifier');p['ids']=p.pop('identifiers')
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('Original.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']+'/reflow-affine'
        preview=c.post(url,json={**p,'preview':True});assert preview.status_code==200 and preview.json()['complete']
        edited=c.post(url,json=p);assert edited.status_code==200 and edited.json()['id']!=doc['id']
        exported=c.post('/api/documents/'+edited.json()['id']+'/export',json={'operations':[]});assert exported.status_code==200
    with f.open(stream=exported.content) as d:
        page=d[1];page.set_rotation(0);_,rows=native_model(d,1,page.rect);r=next(v for v in rows if 'TEXT' in v['text']);assert r['editable'];box=[r['bbox'][0]-.1,r['bbox'][1]-.1,r['bbox'][2]-r['bbox'][0]+.2,r['bbox'][3]-r['bbox'][1]+.2]
    # Inspect again after the flow; the output remains genuine PDF text.
    from backend.styled_text import replace_styled
    edited_again=replace_styled(exported.content,[],1,box,[{'id':r['id'],'text':'TEX'}])
    with f.open(stream=edited_again) as again:
        assert again[1].get_text().count('TEXT')<12
        assert re.search(r'\bTEX\b',again[1].get_text())


@pytest.mark.parametrize('kind',['open','simple','raw-simple','cid','type3'])
def test_embedded_programs_and_type3_glyphs_are_reused(kind):
    from tests.test_cff_forms_mixed import cff_pdf
    from tests.test_type3_fonts import type3_pdf,glyphs
    initial=type3_pdf() if kind=='type3' else cff_pdf(kind)
    with f.open(stream=initial) as d:
        d.new_page(width=650,height=800);base=d.tobytes()
    with f.open(stream=base) as d:
        span=next(s for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text'].startswith('ABC' if kind=='type3' else 'HELLO'))
    m=inspect_selection(base,[],0,[{'origin':list(span['origin']),'text':span['text']}]);text=(span['text']+' ')*20;runs=[{'id':i,'text':text if j==0 else ''} for j,i in enumerate(m['ids'])]
    out,report=reflow(base,[],0,m['box'],m['ids'][0],text,100,30,False,m['ids'],runs,True,[{'page':1,'box':[30,80,540,600]}]);assert report['complete']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        original={a.extract_font(font[0])[3] for font in a[0].get_fonts() if a.extract_font(font[0])[3]};continued={b.extract_font(font[0])[3] for font in b[1].get_fonts() if b.extract_font(font[0])[3]};assert original<=continued or kind=='type3'
        if kind=='type3':assert glyphs(a)==glyphs(b)
        assert ('ABC' if kind=='type3' else 'HELLO') in b[1].get_text()


def test_initial_area_cannot_silently_move_the_entire_paragraph():
    base=source();p=payload(base);p['height']=10
    with pytest.raises(DocumentError,match='alto inicial'):reflow(base,[],preview=False,**p)
