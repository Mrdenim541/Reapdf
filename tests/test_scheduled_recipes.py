from datetime import datetime,timezone,timedelta
from io import BytesIO
from zipfile import ZipFile
import json
import pytest,pymupdf as f
from backend.scheduled_recipes import Queue
from backend.engine import DocumentError
from tests.test_automation import recipe
from tests.test_batch_tools import source

MOMENT=datetime(2026,11,4,12,tzinfo=timezone.utc)


@pytest.fixture
def queue(tmp_path):return Queue(tmp_path,clock=lambda:MOMENT)


def add(queue,seconds=0,plan=None):return queue.create([('Example.pdf',source(),[])],plan or recipe({'type':'text'}),(MOMENT+timedelta(seconds=seconds)).isoformat())


def test_future_job_persists_across_restart_and_uses_immutable_snapshot(queue):
    j=add(queue,seconds=30);assert not queue.tick()
    later=Queue(queue.root.parent,clock=lambda:MOMENT+timedelta(seconds=31));assert later.list()[0]['status']=='queued'
    assert later.tick() and later.list()[0]['status']=='completed'
    data=later.result(j['id'])
    with ZipFile(BytesIO(data)) as z:
        manifest=json.loads(z.read('manifest.json'));assert 'Documento de prueba' in z.read(manifest['documents'][0]['file']).decode()
    later.delete(j['id']);assert not later.list() and not (later.root/j['id']).exists()


def test_pending_cancellation_and_failed_job_never_produce_download(queue):
    cancelled=add(queue);queue.cancel(cancelled['id']);assert not queue.tick()
    with pytest.raises(DocumentError):queue.result(cancelled['id'])
    job=add(queue,plan=recipe({'type':'text','pages':'9'}));assert queue.tick()
    row=next(v for v in queue.list() if v['id']==job['id']);assert row['status']=='failed' and row['error']
    with pytest.raises(DocumentError):queue.result(job['id'])


def test_tampered_inputs_are_detected_without_processing(queue):
    j=add(queue);(queue.directory(j['id'])/'inputs.zip').write_bytes(b'tampered');assert queue.tick()
    assert queue.list()[0]['status']=='failed' and 'cambiaron' in queue.list()[0]['error']


def test_interrupted_running_job_is_explicit_and_not_restarted(queue):
    j=add(queue);row=queue.read(j['id']);row['status']='running';queue.save(row)
    queue.start();queue.close();assert queue.list()[0]['status']=='interrupted'
    with pytest.raises(DocumentError):queue.result(j['id'])


def test_running_cancellation_discards_computed_result(queue,monkeypatch):
    import backend.scheduled_recipes as module
    j=add(queue)
    def fake(items,plan):
        queue.cancel(j['id'])
        with pytest.raises(DocumentError,match='espera'):queue.delete(j['id'])
        return b'PK-result-discarded'
    monkeypatch.setattr(module,'process_recipe',fake)
    assert queue.tick() and queue.list()[0]['status']=='cancelled'
    assert not (queue.directory(j['id'])/'result.zip').exists()


@pytest.mark.parametrize('time',['2026-11-04T12:00:00','2020-01-01T00:00:00+00:00','2030-01-01T00:00:00+00:00',None,'broken'])
def test_invalid_times_are_rejected(queue,time):
    with pytest.raises(DocumentError):queue.create([('Example.pdf',source(),[])],recipe({'type':'text'}),time)


def test_passwords_are_not_persisted_and_invalid_id_cannot_escape_directory(queue):
    with pytest.raises(DocumentError,match='contraseñas'):add(queue,plan=recipe({'type':'protect','allow_copy':True,'allow_print':True}))
    for value in ['../outside','x'*32,{},None]:
        with pytest.raises(DocumentError):queue.result(value)
    assert not queue.list()


def test_quota_and_output_hash_are_checked(queue,monkeypatch):
    j=add(queue);assert queue.tick();(queue.directory(j['id'])/'result.zip').write_bytes(b'tampered')
    with pytest.raises(DocumentError,match='cambió'):queue.result(j['id'])
    import backend.scheduled_recipes as module
    monkeypatch.setattr(module,'QUOTA',1)
    with pytest.raises(DocumentError,match='300 MB'):add(queue)


def test_invalid_state_is_visible_and_deletable_without_execution(queue):
    j=add(queue);(queue.directory(j['id'])/'state.json').write_text('not json')
    assert queue.list()[0]['status']=='invalid' and not queue.tick()
    queue.delete(j['id']);assert not queue.list()


def test_api_schedule_survives_document_session_removal(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import app
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path))
    with TestClient(app) as c:
        original=c.post('/api/documents',files={'file':('Example.pdf',source(),'application/pdf')}).json()
        when=(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()
        payload={'documents':[{'id':original['id'],'name':'Example.pdf','operations':[]}],'recipe':recipe({'type':'text'}),'run_at':when}
        response=c.post('/api/scheduled-recipes',json=payload);assert response.status_code==200,response.text
        identity=response.json()['id'];c.delete('/api/documents/'+original['id'])
        assert c.get('/api/scheduled-recipes').json()[0]['status']=='queued'
        app.state.recipe_queue.clock=lambda:datetime.now(timezone.utc)+timedelta(minutes=3)
        assert app.state.recipe_queue.tick()
        result=c.get(f'/api/scheduled-recipes/{identity}/result');assert result.status_code==200 and result.content.startswith(b'PK')
        assert c.delete(f'/api/scheduled-recipes/{identity}').status_code==200
