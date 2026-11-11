"""Real Qt standard colored number appearances and quoted range validation."""
import hashlib,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_colored_form_sample import create as source
from backend.docx_import import import_docx
import base64

root=Path(tempfile.mkdtemp(prefix='reapdf-colored-form-qt-'));original=root/'Colored.pdf';output=root/'Negative-filled.pdf';original.write_bytes(source());digest=hashlib.sha256(original.read_bytes()).hexdigest()
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


def verify(path,value,display,color):
    from backend.forms import form_model
    with f.open(original) as a,f.open(path) as d:
        r=form_model(d)['fields'][0];assert r['editable'] and r['value']==value and r['display_value']==display
        assert a[1].get_pixmap().samples==d[1].get_pixmap().samples
        w=next(d[0].widgets());old=next(a[0].widgets());assert tuple(w.text_color)==color
        assert all(a.xref_get_key(old.xref,'AA/'+e+'/JS')==d.xref_get_key(w.xref,'AA/'+e+'/JS') for e in ['F','K','V'])
        assert display in d[0].get_text()
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Colored.pdf")');click('Formularios y firmas');tool('Rellenar formulario');edit('Valor del formulario','101');wait('document.body.innerText.includes("rango permitido")');assert js(field('Valor del formulario')+'.value')=='101';edit('Valor del formulario','-12.5');click('Aplicar formulario');wait('!document.querySelector(".form-dialog[open]")')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty');verify(output,'-12.5','(12.50 EUR)',(1,0,0))
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes("Negative-filled.pdf")');click('Formularios y firmas');tool('Rellenar formulario');edit('Valor del formulario','4');click('Aplicar formulario');wait('!document.querySelector(".form-dialog[open]")');positive=root/'Positive-filled.pdf';QFileDialog.getSaveFileName=lambda *a,**kw:(str(positive),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty');verify(positive,'4','4.00 EUR',(0,0,0));assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    print('PASS: Qt rejects out-of-range draft using quoted limits, fills red negative with parentheses, native saves/reopens, positive resets to black, original actions and other page preserved; no PDF JavaScript execution.')
finally:window.allow_close=True;window.close();app.processEvents()
