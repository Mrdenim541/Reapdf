"""Synthetic receipt-protocol tests; these do not verify the Windows application."""
import hashlib,json,subprocess
from pathlib import Path
import pytest
from scripts.check_desktop_candidate import CHECKS
from scripts.publish_windows_report import assess,publish,source_objects,BRANCH


def report(folder,sha='a'*40,objects=None):
    folder.mkdir(parents=True,exist_ok=True);checks=[]
    for name in CHECKS:
        path=folder/(Path(name).stem+'.log');path.write_bytes(b'PASS: synthetic protocol fixture\n');checks.append({'name':name,'log':path.name,'passed':True,'returncode':0,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    value={'source_commit':sha,'platform':'Windows','source_dirty':False,'source_dirty_after':False,'source_git_objects':objects or {},'checks':checks,'passed':True}
    (folder/'desktop-report.json').write_text(json.dumps(value));return value


@pytest.mark.parametrize('mutation',['source','platform','dirty','dirty_after','objects','missing_check','missing_log','hash','code'])
def test_stale_incomplete_or_tampered_receipts_never_verify(tmp_path,mutation):
    value=report(tmp_path)
    if mutation=='source':value['source_commit']='b'*40
    if mutation=='platform':value['platform']='Linux'
    if mutation=='dirty':value['source_dirty']=True
    if mutation=='dirty_after':value['source_dirty_after']=True
    if mutation=='objects':value['source_git_objects']={'backend/other.py':'wrong'}
    if mutation=='missing_check':value['checks'].pop()
    if mutation=='missing_log':(tmp_path/value['checks'][0]['log']).unlink()
    if mutation=='hash':value['checks'][0]['sha256']='wrong'
    if mutation=='code':value['checks'][0]['returncode']=1
    (tmp_path/'desktop-report.json').write_text(json.dumps(value))
    assert not assess(tmp_path,'a'*40,{},CHECKS)['verified']


def test_no_report_is_explicitly_unverified(tmp_path):assert not assess(tmp_path,'a'*40,{},CHECKS)['verified']


def git(root,*args):return subprocess.check_output(['git',*args],cwd=root,text=True,stderr=subprocess.DEVNULL).strip()


def test_publication_uses_own_fast_forward_branch_and_does_not_change_source_worktree(tmp_path,monkeypatch):
    root=tmp_path/'source';root.mkdir();remote=tmp_path/'remote.git';subprocess.run(['git','init','--bare',str(remote)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    git(root,'init');git(root,'config','user.name','Fixture');git(root,'config','user.email','fixture@example.invalid');(root/'backend').mkdir();(root/'backend/demo.py').write_text('value = 1\n');git(root,'add','.');git(root,'commit','-m','Fixture source');git(root,'remote','add','origin',str(remote));sha=git(root,'rev-parse','HEAD');objects=source_objects(root)
    folder=tmp_path/'evidence';report(folder,sha,objects);monkeypatch.setenv('GITHUB_ACTIONS','true')
    receipt=publish(root,folder,sha,'10','1');assert receipt['verified']
    first=git(root,'ls-remote','origin','refs/heads/'+BRANCH).split()[0]
    second=publish(root,folder,sha,'10','2');head=git(root,'ls-remote','origin','refs/heads/'+BRANCH).split()[0]
    assert first!=head and second['verified'] and git(root,'rev-parse',head+'^')==first
    assert git(root,'rev-parse','HEAD')==sha and not git(root,'status','--porcelain') and not git(root,'diff','--cached')
