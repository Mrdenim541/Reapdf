"""Kill a controlled parent and verify its real Qt child exits through pipe EOF."""
import json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path
root=Path(tempfile.mkdtemp(prefix='reapdf-parent-exit-'));record=root/'child.json'
code="""import json,sys,time
from pathlib import Path
from portable.desktop import NativeDesktopWindow
window=NativeDesktopWindow(None,'http://127.0.0.1:8000')
assert window.wait_ready()=='ready'
Path(sys.argv[1]).write_text(json.dumps({'pid':window.process.pid}))
while True:time.sleep(1)
"""

def alive(pid):
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.restype=wintypes.HANDLE;kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];kernel.GetExitCodeProcess.restype=wintypes.BOOL
        kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return False
        try:
            value=wintypes.DWORD();assert kernel.GetExitCodeProcess(handle,ctypes.byref(value));return value.value==259
        finally:kernel.CloseHandle(handle)
    try:
        os.kill(pid,0)
        status=Path(f'/proc/{pid}/stat')
        return not status.exists() or status.read_text().split()[2]!='Z'
    except ProcessLookupError:return False

environment=os.environ.copy();environment['REAPDF_INSTANCE_NAMESPACE']=str(root)
parent=subprocess.Popen([sys.executable,'-c',code,str(record)],env=environment)
child=None
try:
    deadline=time.monotonic()+35
    while not record.exists():
        assert parent.poll() is None and time.monotonic()<deadline,'Parent did not confirm a real loaded Qt child'
        time.sleep(.1)
    child=json.loads(record.read_text())['pid'];assert alive(child)
    parent.kill();parent.wait(timeout=10)
    deadline=time.monotonic()+15
    while alive(child) and time.monotonic()<deadline:time.sleep(.1)
    assert not alive(child),'Qt child survived forced parent exit'
    print('PASS: loaded Qt child exits after controlled parent is killed; no unrelated process is terminated.')
finally:
    if parent.poll() is None:parent.terminate();parent.wait(timeout=10)
    if child and alive(child):os.kill(child,signal.SIGTERM)
