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
from tests.test_extended_workflows import layered
from tests.test_document_workspaces import pdf
from backend.layer_usage import for_print
from zipfile import ZipFile
import datetime
from tests.test_local_assistant import source as assistant_source
root=Path(tempfile.mkdtemp(prefix='reapdf-ordered-qt-'));original=root/'Table.pdf';original.write_bytes(table_source());colors=root/'Colors.pdf';colors.write_bytes(color_source());portfolio=root/'Portfolio.pdf';portfolio.write_bytes(portfolio_source());output=root/'Scoped.pdf';assistant=root/'Assistant.pdf';assistant.write_bytes(assistant_source())
layer_data,layer_a,layer_b=layered();layer_file=root/'Layers.pdf';layer_file.write_bytes(layer_data);plain=root/'Recipe.pdf';plain.write_bytes(pdf('PLAN-01'));job_output=root/'Job.zip'
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
    click('Convertir y OCR' if label=='Recetas de trabajo' else 'Proteger' if label=='Inspección de impresión' else 'Documentos');wait(field(label)+'?.disabled===false');js('(()=>{const b='+field(label)+';b.closest("details").open=true;b.click();})()')
def select(label,value):
    e=field(label);wait('!!'+e);js('(()=>{const e='+e+';Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,"value").set.call(e,'+json.dumps(value)+');e.dispatchEvent(new Event("change",{bubbles:true}));})()');QTest.qWait(80)
def native_open(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')
def edit(label,value):
    e=field(label);wait(e+'?.disabled===false');js('(()=>{const e='+e+';Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(e,'+json.dumps(str(value))+');e.dispatchEvent(new Event("input",{bubbles:true}));})()');QTest.qWait(80)
def save(path):
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Table.pdf")');tool('Etiquetas y orden de lectura');click('Editar etiquetas');wait('!!'+field('Tabla estructural para reparar'));js(field('Tabla estructural para reparar')+'.closest("details").open=true')
    identity=js(field('Tabla estructural para reparar')+'.options[1].value');select('Tabla estructural para reparar',identity);click('Preparar reparación de tabla');wait('!!'+field('Alcance de celda 1-1'));select('Alcance de celda 1-1','Both');js(field('Revisé estructura de tabla')+'.click()');click('Guardar reparación de tabla');wait('!document.querySelector("dialog[open]")');save(output)
    assert next(r for r in model(output.read_bytes(),[])['nodes'] if r['role']=='TH')['scope']=='Both'
    with f.open(original) as a,f.open(output) as b:assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
    print('STEP: table repair saved',flush=True)
    native_open(layer_file);tool('Capas del PDF');wait('!!'+field('Imprimir capa '+str(layer_a)));js(field('Imprimir capa '+str(layer_a))+'.closest("details").open=true');select('Imprimir capa '+str(layer_a),'OFF');select('Imprimir capa '+str(layer_b),'ON');click('Vista previa de capas');wait('[...document.images].find(i=>i.alt==="Visibilidad de capas")?.complete');click('Guardar visibilidad');wait('!document.querySelector("dialog[open]")');layer_output=root/'LayerRules.pdf';save(layer_output)
    with f.open(stream=for_print(layer_output.read_bytes())) as d:assert 'ONLY A' not in d[0].get_text() and 'ONLY B' in d[0].get_text()
    assert layer_file.read_bytes()==layer_data
    print('STEP: layer print rules saved',flush=True)
    native_open(plain);tool('Recetas de trabajo');select('Plantilla de receta','3');click('2. Pasos');edit('Páginas del paso 1','1');click('3. Documentos');click('Revisar receta y documentos');wait('!!'+field('Aceptar resultados de receta'));js(field('Aceptar resultados de receta')+'.click()');wait('document.body.innerText.includes("páginas 1")')
    js(field('Fecha de receta programada')+'.closest("details").open=true');instant=js('(()=>{const d=new Date();return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);})()');edit('Fecha de receta programada',instant);js(field('Aceptar copias de tarea local')+'.click()');click('Programar receta local');wait('document.body.innerText.includes("Tarea guardada para")')
    for _ in range(20):
        click('Actualizar tareas locales');QTest.qWait(150)
        if js('document.body.innerText.includes("Completada")'):break
    wait('document.body.innerText.includes("Completada")');QFileDialog.getSaveFileName=lambda *a,**kw:(str(job_output),'');click('Descargar resultado de tarea')
    deadline=time.monotonic()+20
    while not job_output.exists() and time.monotonic()<deadline:QTest.qWait(100)
    assert job_output.exists()
    with ZipFile(job_output) as z:
        manifest=json.loads(z.read('manifest.json'));assert 'PLAN-01' in z.read(manifest['documents'][0]['file']).decode();assert manifest['documents'][0]['steps'][0]['details']['selected_pages']==[0]
    click('Eliminar tarea y copias locales');wait('!document.body.innerText.includes("Completada")')
    print('PASS: actual Qt repairs an existing table and saves without pixel changes; edits independent layer print rules and verifies resolved print content; reviews a page-scoped recipe, schedules a persistent local snapshot, executes through the real background queue, downloads its actual ZIP through native dialog and deletes the stored task.')
except Exception:
    print(js('document.body.innerText'));raise
finally:window.allow_close=True;window.close();app.processEvents()
