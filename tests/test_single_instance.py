import json,subprocess,sys,time,uuid
from pathlib import Path
import pytest
pytest.importorskip('PySide6.QtNetwork')
from PySide6.QtCore import QCoreApplication
from portable.single_instance import SingleInstance,message

@pytest.fixture
def owner():
    app=QCoreApplication.instance() or QCoreApplication([]);namespace=uuid.uuid4().hex
    instance=SingleInstance(namespace=namespace);assert instance.owner
    received=[];instance.set_handler(received.append)
    yield app,instance,namespace,received
    instance.close();app.processEvents()

def child_request(app,namespace,file):
    code='from PySide6.QtCore import QCoreApplication;from portable.single_instance import SingleInstance;import sys;app=QCoreApplication([]);s=SingleInstance(sys.argv[2] or None,namespace=sys.argv[1]);print(s.owner)'
    process=subprocess.Popen([sys.executable,'-c',code,namespace,str(file or '')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    deadline=time.monotonic()+15
    while process.poll() is None and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    if process.poll() is None:process.kill();process.wait();raise AssertionError('IPC child timed out')
    return process.returncode,*process.communicate()

def test_second_process_forwards_path_and_activation_without_owning_server(owner,tmp_path):
    app,instance,namespace,received=owner;file=tmp_path/'plano con espacios á.pdf';file.write_bytes(b'%PDF')
    code,out,err=child_request(app,namespace,file);assert code==0,err;assert out.strip()=='False'
    assert received==[str(file.resolve())]
    code,out,err=child_request(app,namespace,None);assert code==0,err;assert received[-1] is None

def test_owner_release_allows_next_start(owner):
    app,instance,namespace,_=owner;instance.close()
    next_owner=SingleInstance(namespace=namespace)
    try:assert next_owner.owner
    finally:next_owner.close()

def test_stale_lock_from_dead_process_can_restart(tmp_path):
    app=QCoreApplication.instance() or QCoreApplication([]);namespace=uuid.uuid4().hex;ready=tmp_path/'ready'
    code='from PySide6.QtCore import QCoreApplication;from portable.single_instance import SingleInstance;from pathlib import Path;import sys,time;app=QCoreApplication([]);s=SingleInstance(namespace=sys.argv[1]);Path(sys.argv[2]).write_text(str(s.owner));time.sleep(60)'
    child=subprocess.Popen([sys.executable,'-c',code,namespace,str(ready)])
    try:
        deadline=time.monotonic()+5
        while not ready.exists() and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert ready.read_text()=='True'
    finally:child.kill();child.wait(timeout=5)
    instance=SingleInstance(namespace=namespace)
    try:assert instance.owner
    finally:instance.close()

def test_missing_or_wrong_type_files_are_not_handed_off(tmp_path):
    with pytest.raises(OSError):message(tmp_path/'missing.pdf')
    file=tmp_path/'file.exe';file.write_bytes(b'not pdf')
    with pytest.raises(ValueError):message(file)
