import pytest
import pymupdf as f
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_columns import source
from tests.test_docx_sections import p


def mark(name='target',identity=1,text='DESTINATIONWORD'):
    return f'<w:p><w:bookmarkStart w:id="{identity}" w:name="{name}"/><w:r><w:t>{text}</w:t></w:r><w:bookmarkEnd w:id="{identity}"/></w:p>'


def link(name='target',text='FOLLOWLINK'):
    return f'<w:p><w:hyperlink w:anchor="{name}"><w:r><w:rPr><w:b/></w:rPr><w:t>{text}</w:t></w:r></w:hyperlink></w:p>'


@pytest.mark.parametrize('columns',[1,2,3])
@pytest.mark.parametrize('backwards',[False,True])
def test_internal_links_resolve_forward_and_backwards_to_saved_native_coordinates(columns,backwards):
    filler=''.join(p('Body text for repagination. '*50) for _ in range(12))
    body=(mark()+filler+link()) if backwards else link()+filler+mark()
    pdf,report=import_docx(source(f'<w:cols w:num="{columns}" w:space="240"/>',body=body))
    assert report['text_check_passed'] and report['internal_hyperlinks']==1 and report['bookmarks']==1
    with f.open(stream=pdf) as d:
        destination=next(page for page in d if page.search_for('DESTINATIONWORD'))
        links=[l for page in d for l in page.get_links() if l['kind']==f.LINK_GOTO]
        assert len(links)==1 and links[0]['page']==destination.number
        point=links[0]['to'];rect=destination.search_for('DESTINATIONWORD')[0]
        assert abs(point.x-rect.x0)<2 and abs(point.y-rect.y0)<3
        assert any(s['flags']&16 for page in d for b in page.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'] if 'FOLLOWLINK' in s['text'])


def test_bookmark_can_span_paragraphs_and_two_links_keep_one_target():
    body=link()+link(text='SECONDLINK')+'<w:p><w:bookmarkStart w:id="1" w:name="target"/><w:r><w:t>DESTINATIONWORD</w:t></w:r></w:p>'+p('Inside bookmark')+'<w:p><w:bookmarkEnd w:id="1"/><w:r><w:t>After bookmark</w:t></w:r></w:p>'
    pdf,r=import_docx(source(body=body));assert r['internal_hyperlinks']==2 and r['text_check_passed']
    with f.open(stream=pdf) as d:assert len([l for page in d for l in page.get_links() if l['kind']==f.LINK_GOTO])==2


def test_unknown_target_keeps_visible_text_and_reports_missing_destination():
    pdf,r=import_docx(source(body=link('missing')+p('Body')))
    assert r['internal_hyperlinks']==0 and any('destino del enlace interno' in w for w in r['warnings'])
    with f.open(stream=pdf) as d:assert 'FOLLOWLINK' in d[0].get_text() and not d[0].get_links()


@pytest.mark.parametrize('body',[
    mark()+mark(),mark()+mark('other'),mark()+mark('target',2),
    link()+'<w:p><w:bookmarkStart w:id="1" w:name="target"/><w:r><w:t>Text</w:t></w:r></w:p>',
    mark().replace('w:id="1"','w:id="-1"'),
    mark().replace('</w:p>','<w:bookmarkEnd w:id="1"/></w:p>')])
def test_ambiguous_or_unclosed_link_targets_are_rejected(body):
    with pytest.raises(DocumentError,match='marcador'):import_docx(source(body=body))
