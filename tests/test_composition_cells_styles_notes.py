from io import BytesIO
import xml.etree.ElementTree as E
import pymupdf as f
import pytest
from backend.engine import DocumentError,spans
from backend.styled_text import inspect_styled,replace_styled
from backend.paragraphs import replace_paragraph
from backend.text_compositing import BLENDS
from backend.basic_tagging import candidates,create
from backend.structure_editing import model,reading_preview
from backend import xfdf
from backend.xfdf_styled_text import STYLES,REGULAR
from tests.test_text_states_compositing import source as state_source,row_for
from tests.test_xfdf_appearance import blank


def blended(mode='Multiply',form=False,isolated=False):
    base=state_source(alpha=1,form=form)
    with f.open(stream=base) as d:
        for x in range(1,d.xref_length()):
            if d.xref_get_key(x,'ExtGState/Fade')[0]=='dict':d.xref_set_key(x,'ExtGState/Fade/BM','/'+mode)
        if form:
            for page in d:
                for x in page.get_xobjects():
                    if d.xref_get_key(x[0],'Group')[0]!='null':d.xref_set_key(x[0],'Group',f'<</S/Transparency/I {str(isolated).lower()}/K false/CS/DeviceRGB>>')
        return d.tobytes()


@pytest.mark.parametrize('mode',sorted(BLENDS-{'Normal','Compatible'}))
@pytest.mark.parametrize('form',[False,True])
def test_native_blend_text_edit_preserves_state_neighbors_shared_occurrences(mode,form):
    base=blended(mode,form);box,row=row_for(base);assert row['editable'] and row['original_only'],row['reason']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert 'CBA AB' in b[0].get_text()
        assert next(s for s in spans(a[0]) if s['text']=='ABC ABC')['original_only']
        for text in ['BAC BAC','CAB CAB']:
            for rect in a[0].search_for(text):assert a[0].get_pixmap(clip=rect).samples==b[0].get_pixmap(clip=rect).samples
        if form:assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        state=lambda d:sorted(d.xref_get_key(x,'ExtGState/Fade')[1] for x in range(1,d.xref_length()) if d.xref_get_key(x,'ExtGState/Fade')[0]=='dict')
        assert state(a)==state(b)
    with pytest.raises(DocumentError):replace_paragraph(base,[],0,box,'CBA',size=18)


def multibody():
    with f.open() as d:
        p=d.new_page(width=400,height=300)
        for x,y,text in [(40,40,'Header A'),(220,40,'Header B'),(40,90,'First line'),(40,110,'Second line'),(220,90,'Value')]:p.insert_text((x,y),text)
        return d.tobytes()


def multicells(info):
    return [{'id':e['id'],'role':'TH' if i<2 else 'TD','table':1,'row':1 if i<2 else 2,'column':2 if i in [1,4] else 1,'merge_fragments':i in [2,3]} for i,e in enumerate(info['entries'])]


def test_multiple_objects_one_real_cell_mcid_parents_reading_split_project():
    base=multibody();entries=multicells(candidates(base,[]));out,report=create(base,[],entries,reviewed=True);assert report['table_cells']==4 and report['table_fragments']==5
    rows=model(out,[])['nodes'];assert sum(r['role']=='TD' for r in rows)==2 and all(r['parent_valid'] for r in rows)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples and a[0].get_text()==b[0].get_text()
        leaf=next(r for r in rows if r['role']=='TD');assert b.xref_get_key(leaf['id'],'K')==('array','[2 3]')
    flow=reading_preview(out,[],0);assert not flow['untagged_blocks'] and 'Second line' in '\n'.join(r['text'] for r in flow['blocks'])
    from backend.projects import build_project,read_project
    assert read_project(build_project(out,[],{'name':'Cells.pdf'})[0])[0]==out
    from backend.page_tools import split_pdf
    from zipfile import ZipFile
    with ZipFile(BytesIO(split_pdf(out,[],size=1))) as z:assert sum(r['role']=='TD' for r in model(z.read(z.namelist()[0]),[])['nodes'])==2


