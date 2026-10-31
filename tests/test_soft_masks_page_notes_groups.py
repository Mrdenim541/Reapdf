from io import BytesIO
from zipfile import ZipFile
import xml.etree.ElementTree as E
import pymupdf as f
import pytest
from backend.engine import DocumentError,spans
from backend.styled_text import inspect_styled,replace_styled
from backend.paragraphs import replace_paragraph
from backend import xfdf
from tests.test_text_states_compositing import source as state_source,row_for
from tests.test_docx_notes import source as note_source,W,R,p,reference
from backend.docx_import import import_docx


def masked(mode='Luminosity',form=False,rotation=0,nested=False):
    with f.open(stream=state_source(alpha=1)) as d:
        mask=d.get_new_xref();d.update_object(mask,'<</Type/XObject/Subtype/Form/BBox[0 0 595 842]/Resources<<>>/Group<</S/Transparency/I true/CS/DeviceGray>>>>');d.update_stream(mask,b'% Reapdf synthetic mask\n.55 g 0 0 595 842 re f')
        if nested:
            child=d.get_new_xref();d.update_object(child,'<</Type/XObject/Subtype/Form/BBox[0 0 595 842]/Resources<<>>>>');d.update_stream(child,b'% Reapdf synthetic mask child\n.55 g 0 0 595 842 re f');d.xref_set_key(mask,'Resources',f'<</XObject<</Child {child} 0 R>>>>');d.update_stream(mask,b'% Reapdf synthetic mask\n/Child Do')
        res=int(d.xref_get_key(d[0].xref,'Resources')[1].split()[0]);d.xref_set_key(res,'ExtGState/Fade/SMask',f'<</Type/Mask/S/{mode}/G {mask} 0 R/BC[0]/TR/Identity>>');base=d.tobytes()
    if form:
        with f.open(stream=base) as src,f.open() as d:
            page=d.new_page(width=800,height=1000);page.show_pdf_page(f.Rect(0,0,595,842),src,0);page.show_pdf_page(f.Rect(450,600,747.5,1021),src,0);d.new_page().show_pdf_page(f.Rect(0,0,595,842),src,0);base=d.tobytes()
    with f.open(stream=base) as d:d[0].set_rotation(rotation);return d.tobytes()


@pytest.mark.parametrize('mode',['Alpha','Luminosity'])
@pytest.mark.parametrize('form',[False,True])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_masked_original_text_edit_keeps_mask_font_neighbors_and_shared_occurrences(mode,form,rotation):
    base=masked(mode,form,rotation);box,row=row_for(base);assert row['editable'] and row['original_only'],row['reason'];out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].rotation==rotation and 'CBA AB' in b[0].get_text()
        mask_streams=lambda doc:{doc.xref_stream(x) for x in range(1,doc.xref_length()) if doc.xref_is_stream(x) and b'Reapdf synthetic mask' in doc.xref_stream(x)}
        assert mask_streams(a)==mask_streams(b)
        assert {v[3]:a.extract_font(v[0])[3] for v in a[0].get_fonts()}=={v[3]:b.extract_font(v[0])[3] for v in b[0].get_fonts()}
        a[0].set_rotation(0);b[0].set_rotation(0)
        for text in ['BAC BAC','CAB CAB']:
            for rect in a[0].search_for(text):assert a[0].get_pixmap(clip=rect).samples==b[0].get_pixmap(clip=rect).samples
        if form:assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert any(s.get('original_only') for s in spans(a[0]) if s['text']=='ABC ABC')
    with pytest.raises(DocumentError):replace_paragraph(base,[],0,box,'CBA',size=18)


def test_nested_vector_mask_retained_and_luminosity_is_visibly_effective():
    base=masked(nested=True);box,row=row_for(base);out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}]);assert out
    with f.open(stream=base) as masked_doc,f.open(stream=state_source(alpha=1)) as plain:
        rect=masked_doc[0].search_for('ABC ABC')[0];assert masked_doc[0].get_pixmap(clip=rect).samples!=plain[0].get_pixmap(clip=rect).samples


@pytest.mark.parametrize('case',['transfer','group_missing','group_knockout','color','cycle','text','image','state','unknown_type','bad_pen'])
def test_unverified_mask_variants_cannot_enable_native_edit_or_paragraph_fallback(case):
    with f.open(stream=masked()) as d:
        res=int(d.xref_get_key(d[0].xref,'Resources')[1].split()[0]);g=int(d.xref_get_key(res,'ExtGState/Fade/SMask/G')[1].split()[0])
        if case=='transfer':d.xref_set_key(res,'ExtGState/Fade/SMask/TR','<</FunctionType 2/Domain[0 1]/C0[0]/C1[1]/N 2>>')
        elif case=='group_missing':d.xref_set_key(g,'Group','null')
        elif case=='group_knockout':d.xref_set_key(g,'Group/K','true')
        elif case=='color':d.xref_set_key(g,'Group/CS','/DeviceCMYK')
        elif case=='cycle':d.xref_set_key(g,'Resources',f'<</XObject<</Cycle {g} 0 R>>>>');d.update_stream(g,b'/Cycle Do')
        elif case=='text':d.update_stream(g,b'BT (Text) Tj ET')
        elif case=='image':d.update_stream(g,b'BI /W 1 /H 1 /BPC 8 /CS /G ID X EI')
        elif case=='state':d.update_stream(g,b'/Unknown gs 0 0 100 100 re f')
        elif case=='unknown_type':d.xref_set_key(res,'ExtGState/Fade/SMask/Type','/Unknown')
        elif case=='bad_pen':d.update_stream(g,b'-1 w 0 0 100 100 re S')
        bad=d.tobytes()
    try:_,row=row_for(bad)
    except DocumentError:row=None
    assert row is None or not row['editable']
    with pytest.raises(DocumentError):replace_paragraph(bad,[],0,[70,120,150,40],'CBA',size=18)


