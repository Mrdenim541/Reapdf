import pytest,pymupdf as f
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_notes import source,W,R


def ref(kind='footnote',ident=1,mark='*',extra='',wrapper=False):
    r=f'<w:r><w:t>BEFOREWORD</w:t><w:{kind}Reference w:id="{ident}" w:customMarkFollows="1"/></w:r>'
    r+=extra+f'<w:r><w:rPr><w:b/><w:vertAlign w:val="superscript"/></w:rPr><w:t>{mark}</w:t></w:r><w:r><w:t>AFTERWORD</w:t></w:r>'
    if wrapper:r=f'<w:hyperlink r:id="missing">{r}</w:hyperlink>'
    return '<w:p>'+r+'</w:p>'


@pytest.mark.parametrize('kind,ident',[('footnote',1),('endnote',2)])
@pytest.mark.parametrize('mark',['*','**','†','AB12'])
def test_custom_note_mark_in_next_styled_run_preserves_body_and_links(kind,ident,mark):
    pdf,report=import_docx(source(body=ref(kind,ident,mark)));assert report['text_check_passed'] and report['note_references']==1
    with f.open(stream=pdf) as d:
        text=''.join(p.get_text() for p in d);assert 'BEFOREWORD' in text and 'AFTERWORD' in text and mark in text
        assert ('FOOTNOTEALPHA' if kind=='footnote' else 'ENDNOTEBETA') in text
        links=[l for p in d for l in p.get_links() if l['kind']==f.LINK_GOTO];assert len(links)>=2
        assert not any(p.get_images() for p in d)


def test_adjacent_note_marks_are_scoped_to_hyperlink_container():
    pdf,report=import_docx(source(body=ref(wrapper=True)));assert report['text_check_passed']
    with f.open(stream=pdf) as d:assert 'AFTERWORD' in ''.join(p.get_text() for p in d)


@pytest.mark.parametrize('mark',['','TOOLONG','a b'])
def test_invalid_following_marks_are_rejected_without_truncation(mark):
    with pytest.raises(DocumentError,match='marcador personalizado'):import_docx(source(body=ref(mark=mark)))


@pytest.mark.parametrize('separator',['<w:bookmarkStart w:id="1" w:name="boundary"/>','<w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple>'])
def test_does_not_guess_marks_across_structural_boundaries(separator):
    with pytest.raises(DocumentError,match='justo después'):import_docx(source(body=ref(extra=separator)))


def test_marker_run_with_other_content_is_not_silently_consumed():
    body=ref().replace('<w:t>*</w:t>','<w:t>*</w:t><w:tab/>')
    with pytest.raises(DocumentError,match='justo después'):import_docx(source(body=body))


def test_automatic_note_between_body_fragments_keeps_both_words():
    body='<w:p><w:r><w:t>BEFOREWORD</w:t><w:footnoteReference w:id="1"/><w:t>AFTERWORD</w:t></w:r></w:p>'
    pdf,report=import_docx(source(body=body));assert report['text_check_passed']
    with f.open(stream=pdf) as d:assert all(word in ''.join(p.get_text() for p in d) for word in ['BEFOREWORD','AFTERWORD','FOOTNOTEALPHA'])
