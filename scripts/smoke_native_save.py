"""Initial-file opening and real frontend save/acknowledgement in Qt."""
import tempfile,time,json
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import Qt,QCoreApplication,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([]);root=Path(tempfile.mkdtemp(prefix='reapdf-save-check-'));source=root/'inicio.pdf';output=root/'guardado.pdf'
with f.open() as d:
    d.new_page().insert_text((45,100),'ORIGINAL LARGO',fontsize=18);d.save(source)
original=source.read_bytes();QMessageBox.question=lambda *args:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(source));window.show()
def js(script):
    values=[];loop=QEventLoop();window.page.runJavaScript(script,lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec();assert values;return values[0]
def wait(script):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        if js(script):return
        QTest.qWait(100)
    raise AssertionError(script)
try:
    wait('document.body.innerText.includes("inicio.pdf") && [...document.images].some(i=>i.alt==="Página 1 del documento"&&i.naturalWidth>0)')
    js('[...document.querySelectorAll("[role=tab]")].find(e=>e.textContent.trim()==="Editar").click()')
    wait('[...document.querySelectorAll("button")].some(e=>e.getAttribute("aria-label")==="Editar texto")')
    js('[...document.querySelectorAll("button")].find(e=>e.getAttribute("aria-label")==="Editar texto").click()')
    wait('[...document.querySelectorAll("[role=button]")].some(e=>e.getAttribute("aria-label")==="Editar en página: ORIGINAL LARGO")')
    js('[...document.querySelectorAll("[role=button]")].find(e=>e.getAttribute("aria-label")==="Editar en página: ORIGINAL LARGO").dispatchEvent(new MouseEvent("click",{bubbles:true}))')
    wait('!!document.querySelector("textarea") && !document.querySelector("textarea").disabled')
    js('(()=>{const input=document.querySelector("textarea");Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,"value").set.call(input,"CORREGIDO");input.dispatchEvent(new Event("input",{bubbles:true}));})()')
    js('[...document.querySelectorAll("button")].find(e=>e.textContent.trim()==="Aplicar").click()')
    wait('document.querySelector(".text-layer")?.textContent.includes("CORREGIDO")')
    wait('!!window.__reapdfCloseState?.dirty')
    QFileDialog.getSaveFileName=lambda *args,**kwargs:('','');window.save_action.trigger()
    wait('document.body.innerText.includes("Guardado cancelado")');assert js('window.__reapdfCloseState.dirty')
    QFileDialog.getSaveFileName=lambda *args,**kwargs:(str(output),'');window.save_action.trigger()
    wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    with f.open(output) as d:assert 'CORREGIDO' in d[0].get_text() and 'ORIGINAL LARGO' not in d[0].get_text()
    assert source.read_bytes()==original
    def unexpected(*args,**kwargs):raise AssertionError('Repeated save unexpectedly requested a path')
    QFileDialog.getSaveFileName=unexpected;window.save_action.trigger();QTest.qWait(500);assert output.exists()
    output.write_bytes(b'EXTERNAL CHANGE');information=[];QMessageBox.information=lambda *args:information.append('conflict')
    QFileDialog.getSaveFileName=lambda *args,**kwargs:('','');window.save_action.trigger()
    deadline=time.monotonic()+5
    while not information and time.monotonic()<deadline:QTest.qWait(100)
    assert information==['conflict'] and output.read_bytes()==b'EXTERNAL CHANGE'
    wait('!!window.__reapdfCloseState?.dirty')
    print('PASS: initial PDF, real edit, cancelled save keeps dirty, atomic save acknowledgement, repeat destination and external-change protection.')
finally:window.allow_close=True;window.close();app.processEvents()
