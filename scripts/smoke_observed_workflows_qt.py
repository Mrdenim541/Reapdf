"""Real Qt workflows for the reported tagged-PDF blocks, naming and OCR safety."""
import json,tempfile,time
from pathlib import Path
from zipfile import ZipFile
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_tagged_working_copy import source
from tests.test_long_advance import source as scan_source
root=Path(tempfile.mkdtemp(prefix='reapdf-observed-qt-'));original=root/'Tagged.pdf';base=source();original.write_bytes(base);scan=root/'Scan.pdf';scan_base=scan_source(scan=True);scan.write_bytes(scan_base)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1650,1100);window.show()
def js(script):
    values=[];loop=QEventLoop();window.page.runJavaScript(script,lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec();return values[0] if values else None
def wait(script):
    end=time.monotonic()+40
    while time.monotonic()<end:
        if js(script):return
        QTest.qWait(100)
    raise AssertionError(script)
def field(label):return 'document.querySelector('+json.dumps('[aria-label="'+label+'"]')+')'
def click(label):
    e='[...document.querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+json.dumps(label)+')';wait('!!'+e+'&&!'+e+'.disabled');js(e+'.dispatchEvent(new MouseEvent("click",{bubbles:true}))')
def edit(label,value,select=False):
    e=field(label);wait(e+'?.disabled===false');proto='HTMLSelectElement' if select else 'HTMLInputElement'
    js('(()=>{const e='+e+';Object.getOwnPropertyDescriptor('+proto+'.prototype,"value").set.call(e,'+json.dumps(str(value))+');e.dispatchEvent(new Event("'+('change' if select else 'input')+'",{bubbles:true}));})()');QTest.qWait(70)
def tool(area,label):
    click(area);wait(field(label)+'?.disabled===false');js('(()=>{const e='+field(label)+';e.closest("details").open=true;e.click();})()')
def open_native(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')
def save(path,force_as=True):
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');(window.save_as_action if force_as else window.save_action).trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty');assert path.exists()
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Tagged.pdf")')
    tool('Editar','Buscar y reemplazar');edit('Texto a buscar','CODIGO GENERAL');edit('Reemplazar por','CODIGO NUEVO');edit('Ámbito de búsqueda','document',True);click('Buscar coincidencias')
    wait('document.querySelector("dialog").innerText.includes("0 compatibles")');window.resize(1280,760);QTest.qWait(200)
    assert js('(()=>{const b=document.querySelector("dialog[open]").getBoundingClientRect();const f=document.querySelector(".organizer-footer").getBoundingClientRect();return b.top>=0&&b.bottom<=innerHeight+1&&f.bottom<=innerHeight+1;})()'),'Search dialog/footer must stay inside the smaller window'
    assert js('[...document.querySelectorAll(".find-replace-match input")].every(e=>e.disabled)')
    click('Crear copia sin etiquetas para editar');wait('document.querySelector("dialog")?.innerText.includes("3 compatibles")')
    window.resize(1650,1100);QTest.qWait(150)
    assert js(field('Texto a buscar')+'.value')=='CODIGO GENERAL';assert js(field('Reemplazar por')+'.value')=='CODIGO NUEVO'
    click('Seleccionar todas compatibles');click('Preparar vista previa');wait('document.querySelectorAll(".find-replace-preview img").length===3');click('Aplicar reemplazos');wait('!document.querySelector("dialog[open]")');edited=root/'Replaced.pdf';save(edited,False)
    with f.open(edited) as d:assert all('CODIGO NUEVO' in p.get_text() for p in d)
    print('STEP: incompatible search results identified before selection; explicit copy kept search fields and reran search; actual batch preview/replacement/native save passed.',flush=True)
    open_native(original);tool('Editar','Editar imágenes del PDF');wait('document.querySelector(".tagged-copy-choice button")?.disabled===false');click('Crear copia sin etiquetas para editar');wait(field('Acción de imagen existente')+'?.disabled===false')
    edit('X de imagen existente',110);edit('Y de imagen existente',180);edit('Ancho de imagen existente',100);edit('Alto de imagen existente',50);click('Vista previa de imagen editada');wait('[...document.querySelectorAll("button")].find(e=>e.textContent==="Aplicar imagen editada")?.disabled===false');click('Aplicar imagen editada');wait('!document.querySelector("dialog[open]")');image_out=root/'Image.pdf';save(image_out,False)
    with f.open(image_out) as a,f.open(stream=base) as b:
        assert list(a[0].get_image_info()[0]['bbox'])==[110,180,210,230];assert a[0].get_text()==b[0].get_text();assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
    print('STEP: tagged image unblocked via explicit native copy; image moved/resized, previewed, applied and saved with other page/text unchanged.',flush=True)
    open_native(original);tool('Organizar páginas','Dividir PDF');edit('Prefijo de nombres de partes','1.46 PINTURA');assert js(field('Nombre de parte 3')+'.value')=='1.46 PINTURA 003.pdf'
    edit('Nombre de parte 1','bad/name');assert js(field('Nombre de parte 1')+'.value')=='bad/name';assert js('[...document.querySelectorAll("button")].find(e=>e.textContent==="Descargar partes ZIP").disabled');click('Generar nombres numerados')
    wait('document.querySelector("dialog").innerText.includes("estructura etiquetada")');js(field('Conservar etiquetas al dividir')+'.click()');js(field('Incluir relación de archivos de división')+'.click()')
    archive=root/'Parts.zip';QFileDialog.getSaveFileName=lambda *a,**kw:(str(archive),'');click('Descargar partes ZIP');end=time.monotonic()+25
    while not archive.exists() and time.monotonic()<end:QTest.qWait(100)
    assert archive.exists()
    with ZipFile(archive) as z,f.open(stream=base) as original_doc:
        names=[f'1.46 PINTURA {n:03d}.pdf' for n in range(1,4)];assert z.namelist()==names+['reapdf-division.json'];assert json.loads(z.read('reapdf-division.json'))['accessibility_tags_retained'] is False
        for i,name in enumerate(names):
            with f.open(stream=z.read(name)) as d:assert d[0].get_pixmap().samples==original_doc[i].get_pixmap().samples;assert 'CODIGO GENERAL' in d[0].get_text()
    click('Cerrar');assert original.read_bytes()==base
    print('STEP: custom spaced names update immediately; invalid manual name stays editable; unsupported tagged split fails safely, explicit tag-free parts save natively with exact appearance and selectable text.',flush=True)
    open_native(scan);tool('Convertir y OCR','Reconocer texto (OCR)');edit('Idioma OCR','eng',True);edit('Resolución OCR','150',True);click('Reconocer páginas');wait('!document.querySelector("dialog[open]")&&document.body.innerText.includes("aspecto visual comprobado a 150 ppp")');ocr_out=root/'OCR.pdf';save(ocr_out)
    with f.open(ocr_out) as a,f.open(stream=scan_base) as b:assert '12345' in a[0].get_text();assert a[0].get_pixmap(matrix=f.Matrix(2,2)).samples==b[0].get_pixmap(matrix=f.Matrix(2,2)).samples
    assert scan.read_bytes()==scan_base
    print('PASS: real Qt completes native search/replace and image edits after an explicit tag-free working copy, retains dialog input, generates requested numbered independent PDFs without rasterization, preserves originals, and applies genuine OCR with verified unchanged visible appearance and native save/reopen.')
except Exception:
    print(js('[...document.querySelectorAll("[role=alert]")].map(e=>e.textContent)'));raise
finally:window.allow_close=True;window.close();app.processEvents()
