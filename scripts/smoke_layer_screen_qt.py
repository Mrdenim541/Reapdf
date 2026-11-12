"""Actual Qt screen conditions, temporary simulation, native save and reopen."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_layer_screen_sample import create
from backend.layers import model
root=Path(tempfile.mkdtemp(prefix='reapdf-layer-screen-qt-'));original=root/'Layers.pdf';original.write_bytes(create());before=original.read_bytes();output=root/'LayerPreferences.pdf'
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1500,1100);window.show()
def js(script):
    result=[];loop=QEventLoop();window.page.runJavaScript('(()=>{try{return eval('+json.dumps(script)+');}catch(e){return {error:String(e)};}})()',lambda value:(result.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec()
    assert result,'Qt did not respond'
    if isinstance(result[0],dict) and 'error' in result[0]:raise AssertionError(result[0])
    return result[0]
def wait(script):
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        if js(script):return
        QTest.qWait(100)
    raise AssertionError(script)
def field(label):return 'document.querySelector('+json.dumps('[aria-label="'+label+'"]')+')'
def click(label):
    expr='[...document.querySelectorAll("button")].find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+json.dumps(label)+')';wait('!!'+expr+' && !'+expr+'.disabled');js(expr+'.click()')
def edit(label,value,select=False):
    expr=field(label);wait(expr+'?.disabled===false');kind='HTMLSelectElement' if select else 'HTMLInputElement'
    js('(()=>{const e='+expr+';Object.getOwnPropertyDescriptor('+kind+'.prototype,"value").set.call(e,'+json.dumps(value)+');e.dispatchEvent(new Event("'+('change' if select else 'input')+'",{bubbles:true}));})()');QTest.qWait(60)
def image():
    wait('document.querySelector(\'img[alt="Visibilidad de capas"]\')?.complete');return js('document.querySelector(\'img[alt="Visibilidad de capas"]\').src')
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Layers.pdf")');click('Documentos');wait(field('Capas del PDF')+'?.disabled===false');js(field('Capas del PDF')+'.closest("details").open=true');js(field('Capas del PDF')+'.click()');wait('!!'+field('Configuración de capas'));edit('Configuración de capas','0',True)
    js('[...document.querySelectorAll("summary")].find(e=>e.textContent==="Pantalla, zoom e idioma").click()')
    edit('Pantalla capa 6','ON',True);js(field('Condición de zoom capa 6')+'.click()');edit('Hasta, sin incluir (%) capa 6','200');js(field('Condición de idioma capa 6')+'.click()');edit('Idioma capa 6','es-MX')
    js(field('Simular condiciones de pantalla')+'.click()');edit('Idioma de simulación','es-MX');edit('Zoom de simulación','150');click('Vista previa de capas');first=image();wait('[...document.querySelectorAll("button")].find(e=>e.textContent==="Guardar visibilidad")?.disabled===false')
    edit('Zoom de simulación','200');assert js('!document.querySelector(\'img[alt="Visibilidad de capas"]\')');assert js('[...document.querySelectorAll("button")].find(e=>e.textContent==="Guardar visibilidad").disabled');click('Vista previa de capas');assert image()!=first
    click('Guardar visibilidad');wait('!document.querySelector("dialog[open]")');QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty');assert output.exists()
    info=model(output.read_bytes(),[]);row=next(r for r in info['screen']['layers'] if r['id']==6);assert row['view']=='ON' and row['zoom']=={'min':1.0,'max':2.0} and row['language']=={'lang':'es-MX','preferred':False}
    with f.open(stream=before) as a,f.open(output) as b:assert a[0].read_contents()==b[0].read_contents() and 'ONLY B' in b[0].get_text()
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes("LayerPreferences.pdf")');assert original.read_bytes()==before
    print('PASS: actual Qt configures native View/Zoom/Language, invalidates simulation after context edits, saves/reopens preferences using native route with test file selector, preserves initial state/content and original. No automatic main-view zoom switching claimed.')
finally:window.allow_close=True;window.close();QTest.qWait(200)
