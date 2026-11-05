"""Exercise task ribbon placement, folding, persistence and document space in Qt."""
import base64,json,tempfile,time
from pathlib import Path
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_semantic_text_sample import create
root=Path(tempfile.mkdtemp(prefix='reapdf-studio-qt-'));sample=root/'Workspace.pdf';sample.write_bytes(create('quick'))
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(sample));window.resize(1500,1000);window.show()
def js(script):
 values=[];loop=QEventLoop();window.page.runJavaScript(script,lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec()
 if not values:raise AssertionError('Qt did not respond')
 return values[0]
def wait(script):
 deadline=time.monotonic()+35
 while time.monotonic()<deadline:
  if js(script):return
  QTest.qWait(100)
 raise AssertionError(script)
def click(selector):
 wait('!!document.querySelector('+json.dumps(selector)+')');js('document.querySelector('+json.dumps(selector)+').scrollIntoView({block:"nearest",inline:"nearest"})');QTest.qWait(100)
 p=json.loads(js('JSON.stringify((()=>{const r=document.querySelector('+json.dumps(selector)+').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];})())'))
 QTest.mouseClick(window.view.focusProxy() or window.view,Qt.MouseButton.LeftButton,pos=QPoint(round(p[0]),round(p[1])))
def dimensions():return json.loads(js('JSON.stringify((()=>{const rect=s=>{const r=document.querySelector(s).getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};return {tools:rect(".tools"),canvas:rect(".canvas-area"),nav:rect(".document-sidebar"),body:document.documentElement.scrollWidth,viewport:innerWidth};})())'))
try:
 wait('document.querySelector(".document-bar")?.textContent.includes("Workspace.pdf")&&document.querySelector(".paper img")?.complete');wait('!document.querySelector(".loading")')
 for width,height in [(1500,1000),(1280,760),(900,760)]:
  window.resize(width,height);QTest.qWait(300);d=dimensions()
  assert d['tools']['bottom']<=d['canvas']['y']+1,d
  assert d['nav']['right']<=d['canvas']['x']+1 and d['canvas']['w']>=width-170,d
  assert d['canvas']['h']>=300 and d['body']<=d['viewport']+1,d
 window.resize(1500,1000);QTest.qWait(250);click('#area-tab-edit');wait('document.querySelector("#area-tab-edit").getAttribute("aria-selected")==="true"')
 click('.catalog-action[aria-label="Editar texto"]');wait('!!document.querySelector(".text-target")')
 click('.ribbon-toggle');wait('document.querySelector("#workspace-tools").hidden');assert js('localStorage.getItem("reapdf.ribbon-open")')=='false';assert js('!!document.querySelector(".text-target")')
 before=dimensions()['canvas']['h'];click('.ribbon-toggle');wait('!document.querySelector("#workspace-tools").hidden');assert dimensions()['canvas']['h']<before-100;assert js('localStorage.getItem("reapdf.ribbon-open")')=='true'
 # Reload the UI and reopen the fixture: a reload does not repeat the native open-file event.
 click('.ribbon-toggle');js('window.__studioBeforeReload=true;location.reload()');wait('window.__studioBeforeReload!==true&&!!document.querySelector(".studio-layout")');assert js('localStorage.getItem("reapdf.ribbon-open")')=='false'
 encoded=base64.b64encode(sample.read_bytes()).decode()
 js('(()=>{const bytes=Uint8Array.from(atob('+json.dumps(encoded)+'),c=>c.charCodeAt(0)),dt=new DataTransfer();dt.items.add(new File([bytes],"Workspace.pdf",{type:"application/pdf"}));const input=document.querySelector('+json.dumps('[aria-label="Archivo PDF"]')+');input.files=dt.files;input.dispatchEvent(new Event("change",{bubbles:true}));})()')
 wait('document.querySelector(".ribbon-toggle")?.getAttribute("aria-expanded")==="false"');click('.ribbon-toggle');wait('!document.querySelector("#workspace-tools").hidden');wait('document.querySelector(".paper img")?.complete&&!document.querySelector(".loading")');click('#area-tab-edit');click('.catalog-action[aria-label="Editar texto"]');wait('!!document.querySelector(".text-target")')
 window.resize(1500,1000);QTest.qWait(400);image=root/'studio.png';window.grab().save(str(image));print('CAPTURE:',image)
 print('PASS: actual Qt mouse selects a task and original text, ribbon folds and persists across reload, navigation stays left, page gains space, and 1500/1280/900 layouts have usable document height without horizontal body overflow.')
finally:window.close()
