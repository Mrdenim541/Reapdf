"""Own Qt UI acceptance of the extended PDF editing and structure journeys."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_extended_workflows import blank,semantic_source,affine_paragraph,layered
from tests.test_portfolio_metadata import sample
from backend.measurements import model
from backend.portfolio_metadata import model as columns
root=Path(tempfile.mkdtemp(prefix='reapdf-extended-qt-'));original=root/'Blank.pdf';original.write_bytes(blank())
for name,data in [('Semantic.pdf',semantic_source()),('Affine.pdf',affine_paragraph()),('Layers.pdf',layered()[0]),('Portfolio.pdf',sample())]:(root/name).write_bytes(data)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1700,1150);window.show()
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
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty');assert path.exists()


def native_open(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')


def point(x,y):
    positions=json.loads(js('JSON.stringify((()=>{const b='+field('Puntos de medición sobre el plano')+'.getBoundingClientRect();return [b.x+'+str(x)+'/600*b.width,b.y+'+str(y)+'/700*b.height];})())'))
    target=window.view.focusProxy() or window.view;QTest.mouseClick(target,Qt.MouseButton.LeftButton,pos=QPoint(round(positions[0]),round(positions[1])));QTest.qWait(80)


try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Blank.pdf")');tool('Documentos','Medir planos');edit('Tipo de medición','angle',True);wait('!!document.querySelector('+json.dumps('img[alt="Plano para medir"]')+')')
    for x,y in [(100,150),(100,100),(150,100)]:point(x,y)
    for i,(x,y) in enumerate([(100,150),(100,100),(150,100)]):edit('Vértice seleccionado',str(i),True);edit('X del vértice seleccionado',str(x));edit('Y del vértice seleccionado',str(y))
    click('Calcular medición');wait('document.querySelector(".measurement-result")?.textContent.includes("90.000")');click('Guardar medición en PDF');wait('!document.querySelector("dialog[open]")');native_save(root/'Angle.pdf');assert abs(model((root/'Angle.pdf').read_bytes(),[],0)['measurements'][0]['value']-90)<1e-5
    native_open(root/'Affine.pdf');QTest.qWait(200);tool('Editar','Editar texto');click('Editar en página: ALPHA BETA');click('Editar párrafo');edit('Párrafo sobre la página','BETA ALPHA\nDELTA GAMMA');edit('Ancho del párrafo en página','140');edit('Alto del párrafo en página','100');click('Comprobar ajuste');click('Aplicar párrafo en página');wait('!'+field('Párrafo sobre la página'));native_save(root/'AffineEdited.pdf')
    native_open(root/'Semantic.pdf');QTest.qWait(200);tool('Documentos','Etiquetas y orden de lectura');click('Preparar etiquetas iniciales')
    for i,role in enumerate(['Lbl','LI','Lbl','LI','TH','TH','TD']):edit('Rol del objeto '+str(i+1),role,True)
    edit('Columna del objeto 6','2');edit('Fila del objeto 7','2');js('[...document.querySelectorAll("summary")].find(e=>e.textContent==="Celdas vacías de tablas").click()');click('Añadir celda vacía');edit('Fila de celda vacía 1','2');edit('Columna de celda vacía 1','2');wait(field('Revisé etiquetas de página 1')+'?.disabled===false');js(field('Revisé etiquetas de página 1')+'.click()');click('Crear etiquetas revisadas');wait('!document.querySelector("dialog[open]")');native_save(root/'Tagged.pdf')
    native_open(root/'Layers.pdf');QTest.qWait(200);tool('Documentos','Capas del PDF');edit('Configuración de capas','0',True);click('Vista previa de capas');wait('!!document.querySelector('+json.dumps('img[alt="Visibilidad de capas"]')+')');click('Guardar visibilidad');wait('!document.querySelector("dialog[open]")');native_save(root/'LayersEdited.pdf')
    native_open(root/'Portfolio.pdf');QTest.qWait(200);tool('Documentos','Portfolio PDF');js('[...document.querySelectorAll("summary")].find(e=>e.textContent==="Columnas del portfolio existente").click()');edit('Columna Code del archivo 1','QTEDIT');click('Guardar valores de columnas');wait('!document.querySelector("dialog[open]")');native_save(root/'PortfolioEdited.pdf');assert columns((root/'PortfolioEdited.pdf').read_bytes())['files'][0]['values']['Code']=='QTEDIT'
    with f.open(root/'Tagged.pdf') as d:assert sum(d.xref_get_key(x,'S')==('name','/Lbl') for x in range(1,d.xref_length()))==2
    with f.open(root/'AffineEdited.pdf') as d:assert 'BETA ALPHA' in d[0].get_text() and 'ALPHA BETA' not in d[0].get_text()
    print('PASS: own Qt Linux window angle creation, multi-group affine reflow, separate list labels/empty cells, OCG configurations and foreign portfolio columns; atomic PDF save and reopen of all outputs. Windows not verified.')
finally:
    window.allow_close=True;window.close();QTest.qWait(200)
