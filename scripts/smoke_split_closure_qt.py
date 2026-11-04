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
from scripts.create_split_sample import create as source
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
    wait('document.querySelector(".document-bar")?.textContent.includes("Combined.pdf")');tool('Organizar páginas','Dividir PDF');edit('Prefijo de nombres de partes','1.46 PINTURA')
    wait('document.querySelector("dialog").innerText.includes("Configuración comprobada")')
    assert js(field('Nombre de parte 42')+'.value')=='1.46 PINTURA 042.pdf'
    edit('Nombre de parte 1','bad/name');assert js('[...document.querySelectorAll("button")].find(e=>e.textContent==="Descargar partes ZIP").disabled');click('Generar nombres numerados')
    js(field('Incluir relación de archivos de división')+'.click()');QFileDialog.getSaveFileName=lambda *a,**kw:(str(parts),'');click('Descargar partes ZIP');deadline=time.monotonic()+80
    while not parts.exists() and time.monotonic()<deadline:QTest.qWait(100)
    with ZipFile(parts) as z,f.open(original) as base:
        report=json.loads(z.read('reapdf-division.json'));assert len(report['parts'])==42 and report['native_content_verified']
        for i,p in enumerate(report['parts']):
            assert p['name']==f'1.46 PINTURA {i+1:03d}.pdf' and p['tagged']
            with f.open(stream=z.read(p['name'])) as d:assert d[0].get_text()==base[i].get_text() and d[0].get_pixmap().samples==base[i].get_pixmap().samples
    edit('Modo de división','groups',True);edit('Grupos para dividir','1-14\n15-28\n29-42');wait('document.querySelector("dialog").innerText.includes("Configuración comprobada")')
    assert js('document.querySelector("dialog").innerText.includes("3 archivos PDF")')
    grouped=root/'Groups.zip';QFileDialog.getSaveFileName=lambda *a,**kw:(str(grouped),'');click('Descargar partes ZIP');deadline=time.monotonic()+60
    while not grouped.exists() and time.monotonic()<deadline:QTest.qWait(100)
    with ZipFile(grouped) as z:
        receipt=json.loads(z.read('reapdf-division.json'));assert [p['pages'] for p in receipt['parts']]==[14,14,14]

    edit('Modo de división','bookmarks',True);click('Preparar desde marcadores');wait('document.querySelector("dialog").innerText.includes("Configuración comprobada")')
    assert js(field('Nombre de parte 1')+'.value')=='001-Section 1.pdf'
    bookmarked=root/'Bookmarks.zip';QFileDialog.getSaveFileName=lambda *a,**kw:(str(bookmarked),'');click('Descargar partes ZIP');deadline=time.monotonic()+60
    while not bookmarked.exists() and time.monotonic()<deadline:QTest.qWait(100)
    with ZipFile(bookmarked) as z:
        assert z.namelist()==['001-Section 1.pdf','002-Section 2.pdf','003-Section 3.pdf','reapdf-division.json']
        assert all(p['native_content_verified'] for p in json.loads(z.read('reapdf-division.json'))['parts'])
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    click('Cerrar');print('PASS: native Qt split with automatic preflight, invalid-name recovery, 42 numbered files with native text/pixels/tags, grouped and bookmark plans; original unchanged.')
finally:
    window.close();QTest.qWait(200)
