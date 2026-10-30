"""Own Qt window: initial text tags and automatically suggested scanned merges."""
import hashlib,json,tempfile,time
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as E
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_basic_tagging import source
from tests.test_auto_table_merges import source as table_source
from backend.structure_editing import reading_preview
root=Path(tempfile.mkdtemp(prefix='reapdf-initial-tags-qt-'));original=root/'Original.pdf';original.write_bytes(source());output=root/'Tagged.pdf';table=root/'Scan.pdf';table.write_bytes(table_source(True));word=root/'Merged.docx';digest=hashlib.sha256(original.read_bytes()).hexdigest()
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
    expr=field(label);wait(expr+'?.disabled===false');prototype='HTMLSelectElement' if select else 'HTMLInputElement'
    js('(()=>{const e='+expr+';Object.getOwnPropertyDescriptor('+prototype+'.prototype,"value").set.call(e,'+json.dumps(value)+');e.dispatchEvent(new Event("'+('change' if select else 'input')+'",{bubbles:true}));})()');QTest.qWait(60)


def tool(area,label):
    click(area);wait(field(label)+'?.disabled===false');js('(()=>{const b='+field(label)+';b.closest("details").open=true;b.click();})()')


def native_save(path):
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty');assert path.exists()


def native_open(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')


try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Original.pdf")')
    tool('Documentos','Etiquetas y orden de lectura');click('Preparar etiquetas iniciales');wait('!!'+field('Rol del objeto 1'));edit('Rol del objeto 1','H1',True)
    wait(field('Revisé etiquetas de página 1')+'?.disabled===false');js(field('Revisé etiquetas de página 1')+'.click()');edit('Página de etiquetado inicial','1',True);wait('!!'+field('Revisé etiquetas de página 2'));edit('Rol del objeto 1','H1',True);wait(field('Revisé etiquetas de página 2')+'?.disabled===false');js(field('Revisé etiquetas de página 2')+'.click()');click('Crear etiquetas revisadas');wait('!document.querySelector("dialog[open]")');native_save(output)
    with f.open(original) as a,f.open(output) as b:
        assert len(a)==len(b)==2
        for p,q in zip(a,b):assert p.get_text()==q.get_text() and p.get_pixmap().samples==q.get_pixmap().samples
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    for i in [0,1]:assert reading_preview(output.read_bytes(),[],i)['blocks'][0]['roles'][-1]=='H1'
    native_open(table);tool('Convertir y OCR','Extraer tabla por región');wait('!!'+field('X de tabla'))
    for label,value in zip(['X','Y','Ancho','Alto'],[40,80,450,180]):edit(label+' de tabla',str(value))
    edit('Idioma OCR de tabla','eng',True);js(field('Sugerir combinaciones por bordes')+'.click()');click('Extraer y revisar');wait(field('Celda 1, 1')+'?.value==="MERGED HEADER"');assert js('!'+field('Celda 1, 2')+' && !'+field('Celda 3, 1'))
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(word),'');click('Exportar Word revisado');deadline=time.monotonic()+35
    while not word.exists() and time.monotonic()<deadline:QTest.qWait(100)
    with ZipFile(word) as z:
        node=E.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};assert node.find('.//w:gridSpan',ns) is not None and node.find('.//w:vMerge',ns) is not None
    click('Cerrar');print('PASS: own Qt window reviewed two-page initial tags, created native MCID/ParentTree and heading roles, saved atomically with identical pixels and original intact; suggested scanned horizontal/vertical cell merges and exported Word through native dialog.')
finally:
    window.close();QTest.qWait(200)
