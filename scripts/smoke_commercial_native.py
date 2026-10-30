"""Fill a standard formatted form and extract a real scanned table through Qt."""
import hashlib,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_form_standard_actions import source
from tests.test_table_regions import source as table_source
from backend.docx_import import import_docx
import csv

root=Path(tempfile.mkdtemp(prefix='reapdf-commercial-qt-'));original=root/'Original.pdf';output=root/'Editado.pdf';original.write_bytes(source(initial=''));digest=hashlib.sha256(original.read_bytes()).hexdigest()
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([]);QMessageBox.question=lambda *args:QMessageBox.StandardButton.Yes
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


def click(label):
    expr='[...document.querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+json.dumps(label)+')'
    wait('!!'+expr+' && !'+expr+'.disabled');js(expr+'.dispatchEvent(new MouseEvent("click",{bubbles:true}))')


def field(label):return 'document.querySelector('+json.dumps('[aria-label="'+label+'"]')+')'


def edit(label,value):
    wait(field(label)+'?.disabled===false')
    js('(()=>{const e='+field(label)+';Object.getOwnPropertyDescriptor((e.tagName==="TEXTAREA"?HTMLTextAreaElement:HTMLInputElement).prototype,"value").set.call(e,'+json.dumps(value)+');e.dispatchEvent(new Event("input",{bubbles:true}));})()')
    QTest.qWait(50)


def tool(label):
    wait(field(label)+'?.disabled===false');js('(()=>{const b='+field(label)+';b.closest("details").open=true;b.click();})()')


def file_ready(path):
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        if path.exists() and path.stat().st_size:return
        QTest.qWait(100)
    raise AssertionError('Native download did not finish: '+str(path))


try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Original.pdf")')
    click('Formularios y firmas');tool('Rellenar formulario');edit('Valor del formulario','1500,25')
    click('Aplicar formulario');wait('!document.querySelector(".form-dialog[open]")')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    with f.open(original) as a,f.open(output) as b:
        old=next(a[0].widgets());new=next(b[0].widgets());assert new.field_value=='1500.25' and 'EUR 1.500,25' in b[0].get_text()
        assert a.xref_get_key(old.xref,'AA/F/JS')==b.xref_get_key(new.xref,'AA/F/JS') and a[1].get_pixmap().samples==b[1].get_pixmap().samples
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    scan=root/'Scan.pdf';scan.write_bytes(table_source(True));scan_digest=hashlib.sha256(scan.read_bytes()).hexdigest();window.open_path(str(scan));wait('document.querySelector(".document-bar")?.textContent.includes("Scan.pdf")')
    click('Convertir y OCR');tool('Extraer tabla por región');wait('!!'+field('X de tabla'))
    for label,value in [('X de tabla','40'),('Y de tabla','80'),('Ancho de tabla','450'),('Alto de tabla','150')]:edit(label,value)
    js('(()=>{const e='+field('Idioma OCR de tabla')+';e.value="eng";e.dispatchEvent(new Event("change",{bubbles:true}));})()')
    click('Extraer y revisar');wait(field('Celda 2, 1')+'?.value==="BOLT"');edit('Celda 2, 1','PERNO')
    csv_path=root/'Reviewed.csv';word_path=root/'Reviewed.docx'
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(csv_path),'');click('Exportar CSV revisado');file_ready(csv_path)
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(word_path),'');click('Exportar Word revisado');file_ready(word_path)
    with csv_path.open(encoding='utf-8-sig',newline='') as handle:assert list(csv.reader(handle))[1][0]=='PERNO'
    pdf,report=import_docx(word_path.read_bytes())
    with f.open(stream=pdf) as d:assert 'PERNO' in ''.join(p.get_text() for p in d) and report['tables']==1
    assert hashlib.sha256(scan.read_bytes()).hexdigest()==scan_digest
    print('PASS: actual Qt window filled a standard formatted PDF with automatic preview and native atomic save, preserved actions/original/other page; opened a real scanned table, performed OCR/review, corrected a cell and saved CSV and editable Word through native download dialogs, preserving source.')
except Exception:
    print(js("document.body.innerText"));raise
finally:window.allow_close=True;window.close();app.processEvents()
