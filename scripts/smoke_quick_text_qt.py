"""Right-click and keyboard context editing, deletion and native save in Qt."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_semantic_text_sample import create
root=Path(tempfile.mkdtemp(prefix='reapdf-quick-qt-'));original=root/'Numbers.pdf';base=create('quick');original.write_bytes(base);output=root/'Updated.pdf'
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1500,1050);window.show()
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
def field(label):return 'document.querySelector('+json.dumps('[aria-label="'+label+'"]')+')'
def click(label):
    expr='(document.querySelector(".text-context-menu")?[...document.querySelectorAll(".text-context-menu button")]:[...document.querySelectorAll("button,[role=button],[role=menuitem]")]).find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+json.dumps(label)+')';wait('!!'+expr+'&&!'+expr+'.disabled');js(expr+'.click()')
def target(text):return '[...document.querySelectorAll(".text-target")].find(e=>e.getAttribute("aria-label")==='+json.dumps('Editar en página: '+text)+')'
def menu(text,keyboard=False):
    click('Editar');wait(field('Editar texto')+'?.disabled===false');js(field('Editar texto')+'.closest("details").open=true');js(field('Editar texto')+'.click()');expr=target(text);wait('!!'+expr);js(expr+'.scrollIntoView({block:"center"})');QTest.qWait(150)
    if keyboard:js(expr+'.focus()');QTest.keyClick(window.view.focusProxy() or window.view,Qt.Key.Key_F10,Qt.KeyboardModifier.ShiftModifier)
    else:
        p=json.loads(js('JSON.stringify((()=>{const r='+expr+'.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];})())'));QTest.mouseClick(window.view.focusProxy() or window.view,Qt.MouseButton.RightButton,pos=QPoint(round(p[0]),round(p[1])))
    wait('!!document.querySelector(".text-context-menu")')
def type_value(value):
    js(field('Texto de edición rápida')+'.focus()');t=window.view.focusProxy() or window.view;QTest.keyClick(t,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);QTest.keyClicks(t,value)
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Numbers.pdf")');menu('1000000001');click('Editar');wait(field('Texto de edición rápida')+'?.value==="1000000001"');assert js('window.__reapdfCloseState.dirty')
    type_value('1000000002');click('Cancelar');wait('!document.querySelector("dialog[open]")');assert js('!!'+target('1000000001'))
    menu('1000000001',keyboard=True);click('Editar');wait(field('Texto de edición rápida')+'?.disabled===false');type_value('X'*100);click('Aplicar');wait('document.querySelector(".quick-text-dialog [role=alert]")?.innerText.length>0');assert js(field('Texto de edición rápida')+'.value')=='X'*100
    type_value('1000000002');js(field('Texto de edición rápida')+'.focus()');QTest.keyClick(window.view.focusProxy() or window.view,Qt.Key.Key_Return,Qt.KeyboardModifier.ControlModifier);wait('!document.querySelector("dialog[open]")');wait('!!'+target('1000000002'))
    menu('1000000002');click('Eliminar');wait('!document.querySelector("dialog[open]")&&!document.querySelector(".text-context-menu")');wait('!'+target('1000000002'));click('↶ Deshacer');click('Editar');js(field('Editar texto')+'.closest("details").open=true');js(field('Editar texto')+'.click()');wait('!!'+target('1000000002'))
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty')
    with f.open(output) as d:
        assert '1000000002' in d[0].get_text() and '1000000001' not in d[0].get_text()
        assert '1000000002' in d[0].get_text(flags=f.TEXTFLAGS_TEXT|f.TEXT_IGNORE_ACTUALTEXT)
    assert original.read_bytes()==base
    print('PASS: actual Qt right-click and Shift+F10 open text menu; compact dialog preloads code, cancel preserves original, overflow retains draft, Ctrl+Enter updates visible/accessible code, Delete works with document undo, native save preserves final edit and source bytes.')
except Exception:
    print(js('document.body.innerText'));raise
finally:window.allow_close=True;window.close();app.processEvents()
