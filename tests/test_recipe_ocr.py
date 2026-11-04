import pytest,pymupdf as f
from backend.automation import validate_recipe,process_recipe
from backend.engine import DocumentError
from tests.test_automation import recipe,rows
from tests.test_long_advance import source

STEP={'type':'ocr','language':'eng','dpi':150,'orientation':0}


def test_actual_local_ocr_then_text_manifest_and_original_unchanged():
    base=source(scan=True);plan=recipe(STEP,{'type':'text'});z,r=rows(process_recipe([('Scan.pdf',base,[])],plan))
    row=r['documents'][0];text=z.read(row['file']).decode();assert 'REAPDF' in text.upper(),text
    details=row['steps'][0]['details'];assert details['processed'] and details['words']>0
    with f.open(stream=base) as d:assert not d[0].get_text().strip()
    assert row['steps'][0]['output_sha256']==row['steps'][1]['input_sha256']


@pytest.mark.parametrize('change',[{'language':'fra'},{'language':{}},{'dpi':True},{'dpi':72},{'orientation':45},{'orientation':False}])
def test_invalid_ocr_recipe_rejected(change):
    with pytest.raises(DocumentError,match='OCR'):validate_recipe(recipe({**STEP,**change}))


def test_text_pages_are_skipped_and_result_remains_a_pdf():
    z,r=rows(process_recipe([('Text.pdf',source(),[])],recipe(STEP)))
    assert r['documents'][0]['steps'][0]['details']['skipped']
    with f.open(stream=z.read(r['documents'][0]['file'])) as d:assert d[0].get_text().strip()


def test_large_document_is_atomic_before_any_archive():
    with f.open() as d:
        for _ in range(11):d.new_page()
        base=d.tobytes()
    with pytest.raises(DocumentError,match='10 páginas'):process_recipe([('Too-many.pdf',base,[])],recipe(STEP))
