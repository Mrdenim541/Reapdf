"""Real Qt fills an inherited shared choice from either page, saves and reopens."""
import hashlib,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_shared_choice_sample import create as source
from backend.docx_import import import_docx
import base64

root=Path(tempfile.mkdtemp(prefix='reapdf-shared-choice-qt-'));original=root/'SharedChoice.pdf';output=root/'SharedChoice-filled.pdf';original.write_bytes(source());digest=hashlib.sha256(original.read_bytes()).hexdigest()
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
    wait('document.querySelector(".document-bar")?.textContent.includes("SharedChoice.pdf")');click('Formularios y firmas');tool('Rellenar formulario')
    wait(field('Valor del formulario')+'?.disabled===false');js('(()=>{const e='+field('Valor del formulario')+';e.value="LIM";e.dispatchEvent(new Event("change",{bubbles:true}));})()');click('Aplicar formulario');wait('!document.querySelector(".form-dialog[open]")');click('↶ Deshacer');click('↷ Rehacer')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    from backend.forms import form_model
    with f.open(original) as a,f.open(output) as b:
        rows=form_model(b)['fields'];assert len(rows)==2 and all(r['editable'] and r['value']=='LIM' and r['group_size']==2 for r in rows)
        assert a[2].get_pixmap().samples==b[2].get_pixmap().samples
        for r in rows:assert 'Lima' in b[r['page']].get_text() and b.xref_get_key(r['xref'],'V')[0]=='null' and b.xref_get_key(r['xref'],'I')[0]=='null'
        assert b.xref_get_key(rows[0]['group'],'V')==('string','LIM') and b.xref_get_key(rows[0]['group'],'I')==('array','[1]')
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes("SharedChoice-filled.pdf")');click('Formularios y firmas');tool('Rellenar formulario');wait(field('Valor del formulario')+'?.value==="LIM"')
    js('(()=>{const e='+field('Campo del formulario')+';e.value="1";e.dispatchEvent(new Event("change",{bubbles:true}));})()');wait(field('Valor del formulario')+'?.value==="LIM"');click('Cancelar');assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    print('PASS: real Qt changes a shared inherited choice, synchronizes both page appearances, undo/redo, native save and reopen selecting the second widget; only logical owner stores value/index, unrelated page and original remain unchanged.')
finally:window.allow_close=True;window.close();app.processEvents()
