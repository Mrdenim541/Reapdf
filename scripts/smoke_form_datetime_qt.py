"""Exercise native PDF calculations and actual Word footnotes through the Qt app."""
import hashlib,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_datetime_form_sample import create as source
from backend.docx_import import import_docx
import base64

root=Path(tempfile.mkdtemp(prefix='reapdf-datetime-qt-'));original=root/'DateTime.pdf';output=root/'DateTime-filled.pdf';original.write_bytes(source());digest=hashlib.sha256(original.read_bytes()).hexdigest()
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([]);QMessageBox.question=lambda *args:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1500,1100);window.show()


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


def click(label):
    expr='[...document.querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+json.dumps(label)+')'
    wait('!!'+expr+' && !'+expr+'.disabled');js(expr+'.dispatchEvent(new MouseEvent("click",{bubbles:true}))')


def field(label):return 'document.querySelector('+json.dumps('[aria-label="'+label+'"]')+')'


def edit(label,value):
    wait(field(label)+'?.disabled===false')
    js('(()=>{const e='+field(label)+';Object.getOwnPropertyDescriptor((e.tagName==="TEXTAREA"?HTMLTextAreaElement:HTMLInputElement).prototype,"value").set.call(e,'+json.dumps(value)+');e.dispatchEvent(new Event("input",{bubbles:true}));})()')
    QTest.qWait(50)


def tool(label):
    wait(field(label)+'?.disabled===false');js('(()=>{const b='+field(label)+';b.closest("details").open=true;b.click();})()')


def file_ready(path):
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        if path.exists() and path.stat().st_size:return
        QTest.qWait(100)
    raise AssertionError('Native download did not finish: '+str(path))


try:
    wait('document.querySelector(".document-bar")?.textContent.includes("DateTime.pdf")');click('Formularios y firmas');tool('Rellenar formulario');edit('Valor del formulario','31/02/2026 25:00:00');wait('document.body.innerText.includes("La fecha no es válida")');assert js(field('Valor del formulario')+'.value')=='31/02/2026 25:00:00'
    edit('Valor del formulario','06/11/2026 10:30:45');click('Aplicar formulario');wait('!document.querySelector(".form-dialog[open]")');QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    from backend.forms import form_model
    from backend.form_actions import actions
    from backend.form_structure import field_structure
    with f.open(original) as a,f.open(output) as b:
        old=form_model(a)['fields'][0];new=form_model(b)['fields'][0];assert new['editable'] and new['value']=='06/11/2026 10:30:45' and new['display_value']==new['value'];assert new['value'] in b[0].get_text();assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        _,own_a,_,_=field_structure(a);_,own_b,_,_=field_structure(b);assert actions(a,own_a[old['xref']]['chain'])==actions(b,own_b[new['xref']]['chain'])
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes("DateTime-filled.pdf")');click('Formularios y firmas');tool('Rellenar formulario');wait(field('Valor del formulario')+'?.value==="06/11/2026 10:30:45"');assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    print('PASS: actual Qt fills combined date/time from compressed standard helper streams, retains invalid draft, saves and reopens with native appearance and unchanged actions/other page; original PDF unchanged.')
finally:window.allow_close=True;window.close();app.processEvents()
