import pytest
import pymupdf as f
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_columns import source
from tests.test_docx_sections import p,properties,rewrite,W,R,base
from tests.test_docx_physical_pages import continuous,inline
from tests.test_docx_column_breaks import positions


@pytest.mark.parametrize('columns',[2,3,4])
@pytest.mark.parametrize('rows',[12,27,98])
def test_balance_last_page_keeps_all_text_page_count_and_column_bounds(columns,rows):
    data=source(f'<w:cols w:num="{columns}" w:space="240"/>',body=''.join(p(f'ITEM{i:03d}') for i in range(rows)))
    original,old=import_docx(data);out,r=import_docx(data,balance_columns=True)
    assert r['pages']==old['pages'] and r['balanced_column_pages']==1 and r['text_check_passed']
    with f.open(stream=out) as d,f.open(stream=original) as a:
        for page in list(d)[:-1]:assert page.get_text()==a[page.number].get_text() and page.get_pixmap().samples==a[page.number].get_pixmap().samples
        text=''.join(page.get_text() for page in d);assert all(text.count(f'ITEM{i:03d}')==1 for i in range(rows))
        last=d[-1];found=last.search_for('ITEM');by_x={round(rect.x0):[] for rect in found}
        for rect in found:by_x[round(rect.x0)].append(rect.y1)
        assert len(by_x)==columns and max(map(max,by_x.values()))-min(map(max,by_x.values()))<(columns-1)*22
        assert not last.get_xobjects()


@pytest.mark.parametrize('kind',['page','column'])
def test_balancing_preserves_explicit_breaks_and_native_links(kind):
    data=source(body=inline(['BEFOREMARK','AFTERMARK'],[kind]))
    original,old=import_docx(data);out,r=import_docx(data,balance_columns=True)
    with f.open(stream=out) as d,f.open(stream=original) as a:
        before=positions(a,['BEFOREMARK','AFTERMARK']);after=positions(d,['BEFOREMARK','AFTERMARK']);assert [v[0] for v in before]==[v[0] for v in after]
        assert len([l for page in d for l in page.get_links() if l['kind']==f.LINK_GOTO])==2


@pytest.mark.parametrize('rows',[12,70])
def test_balancing_with_footnotes_retains_original_reference_page_and_visible_note(rows):
    from tests.test_docx_notes import source as notes,reference
    data=notes(body=''.join(p(f'WORDROW{i:03d}') for i in range(rows))+reference('footnote',1,'NOTEREFERENCEMARK'),options='<w:cols w:num="2" w:space="240"/>')
    original,old=import_docx(data);out,r=import_docx(data,balance_columns=True)
    with f.open(stream=out) as d,f.open(stream=original) as a:
        ref,note=positions(d,['NOTEREFERENCEMARK','FOOTNOTEALPHA']);assert ref[0]==note[0]==positions(a,['NOTEREFERENCEMARK'])[0][0] and ref[1].y1<note[1].y0
        assert len(d)==len(a) and r['text_check_passed']


@pytest.mark.parametrize('before',[1,2,3,4])
@pytest.mark.parametrize('after',[1,2,3,4])
def test_continuous_changes_columns_on_same_page_without_overlap(before,after):
    second=properties(kind='continuous').replace('</w:sectPr>',f'<w:cols w:num="{after}" w:space="240"/></w:sectPr>')
    data=continuous(cols=before,body2=''.join(p(f'NEWITEM{i:03d}') for i in range(12)),second=second)
    out,r=import_docx(data)
    with f.open(stream=out) as d:
        assert len(d)==1 and r['text_check_passed'];first=positions(d,['SECTIONFIRST'])[0][1];rows=d[0].search_for('NEWITEM')
        if before!=after:
            assert r['continuous_column_changes']==1 and len({round(rect.x0) for rect in rows})==after and min(rect.y0 for rect in rows)>first.y1
            assert [v['columns'] for v in r['sections'][0]['continuous_bands']]==[before,after]
        else:assert r['continuous_column_changes']==0
        assert not d[0].get_xobjects()


def test_changing_continuous_columns_keep_hyperlinks_and_editable_native_text():
    from backend.native_text import native_model
    second=properties(kind='continuous').replace('</w:sectPr>','<w:cols w:num="3" w:space="240"/></w:sectPr>')
    out,r=import_docx(continuous(body2=inline(['LINKALPHA','LINKBETA'],['column']),second=second));assert r['text_check_passed']
    with f.open(stream=out) as d:
        rows=native_model(d,0,d[0].rect)[1];assert any(v['editable'] and 'LINK' in v['text'] for v in rows)
        assert len([l for l in d[0].get_links() if l['kind']==f.LINK_GOTO])==2


def test_page_break_before_new_column_band_respects_a_real_new_page():
    second=properties(kind='continuous').replace('</w:sectPr>','<w:cols w:num="3" w:space="240"/></w:sectPr>')
    body='<w:p><w:pPr><w:pageBreakBefore/></w:pPr><w:r><w:t>NEWBANDPAGE</w:t></w:r></w:p>'
    out,r=import_docx(continuous(body2=body,second=second))
    with f.open(stream=out) as d:assert len(d)==2 and positions(d,['NEWBANDPAGE'])[0][0]==1


def test_long_changed_band_continues_on_more_pages_and_preserves_all_tokens():
    second=properties(kind='continuous').replace('</w:sectPr>','<w:cols w:num="3" w:space="240"/></w:sectPr>')
    out,r=import_docx(continuous(body2=''.join(p(f'LONGITEM{i:03d}') for i in range(150)),second=second))
    with f.open(stream=out) as d:
        text=''.join(page.get_text() for page in d);assert len(d)>1 and all(text.count(f'LONGITEM{i:03d}')==1 for i in range(150))
        assert r['text_check_passed'] and len({round(rect.x0) for rect in d[-1].search_for('LONGITEM')})==3


