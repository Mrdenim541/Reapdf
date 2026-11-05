from io import BytesIO
from zipfile import ZipFile
import pytest
import pymupdf as f
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_sections import rewrite,base,properties,p,W,R


def source(columns='<w:cols w:num="2" w:space="480"/>',*,body=None):
    section=properties().replace('</w:sectPr>',columns+'</w:sectPr>')
    if body is None:body=''.join(p(f'ENTRY{i:03d} '+('Selectable column text. '*6)) for i in range(90))
    xml=f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>'+body+section+'</w:body></w:document>'
    return rewrite(base(),{'word/document.xml':xml})


@pytest.mark.parametrize('count',[2,3,4])
@pytest.mark.parametrize('separator',[False,True])
def test_equal_columns_keep_text_in_order_geometry_and_optional_separator(count,separator):
    pdf,report=import_docx(source(f'<w:cols w:num="{count}" w:space="240" w:sep="{int(separator)}"/>'))
    assert report['text_check_passed'] and report['pages']>1
    c=report['sections'][0]['columns'];assert len(c['widths'])==count
    with f.open(stream=pdf) as d:
        text=''.join(page.get_text() for page in d)
        for i in range(90):assert text.count(f'ENTRY{i:03d}')==1
        assert [text.index(f'ENTRY{i:03d}') for i in range(90)]==sorted(text.index(f'ENTRY{i:03d}') for i in range(90))
        for page in d:
            assert len(page.get_drawings())==(count-1 if separator else 0)
            for word in page.get_text('words'):
                rect=f.Rect(word[:4]);assert page.rect.contains(rect)
                left=report['sections'][0]['margins'][0]
                xs=[left+sum(c['widths'][:i])+sum(c['gaps'][:i]) for i in range(count)]
                assert any(rect.x0>=x-.5 and rect.x1<=x+w+.5 for x,w in zip(xs,c['widths']))
        assert len({round(r.x0) for r in d[0].search_for('ENTRY')})==count


def test_explicit_unequal_columns_keep_widths_and_native_links():
    columns='<w:cols w:num="2" w:equalWidth="0"><w:col w:w="3600" w:space="480"/><w:col w:w="5666"/></w:cols>'
    body=''.join(p('LEFTANDRIGHT '+('Main text. '*20)) for _ in range(30))
    body+='<w:p><w:hyperlink w:anchor="target"><w:r><w:t>GO_TO_TARGET</w:t></w:r></w:hyperlink></w:p><w:p><w:bookmarkStart w:id="1" w:name="target"/><w:r><w:t>TARGETWORD</w:t></w:r><w:bookmarkEnd w:id="1"/></w:p>'
    pdf,report=import_docx(source(columns,body=body))
    assert report['text_check_passed'] and report['sections'][0]['columns']['widths']==[180,283.3]
    with f.open(stream=pdf) as d:
        assert any(l['kind']==f.LINK_GOTO for page in d for l in page.get_links())
        for page in d:assert all(page.rect.contains(f.Rect(w[:4])) for w in page.get_text('words'))


@pytest.mark.parametrize('fill',[60,110,180])
def test_footnotes_follow_reference_and_reserve_space_below_all_columns(fill):
    from tests.test_docx_notes import source as notes,reference
    body=p('Column body text. '*fill)+reference('footnote',1,'COLUMNREF')+p('Trailing column body. '*150)
    data=notes(body=body,options='<w:cols w:num="2" w:space="480" w:sep="1"/>')
    pdf,r=import_docx(data);assert r['text_check_passed'] and r['footnotes']==1
    with f.open(stream=pdf) as d:
        ref=next(page for page in d if page.search_for('COLUMNREF'));note=next(page for page in d if page.search_for('FOOTNOTEALPHA'));assert ref.number==note.number
        rect=note.search_for('FOOTNOTEALPHA')[0]
        assert all(f.Rect(w[:4]).y1<rect.y0 for w in note.get_text('words') if w[4] in ['Column','Trailing','COLUMNREF'])
        lines=[g for g in note.get_drawings() if g['rect'].height>100]
        assert lines and max(g['rect'].y1 for g in lines)<rect.y0
        assert any(link['kind']==f.LINK_GOTO for page in d for link in page.get_links())


def test_multiple_sections_keep_geometry_running_headers_and_page_numbers():
    from tests.test_docx_sections import fixture
    data=fixture(long=True)
    with ZipFile(BytesIO(data)) as z:xml=z.read('word/document.xml').decode()
    xml=xml.replace('</w:sectPr>','<w:cols w:num="2" w:space="480"/></w:sectPr>',1)
    pdf,r=import_docx(rewrite(data,{'word/document.xml':xml}));assert r['text_check_passed']
    assert [len(s['columns']['widths']) for s in r['sections']]==[2,1,1]
    with f.open(stream=pdf) as d:
        for s in r['sections']:
            for i in range(s['first_page']-1,s['first_page']-1+s['pages']):
                assert f'de {len(d)}' in d[i].get_text()
                assert (d[i].rect.width>d[i].rect.height)==(s['section']==2)


@pytest.mark.parametrize('columns',[
    '<w:cols w:num="5"/>','<w:cols w:num="bad"/>','<w:cols w:num="2" w:space="-1"/>',
    '<w:cols w:num="4" w:space="5000"/>','<w:cols w:num="2" w:equalWidth="0"><w:col w:w="3600"/></w:cols>',
    '<w:cols w:num="2" w:equalWidth="0"><w:col w:w="3600"/><w:col w:w="3600"/></w:cols>',
    '<w:cols w:num="2" w:equalWidth="unknown"/>'])
def test_invalid_or_too_narrow_columns_do_not_return_incomplete_pdf(columns):
    with pytest.raises(DocumentError):import_docx(source(columns))


@pytest.mark.parametrize('kind',['page','column','before'])
def test_manual_breaks_in_columns_are_not_silently_reinterpreted(kind):
    body=p('Before')+('<w:p><w:pPr><w:pageBreakBefore/></w:pPr><w:r><w:t>After</w:t></w:r></w:p>' if kind=='before' else f'<w:p><w:r><w:br w:type="{kind}"/><w:t>After</w:t></w:r></w:p>')
    with pytest.raises(DocumentError,match='saltos manuales'):import_docx(source(body=body))
