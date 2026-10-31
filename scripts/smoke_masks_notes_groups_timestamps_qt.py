"""Native Qt Linux smoke: masked text and grouped XFDF native save."""
import hashlib,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_soft_masks_page_notes_groups import masked,page_notes,group_xml,blank
from backend.structure_editing import model,reading_preview
root=Path(tempfile.mkdtemp(prefix='reapdf-mask-qt-'));original=root/'Masked.pdf';original.write_bytes(masked(form=True));empty=root/'Blank.pdf';empty.write_bytes(blank());xml=group_xml().decode();output=root/'MaskedEdited.pdf';grouped=root/'Grouped.pdf';digest=hashlib.sha256(original.read_bytes()).hexdigest()
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
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


def field(label):return 'document.querySelector('+json.dumps('[aria-label="'+label+'"]')+')'


def click(label):
    expr='[...document.querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+json.dumps(label)+')'
    wait('!!'+expr+' && !'+expr+'.disabled');js(expr+'.dispatchEvent(new MouseEvent("click",{bubbles:true}))')


def edit(label,value,select=False):
    expr=field(label);wait(expr+'?.disabled===false');prototype='HTMLSelectElement' if select else 'HTMLTextAreaElement' if js(expr+'.tagName')=='TEXTAREA' else 'HTMLInputElement'
    js('(()=>{const e='+expr+';Object.getOwnPropertyDescriptor('+prototype+'.prototype,"value").set.call(e,'+json.dumps(value)+');e.dispatchEvent(new Event("'+('change' if select else 'input')+'",{bubbles:true}));})()');QTest.qWait(60)


def tool(area,label):
    click(area);wait(field(label)+'?.disabled===false');js('(()=>{const b='+field(label)+';b.closest("details").open=true;b.click();})()')


def native_save(path):
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty');assert path.exists()


def native_open(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')


try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Masked.pdf")');tool('Editar','Editar texto');click('Editar en página: ABC ABC');wait(field('Texto sobre la página')+'?.disabled===false');assert js(field('Fuente de edición directa')+'.disabled');edit('Texto sobre la página','CBA AB');click('Aplicar');wait('!'+field('Texto sobre la página'));native_save(output)
    with f.open(original) as a,f.open(output) as b:assert 'CBA AB' in b[0].get_text() and a[1].get_pixmap().samples==b[1].get_pixmap().samples
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    native_open(empty);tool('Documentos','Intercambiar XFDF')
    # Supply a real browser File to the same input used by the native app.
    js('(()=>{const e='+field('Archivo XFDF')+';const d=new DataTransfer();d.items.add(new File(['+json.dumps(xml)+'],"Groups.xfdf",{type:"application/xml"}));e.files=d.files;e.dispatchEvent(new Event("change",{bubbles:true}));})()');js(field('Confirmar correspondencia del PDF')+'.click()');click('Revisar importación XFDF');click('Aplicar importación XFDF');wait('!document.querySelector("dialog[open]")');native_save(grouped)
    with f.open(grouped) as d:assert sum(d.xref_get_key(a.xref,'RT')==('name','/Group') for p in d for a in p.annots() or [])==2
    print('PASS: own Qt Linux window edited/saved masked original text while preserving other page and source hash; XFDF Group graph reviewed/imported through real controls, atomically saved and reopened with both native Group relationships.')
finally:
    window.close();QTest.qWait(200)
