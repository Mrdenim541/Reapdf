import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient
from backend.app import app

@pytest.fixture
def client():
    with TestClient(app) as client:yield client

@pytest.fixture
def pdf():
    d=fitz.open();p=d.new_page();p.insert_text((50,80),'Texto original',fontsize=16)
    result=d.tobytes();d.close();return result

def test_upload_preview_edit_export_and_close(client,pdf):
    assert client.get('/api/health').json()['status']=='ok'
    result=client.post('/api/documents',files={'file':('document.pdf',pdf,'application/pdf')})
    assert result.status_code==200
    info=result.json();assert not info['signed']
    base=f"/api/documents/{info['id']}"
    data=client.get(base+'/pages/0').json()
    operations=[{'type':'text','page':0,'span_id':data['spans'][0]['id'],'text':'Nuevo texto'}]
    preview=client.post(base+'/pages/0/preview',json={'operations':operations})
    assert preview.status_code==200 and preview.content.startswith(b'\x89PNG')
    result=client.post(base+'/export',json={'operations':operations})
    assert result.status_code==200
    with fitz.open(stream=result.content,filetype='pdf') as d:
        assert 'Nuevo texto' in d[0].get_text() and 'Texto original' not in d[0].get_text()
    assert client.get(base+'/pages/0').json()['spans'][0]['text']=='Texto original'
    assert client.get(base+'/pages/99').status_code==404
    assert client.post(base+'/export',json=[]).status_code==422
    assert client.post(base+'/export',content=b'{').status_code==422
    assert client.delete(base).status_code==200
    assert client.get(base+'/pages/0').status_code==404

def test_reject_invalid_document_and_cross_origin(client):
    assert client.post('/api/documents',files={'file':('bad.pdf',b'broken')}).status_code==422
    assert client.post('/api/documents',headers={'Origin':'https://example.com'}).status_code==403
    assert client.get('/api/documents/not-a-document/pages/0').status_code==404

def test_same_origin_custom_port_is_allowed_and_wrong_host_is_rejected(pdf):
    with TestClient(app,base_url='http://127.0.0.1:8765') as c:
        r=c.post('/api/documents',files={'file':('demo.pdf',pdf)},headers={'Origin':'http://127.0.0.1:8765'})
        assert r.status_code==200
        assert c.get('/api/health',headers={'Host':'attacker.example'}).status_code==400


def test_review_words_notes_export_and_validation(client,pdf):
    info=client.post('/api/documents',files={'file':('review.pdf',pdf)}).json()
    base=f"/api/documents/{info['id']}"
    text=client.post(base+'/pages/0/text',json={'operations':[]}).json()
    assert [w['text'] for w in text['words']]==['Texto','original']
    operations=[{'type':'highlight','page':0,'color':[1,1,0],'quads':[w['quad'] for w in text['words']]},
                {'type':'note','page':0,'point':[100,200],'color':[1,1,0],'content':'Nota ✓'}]
    assert client.post(base+'/pages/0/preview',json={'operations':operations}).status_code==200
    exported=client.post(base+'/export',json={'operations':operations})
    assert exported.status_code==200
    with fitz.open(stream=exported.content,filetype='pdf') as d:
        p=d[0];aa=list(p.annots());assert [a.type[0] for a in aa]==[8,0]
        assert aa[1].info['content']=='Nota ✓'
    operations[1]['content']=''
    assert client.post(base+'/export',json={'operations':operations}).status_code==422
    # Una operación rechazada no debe modificar el documento de la sesión.
    pristine=client.post(base+'/export',json={'operations':[]})
    assert pristine.content==pdf
