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
from backend.layer_usage import for_print
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
    wait('document.querySelector(\'img[alt="Visibilidad de capas"]\')?.naturalWidth>0');return js('document.querySelector(\'img[alt="Visibilidad de capas"]\').src')
def ink():
    return js("(()=>{const img=document.querySelector('img[alt=\"Visibilidad de capas\"]');const c=document.createElement('canvas');c.width=img.naturalWidth;c.height=img.naturalHeight;const ctx=c.getContext('2d');ctx.drawImage(img,0,0);return ctx.getImageData(0,0,c.width,c.height).data.some((v,i)=>i%4!==3&&v<245);})()")
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Layers.pdf")');click('Documentos');wait(field('Capas del PDF')+'?.disabled===false');js(field('Capas del PDF')+'.closest("details").open=true');js(field('Capas del PDF')+'.click()');wait('!!'+field('Configuración de capas'));edit('Configuración de capas','0',True)
    js('[...document.querySelectorAll("summary")].find(e=>e.textContent==="Pantalla, zoom e idioma").click()')
    edit('Pantalla capa 6','ON',True);js(field('Condición de zoom capa 6')+'.click()');edit('Hasta, sin incluir (%) capa 6','200');js(field('Condición de idioma capa 6')+'.click()');edit('Idioma capa 6','es-MX')
    js(field('Simular condiciones de pantalla')+'.click()');edit('Idioma de simulación','es-MX');edit('Zoom de simulación','150');click('Vista previa de capas');first=image();assert ink();wait('[...document.querySelectorAll("button")].find(e=>e.textContent==="Guardar visibilidad")?.disabled===false')
    edit('Zoom de simulación','200');assert js('!document.querySelector(\'img[alt="Visibilidad de capas"]\')');assert js('[...document.querySelectorAll("button")].find(e=>e.textContent==="Guardar visibilidad").disabled');click('Vista previa de capas');assert image()!=first;assert not ink()
    click('Guardar visibilidad');wait('!document.querySelector("dialog[open]")');QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty');assert output.exists()
    info=model(output.read_bytes(),[]);row=next(r for r in info['screen']['layers'] if r['id']==6);assert row['view']=='ON' and row['zoom']=={'min':1.0,'max':2.0} and row['language']=={'lang':'es-MX','preferred':False}
    with f.open(stream=before) as a,f.open(output) as b:assert a[0].read_contents()==b[0].read_contents() and 'ONLY B' in b[0].get_text()
    assert original.read_bytes()==before
    preferences=output.read_bytes();click('Documentos');wait(field('Capas del PDF')+'?.disabled===false');js(field('Capas del PDF')+'.closest("details").open=true');js(field('Capas del PDF')+'.click()');wait('!!'+field('Simular condiciones de pantalla'));js(field('Simular condiciones de pantalla')+'.click()');edit('Idioma de simulación','es-MX');edit('Zoom de simulación','150');click('Vista previa de capas');image();assert ink();click('Abrir copia contextual');wait('!document.querySelector("dialog[open]")&&window.__reapdfCloseState.dirty')
    frozen=root/'ContextCopy.pdf';QFileDialog.getSaveFileName=lambda *a,**kw:(str(frozen),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty');assert frozen.exists()
    copy_info=model(frozen.read_bytes(),[]);assert all(r['view'] is None and r['zoom'] is None and r['language'] is None for r in copy_info['screen']['layers']);assert copy_info['usage']==model(before,[])['usage']
    with f.open(stream=before) as a,f.open(frozen) as b:assert a[0].read_contents()==b[0].read_contents() and 'ONLY B' in b[0].get_text() and 'ONLY A' not in b[0].get_text()
    with f.open(stream=for_print(frozen.read_bytes())) as printed:assert 'ONLY A' in printed[0].get_text() and 'ONLY B' not in printed[0].get_text()
    assert output.read_bytes()==preferences and original.read_bytes()==before
    for reopen in [output,frozen]:
        QFileDialog.getOpenFileName=lambda *a,**kw:(str(reopen),'');window.open_action.trigger();wait('document.querySelector(\".document-bar\")?.textContent.includes('+json.dumps(reopen.name)+')')
    print('PASS: actual Qt configures native View/Zoom/Language, invalidates simulation after context edits, saves/reopens preferences using native route with test file selector, uses normal Save with a new copy identity, reopens both files and preserves print/export, initial state/content and originals. No automatic main-view zoom switching claimed.')
finally:window.allow_close=True;window.close();QTest.qWait(200)
