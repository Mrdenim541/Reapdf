import base64
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError, export_pdf, spans
from backend.projects import build_project, read_project, RecoveryStore, RecoveryConflict


@pytest.fixture
def example():
    with f.open() as doc:
        p=doc.new_page(width=400,height=500);p.insert_text((30,80),'Texto original',fontsize=16)
        xref=p.add_text_annot((200,200),'Nota original').xref
        line=spans(p)[0]
        doc.new_page();data=doc.tobytes()
    pix=f.Pixmap(f.csRGB,f.IRect(0,0,40,20),False);pix.clear_with(200)
    ops=[{'type':'text','page':0,'span_id':line['id'],'text':'Proyecto'},
         {'type':'note','id':'note','page':0,'point':[40,200],'content':'Nota nueva ✓','color':[1,1,0]},
         {'type':'image','id':'image','page':0,'points':[[50,250],[130,290]],'pixels':[40,20],'name':'foto.png','data':base64.b64encode(pix.tobytes('png')).decode()},
         {'type':'existing_annot','page':0,'xref':xref,'action':'update','changes':{'content':'Corregida'}}]
    state={'name':'Informe español.pdf','page':1,'zoom':1.25,'base_changes':3}
    return data,ops,state


def rewrite(archive,update=None,extra=None):
    out=BytesIO()
    with ZipFile(BytesIO(archive)) as old,ZipFile(out,'w',ZIP_DEFLATED) as new:
        for name in old.namelist():
            data=old.read(name)
            if update and name in update:data=update[name]
            new.writestr(name,data)
        if extra:new.writestr(*extra)
    return out.getvalue()


def test_project_roundtrip_keeps_base_editable_operations_view_and_original(example):
    data,ops,state=example;original=sha256(data).hexdigest()
    packed,manifest=build_project(data,ops,state)
    base,restored,info=read_project(packed)
    assert base==data and restored==ops and info['state']==state and info==manifest
    with f.open(stream=export_pdf(base,restored)) as d:
        assert 'Proyecto' in d[0].get_text() and 'original' not in d[0].get_text()
        assert d[0].get_images()[0][2:4]==(40,20)
        p=d[0];assert sorted(a.info['content'] for a in p.annots())==['Corregida','Nota nueva ✓']
    restored[2]['points']=[[60,260],[140,300]]
    with f.open(stream=export_pdf(base,restored)) as d:assert d[0].get_image_rects(d[0].get_images()[0][0])[0].x0==60
    assert sha256(data).hexdigest()==original


@pytest.mark.parametrize('patch',[{'name':''},{'name':'x\n.pdf'},{'page':-1},{'page':2},{'page':True},{'zoom':0},{'zoom':5},{'zoom':True},{'base_changes':-1},{'base_changes':False}])
def test_invalid_state_rejected(example,patch):
    base,ops,state=example
    with pytest.raises(DocumentError):build_project(base,ops,{**state,**patch})


def test_corruption_hash_mismatch_and_duplicate_or_extra_names_rejected(example):
    packed,_=build_project(*example)
    with pytest.raises(DocumentError):read_project(b'not zip')
    for changed in [rewrite(packed,{'operations.json':b'[]'}),rewrite(packed,{'base.pdf':b'bad'}),rewrite(packed,extra=('../outside','bad')),rewrite(packed,extra=('base.pdf','bad'))]:
        with pytest.raises(DocumentError):read_project(changed)


@pytest.mark.parametrize('patch',[{'version':2},{'version':True},{'format':'other'},{'state':[]},{'saved_at':4}])
def test_manifest_schema_rejected(example,patch):
    packed,manifest=build_project(*example)
    with pytest.raises(DocumentError):read_project(rewrite(packed,{'manifest.json':json.dumps({**manifest,**patch}).encode()}))


def test_zip_size_limits_and_json_ops_validation(example,monkeypatch):
    import backend.projects as module
    packed,manifest=build_project(*example)
    monkeypatch.setattr(module,'MAX_BASE',10)
    with pytest.raises(DocumentError,match='tamaño'):read_project(packed)
    with pytest.raises(DocumentError,match='60 MB'):build_project(*example)


def test_project_operations_are_revalidated_after_hash_matches(example):
    packed,manifest=build_project(*example);invalid=b'[{"type":"unknown","page":0}]'
    manifest['sha256']['operations.json']=sha256(invalid).hexdigest()
    with pytest.raises(DocumentError,match='Tipo de operación'):read_project(rewrite(packed,{'manifest.json':json.dumps(manifest).encode(),'operations.json':invalid}))


def test_non_finite_extra_data_is_not_serializable(example):
    base,ops,state=example
    with pytest.raises(DocumentError,match='serializables'):build_project(base,[{**ops[0],'extra':float('nan')}],state)


def test_atomic_recovery_keeps_previous_checkpoint_on_replace_failure(example,tmp_path,monkeypatch):
    import backend.projects as module
    store=RecoveryStore(tmp_path);packed,_=build_project(*example)
    revision=store.save(packed,None)
    assert store.status()['available'] and store.status()['revision']==revision
    def fail(*args):raise OSError('disk full')
    monkeypatch.setattr(module.os,'replace',fail)
    with pytest.raises(OSError):store.save(packed+b'x',revision)
    assert store.path.read_bytes()==packed and not list(tmp_path.glob('*.tmp'))


