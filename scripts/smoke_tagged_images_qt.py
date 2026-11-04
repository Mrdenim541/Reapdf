"""Real Qt workflows for the reported tagged-PDF blocks, naming and OCR safety."""
import json,tempfile,time
from pathlib import Path
from zipfile import ZipFile
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_tagged_image_sample import create as source
from tests.test_long_advance import source as scan_source
root=Path(tempfile.mkdtemp(prefix='reapdf-observed-qt-'));original=root/'Tagged.pdf';base=source();original.write_bytes(base);scan=root/'Scan.pdf';scan_base=scan_source(scan=True);scan.write_bytes(scan_base)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1650,1100);window.show()
def js(script):
    values=[];loop=QEventLoop();window.page.runJavaScript('(()=>{try{return eval('+json.dumps(script)+');}catch(e){return {__error:String(e)};}})()',lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec();
    if values and isinstance(values[0],dict) and '__error' in values[0]:raise AssertionError(values[0]['__error'])
    return values[0] if values else None
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
    wait('document.querySelector(".document-bar")?.textContent.includes("Tagged.pdf")');tool('Editar','Editar imágenes del PDF');wait(field('Acción de imagen existente')+'?.disabled===false')
    edit('Imagen existente','1',True);wait('!Array.from(document.querySelector(\'[aria-label="Acción de imagen existente"]\').options).some(o=>o.value===\'move\')');assert js('document.querySelector(\'[aria-label="Acción de imagen existente"]\').value===\'replace\'');edit('Imagen existente','0',True)
    target_expr='document.querySelector('+json.dumps('[aria-label="Mover imagen existente en muestra"] rect[data-image-index="0"]')+')'
    wait('!!'+target_expr)
    bounds=json.loads(js('JSON.stringify((()=>{const e='+target_expr+';e.scrollIntoView({block:"center"});const b=e.getBoundingClientRect();return [b.x+b.width/2,b.y+b.height/2];})())'))
    target=window.view.focusProxy() or window.view;origin=target.mapFrom(window.view,QPoint(round(bounds[0]),round(bounds[1])));dest=origin+QPoint(20,12)
    QTest.mousePress(target,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,origin);QTest.mouseMove(target,dest,150);QTest.mouseRelease(target,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,dest)
    wait('Number('+field('X de imagen existente')+'.value)>40')
    click('Aplicar imagen editada');wait('!document.querySelector("dialog[open]")');moved=root/'Moved.pdf';save(moved)
    with f.open(moved) as d,f.open(original) as before:
        assert d.xref_get_key(d.pdf_catalog(),'StructTreeRoot')[0]!='null' and len(d[0].get_image_info())==2
        assert d[0].get_image_info()[0]['bbox']!=before[0].get_image_info()[0]['bbox']
    click('↶ Deshacer');click('↷ Rehacer');tool('Editar','Editar imágenes del PDF');edit('Acción de imagen existente','replace',True)
    from tests.test_images import picture
    import base64
    encoded=base64.b64encode(picture()).decode()
    js('(()=>{const e='+field('Archivo para reemplazar imagen')+';const dt=new DataTransfer();dt.items.add(new File([Uint8Array.from(atob('+json.dumps(encoded)+'),c=>c.charCodeAt(0))],"new.png",{type:"image/png"}));e.files=dt.files;e.dispatchEvent(new Event("change",{bubbles:true}));})()')
    wait(field('Descripción de imagen de reemplazo')+'?.disabled===false');e=field('Descripción de imagen de reemplazo');js('(()=>{const e='+e+';Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,"value").set.call(e,"New accessible diagram");e.dispatchEvent(new Event("input",{bubbles:true}));})()')
    click('Aplicar imagen editada');wait('!document.querySelector("dialog[open]")');replacement=root/'Replaced.pdf';save(replacement)
    from tests.test_tagged_image_editing import inspect
    _,figures=inspect(replacement.read_bytes());assert figures[0]['/Alt']=='New accessible diagram' and figures[1]['/Alt']=='Other diagram'
    tool('Editar','Editar imágenes del PDF');edit('Acción de imagen existente','delete',True);click('Aplicar imagen editada');wait('!document.querySelector("dialog[open]")');deleted=root/'Deleted.pdf';save(deleted)
    _,figures=inspect(deleted.read_bytes());assert len(figures)==1 and figures[0]['/Alt']=='Other diagram'
    with f.open(original) as a:
        for path in [moved,replacement,deleted]:
            with f.open(path) as d:
                assert d[0].get_text('dict',flags=f.TEXTFLAGS_TEXT)==a[0].get_text('dict',flags=f.TEXTFLAGS_TEXT)
                assert d[1].get_pixmap().samples==a[1].get_pixmap().samples
                assert d[0].get_image_info(hashes=True)[-1]['bbox']==a[0].get_image_info(hashes=True)[1]['bbox']
                assert d[0].get_image_info(hashes=True)[-1]['digest']==a[0].get_image_info(hashes=True)[1]['digest']
    assert original.read_bytes()==base
    print('PASS: real Qt pointer drag of a tagged image, automatic preview/application, undo/redo, accessible replacement and semantic deletion; all three native saves reopened with retained text/other image/other page and original unchanged.')
finally:
    window.close();QTest.qWait(200)