def page_notes(fill=0,custom=False):
    body=reference('footnote',1,'FIRSTREF')+(p('Flow text before next reference. '*fill) if fill else '')+reference('footnote',3,'SECONDREF')+'<w:p><w:r><w:br w:type="page"/></w:r></w:p>'+reference('footnote',4,'THIRDREF')
    if custom:body=body.replace('<w:footnoteReference w:id="3"/>','<w:footnoteReference w:id="3" w:customMarkFollows="1"/><w:t>*</w:t>')
    feet=f'<w:footnotes xmlns:w="{W}" xmlns:r="{R}">'+''.join(f'<w:footnote w:id="{n}">{p(text)}</w:footnote>' for n,text in [(1,'NOTEONE content'),(3,'NOTETWO content'),(4,'NOTETHREE content')])+'</w:footnotes>'
    return note_source(body=body,options='<w:footnotePr><w:numRestart w:val="eachPage"/></w:footnotePr>',overrides={'word/footnotes.xml':feet})


@pytest.mark.parametrize('fill',[0,65,140])
@pytest.mark.parametrize('custom',[False,True])
def test_actual_page_numbering_matches_reference_page_and_note_link_labels(fill,custom):
    pdf,report=import_docx(page_notes(fill,custom));assert report['page_restarted_footnotes']==3 and report['text_check_passed']
    with f.open(stream=pdf) as doc:
        counters={}
        for text in ['NOTEONE','NOTETWO','NOTETHREE']:
            page=next(p for p in doc if p.search_for(text));note=page.search_for(text)[0];label='*' if custom and text=='NOTETWO' else str(counters.get(page.number,0)+1)
            if label!='*':counters[page.number]=int(label)
            reference_name={'NOTEONE':'FIRSTREF','NOTETWO':'SECONDREF','NOTETHREE':'THIRDREF'}[text]
            source=next(p for p in doc if p.search_for(reference_name));refbox=source.search_for(reference_name)[0]
            candidates=[l for l in source.get_links() if l['kind']==f.LINK_GOTO and l['page']==page.number and abs(l['from'].y0-refbox.y0)<20 and l['to'].y>page.rect.height*.6]
            assert len(candidates)==1
            box_=candidates[0]['from']+(-.5,-.5,.5,.5)
            chars=''.join(c['c'] for b in source.get_text('rawdict')['blocks'] for line in b.get('lines',[]) for span in line['spans'] for c in span['chars'] if box_.contains((f.Rect(c['bbox']).tl+f.Rect(c['bbox']).br)/2))
            assert chars==label
            lines=[(s['bbox'],s['text']) for b in page.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']]
            assert any(s.strip()==label+('' if label=='*' else '.') and abs(box[1]-note.y0)<55 for box,s in lines)
        assert len([l for p in doc for l in p.get_links() if l['kind']==f.LINK_GOTO])>=6
        assert next(p.number for p in doc if p.search_for('THIRDREF'))==next(p.number for p in doc if p.search_for('NOTETHREE'))


def group_xml():
    root=E.Element(xfdf.tag('xfdf'));annots=E.SubElement(root,xfdf.tag('annots'))
    # Deliberately child-first: importer must reconstruct the graph first.
    for name,kind,parent in [('group-line','line','group-box'),('group-box','square','root'),('root','text',None)]:
        attrs={'page':'0','rect':'40,300,240,450','name':name,'color':'#408020','width':'1'}
        if parent:attrs.update(inreplyto=parent,replyType='Group')
        if kind=='line':attrs.update(start='40,300',end='240,450')
        node=E.SubElement(annots,xfdf.tag(kind),attrs);E.SubElement(node,xfdf.tag('contents')).text=name
    return E.tostring(root)


def blank():
    with f.open() as d:d.new_page(width=500,height=600);return d.tobytes()


def test_group_graph_roundtrip_native_relations_idempotence_and_independent_reader():
    out,report=xfdf.import_data(blank(),[],group_xml(),True);assert report['annotations']==3
    with f.open(stream=out) as d:
        page=d[0];named={a.info['id']:a.xref for a in page.annots()};assert d.xref_get_key(named['group-line'],'IRT')==('xref',f'{named["group-box"]} 0 R') and d.xref_get_key(named['group-box'],'RT')==('name','/Group')
    xml,r=xfdf.export(out,[],True,False);assert r['annotations']==3 and not r['skipped_annotations'];root=xfdf.parse(xml);assert sum(n.get('replyType')=='Group' for n in root.find(xfdf.tag('annots')))==2
    _,repeat=xfdf.import_data(out,[],xml,True);assert repeat['duplicates']==3 and not repeat['annotations']
    from pyhanko.pdf_utils.reader import PdfFileReader
    doc=PdfFileReader(BytesIO(out));annots=[a.get_object() for a in doc.root['/Pages']['/Kids'][0].get_object()['/Annots']];assert sum(a.get('/RT')=='/Group' for a in annots)==2


@pytest.mark.parametrize('case',['cycle','orphan','state','page','unknown'])
def test_invalid_group_graph_never_publishes_a_partial_import(case):
    root=xfdf.parse(group_xml());nodes=list(root.find(xfdf.tag('annots')))
    if case=='cycle':nodes[-1].set('inreplyto','group-line');nodes[-1].set('replyType','Group')
    if case=='orphan':nodes[0].set('inreplyto','absent')
    if case=='state':nodes[0].set('statemodel','Review');nodes[0].set('state','Accepted')
    if case=='page':nodes[0].set('page','1')
    if case=='unknown':nodes[0].set('replyType','Other')
    with pytest.raises(DocumentError):xfdf.import_data(blank(),[],E.tostring(root),True)


def test_alpha_mask_with_internal_opacity_is_effective_and_remains_unchanged():
    with f.open(stream=masked('Alpha')) as d:
        res=int(d.xref_get_key(d[0].xref,'Resources')[1].split()[0]);g=int(d.xref_get_key(res,'ExtGState/Fade/SMask/G')[1].split()[0]);d.xref_set_key(g,'Resources','<</ExtGState<</Soft<</ca .35/CA .35/BM/Normal>>>>>>');d.update_stream(g,b'% Reapdf synthetic mask\n/Soft gs 0 g 0 0 595 842 re f');base=d.tobytes()
    box,row=row_for(base);assert row['editable'];out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=state_source(alpha=1)) as plain,f.open(stream=out) as b:
        rect=a[0].search_for('ABC ABC')[0];assert a[0].get_pixmap(clip=rect).samples!=plain[0].get_pixmap(clip=rect).samples
        assert any(b'/Soft gs' in b.xref_stream(x) for x in range(1,b.xref_length()) if b.xref_is_stream(x))


