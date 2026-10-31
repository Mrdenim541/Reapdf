"""Native Qt Linux smoke: blended original text and semantic cell groups."""
import hashlib,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_composition_cells_styles_notes import blended,multibody,styled_xml,blank
from backend.structure_editing import model,reading_preview
root=Path(tempfile.mkdtemp(prefix='reapdf-composition-qt-'));original=root/'Blend.pdf';original.write_bytes(blended(form=True));table=root/'Cells.pdf';table.write_bytes(multibody());output=root/'BlendEdited.pdf';grouped=root/'Grouped.pdf';digest=hashlib.sha256(original.read_bytes()).hexdigest()
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
    wait('document.querySelector(".document-bar")?.textContent.includes("Blend.pdf")');tool('Editar','Editar texto');click('Editar en página: ABC ABC');wait(field('Texto sobre la página')+'?.disabled===false');assert js(field('Fuente de edición directa')+'.disabled');edit('Texto sobre la página','CBA AB');click('Aplicar');wait('!'+field('Texto sobre la página'));native_save(output)
    with f.open(original) as a,f.open(output) as b:assert 'CBA AB' in b[0].get_text() and a[1].get_pixmap().samples==b[1].get_pixmap().samples
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    native_open(table);tool('Documentos','Etiquetas y orden de lectura');click('Preparar etiquetas iniciales');wait('!!'+field('Rol del objeto 1'))
    for i in range(1,6):
        edit('Rol del objeto '+str(i),'TH' if i<=2 else 'TD',True);edit('Fila del objeto '+str(i),'1' if i<=2 else '2');edit('Columna del objeto '+str(i),'2' if i in [2,5] else '1')
        if i in [3,4]:js(field('Agrupar fragmentos del objeto '+str(i))+'.click()')
    wait(field('Revisé etiquetas de página 1')+'?.disabled===false');js(field('Revisé etiquetas de página 1')+'.click()');click('Crear etiquetas revisadas');wait('!document.querySelector("dialog[open]")');native_save(grouped);assert sum(r['role']=='TD' for r in model(grouped.read_bytes(),[])['nodes'])==2
    print('PASS: own Qt Linux app edited blended text inside shared non-isolated Form via real page controls, kept original composition and other page, atomically saved; multiple original text objects grouped into one semantic cell and saved/reopened with valid reading structure. Original file hash intact.')
finally:
    window.close();QTest.qWait(200)
