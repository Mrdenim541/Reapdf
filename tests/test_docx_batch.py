from io import BytesIO
from zipfile import ZipFile
import hashlib,json
import pytest,pymupdf as f
from backend.docx_batch import convert
from backend.engine import DocumentError
from tests.test_docx_sections import fixture


def test_native_batch_outputs_unique_pdf_names_reports_and_hashes():
    files=[('../../same.docx',fixture(kind='oddPage')),('same.docx',fixture())]
    review=convert(files,review=True);assert review['pages']==7 and all(r['preview'].startswith('data:image/png;base64,') for r in review['documents'])
    with ZipFile(BytesIO(convert(files))) as z:
        report=json.loads(z.read('manifest.json'));assert len(z.namelist())==3
        for row in report['documents']:
            assert '/' not in row['file'] and not row.get('preview')
            data=z.read(row['file']);assert hashlib.sha256(data).hexdigest()==row['output_sha256']
            with f.open(stream=data) as d:assert len(d)==row['pages'] and 'Portada original' in d[0].get_text()
        assert report['documents'][0]['input_sha256']==hashlib.sha256(files[0][1]).hexdigest()


def test_invalid_second_word_stops_the_entire_batch():
    with pytest.raises(DocumentError,match='Word 2'):convert([('Valid.docx',fixture()),('Broken.docx',b'broken')])
    with pytest.raises(DocumentError):convert([('Word.docx',fixture())]*11)


def test_batch_api_preview_and_download():
    from fastapi.testclient import TestClient
    from backend.app import app
    files=[('files',('Word.docx',fixture(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document'))]
    with TestClient(app) as c:
        review=c.post('/api/import/docx-batch',files=files,data={'review':'true'});assert review.status_code==200 and review.json()['documents']
        response=c.post('/api/import/docx-batch',files=files,data={'review':'false'});assert response.status_code==200 and response.content.startswith(b'PK')
