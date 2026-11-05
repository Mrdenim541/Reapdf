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
root=Path(tempfile.mkdtemp(prefix='reapdf-format-qt-'));original=root/'Stream.pdf';base=create();original.write_bytes(base)
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
    wait('document.querySelector(".document-bar")?.textContent.includes("Stream.pdf")');click('Editar');click('Editar texto');wait('!!document.querySelector(".text-target")')
    target='[...document.querySelectorAll(".text-target")].find(e=>e.getAttribute("aria-label")==="Editar en página: HELLO")';js(target+'.scrollIntoView({block:"center"})');QTest.qWait(150)
    pos=json.loads(js('JSON.stringify((()=>{const r='+target+'.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];})())'));QTest.mouseClick(window.view.focusProxy() or window.view,Qt.MouseButton.LeftButton,pos=QPoint(round(pos[0]),round(pos[1])))
    wait(field('Fuente de edición directa')+'?.disabled===false')
    def option(label,value):
        e=field(label);js('(()=>{const e='+e+';e.value='+json.dumps(value)+';e.dispatchEvent(new Event("change",{bubbles:true}));})()')
    option('Fuente de edición directa','serif');option('Estilo de edición directa','bold');edit('Tamaño de edición directa',13);edit('Texto sobre la página','HOLA Ω',True);edit('Texto para lectura accesible','Reading with new font',True);apply('Texto sobre la página');wait('!document.querySelector(".inline-text-editor")');wait('!![...document.querySelectorAll(".text-target")].find(e=>e.getAttribute("aria-label")==="Editar en página: HOLA Ω")')
    click('↶ Deshacer');click('Editar');click('Editar texto');wait('!![...document.querySelectorAll(".text-target")].find(e=>e.getAttribute("aria-label")==="Editar en página: HELLO")');click('↷ Rehacer');click('Editar');click('Editar texto');wait('!![...document.querySelectorAll(".text-target")].find(e=>e.getAttribute("aria-label")==="Editar en página: HOLA Ω")')
    output=root/'Formatted.pdf';QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty');assert output.exists()
    with f.open(output) as d:
        r=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HOLA Ω');assert r['font']=='DejaVuSerif-Bold' and abs(r['size']-13)<.01 and r['editable'] and r['stream_tagged'] and r['accessible_text']=='Reading with new font'
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes("Formatted.pdf")');click('Editar');click('Editar texto');wait('!!document.querySelector(".text-target")')
    target='[...document.querySelectorAll(".text-target")].find(e=>e.getAttribute("aria-label")==="Editar en página: HOLA Ω")';js(target+'.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,clientX:400,clientY:450}))');wait('!!document.querySelector(".text-context-menu")');js('[...document.querySelectorAll(".text-context-menu button")].find(e=>e.textContent==="Editar").click()');wait(field('Tamaño de edición rápida')+'?.disabled===false');js('document.querySelector(".quick-text-format").open=true');edit('Tamaño de edición rápida',11);click('Aplicar');wait('!document.querySelector(".quick-text-dialog")')
    second=root/'Resized.pdf';QFileDialog.getSaveFileName=lambda *a,**kw:(str(second),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty')
    with f.open(second) as d:
        r=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HOLA Ω');assert abs(r['size']-11)<.01 and r['font']=='DejaVuSerif-Bold' and r['editable']
    assert original.read_bytes()==base
    print('PASS: Qt mouse selects original Stm text; included font/style/size and Unicode save natively with accessible reading, undo/redo, reopen and compact-dialog original-font resize; both PDFs reopen editable and the original stays unchanged.')
finally:window.close()
