"""Real Qt window plus a separate IPC client, including draft decisions."""
import subprocess,sys,tempfile,time,uuid
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from portable.single_instance import SingleInstance
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([]);root=Path(tempfile.mkdtemp(prefix='reapdf-single-check-'));first=root/'primero.pdf';second=root/'segundo con espacios.pdf'
for file,text in [(first,'PRIMER PDF'),(second,'SEGUNDO PDF')]:
    with f.open() as d:d.new_page().insert_text((40,80),text,fontsize=18);d.save(file)
namespace=uuid.uuid4().hex;instance=SingleInstance(namespace=namespace);assert instance.owner
QMessageBox.question=lambda *args:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(first));instance.set_handler(window.enqueue_file);window.show()
def js(script):
    values=[];loop=QEventLoop();window.page.runJavaScript(script,lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec();assert values;return values[0]
def wait(script):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        if js(script):return
        QTest.qWait(100)
    raise AssertionError(script)
def send():
    code='from PySide6.QtCore import QCoreApplication;from portable.single_instance import SingleInstance;import sys;app=QCoreApplication([]);s=SingleInstance(sys.argv[2],namespace=sys.argv[1]);assert not s.owner'
    process=subprocess.Popen([sys.executable,'-c',code,namespace,str(second)])
    deadline=time.monotonic()+15
    while process.poll() is None and time.monotonic()<deadline:QTest.qWait(100)
    if process.poll() is None:process.kill();process.wait();raise AssertionError('Handoff timed out')
    assert process.returncode==0
try:
    wait('document.querySelector(".text-layer")?.textContent.includes("PRIMER PDF")')
    js('[...document.querySelectorAll("[role=tab]")].find(e=>e.textContent.trim()==="Editar").click()')
    wait('[...document.querySelectorAll("button")].some(e=>e.getAttribute("aria-label")==="Editar texto")')
    js('[...document.querySelectorAll("button")].find(e=>e.getAttribute("aria-label")==="Editar texto").click()')
    wait('[...document.querySelectorAll("[role=button]")].some(e=>e.getAttribute("aria-label")==="Editar en página: PRIMER PDF")')
    js('[...document.querySelectorAll("[role=button]")].find(e=>e.getAttribute("aria-label")==="Editar en página: PRIMER PDF").dispatchEvent(new MouseEvent("click",{bubbles:true}))')
    wait('!!document.querySelector("textarea") && !document.querySelector("textarea").disabled')
    js('(()=>{const e=document.querySelector("textarea");Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,"value").set.call(e,"BORRADOR");e.dispatchEvent(new Event("input",{bubbles:true}));})()')
    wait('!!window.__reapdfCloseState?.dirty')
    questions=[];QMessageBox.question=lambda *args:(questions.append('no') or QMessageBox.StandardButton.No)
    send()
    deadline=time.monotonic()+10
    while not questions and time.monotonic()<deadline:QTest.qWait(100)
    assert questions and js('document.querySelector("textarea")?.value')=='BORRADOR'
    assert js('document.body.innerText.includes("primero.pdf")')
    QMessageBox.question=lambda *args:QMessageBox.StandardButton.Yes
    send();wait('document.querySelector(".text-layer")?.textContent.includes("SEGUNDO PDF")')
    assert window.isVisible() and instance.owner
    print('PASS: separate process hands off PDF, refusal preserves draft, confirmation opens in the same Qt window.')
finally:window.allow_close=True;window.close();instance.close();app.processEvents()
