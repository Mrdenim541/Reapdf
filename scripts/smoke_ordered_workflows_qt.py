"""Actual Qt table-header repair, nested color diagnostics and derived portfolio data."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_structure_scope import source as table_source
from tests.test_preflight_color_forms import sample as color_source
from tests.test_portfolio_derived_columns import source as portfolio_source
from backend.structure_editing import model
from tests.test_local_assistant import source as assistant_source
root=Path(tempfile.mkdtemp(prefix='reapdf-ordered-qt-'));original=root/'Table.pdf';original.write_bytes(table_source());colors=root/'Colors.pdf';colors.write_bytes(color_source());portfolio=root/'Portfolio.pdf';portfolio.write_bytes(portfolio_source());output=root/'Scoped.pdf';assistant=root/'Assistant.pdf';assistant.write_bytes(assistant_source())
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1700,1150);window.show()
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
def tool(label):
    click('Proteger' if label=='Inspección de impresión' else 'Documentos');wait(field(label)+'?.disabled===false');js('(()=>{const b='+field(label)+';b.closest("details").open=true;b.click();})()')
def select(label,value):
    e=field(label);wait('!!'+e);js('(()=>{const e='+e+';Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,"value").set.call(e,'+json.dumps(value)+');e.dispatchEvent(new Event("change",{bubbles:true}));})()');QTest.qWait(80)
def native_open(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Table.pdf")');tool('Etiquetas y orden de lectura');click('Editar etiquetas');wait('!!'+field('Etiqueta de estructura'))
    identity=js('[...'+field('Etiqueta de estructura')+'.options].find(o=>/\\bTH\\b/.test(o.textContent)).value');select('Etiqueta de estructura',identity);wait('!!'+field('Alcance de cabecera de tabla'));js(field('Alcance de cabecera de tabla')+'.closest("details").open=true');select('Alcance de cabecera de tabla','Both');click('Guardar alcance de cabecera');wait('!document.querySelector("dialog[open]")')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    heads=[r for r in model(output.read_bytes(),[])['nodes'] if r['role']=='TH'];assert heads[0]['scope']=='Both' and heads[1]['scope']=='Column'
    with f.open(original) as a,f.open(output) as b:assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
    native_open(colors);tool('Inspección de impresión');click('Inspeccionar PDF');wait('document.body.innerText.includes("BrandRed") && document.body.innerText.includes("Hay estados aplicados")');click('Cerrar')
    native_open(portfolio);tool('Portfolio PDF');wait('!!document.querySelector(".portfolio-columns")');js('document.querySelector(".portfolio-columns").open=true');wait(field('Columna File del archivo 1')+'?.value==="original.txt"');assert js(field('Columna File del archivo 1')+'.disabled') and js(field('Columna Bytes del archivo 1')+'.value')==str(len(b'ATTACHMENT BYTES'))
    with f.open(portfolio) as d:assert d.embfile_get('entry')==b'ATTACHMENT BYTES'
    js('document.querySelector("dialog[open]").dispatchEvent(new Event("cancel",{cancelable:true}))');wait('!document.querySelector("dialog[open]")');native_open(assistant);tool('Consultar documento');select('Modo de consulta local','query');e=field('Pregunta de consulta local');wait('!!'+e);js('(()=>{const e='+e+';Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(e,"temperatura");e.dispatchEvent(new Event("input",{bubbles:true}));})()');click('Buscar pasajes locales');wait('document.body.innerText.includes("25 grados")');click('Ver página 2');wait('!document.querySelector("dialog[open]") && document.querySelector(".text-layer")?.textContent.includes("TERM-02")')
    print('PASS: Qt local extractive query retrieves a cited passage and navigates to its source page; repairs selected TH scope and saves natively with identical pixels/unselected header; diagnoses nested spot color and overprint; displays derived portfolio filename/declared size read-only with embedded bytes intact.')
finally:window.allow_close=True;window.close();app.processEvents()
