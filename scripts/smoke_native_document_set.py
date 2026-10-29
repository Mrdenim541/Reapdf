"""Qt document-set save acknowledgement, cancellation and close protection."""
import tempfile,time,json
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import Qt,QCoreApplication,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from backend.document_sets import read
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([]);root=Path(tempfile.mkdtemp(prefix='reapdf-set-qt-'));source=root/'inicio.pdf';output=root/'guardado.reapdfset'
with f.open() as d:
    d.new_page().insert_text((45,100),'PLAN-01');d.save(source)
QMessageBox.question=lambda *args:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(source));window.show()
def js(script):
    values=[];loop=QEventLoop();window.page.runJavaScript(script,lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec();assert values;return values[0]
def wait(script):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        if js(script):return
        QTest.qWait(100)
    raise AssertionError(script)
def button(name):
    print("CLICK:",name,flush=True);js(f'[...document.querySelectorAll("button")].find(e=>e.textContent.trim()==={json.dumps(name)}).click()')
try:
    wait('document.body.innerText.includes("inicio.pdf") && [...document.images].some(i=>i.alt==="Página 1 del documento"&&i.naturalWidth>0)')
    js('[...document.querySelectorAll("[role=tab]")].find(e=>e.textContent.trim()==="Documentos").click()')
    wait('!![...document.querySelectorAll("button")].find(e=>e.getAttribute("aria-label")==="Vincular documentos")')
    js('[...document.querySelectorAll("button")].find(e=>e.getAttribute("aria-label")==="Vincular documentos").click()')
    wait('[...document.querySelectorAll("button")].some(e=>e.textContent.trim()==="Guardar conjunto"&&!e.disabled)')
    wait('!!window.__reapdfCloseState?.dirty')
    QFileDialog.getSaveFileName=lambda *args,**kwargs:('','');button('Guardar conjunto')
    wait('document.body.innerText.includes("Guardado cancelado; el conjunto")');assert js('window.__reapdfCloseState.dirty')
    print("STAGE: cancel acknowledged",flush=True)
    QFileDialog.getSaveFileName=lambda *args,**kwargs:(str(output),'');button('Guardar conjunto')
    wait('!window.__reapdfCloseState.dirty')
    print('STAGE: save acknowledged',flush=True)
    items,relations,name=read(output.read_bytes());assert len(items)==1 and not relations
    def unexpected(*args,**kwargs):raise AssertionError('Repeated save requested a new path')
    QFileDialog.getSaveFileName=unexpected;button('Guardar conjunto');QTest.qWait(500)
    js('(()=>{const input=[...document.querySelectorAll("input")].find(e=>e.getAttribute("aria-label")==="Nombre del conjunto");Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(input,"Conjunto revisado");input.dispatchEvent(new Event("input",{bubbles:true}));})()')
    wait('!!window.__reapdfCloseState.dirty');button('Cerrar');wait('document.querySelectorAll("dialog[open]").length===0');assert js('window.__reapdfCloseState.dirty')
    print('PASS: Qt .reapdfset atomic save, cancellation retains dirty, acknowledged save clears dirty, repeat destination, closed panel retains workspace changes.')
finally:window.allow_close=True;window.close();app.processEvents()
