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
from scripts.create_byte_split_sample import create as source
root=Path(tempfile.mkdtemp(prefix='reapdf-byte-split-qt-'));original=root/'Combined.pdf';original.write_bytes(source());parts=root/'Named.zip';digest=hashlib.sha256(original.read_bytes()).hexdigest()
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
    wait('document.querySelector(".document-bar")?.textContent.includes("Combined.pdf")');tool('Organizar páginas','Dividir PDF');edit('Modo de división','bytes',True);edit('Tamaño máximo de partes en MB','0.06');wait('document.querySelector("dialog").innerText.includes("Configuración comprobada")');assert js(field('Nombre de parte 3')+'!==null')
    edit('Prefijo de nombres de partes','1.46 PINTURA');wait('document.querySelector("dialog").innerText.includes("Configuración comprobada")');assert js(field('Nombre de parte 1')+'.value')=='1.46 PINTURA 001.pdf'
    edit('Tamaño máximo de partes en MB','0.001');assert js('[...document.querySelectorAll("button")].find(e=>e.textContent==="Descargar partes ZIP").disabled')
    edit('Tamaño máximo de partes en MB','1');wait('document.querySelector("dialog").innerText.includes("Configuración comprobada") && !'+field('Nombre de parte 2'))
    edit('Tamaño máximo de partes en MB','0.06');wait('document.querySelector("dialog").innerText.includes("Configuración comprobada") && !!'+field('Nombre de parte 3'));js(field('Incluir relación de archivos de división')+'.click()');QFileDialog.getSaveFileName=lambda *a,**kw:(str(parts),'');click('Descargar partes ZIP');deadline=time.monotonic()+80
    while not parts.exists() and time.monotonic()<deadline:QTest.qWait(100)
    with ZipFile(parts) as z,f.open(original) as base:
        report=json.loads(z.read('reapdf-division.json'));assert report['max_bytes_per_pdf']==60000 and len(report['parts'])==3
        for i,p in enumerate(report['parts']):
            data=z.read(p['name']);assert len(data)==p['bytes']<=60000 and p['name']==f'1.46 PINTURA {i+1:03d}.pdf' and p['source_pages']==[i+1]
            with f.open(stream=data) as d:assert len(d)==1 and d[0].get_pixmap().samples==base[i].get_pixmap().samples and d[0].get_text()==base[i].get_text()
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    assert js('document.querySelector(".document-bar").textContent.includes("0 cambios")');click('Cerrar')
    print('PASS: Qt native size-based split automatically measures and refreshes groups, rejects invalid limit, keeps personalized numbered names, saves ZIP through native dialog and reopens all native parts within exact byte limit; original and pixels unchanged.')
finally:window.close()
