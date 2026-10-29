"""Batch outputs remain atomic, permission-aware, bounded and independently usable."""
from io import BytesIO
from zipfile import ZipFile
import hashlib,json
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.batch_tools import process_batch
from backend.engine import DocumentError


def source(text='Documento de prueba',pages=1):
    with f.open() as d:
        for i in range(pages):d.new_page(width=400,height=500).insert_text((40,80),text+f' {i+1}')
        return d.tobytes()


@pytest.mark.parametrize('action',['optimize','text','protect'])
def test_batch_manifest_hashes_duplicate_names_and_native_outputs(action):
    items=[('../../nombre ñ.pdf',source('Primero'),[]),('..\\nombre ñ.pdf',source('Segundo'),[])]
    settings={'password':'Batch-user-2026!','owner_password':'Batch-owner-2026!','allow_copy':False,'allow_print':True} if action=='protect' else {}
    review=process_batch(items,action,settings,True);assert review['pages']==2 and len(review['documents'])==2
    archive=process_batch(items,action,settings)
    with ZipFile(BytesIO(archive)) as z:
        report=json.loads(z.read('manifest.json'));assert len(z.namelist())==3 and len(set(z.namelist()))==3
        assert report['action']==action and report['pages']==2
        assert 'Batch-user' not in json.dumps(report) and 'Batch-owner' not in json.dumps(report)
        for row,(_,base,_) in zip(report['documents'],items):
            assert '/' not in row['file'] and '\\' not in row['file']
            data=z.read(row['file']);assert hashlib.sha256(data).hexdigest()==row['output_sha256'] and hashlib.sha256(base).hexdigest()==row['input_sha256']
            if action=='text':assert 'Página 1' in data.decode() and ('Primero' in data.decode() or 'Segundo' in data.decode())
            else:
                with f.open(stream=data) as doc,f.open(stream=base) as old:
                    if action=='protect':
                        assert doc.needs_pass and doc.authenticate(settings['password']) and not doc.permissions&f.PDF_PERM_COPY and doc.permissions&f.PDF_PERM_PRINT
                    assert doc[0].get_text()==old[0].get_text() and doc[0].get_pixmap().samples==old[0].get_pixmap().samples
                    if action=='optimize':assert len(data)<=len(base)


def test_one_invalid_document_fails_entire_batch_and_operations_are_applied():
    with pytest.raises(DocumentError):process_batch([('a.pdf',source(),[]),('bad.pdf',b'not a PDF',[])],'optimize')
    base=source();op={'type':'note','page':0,'point':[100,150],'content':'Comentario del lote','color':[1,0,0]}
    archive=process_batch([('a.pdf',base,[op])],'optimize')
    with ZipFile(BytesIO(archive)) as z:
        report=json.loads(z.read('manifest.json'));row=report['documents'][0];assert row['includes_applied_operations']
        with f.open(stream=z.read(row['file'])) as d:
            p=d[0];assert next(p.annots()).info['content']=='Comentario del lote'


@pytest.mark.parametrize('action',['optimize','protect','text'])
def test_permissions_are_checked_for_each_document(action):
    with f.open(stream=source()) as d:restricted=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_PRINT)
    settings={'password':'Batch-user-2026!','owner_password':'Batch-owner-2026!'} if action=='protect' else {}
    with pytest.raises(DocumentError):process_batch([('allowed.pdf',source(),[]),('restricted.pdf',restricted,[])],action,settings)


@pytest.mark.parametrize('items,action,settings',[
 ([], 'text',{}),([('a.pdf',b'x',[])]*11,'text',{}),([('a.pdf',b'x',[])],'office',{}),
 ([('a\nb.pdf',b'x',[])],'text',{}),([('a.pdf',b'x',[])],'optimize',{'password':'unexpected'}),
 ([('a.pdf',b'x',[])],'text',[]),
])
def test_invalid_batch_configuration_rejected(items,action,settings):
    with pytest.raises(DocumentError):process_batch(items,action,settings)


def test_page_and_byte_budgets(monkeypatch):
    with pytest.raises(DocumentError,match='100 páginas'):process_batch([('a.pdf',source(pages=51),[]),('b.pdf',source(pages=50),[])],'text')
    monkeypatch.setattr('backend.batch_tools.MAX_INPUT',10)
    with pytest.raises(DocumentError,match='entrada'):process_batch([('a.pdf',source(),[])],'text')
    monkeypatch.setattr('backend.batch_tools.MAX_INPUT',1000000);monkeypatch.setattr('backend.batch_tools.MAX_OUTPUT',10)
    with pytest.raises(DocumentError,match='salida'):process_batch([('a.pdf',source(),[])],'text')


def test_text_batch_keeps_signed_documents_read_only_and_does_not_run_ocr():
    with f.open(stream=source()) as d:
        d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>');base=d.tobytes()
    archive=process_batch([('signed.pdf',base,[])],'text')
    with ZipFile(BytesIO(archive)) as z:
        report=json.loads(z.read('manifest.json'));row=report['documents'][0];assert not row['details']['ocr'] and 'Documento' in z.read(row['file']).decode()
    with pytest.raises(DocumentError):process_batch([('signed.pdf',base,[])],'optimize')


def test_api_review_download_duplicate_validation_and_unchanged_session():
    with TestClient(app) as client:
        docs=[client.post('/api/documents',files={'file':(name,source(name),'application/pdf')}).json() for name in ['Uno.pdf','Dos.pdf']]
        payload={'documents':[{'id':d['id'],'name':f'Archivo {i}.pdf'} for i,d in enumerate(docs)],'action':'text'}
        reviewed=client.post('/api/batch',json=payload|{'review':True});assert reviewed.status_code==200 and reviewed.json()['pages']==2
        result=client.post('/api/batch',json=payload);assert result.status_code==200 and result.headers['content-type']=='application/zip'
        with ZipFile(BytesIO(result.content)) as z:assert len(z.namelist())==3
        for d in docs:assert client.post('/api/documents/'+d['id']+'/forms',json={}).status_code==200
        invalid=payload|{'documents':[payload['documents'][0]]*2}
        assert client.post('/api/batch',json=invalid).status_code==422
