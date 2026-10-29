import json
from pathlib import Path
import pytest
from scripts.release_readiness import REQUIRED_CRITERIA,audit,record,parse_logs,snapshot


@pytest.fixture
def repo(tmp_path):
    root=tmp_path/'repo';root.mkdir();(root/'backend').mkdir();(root/'backend/app.py').write_text('VERSION="test"\n');(root/'package.json').write_text('{"version":"0.34.0"}')
    (root/'web/dist').mkdir(parents=True);(root/'web/dist/index.html').write_text('<html></html>');(root/'docs').mkdir()
    criteria={'schema':1,'scope':'test','criteria':[{'id':key,'status':'partial','remaining':'Pendiente'} for key in sorted(REQUIRED_CRITERIA)]}
    (root/'docs/release-criteria.json').write_text(json.dumps(criteria))
    values={'python':'48 passed in 1s','javascript':'ℹ pass 3\nℹ fail 0','browser':'PASS: browser','build':'✓ built in 200ms'};paths={}
    for key,value in values.items():p=tmp_path/(key+'.log');p.write_text(value);paths[key]=p
    return root,root/'docs/validation/test/receipt.json',paths


def test_receipt_binds_sources_build_and_evidence_without_claiming_release(repo):
    root,path,logs=repo;proof=record(root,path,logs);report=audit(root,path)
    assert report['local_regression_verified'] and report['validation']['python']==48
    assert not report['ready_for_1_0'] and len(report['pending'])==len(REQUIRED_CRITERIA)
    assert proof['sources']==snapshot(root) and set(proof['evidence'])=={'python','javascript','browser','build'}


@pytest.mark.parametrize('change',['source','build','log','version','count'])
def test_stale_or_changed_receipt_fails_closed(repo,change):
    root,path,logs=repo;record(root,path,logs)
    if change=='source':(root/'backend/app.py').write_text('changed')
    elif change=='build':(root/'web/dist/index.html').write_text('changed')
    elif change=='log':(path.parent/'python.log').write_text('49 passed')
    elif change=='version':(root/'package.json').write_text('{"version":"0.35.0"}')
    else:
        proof=json.loads(path.read_text());proof['validation']['python']=999;path.write_text(json.dumps(proof))
    report=audit(root,path);assert not report['local_regression_verified'] and not report['ready_for_1_0'] and report['evidence_errors']


@pytest.mark.parametrize('kind,value',[('python','1 failed'),('python','0 passed'),('javascript','ℹ pass 3\nℹ fail 1'),('browser','FAIL: browser'),('browser','PASS: browser\nExpectError: broken'),('build','error during build')])
def test_failed_logs_cannot_be_recorded(repo,kind,value):
    root,path,logs=repo;logs[kind].write_text(value)
    with pytest.raises(ValueError):record(root,path,logs)
    assert not path.exists()


def test_missing_proof_and_incomplete_checklist_not_ready(repo):
    root,path,logs=repo;assert not audit(root,path)['local_regression_verified']
    criteria=json.loads((root/'docs/release-criteria.json').read_text());criteria['criteria'].pop();(root/'docs/release-criteria.json').write_text(json.dumps(criteria))
    with pytest.raises(ValueError):audit(root,path)


def test_linux_evidence_does_not_certify_windows_even_if_manually_marked_done(repo,monkeypatch):
    import scripts.release_readiness as module
    root,path,logs=repo;criteria=json.loads((root/'docs/release-criteria.json').read_text())
    for r in criteria['criteria']:r['status']='verified'
    (root/'docs/release-criteria.json').write_text(json.dumps(criteria));monkeypatch.setattr(module.platform,'system',lambda:'Linux');record(root,path,logs)
    report=audit(root,path);assert report['local_regression_verified'] and not report['windows_execution_evidence'] and not report['ready_for_1_0'];assert report['pending'][0]['id']=='windows_execution'
