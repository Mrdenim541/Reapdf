import json
import hashlib
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.document_review import review_document
from backend.engine import DocumentError


def sample(pages=3):
    with f.open() as doc:
        for i in range(pages):doc.new_page(width=400,height=500)
        p=doc[0];p.insert_text((30,50),'CONTENIDO PRIVADO');p.add_text_annot((30,80),'COMENTARIO PRIVADO')
        p=doc[0];w=f.Widget();w.field_name='Campo privado';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_value='VALOR PRIVADO';w.rect=f.Rect(30,100,180,130);p.add_widget(w)
        p=doc[0];p.insert_link({'kind':f.LINK_URI,'from':f.Rect(30,160,140,180),'uri':'https://example.com/secreto'})
        if pages>1:
            pix=f.Pixmap(f.csRGB,f.IRect(0,0,10,10),False);pix.clear_with(80);doc[1].insert_image(f.Rect(0,0,400,500),stream=pix.tobytes('png'));doc[1].set_rotation(90)
        doc.embfile_add('archivo.txt',b'ADJUNTO PRIVADO')
        doc.set_page_labels([{'startpage':0,'prefix':'Hoja ','style':'D','firstpagenum':1}])
        return doc.tobytes()


def test_review_counts_real_objects_and_preserves_input_without_leaking_values():
    data=sample();before=hashlib.sha256(data).hexdigest();result=review_document(data,[])
    assert hashlib.sha256(data).hexdigest()==before
    a,b,c=result['pages'];assert a['annotations']==a['fields']==a['links']==1 and a['has_text']
    assert a['label']=='Hoja 1' and a['fonts']>=1 and not a['ocr_candidate']
    assert b['ocr_candidate'] and b['rotation']==90 and [b['width'],b['height']]==[500,400]
    assert not c['has_text'] and not c['ocr_candidate'] and c['images']==0
    assert result['next_offset'] is None and result['attachments']==1 and result['layers']==0
    encoded=json.dumps(result);assert all(secret not in encoded for secret in ['CONTENIDO PRIVADO','COMENTARIO PRIVADO','VALOR PRIVADO','Campo privado','secreto','ADJUNTO PRIVADO'])


def test_pagination_visits_each_page_once_in_order():
    data=sample(43);rows=[];offset=0
    while offset is not None:
        result=review_document(data,[],offset);assert len(result['pages'])<=20
        rows.extend(r['page'] for r in result['pages']);offset=result['next_offset']
    assert rows==list(range(43))


@pytest.mark.parametrize('offset,limit',[(True,1),(-1,1),(3,1),(0,True),(0,0),(0,21),(0,1.5),('0',1),(None,1),(0,None)])
def test_invalid_ranges_are_rejected(offset,limit):
    with pytest.raises(DocumentError):review_document(sample(),[],offset,limit)


def test_review_includes_pending_applied_operations_without_modifying_original():
    data=sample();op={'type':'ink','id':'test-review','page':2,'points':[[30,30],[100,100]],'color':[1,0,0],'width':2}
    assert review_document(data,[op])['pages'][2]['annotations']==1
    assert review_document(data,[])['pages'][2]['annotations']==0
    with pytest.raises(DocumentError):review_document(data,[{'type':'unknown','page':0}])


def test_review_respects_declared_permissions_and_signed_read_only_documents():
    with f.open(stream=sample()) as doc:
        protected=doc.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner-password',user_pw='',permissions=f.PDF_PERM_PRINT)
        doc.xref_set_key(doc.pdf_catalog(),'AcroForm/SigFlags','3');signed=doc.tobytes()
    result=review_document(protected,[]);assert not any(result['permissions'].values()) and result['pages'][0]['has_text']
    assert review_document(signed,[])['signed']


def test_resource_limits_fail_explicitly(monkeypatch):
    import backend.document_review as module
    data=sample();monkeypatch.setattr(module,'MAX_XREFS',1)
    with pytest.raises(DocumentError,match='objetos'):review_document(data,[])
    monkeypatch.setattr(module,'MAX_XREFS',100000);monkeypatch.setattr(module,'MAX_PAGE_OBJECTS',0)
    with pytest.raises(DocumentError,match='anotaciones'):review_document(data,[])


def test_api_review_and_validation(tmp_path,monkeypatch):
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'state'))
    with TestClient(app) as client:
        document=client.post('/api/documents',files={'file':('review.pdf',sample())}).json();url=f"/api/documents/{document['id']}/review"
        result=client.post(url,json={'offset':1,'limit':1});assert result.status_code==200 and result.json()['pages'][0]['ocr_candidate']
        assert client.post(url,json={'offset':False}).status_code==422
        assert client.post(url,json={'limit':21}).status_code==422
        assert client.post(url,json=[]).status_code==422
        assert client.post('/api/documents/'+'0'*32+'/review',json={}).status_code==404
