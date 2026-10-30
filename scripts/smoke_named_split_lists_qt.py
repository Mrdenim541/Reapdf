"""Own Qt window: named independent PDF parts and reviewed semantic lists."""
import hashlib,json,tempfile,time
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_named_split import source
from tests.test_basic_tagging import source as plain
from backend.structure_editing import model,reading_preview
root=Path(tempfile.mkdtemp(prefix='reapdf-named-split-qt-'));original=root/'Combined.pdf';original.write_bytes(source());parts=root/'Named.zip';text=root/'Lists.pdf';text.write_bytes(plain());output=root/'Tagged.pdf';taggedparts=root/'TaggedParts.zip';digest=hashlib.sha256(original.read_bytes()).hexdigest()
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
    wait('document.querySelector(".document-bar")?.textContent.includes("Combined.pdf")');tool('Organizar páginas','Dividir PDF');edit('Modo de división','groups',True);edit('Grupos para dividir','1-2\n3,5\n4,6')
    for i,name in enumerate(['Portada','Documento A','Plano de ubicación'],1):edit('Nombre de parte '+str(i),name)
    js(field('Incluir relación de archivos de división')+'.click()');QFileDialog.getSaveFileName=lambda *a,**kw:(str(parts),'');click('Descargar partes ZIP');deadline=time.monotonic()+35
    while not parts.exists() and time.monotonic()<deadline:QTest.qWait(100)
    with ZipFile(parts) as z:
        assert z.namelist()==['Portada.pdf','Documento A.pdf','Plano de ubicación.pdf','reapdf-division.json']
        with f.open(stream=z.read('Plano de ubicación.pdf')) as d:assert len(d)==2 and 'Base pagina 4' in d[0].get_text() and 'Base pagina 6' in d[1].get_text()
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest;click('Cerrar');native_open(text);tool('Documentos','Etiquetas y orden de lectura');click('Preparar etiquetas iniciales');wait('!!'+field('Rol del objeto 1'))
    for page in [0,1]:
        if page:edit('Página de etiquetado inicial',str(page),True)
        wait('!!'+field('Revisé etiquetas de página '+str(page+1)));edit('Rol del objeto 1','H1',True)
        for i in [2,3]:edit('Rol del objeto '+str(i),'LI',True)
        wait(field('Revisé etiquetas de página '+str(page+1))+'?.disabled===false');js(field('Revisé etiquetas de página '+str(page+1))+'.click()')
    click('Crear etiquetas revisadas');wait('!document.querySelector("dialog[open]")');native_save(output);assert sum(r['role']=='LI' for r in model(output.read_bytes(),[])['nodes'])==4
    tool('Organizar páginas','Dividir PDF');edit('Nombre de parte 1','First list');edit('Nombre de parte 2','Second list');QFileDialog.getSaveFileName=lambda *a,**kw:(str(taggedparts),'');click('Descargar partes ZIP');deadline=time.monotonic()+35
    while not taggedparts.exists() and time.monotonic()<deadline:QTest.qWait(100)
    with ZipFile(taggedparts) as z:
        for name in z.namelist():
            data=z.read(name);assert sum(r['role']=='LI' for r in model(data,[])['nodes'])==2 and reading_preview(data,[],0)['untagged_blocks']==0
    click('Cerrar');print('PASS: own Qt app saved ZIP with personalized independent PDF names, ordered ranges and receipt through native dialog, original unchanged; reviewed/created semantic lists and saved PDF, split it into named parts with retained reading structure and pruned off-part nodes.')
finally:
    window.close();QTest.qWait(200)
