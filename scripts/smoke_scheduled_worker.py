"""Kill an owned queue parent and verify its actual isolated PDF worker exits."""
import json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path
import pymupdf as f
root=Path(tempfile.mkdtemp(prefix='reapdf-job-parent-'));source=root/'Scan.pdf';record=root/'worker.json'
with f.open() as text,f.open() as d:
    p=text.new_page(width=300,height=400);p.insert_text((30,100),'REAPDF DOCUMENT 12345',fontsize=16);pix=p.get_pixmap(matrix=f.Matrix(2,2),alpha=False)
    for _ in range(10):
        page=d.new_page(width=300,height=400);page.insert_image(page.rect,pixmap=pix)
    d.save(source)
code='''import json,sys,threading,time
from datetime import datetime,timezone
from pathlib import Path
from backend.scheduled_recipes import Queue
root=Path(sys.argv[1]);q=Queue(root)
recipe={'format':'reapdf-recipe','version':1,'name':'Owned worker','filename':'{name}','steps':[{'type':'ocr','language':'eng','dpi':300,'orientation':0}]}
job=q.create([('Scan.pdf',(root/'Scan.pdf').read_bytes(),[])],recipe,datetime.now(timezone.utc).isoformat())
threading.Thread(target=q.tick,daemon=True).start()
deadline=time.monotonic()+15
while q.process is None:
    assert time.monotonic()<deadline,'Queue did not start its isolated process'
    time.sleep(.01)
(root/'worker.json').write_text(json.dumps({'pid':q.process.pid,'job':job['id']}))
while True:time.sleep(1)
'''
def alive(pid):
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes as w
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE;kernel.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];kernel.CloseHandle.argtypes=[w.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return False
        try:value=w.DWORD();return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(value))) and value.value==259
        finally:kernel.CloseHandle(handle)
    try:
        os.kill(pid,0);stat=Path(f'/proc/{pid}/stat');return not stat.exists() or stat.read_text().split()[2]!='Z'
    except ProcessLookupError:return False
parent=subprocess.Popen([sys.executable,'-c',code,str(root)]);child=None
try:
    deadline=time.monotonic()+20
    while not record.exists():
        assert parent.poll() is None and time.monotonic()<deadline,'Parent did not record its queue worker';time.sleep(.05)
    info=json.loads(record.read_text());child=info['pid'];assert alive(child)
    parent.kill();parent.wait(timeout=10);deadline=time.monotonic()+10
    while alive(child) and time.monotonic()<deadline:time.sleep(.1)
    assert not alive(child),'Scheduled PDF worker survived forced parent exit'
    state=json.loads((root/'scheduled-recipes'/info['job']/'state.json').read_text());assert state['status']=='running'
    assert not (root/'scheduled-recipes'/info['job']/'result.zip').exists()
    from backend.scheduled_recipes import Queue
    q=Queue(root);q.start();q.close();assert q.list()[0]['status']=='interrupted'
    print('PASS: scheduled PDF work runs in its own actual process; forced parent exit closes its pipe, worker exits, no result is published, and restart records interruption. No unrelated process is terminated.')
finally:
    if parent.poll() is None:parent.terminate();parent.wait(timeout=10)
    if child and alive(child):os.kill(child,signal.SIGTERM)
