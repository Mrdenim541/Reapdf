from pathlib import Path
import json
import pytest
from scripts import local_workspace as local


@pytest.mark.parametrize('value,reapdf,rea', [('v24.19.0',True,False),('v24.22.1',True,True),('24.30.0',True,True),('v22.23.4',False,False),('v26.12.1',False,False),('bad',False,False),(None,False,False)])
def test_shared_node_version_must_satisfy_project_and_rea(value,reapdf,rea):
    assert local.node_ready(value)==reapdf and local.node_ready(value,True)==rea


def test_setup_uses_only_local_venv_and_locked_dependencies(tmp_path,monkeypatch):
    root=tmp_path/'Proyecto con espacios';root.mkdir();monkeypatch.setattr(local,'executable',lambda name:'C:/Program Files/nodejs/npm.cmd')
    commands=local.setup_commands(root);assert commands[0][-2:]==['venv',str(root/'.venv')]
    assert commands[1][0]==str(local.python_path(root)) and commands[1][1:]==['-m','pip','install','-r','requirements-lock.txt','PySide6==6.8.3']
    assert commands[2][1:]==['ci'] and commands[3][1:]==['run','build']
    assert not (root/'.venv').exists()
    assert local.python_path(root,windows=True)==root/'.venv/Scripts/python.exe'


def test_rea_is_pinned_codex_only_and_plan_does_not_apply_configuration(monkeypatch):
    monkeypatch.setattr(local,'version',lambda name:'v24.22.1');monkeypatch.setattr(local,'executable',lambda name:'C:/Program Files/nodejs/npx.cmd')
    plan=local.rea_commands()[0];apply=local.rea_commands(True)[0]
    assert 'rea-agents@6.8.0' in plan and plan[-2:]==['--dry-run','--json']
    assert apply[-2:]==['--client','codex'] and '--all-detected' not in apply and '--install-hopper' not in apply
    monkeypatch.setattr(local,'version',lambda name:'v24.19.0')
    with pytest.raises(ValueError,match='24.22.1'):local.rea_commands()


def test_dry_run_does_not_launch_installations_or_modify_files(monkeypatch,tmp_path,capsys):
    monkeypatch.setattr(local,'ROOT',tmp_path);monkeypatch.setattr(local,'setup_commands',lambda:[['local-python','-m','pip','install','example']]);monkeypatch.setattr(local,'version',lambda name:'v24.22.1');monkeypatch.setattr(local,'executable',lambda name:'npm');monkeypatch.setattr(local.sys,'argv',['local_workspace.py','setup','--dry-run'])
    monkeypatch.setattr(local,'execute',lambda *args:pytest.fail('Dry run executed a command'))
    assert local.main()==0 and json.loads(capsys.readouterr().out)['commands'][0][0]=='local-python'
    assert not list(tmp_path.iterdir())
