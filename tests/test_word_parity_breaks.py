import pytest,pymupdf as f
from backend.docx_import import import_docx
from tests.test_docx_sections import fixture,rewrite,field


@pytest.mark.parametrize('kind,blank,total',[('oddPage',1,4),('evenPage',0,3)])
def test_section_parity_blanks_numbering_geometry_headers_and_links(kind,blank,total):
    data=fixture(kind=kind);out,r=import_docx(data)
    assert r['pages']==total and r['text_check_passed']
    assert r['sections'][0]['blank_pages']==blank
    assert r['sections'][1]['first_page']==(3 if blank else 2)
    assert r['sections'][1]['number_start']==(5 if blank else 4)
    with f.open(stream=out) as d:
        assert len(d)==total and d[1+blank].rect.width>d[1+blank].rect.height
        assert d[1+blank].get_links() and 'Tabla horizontal' in d[1+blank].get_text()
        assert f'de {total}' in d[0].get_text()
        if blank:
            assert not d[1].get_text().strip() and not d[1].get_links()
            assert d[1].rect==d[0].rect and d[1].get_label()=='iv'
            assert d[2].get_label()=='v'


def test_sectionpages_includes_its_automatic_blank_and_global_total_is_final():
    data=fixture(kind='oddPage')
    from io import BytesIO
    from zipfile import ZipFile
    with ZipFile(BytesIO(data)) as z:
        header=z.read('word/header1.xml').decode().replace(field('NUMPAGES'),field('SECTIONPAGES')+'<w:r><w:t> / </w:t></w:r>'+field('NUMPAGES'))
    out,r=import_docx(rewrite(data,{'word/header1.xml':header}))
    with f.open(stream=out) as d:
        assert 'de 2 / 4' in d[0].get_text() and not d[1].get_text()
    assert r['sections'][0]['pages']==2


def test_automatic_blank_must_fit_roman_numbering_limit():
    from io import BytesIO
    from zipfile import ZipFile
    from backend.engine import DocumentError
    data=fixture(kind='oddPage')
    with ZipFile(BytesIO(data)) as z:body=z.read('word/document.xml').decode().replace('w:start="3"','w:start="3999"')
    with pytest.raises(DocumentError,match='3999'):import_docx(rewrite(data,{'word/document.xml':body}))