@pytest.mark.parametrize('mode',['unconfirmed','mismatched_role','mismatched_scope','mismatched_span','not_bool'])
def test_grouping_requires_explicit_consistent_cell_properties(mode):
    base=multibody();entries=multicells(candidates(base,[]))
    if mode=='unconfirmed':entries[3]['merge_fragments']=False
    if mode=='mismatched_role':entries[3]['role']='TH'
    if mode=='mismatched_scope':entries[3]['scope']='Row'
    if mode=='mismatched_span':entries[3]['rowspan']=2
    if mode=='not_bool':entries[3]['merge_fragments']=1
    with pytest.raises(DocumentError):create(base,[],entries,reviewed=True)


def styled_xml(font='Helvetica-Bold',rotation=0):
    root=E.Element(xfdf.tag('xfdf'));annots=E.SubElement(root,xfdf.tag('annots'));node=E.SubElement(annots,xfdf.tag('freetext'),{'page':'0','rect':'40,300,280,540','name':'styled-note','font':font,'size':'15','rotation':str(rotation),'justification':'1','text-color':'#204080','width':'0','opacity':'.75'});E.SubElement(node,xfdf.tag('contents')).text='Styled ABC\nSecond line';return E.tostring(root)


@pytest.mark.parametrize('font',sorted(set(STYLES)-REGULAR))
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_bold_italic_xfdf_native_font_metrics_and_roundtrip(font,rotation):
    out,report=xfdf.import_data(blank(),[],styled_xml(font,rotation),True);assert report['annotations']==1
    xml,exported=xfdf.export(out,[],True,False);assert exported['annotations']==1 and not exported['skipped_annotations']
    node=xfdf.parse(xml).find('./'+xfdf.tag('annots')+'/*');assert node.get('font')==font and node.get('rotation')==str(rotation)
    out2,_=xfdf.import_data(blank(),[],xml,True)
    with f.open(stream=out) as a,f.open(stream=out2) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
        text=[s for block in a[0].get_text('dict')['blocks'] for line in block.get('lines',[]) for s in line['spans'] if 'Styled' in s['text']];assert text and all(s['font']==font for s in text)
    from pyhanko.pdf_utils.reader import PdfFileReader
    doc=PdfFileReader(BytesIO(out));annot=doc.root['/Pages']['/Kids'][0].get_object()['/Annots'][0].get_object();fonts=annot['/AP']['/N']['/Resources']['/Font'];assert any(str(v.get_object()['/BaseFont'])=='/'+font for v in fonts.values())


def test_styled_text_rejects_overflow_and_non_winansi_without_publishing():
    for text in ['A '*3000,'漢字']:
        root=xfdf.parse(styled_xml());root.find('./'+xfdf.tag('annots')+'/*/'+xfdf.tag('contents')).text=text
        with pytest.raises(DocumentError):xfdf.import_data(blank(),[],E.tostring(root),True)


def test_custom_word_note_marks_links_numbering_and_text_are_preserved():
    from tests.test_docx_notes import source,reference
    from backend.docx_import import import_docx
    body='<w:p><w:r><w:t>MARKREFERENCE</w:t><w:footnoteReference w:id="1" w:customMarkFollows="1"/><w:t>†</w:t></w:r></w:p>'+reference('endnote',2,'ENDREFERENCE')
    pdf,report=import_docx(source(body=body));assert report['custom_note_marks']==1 and report['text_check_passed']
    with f.open(stream=pdf) as d:
        text='\n'.join(p.get_text() for p in d);assert '†' in text and 'FOOTNOTEALPHA' in text and 'MARKREFERENCE' in text
        assert len([l for p in d for l in p.get_links() if l['kind']==f.LINK_GOTO])>=4


def test_blend_rewrite_guard_does_not_depend_on_recognizing_a_native_text_frame():
    base=blended()
    with f.open(stream=base) as d:
        page=d[0];page.insert_text((80,700),'EXTRA SIMPLE');base=d.tobytes();rect=page.search_for('EXTRA SIMPLE')[0]+(-2,-2,2,2);box=[rect.x0,rect.y0,rect.width,rect.height]
    with pytest.raises(DocumentError):replace_paragraph(base,[],0,box,'REWRITE',size=12)