def test_revision_conflicts_prevent_old_window_overwriting_or_deleting(example,tmp_path):
    store=RecoveryStore(tmp_path);packed,_=build_project(*example);revision=store.save(packed,None)
    for action in [lambda:store.save(packed,None),lambda:store.read(None),lambda:store.delete(None)]:
        with pytest.raises(RecoveryConflict):action()
    assert store.path.read_bytes()==packed
    store.delete(revision);assert store.status()=={'available':False,'revision':None}


def test_distinct_instances_use_os_lock_for_compare_and_replace(example,tmp_path):
    packed,_=build_project(*example)
    def attempt(_):
        try:return RecoveryStore(tmp_path).save(packed,None)
        except RecoveryConflict:return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(attempt,range(2)))
    assert results.count('conflict')==1 and RecoveryStore(tmp_path).status()['available']


def test_recovery_survives_new_python_process(example,tmp_path):
    packed,_=build_project(*example);store=RecoveryStore(tmp_path);store.save(packed,None)
    code='from backend.projects import RecoveryStore;import sys,json;s=RecoveryStore(sys.argv[1]);print(json.dumps(s.status()))'
    output=subprocess.run([sys.executable,'-c',code,str(tmp_path)],capture_output=True,text=True,check=True)
    report=json.loads(output.stdout);assert report['available'] and report['state']['page']==1


def test_corrupt_recovery_report_can_be_discarded_without_loading_it(tmp_path):
    store=RecoveryStore(tmp_path);tmp_path.mkdir(exist_ok=True);store.path.write_bytes(b'bad checkpoint')
    status=store.status();assert status['error'] and not status['available']
    store.delete(status['revision']);assert not store.path.exists()


def test_api_project_and_recovery_survive_backend_lifespan_restart(example,tmp_path,monkeypatch):
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path));base,ops,state=example
    with TestClient(app) as c:
        document=c.post('/api/documents',files={'file':('demo.pdf',base)}).json();url=f"/api/documents/{document['id']}"
        payload={**state,'operations':ops,'revision':None}
        project=c.post(url+'/project',json=payload);assert project.status_code==200
        imported=c.post('/api/projects/open',files={'file':('demo.reapdf',project.content)});assert imported.status_code==200
        result=imported.json();assert result['operations']==ops and result['state']==state
        assert c.get('/api/recovery').json()['revision'] is None
        checkpoint=c.post(url+'/recovery',json=payload);assert checkpoint.status_code==200
        revision=checkpoint.json()['revision']
        assert c.post(url+'/recovery',json=payload).status_code==409
        assert c.request('DELETE','/api/recovery',json={}).status_code==409
        assert c.post('/api/projects/open',files={'file':('bad.reapdf',b'bad')}).status_code==422
        assert c.post(url+'/export',json={}).content==base
    with TestClient(app) as c:
        assert c.get('/api/recovery').json()['revision']==revision
        restored=c.post('/api/recovery/restore',json={'revision':revision});assert restored.status_code==200
        result=restored.json();assert result['operations']==ops
        assert c.post(f"/api/documents/{result['document']['id']}/export",json={}).content==base
        assert c.request('DELETE','/api/recovery',json={'revision':revision}).status_code==200


def test_read_only_signed_pdf_can_be_saved_without_modifying_it(example):
    data,_,state=example
    with f.open(stream=data) as doc:
        doc.xref_set_key(doc.pdf_catalog(),'AcroForm','<< /SigFlags 3 >>');signed=doc.tobytes()
    packed,_=build_project(signed,[],state)
    assert read_project(packed)[0]==signed


def test_project_normalizes_image_ui_metadata_and_assigns_missing_id(example):
    base,ops,state=example
    image={**ops[2]};image.pop('id');image.pop('pixels');image['name']=None
    packed,_=build_project(base,[image],state)
    restored=read_project(packed)[1][0]
    assert isinstance(restored['id'],str) and restored['pixels']==[40,20] and restored['name']=='Imagen insertada'
    packed,_=build_project(base,[{**ops[0],'id':'not-a-mark'},image],state)
    assert 'id' not in read_project(packed)[1][0]


def test_duplicate_session_ids_rejected(example):
    base,ops,state=example
    with pytest.raises(DocumentError,match='identificadores'):build_project(base,[ops[1],{**ops[1],'point':[80,220]}],state)


def test_restore_quota_failure_and_storage_failure_keep_existing_document(example,tmp_path,monkeypatch):
    import importlib
    module=importlib.import_module('backend.app')
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path));base,ops,state=example
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('base.pdf',base)}).json();url=f"/api/documents/{doc['id']}"
        revision=c.post(url+'/recovery',json={**state,'operations':ops}).json()['revision']
        monkeypatch.setattr(module,'MAX_STORE',len(base)+1)
        assert c.post('/api/recovery/restore',json={'revision':revision}).status_code==413
        assert c.post(url+'/export',json={}).content==base
        assert c.get('/api/recovery').json()['revision']==revision
        def fail(*args,**kwargs):raise OSError('disk full')
        monkeypatch.setattr(app.state.recovery,'save',fail)
        assert c.post(url+'/recovery',json={**state,'operations':ops,'revision':revision}).status_code==507
        assert c.get('/api/recovery').json()['revision']==revision
        assert c.post(url+'/project',json={**state,'operations':ops}).status_code==200