def test_page_restart_and_continuous_numbering_across_sections_use_last_real_page_counter():
    body=reference('footnote',1,'FIRSTREF')+'<w:p><w:r><w:br w:type="page"/></w:r></w:p>'+reference('footnote',3,'SECONDREF')+'<w:p><w:pPr><w:sectPr><w:footnotePr><w:numRestart w:val="eachPage"/></w:footnotePr></w:sectPr></w:pPr></w:p>'+reference('footnote',4,'THIRDREF')
    feet=f'<w:footnotes xmlns:w="{W}">'+''.join(f'<w:footnote w:id="{n}">{p(text)}</w:footnote>' for n,text in [(1,'NOTEONE content'),(3,'NOTETWO content'),(4,'NOTETHREE content')])+'</w:footnotes>'
    pdf,report=import_docx(note_source(body=body,options='<w:footnotePr><w:numRestart w:val="continuous"/></w:footnotePr>',overrides={'word/footnotes.xml':feet}));assert report['text_check_passed'] and report['section_count']==2
    with f.open(stream=pdf) as doc:
        for token,label in [('NOTEONE','1.'),('NOTETWO','1.'),('NOTETHREE','2.')]:
            page=next(p for p in doc if p.search_for(token));note=page.search_for(token)[0]
            assert any(s['text'].strip()==label and abs(s['bbox'][1]-note.y0)<55 for b in page.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'])


def test_page_restart_roman_format_start_is_applied_on_each_actual_page():
    with ZipFile(BytesIO(page_notes())) as z:
        out=BytesIO()
        with ZipFile(out,'w') as target:
            for name in z.namelist():
                data=z.read(name)
                if name=='word/document.xml':data=data.replace(b'<w:numRestart w:val="eachPage"/>',b'<w:numRestart w:val="eachPage"/><w:numFmt w:val="upperRoman"/><w:numStart w:val="3"/>')
                target.writestr(name,data)
    pdf,report=import_docx(out.getvalue());assert report['text_check_passed']
    with f.open(stream=pdf) as doc:
        for token,label in [('NOTEONE','III.'),('NOTETWO','IV.'),('NOTETHREE','III.')]:
            page=next(p for p in doc if p.search_for(token));note=page.search_for(token)[0];assert any(s['text'].strip()==label and abs(s['bbox'][1]-note.y0)<55 for b in page.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'])
