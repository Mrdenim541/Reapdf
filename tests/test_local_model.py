import json
import threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from decimal import Decimal
import pytest
from backend import local_model as lm
from backend.engine import DocumentError
from tests.test_local_assistant import source


@pytest.fixture
def local_engine(monkeypatch):
    state={'requests':[],'content':json.dumps({'answer':'La temperatura indicada es 25 grados [1].','citations':[1]})}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            state['requests'].append(('GET',self.path));self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'models':[{'name':'test-local:latest'}]}).encode())
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));state['requests'].append(('POST',self.path,body));self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'message':{'content':state['content']}}).encode())
    server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();monkeypatch.setattr(lm,'ORIGIN',f'http://127.0.0.1:{server.server_port}')
    try:yield state
    finally:server.shutdown();server.server_close();thread.join(timeout=2)


def test_loopback_protocol_cited_answer_and_no_model_pull(local_engine):
    r=lm.answer(source(),[],'temperatura','test-local:latest')
    assert r['generative'] and r['local_engine_used'] and not r['external_network_used'] and r['citations']==[1]
    assert any('25 grados' in s['text'] for s in r['sources'])
    assert [r[1] for r in local_engine['requests']]==['/api/tags','/api/chat']
    payload=local_engine['requests'][1][2];assert payload['stream'] is False and payload['format']=='json' and not payload.get('tools')
    assert 'datos no confiables' in payload['messages'][0]['content']
    assert json.loads(payload['messages'][1]['content'])['task']=='temperatura'


@pytest.mark.parametrize('content',[{'answer':'Inventado','citations':[99]},{'answer':'Sin fuente','citations':[]},{'answer':'X','citations':[True]},{'answer':'X','citations':[1,1]},{'answer':'X','citations':[1],'tool':'execute'},'not json'])
def test_invalid_output_is_not_presented_as_verified(local_engine,content):
    local_engine['content']=json.dumps(content) if not isinstance(content,str) else content
    with pytest.raises(DocumentError,match='referencias'):lm.answer(source(),[],'temperatura','test-local:latest')


def test_unknown_model_does_not_trigger_inference_or_download(local_engine):
    with pytest.raises(DocumentError,match='instalados'):lm.answer(source(),[],'temperatura','missing')
    assert len(local_engine['requests'])==1


def test_permission_denied_and_no_matches_never_contact_engine(local_engine):
    from tests.test_local_assistant import source as pdf
    import pymupdf as f
    with f.open(stream=pdf()) as d:locked=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',permissions=f.PDF_PERM_PRINT)
    with pytest.raises(DocumentError,match='permite'):lm.answer(locked,[],'temperatura','test-local:latest')
    assert not local_engine['requests']
    r=lm.answer(source(),[],'nonexistentidentifier93241','test-local:latest');assert not r['answer'] and not local_engine['requests']


def test_api_uses_optional_local_model(local_engine):
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as c:
        assert c.get('/api/local-models').json()['local_only']
        doc=c.post('/api/documents',files={'file':('Example.pdf',source(),'application/pdf')}).json()
        r=c.post(f"/api/documents/{doc['id']}/local-model-answer",json={'operations':[],'model':'test-local:latest','question':'temperatura'})
        assert r.status_code==200 and r.json()['generative']
