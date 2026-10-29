from io import BytesIO
from zipfile import ZipFile
import json,hashlib
import pymupdf as f
import pytest
from backend.automation import process_recipe,validate_recipe
from backend.engine import DocumentError
from tests.test_automation import recipe
from tests.test_batch_tools import source


def word():return {'type':'docx','keep_lines':False,'include_images':False,'include_tables':False,'include_links':True}


def test_recipe_word_download_manifest_and_names_are_verified():
    plan=recipe({'type':'numbering','template':'Folio {numero}','start':15,'size':10},word())
    archive=process_recipe([('Uno.pdf',source(),[]),('Dos.pdf',source('Segundo'),[])],plan)
    with ZipFile(BytesIO(archive)) as z:
        report=json.loads(z.read('manifest.json'));assert len(z.namelist())==3
        for row in report['documents']:
            assert row['file'].endswith('.docx');data=z.read(row['file']);assert hashlib.sha256(data).hexdigest()==row['output_sha256']
            with ZipFile(BytesIO(data)) as doc:assert b'Folio 15' in doc.read('word/document.xml')
            assert row['steps'][-1]['details']['editable_text']
    reviewed=process_recipe([('Uno.pdf',source(),[])],plan,review=True);assert 'preview' not in reviewed['documents'][0]


def test_word_only_recipe_is_read_only_for_signed_sources_and_checks_copy_permission():
    with f.open(stream=source()) as d:d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>');signed=d.tobytes()
    assert process_recipe([('signed.pdf',signed,[])],recipe(word()))
    with f.open(stream=source()) as d:restricted=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_MODIFY)
    with pytest.raises(DocumentError):process_recipe([('restricted.pdf',restricted,[])],recipe(word()))


def test_word_terminal_order_and_options_are_validated():
    with pytest.raises(DocumentError,match='último'):validate_recipe(recipe(word(),{'type':'optimize'}))
    with pytest.raises(DocumentError):validate_recipe(recipe(word()|{'include_images':1}))
