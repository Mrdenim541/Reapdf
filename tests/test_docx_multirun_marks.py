import pytest,pymupdf as f
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_notes import source,W


def marked(kind,ident,values):
    style='FootnoteReference' if kind=='footnote' else 'EndnoteReference'
    return '<w:p><w:r><w:t>BEFOREWORD</w:t><w:'+kind+'Reference w:id="'+str(ident)+'" w:customMarkFollows="1"/></w:r>'+''.join('<w:r><w:rPr><w:rStyle w:val="'+style+'"/><w:b/></w:rPr><w:t>'+s+'</w:t></w:r>' for s in values)+'<w:r><w:t>AFTERWORD</w:t></w:r></w:p>'


@pytest.mark.parametrize('kind,ident',[('footnote',1),('endnote',2)])
@pytest.mark.parametrize('parts',[['*','*'],['A','B','1','2'],['†','†']])
def test_styled_mark_split_between_runs_remains_one_note(kind,ident,parts):
    pdf,report=import_docx(source(body=marked(kind,ident,parts)));assert report['text_check_passed'] and report['custom_note_marks']==1
    with f.open(stream=pdf) as d:
        text=''.join(p.get_text() for p in d);assert 'BEFOREWORD' in text and 'AFTERWORD' in text
        assert len([v for p in d for v in p.get_links() if v['kind']==f.LINK_GOTO])>=2


def test_long_split_mark_is_rejected_without_eating_body():
    with pytest.raises(DocumentError,match='marcador personalizado'):import_docx(source(body=marked('footnote',1,['AB','CD','E'])))


def test_leading_custom_mark_is_removed_across_definition_runs_only():
    from backend.docx_notes import strip_custom_label,tag
    from xml.etree import ElementTree as E
    for tail,expected in [(' BODY','BODY'),('BODY','AB12BODY')]:
        note=E.fromstring(f'<w:footnote xmlns:w="{W}"><w:p><w:r><w:footnoteRef/><w:t>AB</w:t></w:r><w:r><w:t>12{tail}</w:t></w:r></w:p></w:footnote>')
        strip_custom_label(note,'AB12');assert ''.join(t.text or '' for t in note.iter(tag('t')))==expected
