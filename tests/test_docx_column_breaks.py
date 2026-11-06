import pytest
import pymupdf as f
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_columns import source
from tests.test_docx_sections import W,R


def paragraph(labels,properties='',style=''):
    content='<w:br w:type="column"/>'.join('<w:t>'+s+'</w:t>' for s in labels)
    return '<w:p>'+properties+'<w:r>'+style+content+'</w:r></w:p>'


def positions(doc,labels):
    result=[]
    for label in labels:
        matches=[(p.number,r) for p in doc for r in p.search_for(label)];assert len(matches)==1,(label,matches)
        result.append(matches[0])
    return result


@pytest.mark.parametrize('columns',[1,2,3,4])
def test_column_break_advances_one_frame_then_wraps_to_next_page(columns):
    labels=[f'COLMARK{i}END' for i in range(columns+2)]
    out,report=import_docx(source(f'<w:cols w:num="{columns}" w:space="240"/>',body=paragraph(labels)))
    assert report['manual_column_breaks']==len(labels)-1 and report['manual_page_breaks']==0 and report['text_check_passed']
    with f.open(stream=out) as d:
        located=positions(d,labels);assert len(d)==(len(labels)+columns-1)//columns
        c=report['sections'][0]['columns'];left=report['sections'][0]['margins'][0]
        for i,(page,rect) in enumerate(located):
            expected=left+sum(c['widths'][:i%columns])+sum(c['gaps'][:i%columns]);assert page==i//columns and rect.x0==pytest.approx(expected,abs=1)
            assert rect.y0==pytest.approx(located[0][1].y0,abs=1)


def test_column_continuation_preserves_bold_color_but_does_not_repeat_first_line_indent():
    body=paragraph(['FIRSTMARK','NEXTMARK'],'<w:pPr><w:ind w:firstLine="720"/></w:pPr>','<w:rPr><w:b/><w:color w:val="C02030"/></w:rPr>')
    out,r=import_docx(source(body=body))
    with f.open(stream=out) as d:
        spans=[s for p in d for b in p.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'] if 'MARK' in s['text']]
        assert len(spans)==2 and all('Bold' in s['font'] and s['color']==0xc02030 for s in spans)
        left=r['sections'][0]['margins'][0];c=r['sections'][0]['columns'];found=positions(d,['FIRSTMARK','NEXTMARK'])
        assert found[0][1].x0==pytest.approx(left+36,abs=1)
        assert found[1][1].x0==pytest.approx(left+c['widths'][0]+c['gaps'][0],abs=1)


@pytest.mark.parametrize('count',[2,3,4])
def test_leading_and_consecutive_breaks_keep_empty_columns(count):
    body='<w:p><w:r>'+('<w:br w:type="column"/>'*count)+'<w:t>AFTERBLANKCOLS</w:t></w:r></w:p>'
    out,r=import_docx(source('<w:cols w:num="3" w:space="240"/>',body=body))
    with f.open(stream=out) as d:
        page,rect=positions(d,['AFTERBLANKCOLS'])[0];assert page==count//3
        left=r['sections'][0]['margins'][0];c=r['sections'][0]['columns'];assert rect.x0==pytest.approx(left+sum(c['widths'][:count%3])+sum(c['gaps'][:count%3]),abs=1)


def test_internal_link_across_columns_keeps_two_native_link_rectangles_and_one_destination():
    body='<w:p><w:hyperlink w:anchor="destination"><w:r><w:t>LINKLEFT</w:t><w:br w:type="column"/><w:t>LINKRIGHT</w:t></w:r></w:hyperlink></w:p><w:p><w:bookmarkStart w:id="1" w:name="destination"/><w:r><w:t>DESTINATIONMARK</w:t></w:r><w:bookmarkEnd w:id="1"/></w:p>'
    out,r=import_docx(source(body=body));assert r['text_check_passed']
    with f.open(stream=out) as d:
        links=[link for p in d for link in p.get_links() if link['kind']==f.LINK_GOTO];assert len(links)==2
        first,second=positions(d,['LINKLEFT','LINKRIGHT']);assert first[0]==second[0]==0 and first[1].x0<second[1].x0
        assert all(link['page']==0 for link in links)


def test_same_link_can_cross_a_manual_page_break_in_single_column():
    body='<w:p><w:hyperlink w:anchor="destination"><w:r><w:t>LINKFIRSTPAGE</w:t><w:br w:type="page"/><w:t>LINKSECONDPAGE</w:t></w:r></w:hyperlink></w:p><w:p><w:bookmarkStart w:id="1" w:name="destination"/><w:r><w:t>DESTINATIONMARK</w:t></w:r><w:bookmarkEnd w:id="1"/></w:p>'
    out,r=import_docx(source('<w:cols w:num="1"/>',body=body))
    with f.open(stream=out) as d:
        assert positions(d,['LINKFIRSTPAGE','LINKSECONDPAGE'])[0][0]==0
        assert positions(d,['LINKFIRSTPAGE','LINKSECONDPAGE'])[1][0]==1
        assert len([l for p in d for l in p.get_links() if l['kind']==f.LINK_GOTO])==2


def test_column_break_inside_table_is_not_reinterpreted_as_a_cell_break():
    body='<w:tbl><w:tr><w:tc>'+paragraph(['IN','CELL'])+'</w:tc></w:tr></w:tbl>'
    with pytest.raises(DocumentError,match='dentro de tablas'):import_docx(source(body=body))


@pytest.mark.parametrize('labels',[['LEFTNOTEREF','RIGHTNOTEREF'],['FIRSTCOL','SECONDCOL','NEXTNOTEPAGE']])
def test_footnotes_stay_on_the_reference_page_after_explicit_column_breaks(labels):
    from tests.test_docx_notes import source as notes,reference
    body=paragraph(labels)+reference('footnote',1,'AFTERCOLREF')
    out,r=import_docx(notes(body=body,options='<w:cols w:num="2" w:space="480"/>'))
    assert r['footnotes']==1 and r['manual_column_breaks']==len(labels)-1 and r['text_check_passed']
    with f.open(stream=out) as d:
        ref=positions(d,['AFTERCOLREF'])[0];note=positions(d,['FOOTNOTEALPHA'])[0]
        assert ref[0]==note[0] and note[1].y0>ref[1].y1


def test_column_break_inside_note_is_not_interpreted_as_main_document_flow():
    from tests.test_docx_notes import source as notes,reference
    from tests.test_docx_sections import rewrite
    from io import BytesIO
    from zipfile import ZipFile
    base=notes(body=reference('footnote',1,'REF'))
    with ZipFile(BytesIO(base)) as z:xml=z.read('word/footnotes.xml').decode()
    xml=xml.replace('FOOTNOTEALPHA','FOOTNOTEALPHA</w:t><w:br w:type="column"/><w:t>CONTINUATION')
    with pytest.raises(DocumentError,match='dentro de notas'):import_docx(rewrite(base,{'word/footnotes.xml':xml}))
