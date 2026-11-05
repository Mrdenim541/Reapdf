"""Real Qt caret edits of ActualText/Stm and page-owned shared Form paragraphs."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_semantic_text_sample import create
from backend.native_text import native_model
from backend.structure_editing import reading_preview
root=Path(tempfile.mkdtemp(prefix='reapdf-semantic-qt-'));original=root/'Stream.pdf';base=create();original.write_bytes(base)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1650,1100);window.show()
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
    expr='[...document.querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+json.dumps(label)+')'
    wait('!!'+expr+' && !'+expr+'.disabled');js(expr+'.click()')
def edit(label,value,textarea=False):
    expr=field(label);wait(expr+'?.disabled===false');js('(()=>{const e='+expr+';Object.getOwnPropertyDescriptor(' + ('HTMLTextAreaElement' if textarea else 'HTMLInputElement')+'.prototype,"value").set.call(e,'+json.dumps(str(value))+');e.dispatchEvent(new Event("input",{bubbles:true}));})()')
def type_text(label,text):
    js(field(label)+'.focus()');target=window.view.focusProxy() or window.view;QTest.keyClick(target,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);QTest.keyClicks(target,text,delay=2)
def apply(label):
    js(field(label)+'.focus()');QTest.keyClick(window.view.focusProxy() or window.view,Qt.Key.Key_Return,Qt.KeyboardModifier.ControlModifier)
def select(text):
    click('Editar');wait(field('Editar texto')+'?.disabled===false');js(field('Editar texto')+'.closest("details").open=true');js(field('Editar texto')+'.click()')
    expr='[...document.querySelectorAll("[role=button]")].find(e=>(e.getAttribute("aria-label")||"").startsWith('+json.dumps('Editar en página: '+text)+'))';wait('!!'+expr);js(expr+'.scrollIntoView({block:"center"})');QTest.qWait(150)
    point=json.loads(js('JSON.stringify((()=>{const r='+expr+'.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];})())'));QTest.mouseClick(window.view.focusProxy() or window.view,Qt.MouseButton.LeftButton,pos=QPoint(round(point[0]),round(point[1])));wait(field('Texto sobre la página')+'?.disabled===false')
def save(path):
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty')
def open_file(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Stream.pdf")');select('HELLO');wait(field('Texto para lectura accesible')+'?.value==="Accessible original"')
    type_text('Texto sobre la página','HOLA');type_text('Texto para lectura accesible','Updated accessible');apply('Texto sobre la página');wait('!document.querySelector(".inline-text-editor")');click('↶ Deshacer');click('↷ Rehacer');edited=root/'Edited.pdf';save(edited)
    with f.open(edited) as d:
        r=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HOLA');assert r['stream_tagged'] and r['accessible_text']=='Updated accessible'
    open_file(edited);select('HOLA');wait(field('Texto para lectura accesible')+'?.value==="Updated accessible"');type_text('Texto para lectura accesible','Second reading');apply('Texto sobre la página');wait('!document.querySelector(".inline-text-editor")');second=root/'Second.pdf';save(second)
    with f.open(edited) as a,f.open(second) as b:assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
    actual=root/'Actual.pdf';actual.write_bytes(create('actual'));open_file(actual);select('HELLO');wait('document.querySelector(".inline-accessible-text input")?.checked===true');type_text('Texto sobre la página','HOLA');apply('Texto sobre la página');wait('!document.querySelector(".inline-text-editor")');matched=root/'Matching.pdf';save(matched)
    with f.open(matched) as d:assert 'HOLA' in d[0].get_text() and 'HELLO' not in d[0].get_text()
    outer=root/'Outer.pdf';outer.write_bytes(create('outer'));open_file(outer);select('HELLO');click('Editar párrafo');wait(field('Párrafo sobre la página')+'?.disabled===false');type_text('Párrafo sobre la página','HOLA '*20);edit('Ancho del párrafo en página',120);edit('Alto del párrafo en página',30);click('Continuar en otra página');wait(field('Texto del párrafo entre páginas')+'?.disabled===false');apply('Texto del párrafo entre páginas');wait('!document.querySelector("dialog[open]")');continued=root/'Continued.pdf';save(continued)
    with f.open(continued) as d:assert d[0].get_text().count('HELLO')==1 and sum(p.get_text().count('HOLA') for p in d)==20
    assert all(b['tagged'] for b in reading_preview(continued.read_bytes(),[],1)['blocks'] if 'HOLA' in b['text'])
    assert original.read_bytes()==base
    print('PASS: actual Qt mouse/caret edits visible glyphs and accessible reading in a Stm Form, undo/redo, native save/reopen/reedit; accessible-only edit preserves pixels; matching ActualText updates automatically; shared page-owned Form paragraph continues with tags and other occurrence intact.')
except Exception:
    print(js('document.body.innerText'));raise
finally:window.allow_close=True;window.close();app.processEvents()
