"""Native Qt schema designer acceptance with atomic save and attachment checks."""
import json,tempfile,time,hashlib
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_portfolio_metadata import sample
from backend.portfolio_metadata import model
root=Path(tempfile.mkdtemp(prefix='reapdf-schema-qt-'));original=root/'Portfolio.pdf';original.write_bytes(sample())
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1600,1150);window.show()
def js(script):
    values=[];loop=QEventLoop();window.page.runJavaScript('(()=>{try{return eval('+json.dumps(script)+');}catch(e){return {__error:String(e)};}})()',lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec()
    if not values:raise AssertionError('Qt did not respond')
    if isinstance(values[0],dict) and '__error' in values[0]:raise AssertionError(values[0]['__error'])
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
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');window.save_as_action.trigger()
    deadline=time.monotonic()+35
    while not path.exists():
        if time.monotonic()>deadline:raise AssertionError('Native Save As did not create the expected file')
        QTest.qWait(100)
    wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')


def native_open(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')


def portfolio(design=False):
    tool('Documentos','Portfolio PDF');wait('!!document.querySelector("dialog[open]")');js('[...document.querySelectorAll("summary")].find(e=>e.textContent==="Columnas del portfolio existente").click()')
    if design:
        wait('[...document.querySelectorAll("summary")].some(e=>e.textContent==="Diseñar columnas")');js('[...document.querySelectorAll("summary")].find(e=>e.textContent==="Diseñar columnas").click()')


try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Portfolio.pdf")');click('Guía y atajos');click('Consultar manual por función');edit('Buscar en el manual','Editar texto');wait('document.body.innerText.includes("pulsa el texto directamente")');assert js('document.querySelector(".workspace-help table").textContent.includes("Guardar PDF como")');click('Entendido');portfolio(True);edit('Nombre de columna 1','Identificador');click('Añadir columna');edit('Nombre de columna 5','Revisión');edit('Tipo de columna 5','number',True);click('Subir columna 5');js(field('Revisé el diseño de columnas')+'.click()');click('Guardar diseño de columnas');wait('!document.querySelector("dialog[open]")');native_save(root/'Designed.pdf')
    portfolio();edit('Columna Revisión del archivo 1','7');click('Guardar valores de columnas');wait('!document.querySelector("dialog[open]")');native_save(root/'Filled.pdf')
    portfolio(True);click('Retirar columna 2');assert not js(field('Revisé el diseño de columnas')+'.checked');js(field('Revisé el diseño de columnas')+'.click()');click('Guardar diseño de columnas');wait('!document.querySelector("dialog[open]")');native_save(root/'Removed.pdf')
    info=model((root/'Removed.pdf').read_bytes());assert [c['label'] for c in info['columns']]==['Identificador','Date','Revisión','Locked'];key=next(c['id'] for c in info['columns'] if c['label']=='Revisión');assert info['files'][0]['values'][key]==7
    with f.open(original) as a,f.open(root/'Removed.pdf') as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
        assert {n:hashlib.sha256(a.embfile_get(n)).digest() for n in a.embfile_names()}=={n:hashlib.sha256(b.embfile_get(n)).digest() for n in b.embfile_names()}
    print('PASS: own Qt window searchable per-function manual/native save shortcuts and portfolio schema create/rename/reorder/typed fill/reviewed remove, atomic save/reopen and attachment bytes/cover preservation. Windows depends on the host of this execution.')
finally:
    window.allow_close=True;window.close();QTest.qWait(200)
