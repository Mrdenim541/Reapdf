"""Own Qt window: geometric OCR, native save, tag semantics and merged Word download."""
import hashlib,json,tempfile,time
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as E
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_scan_geometry import scan
from tests.test_table_regions import source
from tests.test_structure_preflight_regions import tagged
from backend.structure_editing import reading_preview

root=Path(tempfile.mkdtemp(prefix='reapdf-geometry-qt-'));original=root/'Original.pdf';original.write_bytes(scan(7));output=root/'Corrected.pdf';tag_source=root/'Tagged.pdf';tag_source.write_bytes(tagged());tag_output=root/'Semantic.pdf';table=root/'Table.pdf';table.write_bytes(source());word=root/'Merged.docx'
digest=hashlib.sha256(original.read_bytes()).hexdigest()
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
    tool('Convertir y OCR','OCR de región');wait('!!'+field('X de región OCR'))
    for label,value in zip(['X','Y','Ancho','Alto'],[80,110,450,160]):edit(label+' de región OCR',str(value))
    edit('Idioma del OCR de región','eng',True);edit('Corrección geométrica OCR','angle',True);edit('Inclinación OCR','7');click('Reconocer esta región');wait('!document.querySelector("dialog[open]")');native_save(output)
    with f.open(original) as a,f.open(output) as b:assert b[0].get_text().split()==['GEOMETRY','TEST','12345'] and a[0].get_pixmap().samples==b[0].get_pixmap().samples
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    native_open(tag_source);tool('Documentos','Etiquetas y orden de lectura');wait('document.body.innerText.includes("PARRAFO")');click('Editar etiquetas');wait('!!'+field('Etiqueta de estructura'))
    js('(()=>{const e='+field('Etiqueta de estructura')+';e.value=[...e.options].find(o=>o.textContent.includes("P · página 1")).value;e.dispatchEvent(new Event("change",{bubbles:true}));})()');wait('!!'+field('Rol de etiqueta'));edit('Rol de etiqueta','H1',True);click('Guardar rol de etiqueta');wait('!document.querySelector("dialog[open]")');native_save(tag_output)
    assert reading_preview(tag_output.read_bytes(),[],0)['blocks'][0]['roles']==['Document','H1']
    native_open(table);tool('Convertir y OCR','Extraer tabla por región');wait('!!'+field('X de tabla'))
    for label,value in zip(['X','Y','Ancho','Alto'],[40,80,450,150]):edit(label+' de tabla',str(value))
    edit('Contenido de tabla','digital',True);click('Extraer y revisar');wait(field('Celda 1, 1')+'?.value==="ITEM"');click('Combinar selección');wait(field('Celda 1, 1')+'?.value==="ITEM\\nCOUNT"')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(word),'');click('Exportar Word revisado');deadline=time.monotonic()+35
    while not word.exists() and time.monotonic()<deadline:QTest.qWait(100)
    with ZipFile(word) as z:
        node=E.fromstring(z.read('word/document.xml'));assert node.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}gridSpan') is not None
    click('Cerrar');print('PASS: own Qt window corrected inclined scan and saved atomically with identical pixels/original intact; reviewed and changed existing tag role with native save; merged reviewed cells and downloaded Word through native dialog.')
finally:
    window.close();QTest.qWait(200)
