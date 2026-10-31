"""Actual Qt wildcard replacement and bounded curved-path measurement/save."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_wildcard_search import sample as search_sample
from tests.test_measurement_paths import sample as curve_sample,CAL
from backend.measurements import measure,model
root=Path(tempfile.mkdtemp(prefix='reapdf-search-curves-qt-'));search=root/'Search.pdf';search.write_bytes(search_sample());curves=root/'Curves.pdf';curves.write_bytes(measure(curve_sample(),[],0,'distance',CAL['points'],CAL))
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(search));window.resize(1700,1150);window.show()
def js(script):
    values=[];loop=QEventLoop();window.page.runJavaScript('(()=>{try{return eval('+json.dumps(script)+');}catch(e){return {__error:String(e)};}})()',lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec()
    if not values:raise AssertionError('Qt did not respond')
    if isinstance(values[0],dict) and '__error' in values[0]:raise AssertionError(values[0]['__error'])
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
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');window.save_as_action.trigger()
    wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    assert path.exists()

def native_open(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger()
    wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')

try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Search.pdf") && !!document.querySelector(".text-layer")')
    tool('Editar','Buscar y reemplazar');edit('Modo de búsqueda','wildcard',True);edit('Texto a buscar','COD-?');edit('Reemplazar por','X');click('Buscar coincidencias')
    wait('document.body.innerText.includes("3 coincidencias.")');click('Siguiente');click('Revisar reemplazo actual');click('Aplicar reemplazos');wait('!document.querySelector("dialog[open]")');native_save(root/'SearchEdited.pdf')
    with f.open(root/'SearchEdited.pdf') as d:assert 'COD-1 X COD-3' in d[0].get_text()
    native_open(curves);tool('Documentos','Medir planos');edit('Tipo de medición','perimeter',True);click('Seleccionar trazado del PDF');click('Seleccionar trazado 2 en plano');click('Calcular medición')
    wait('document.querySelector(".measurement-result")?.textContent.includes("Margen por aproximación")');click('Guardar medición en PDF');wait('!document.querySelector("dialog[open]")');native_save(root/'CurvesMeasured.pdf')
    rows=model((root/'CurvesMeasured.pdf').read_bytes(),[],0)['measurements'];row=next(r for r in rows if r['kind']=='perimeter');assert row['trace_source_verified'] and row['approximation']['error_bound']>0 and row['points'][0]==row['points'][-1]
    with f.open(curves) as a,f.open(root/'CurvesMeasured.pdf') as b:assert a[0].get_pixmap(annots=False).samples==b[0].get_pixmap(annots=False).samples and a[1].get_pixmap().samples==b[1].get_pixmap().samples
    print('PASS: own Qt window wildcard search, current-match review, original-font replacement, native atomic save/reopen, visually selected closed curve with bounded approximation, calibration and unchanged underlying plan/other page.')
finally:window.allow_close=True;window.close();app.processEvents()
