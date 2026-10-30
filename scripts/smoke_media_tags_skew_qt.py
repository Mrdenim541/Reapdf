"""Own Qt window: media semantics and detected OCR skew with native atomic saves."""
import hashlib,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_media_tagging import source
from tests.test_scan_geometry import scan as scan_source
from backend.structure_editing import model
root=Path(tempfile.mkdtemp(prefix='reapdf-media-skew-qt-'));original=root/'Original.pdf';original.write_bytes(source());output=root/'Tagged.pdf';scan=root/'Scan.pdf';scan.write_bytes(scan_source(7));recognized=root/'Recognized.pdf';digest=hashlib.sha256(original.read_bytes()).hexdigest()
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
    wait('document.querySelector(".document-bar")?.textContent.includes("Original.pdf")')
    tool('Documentos','Etiquetas y orden de lectura');click('Preparar etiquetas iniciales');wait('!!'+field('Alternativa del objeto 3'));edit('Alternativa del objeto 2','Open documentation');edit('Alternativa del objeto 3','Equipment diagram');edit('Rol del objeto 4','Artifact',True);wait(field('Revisé etiquetas de página 1')+'?.disabled===false');js(field('Revisé etiquetas de página 1')+'.click()');click('Crear etiquetas revisadas');wait('!document.querySelector("dialog[open]")');native_save(output)
    rows=model(output.read_bytes(),[])['nodes'];assert [r['alt'] for r in rows if r['role']=='Figure']==['Equipment diagram'];assert [r['alt'] for r in rows if r['role']=='Link']==['Open documentation']
    with f.open(original) as a,f.open(output) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples and a[0].get_text()==b[0].get_text()
        assert a[0].get_links()[0]['uri']==b[0].get_links()[0]['uri'];assert b.xref_get_key(b[0].get_links()[0]['xref'],'StructParent')[0]=='int'
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    native_open(scan);tool('Convertir y OCR','OCR de región');wait('!!'+field('X de región OCR'))
    for label,value in zip(['X','Y','Ancho','Alto'],[80,90,450,200]):edit(label+' de región OCR',str(value))
    edit('Idioma del OCR de región','eng',True);click('Detectar inclinación');wait(field('Corrección geométrica OCR')+'?.value==="angle"');assert abs(float(js(field('Inclinación OCR')+'.value'))-7)<.4
    click('Reconocer esta región');wait('!document.querySelector("dialog[open]")');native_save(recognized)
    with f.open(scan) as a,f.open(recognized) as b:assert b[0].get_text().split()==['GEOMETRY','TEST','12345'] and a[0].get_pixmap().samples==b[0].get_pixmap().samples
    print('PASS: own Qt window reviewed figure/decorative image occurrences and native text link label, saved atomically preserving pixels/destinations/original; detected skew reviewed and used for OCR, native save preserved scan pixels and recognized text.')
finally:
    window.close();QTest.qWait(200)
