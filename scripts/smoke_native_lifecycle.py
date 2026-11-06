"""A confirmed root close must quit even when Qt implicit last-window quit is off."""
import json,os,subprocess,sys,tempfile
from pathlib import Path
root=Path(tempfile.mkdtemp(prefix='reapdf-lifecycle-'))
code=r'''
import sys,time
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
import portable.native_window as native
original=native.create_window;mode=sys.argv[1]
choices=iter([QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Discard])
QMessageBox.question=lambda *a:QMessageBox.StandardButton.Discard if mode=='early' else next(choices)
QMessageBox.information=lambda *a:QMessageBox.StandardButton.Ok
def create(*a,**kw):
 window=original(*a,**kw);QApplication.instance().setQuitOnLastWindowClosed(False);watch=window.watch_ready
 if mode=='early':QTimer.singleShot(0,window.close);return window
 def ready(ok,fail):
  def loaded():
   ok()
   if mode=='clean':QTimer.singleShot(50,window.close);return
   state={'dirty':mode=='cancel','busy':mode=='busy'}
   def close_first(unused):
    window.close();deadline=time.monotonic()+5
    def inspect():
     if window.checking_close and time.monotonic()<deadline:QTimer.singleShot(25,inspect);return
     assert window.isVisible() and not window.allow_close,'The guard allowed premature shutdown'
     print('GUARD_PRESERVED='+mode,flush=True)
     window.page.runJavaScript('window.__reapdfCloseState='+__import__('json').dumps({'dirty':mode=='cancel','busy':False}),lambda unused:window.close())
    QTimer.singleShot(100,inspect)
   window.page.runJavaScript('window.__reapdfCloseState='+__import__('json').dumps(state),close_first)
  watch(loaded,fail)
 window.watch_ready=ready;return window
native.create_window=create
sys.argv=['native_window.py','http://127.0.0.1:8000'];sys.exit(native.main())
'''
for mode in ['early','clean','busy','cancel']:
 env={**os.environ,'REAPDF_TRACE_LIFECYCLE':'1','REAPDF_INSTANCE_NAMESPACE':str(root/mode),'XDG_CACHE_HOME':str(root/(mode+'-cache'))}
 if sys.platform=='win32':env.pop('QTWEBENGINE_CHROMIUM_FLAGS',None) # Exercise the real portable default.
 run=subprocess.run([sys.executable,'-c',code,mode],env=env,capture_output=True,text=True,timeout=30)
 print(run.stdout);print(run.stderr)
 assert run.returncode==0,(mode,run.returncode)
 entries=[json.loads(line.split(' ',1)[1]) for line in (run.stdout+'\n'+run.stderr).splitlines() if line.startswith('REAPDF_LIFECYCLE ')]
 stages=[entry['stage'] for entry in entries]
 assert stages.count('native.close.accepted')==1 and 'native.loop.finished:0' in stages and stages[-1]=='native.instance.closed'
 if mode in ['busy','cancel']:assert 'GUARD_PRESERVED='+mode in run.stdout
 if mode=='early':assert 'native.ready.ready' not in stages
 if mode=='cancel':assert stages.count('native.close.cancelled')==1
 assert stages.index('native.close.accepted')<stages.index('native.loop.finished:0')<stages.index('native.instance.closed')
print('PASS: real native main quits after confirmed close with implicit Qt quit disabled; busy and Cancel keep the window alive first; normal zero exit and ordered loop/instance cleanup are verified for all four owned subprocesses, including cancellation before readiness without publishing a ready signal.')
