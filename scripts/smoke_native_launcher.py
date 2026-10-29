"""Launch the real parent/backend/Qt chain and verify secondary exit ownership."""
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


root=Path(tempfile.mkdtemp(prefix='reapdf-launch-check-'))
def launch(name):
    ready=root/(name+'.ready');log=(root/(name+'.log')).open('wb')
    process=subprocess.Popen([sys.executable,'portable/launcher.py','--native-desktop','--require-desktop','--ready-file',str(ready)],stdout=log,stderr=subprocess.STDOUT)
    return process,ready,log

def wait_ready(process,path):
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        if path.exists() and path.stat().st_size:return path.read_text()
        if process.poll() is not None:raise AssertionError(f'Launcher exited before ready: {process.returncode}')
        time.sleep(.1)
    raise AssertionError('Launcher did not confirm readiness')

def health(url):
    with urllib.request.urlopen(url+'/api/health',timeout=5) as response:return json.load(response)

first,ready,first_log=launch('first')
try:
    url=wait_ready(first,ready);assert first.poll() is None and health(url)['status']=='ok'
    second,second_ready,second_log=launch('second')
    try:
        other=wait_ready(second,second_ready);assert second.wait(timeout=10)==0
        assert other!=url and first.poll() is None and health(url)['status']=='ok'
        try:health(other)
        except OSError:pass
        else:raise AssertionError('Secondary backend survived successful handoff')
    finally:
        if second.poll() is None:second.terminate();second.wait(timeout=10)
        second_log.close()
finally:
    if first.poll() is None:first.terminate();first.wait(timeout=15)
    first_log.close()
print('PASS: actual launcher confirms loaded Qt frontend, secondary exits normally, own backend stops, first remains available.')