@pytest.mark.parametrize('value',[None,1,'true',[],{}])
def test_balance_configuration_rejects_non_boolean_values(value):
    with pytest.raises(DocumentError,match='booleana'):import_docx(source(),balance_columns=value)


def test_earlier_pages_with_links_remain_pixel_exact_when_balancing_last_page():
    from scripts.create_word_manual_columns_sample import create
    a,_=import_docx(create());b,_=import_docx(create(),balance_columns=True)
    with f.open(stream=a) as old,f.open(stream=b) as new:
        for index in range(3):assert old[index].get_pixmap().samples==new[index].get_pixmap().samples


@pytest.mark.parametrize('changing',[False,True])
def test_import_api_balances_and_exports_reopenable_native_pdf(changing):
    from fastapi.testclient import TestClient
    from backend.app import app
    from scripts.create_word_manual_columns_sample import create
    data=create(changing=True) if changing else source(body=''.join(p(f'APIROW{i:03d}') for i in range(18)))
    with TestClient(app) as client:
        response=client.post('/api/import/docx',data={'balance_columns':'true'},files={'file':('columns.docx',data,'application/zip')});assert response.status_code==200,response.text
        result=response.json();assert result['report']['balance_columns_requested'] and result['report']['balanced_column_pages']>0
        output=client.post('/api/documents/'+result['document']['id']+'/export',json={'operations':[]})
        with f.open(stream=output.content) as d:assert len(d)==(4 if changing else 1) and all(not page.get_xobjects() for page in d)


def test_prior_section_endnote_is_not_dropped_when_final_section_changes_columns():
    from tests.test_docx_notes import source as notes,reference
    first=properties();two=first.replace('</w:sectPr>','<w:cols w:num="2" w:space="240"/></w:sectPr>');three=two.replace('nextPage','continuous').replace('w:num="2"','w:num="3"')
    body=reference('endnote',2,'PREVIOUSENDREF')+'<w:p><w:pPr>'+first+'</w:pPr><w:r><w:t>FIRSTENDING</w:t></w:r></w:p>'+'<w:p><w:pPr>'+two+'</w:pPr><w:r><w:t>COLUMNSECOND</w:t></w:r></w:p>'+p('COLUMNTHIRD')+three
    data=rewrite(notes(),{'word/document.xml':f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>{body}</w:body></w:document>'})
    out,r=import_docx(data);assert r['endnotes']==1 and r['text_check_passed']
    with f.open(stream=out) as d:assert sum(page.get_text().count('ENDNOTEBETA') for page in d)==1


def test_notes_in_changing_continuous_group_are_placed_on_the_reference_page():
    from tests.test_docx_notes import source as notes,reference
    two=properties().replace('</w:sectPr>','<w:cols w:num="2" w:space="240"/></w:sectPr>');three=two.replace('nextPage','continuous').replace('w:num="2"','w:num="3"')
    body=reference('footnote',1,'PROTECTEDREF')+'<w:p><w:pPr>'+two+'</w:pPr><w:r><w:t>NOTEENDING</w:t></w:r></w:p>'+p('AFTERNOTE')+three
    data=rewrite(notes(),{'word/document.xml':f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'})
    output,report=import_docx(data)
    with f.open(stream=output) as d:
        ref,note=positions(d,['PROTECTEDREF','FOOTNOTEALPHA']);assert ref[0]==note[0] and ref[1].y1<note[1].y0 and report['text_check_passed']


def test_unequal_continuous_columns_keep_declared_widths_and_order():
    cols='<w:cols w:num="3" w:equalWidth="0"><w:col w:w="2400" w:space="240"/><w:col w:w="2800" w:space="240"/><w:col w:w="4066"/></w:cols>'
    second=properties(kind='continuous').replace('</w:sectPr>',cols+'</w:sectPr>')
    out,r=import_docx(continuous(body2=inline(['UNEQUALA','UNEQUALB','UNEQUALC'],['column','column']),second=second))
    with f.open(stream=out) as d:
        rows=positions(d,['UNEQUALA','UNEQUALB','UNEQUALC']);assert [v[1].x0 for v in rows]==pytest.approx([72,204,356],abs=.1)
        assert all(v[0]==0 for v in rows)


def test_visible_paint_outside_balanced_column_is_rejected_instead_of_clipped():
    body='<w:p><w:pPr><w:ind w:left="-720"/></w:pPr><w:r><w:t>OUTSIDEPAINT</w:t></w:r></w:p>'
    with pytest.raises(DocumentError,match='pintura|equilibrio'):import_docx(source(body=body),balance_columns=True)


def test_continuous_band_keeps_explicit_paragraph_after_spacing():
    from io import BytesIO
    from zipfile import ZipFile
    second=properties(kind='continuous').replace('</w:sectPr>','<w:cols w:num="3" w:space="240"/></w:sectPr>')
    data=continuous(second=second)
    with ZipFile(BytesIO(data)) as z:xml=z.read('word/document.xml').decode()
    xml=xml.replace('<w:pPr><w:sectPr>','<w:pPr><w:spacing w:after="720"/><w:sectPr>',1)
    out,r=import_docx(rewrite(data,{'word/document.xml':xml}))
    with f.open(stream=out) as d:
        first,last=positions(d,['SECTIONFIRST','SECTIONSECOND']);assert first[0]==last[0]==0 and last[1].y0-first[1].y1>=35