def test_custom_marks_do_not_increment_automatic_note_numbers():
    from tests.test_docx_notes import source,W,R,reference
    from backend.docx_import import import_docx
    body='<w:p><w:r><w:t>CUSTOMREF</w:t><w:footnoteReference w:id="1" w:customMarkFollows="true"/><w:t>*</w:t></w:r></w:p>'+reference('footnote',3,'AUTOMATICREF')
    feet=f'<w:footnotes xmlns:w="{W}" xmlns:r="{R}"><w:footnote w:id="1"><w:p><w:r><w:footnoteRef/><w:t>* Custom content</w:t></w:r></w:p></w:footnote><w:footnote w:id="3"><w:p><w:r><w:footnoteRef/><w:t>Automatic content</w:t></w:r></w:p></w:footnote></w:footnotes>'
    pdf,report=import_docx(source(body=body,overrides={'word/footnotes.xml':feet}));assert report['custom_note_marks']==1
    with f.open(stream=pdf) as d:
        text='\n'.join(p.get_text() for p in d);assert '*\nCustom content' in text and '1.\nAutomatic content' in text
        assert '2.\nAutomatic content' not in text


@pytest.mark.parametrize('mark',['','longlabel','two words','\u200b','\u202e','\U0001f642'])
def test_invalid_custom_note_mark_does_not_silently_lose_text(mark):
    from tests.test_docx_notes import source
    from backend.docx_import import import_docx
    body='<w:p><w:r><w:t>REF</w:t><w:footnoteReference w:id="1" w:customMarkFollows="1"/><w:t>'+mark+'</w:t></w:r></w:p>'
    with pytest.raises(DocumentError):import_docx(source(body=body))


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_styled_borders_fill_crop_rotation_and_opacity_roundtrip(rotation):
    root=xfdf.parse(styled_xml('Times-BoldItalic',rotation));node=root.find('./'+xfdf.tag('annots')+'/*');node.set('interior-color','#EEDDCC');node.set('width','2');node.set('dashes','2.5,1.5')
    with f.open(stream=blank()) as d:d[0].set_cropbox(f.Rect(10,20,480,580));d[0].set_rotation(rotation);base=d.tobytes()
    out,_=xfdf.import_data(base,[],E.tostring(root),True);xml,report=xfdf.export(out,[],True,False);assert report['annotations']==1;second,_=xfdf.import_data(base,[],xml,True)
    with f.open(stream=out) as a,f.open(stream=second) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples and a[0].rotation==rotation and a[0].cropbox==b[0].cropbox


def test_spoofed_direct_font_dictionary_cannot_be_exported_as_a_base_font():
    out,_=xfdf.import_data(blank(),[],styled_xml(),True)
    with f.open(stream=out) as d:
        a=next(d[0].annots());d.xref_set_key(a.xref,'Resources','<</Font<</hebo<</Type/Font/Subtype/Type1/BaseFont/Courier-Bold>>>>>>');bad=d.tobytes()
    _,report=xfdf.export(bad,[],True,False);assert not report['annotations'] and report['skipped_annotations']==1


def test_standard_blend_on_marked_clipped_original_truetype_keeps_program_and_other_page():
    from tests.test_native_content import custom_source,BOX
    with f.open(stream=custom_source()) as d:
        page=d[0];resources=int(d.xref_get_key(page.xref,'Resources')[1].split()[0]);d.xref_set_key(resources,'ExtGState','<</Alpha<</ca 0.5/BM/Multiply>>>>');d.update_stream(page.get_contents()[0],page.read_contents().replace(b'BT',b'/Alpha gs BT'));base=d.tobytes()
    row=inspect_styled(base,[],0,BOX)['runs'][0];assert row['editable'] and row['original_only'];out=replace_styled(base,[],0,BOX,[{'id':row['id'],'text':'BARRA'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].get_text().strip()=='BARRA' and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert b'/MCID 7' in b[0].read_contents() and b' re W n' in b[0].read_contents()
        assert a.extract_font(a[0].get_fonts()[0][0])[3]==b.extract_font(b[0].get_fonts()[0][0])[3]


def test_missing_styled_appearance_is_reported_as_skipped_instead_of_crashing_export():
    out,_=xfdf.import_data(blank(),[],styled_xml(),True)
    with f.open(stream=out) as d:
        page=d[0];a=next(page.annots());d.xref_set_key(a.xref,'AP','null');bad=d.tobytes()
    _,report=xfdf.export(bad,[],True,False);assert report['annotations']==0 and report['skipped_annotations']==1
