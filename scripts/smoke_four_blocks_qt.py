"""Native Qt Linux smoke: reviewed fonts, semantic tables and time form save."""
import hashlib,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_four_blocks import variable_pdf,table_pdf
from tests.test_form_standard_actions import source
from backend.structure_editing import model,reading_preview
from backend.variable_fonts import inspect
root=Path(tempfile.mkdtemp(prefix='reapdf-four-qt-'));original=root/'Variable.pdf';original.write_bytes(variable_pdf());table=root/'Table.pdf';table.write_bytes(table_pdf());clock=root/'Time.pdf';clock.write_bytes(source('AFTime_Format(2);','AFTime_Keystroke(2);',initial=''));static=root/'Static.pdf';semantic=root/'Semantic.pdf';filled=root/'Filled.pdf';digest=hashlib.sha256(original.read_bytes()).hexdigest()
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
    wait('document.querySelector(".document-bar")?.textContent.includes("Variable.pdf")');tool('Editar','Preparar fuentes variables');wait('document.body.innerText.includes("wght: 400")');js(field('Revisé los ejes de fuentes variables')+'.click()');click('Preparar fuentes estáticas');wait('!document.querySelector("dialog[open]")');native_save(static);assert not inspect(static.read_bytes(),[])['fonts'];assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    native_open(table);tool('Documentos','Etiquetas y orden de lectura');click('Preparar etiquetas iniciales');wait('!!'+field('Rol del objeto 1'))
    click('Sugerir tabla por posición');wait(field('Fila del objeto 6')+"?.value==='3'")
    wait(field('Revisé etiquetas de página 1')+'?.disabled===false');js(field('Revisé etiquetas de página 1')+'.click()');click('Crear etiquetas revisadas');wait('!document.querySelector("dialog[open]")');native_save(semantic);rows=model(semantic.read_bytes(),[])['nodes'];assert sum(r['role']=='TH' for r in rows)==2 and sum(r['role']=='TD' for r in rows)==4;assert not reading_preview(semantic.read_bytes(),[],0)['untagged_blocks']
    native_open(clock);tool('Formularios y firmas','Rellenar formulario');edit('Valor del formulario','14:35:20');click('Aplicar formulario');wait('!document.querySelector("dialog[open]")');native_save(filled)
    with f.open(filled) as d:assert next(d[0].widgets()).field_value=='14:35:20'
    print('PASS: own Qt Linux window, reviewed variable default conversion and atomic native save, semantic table reviewed through real controls and saved with valid reading tree, native time form filled/saved/reopened; original source hash intact. No Windows execution claimed.')
finally:
    window.close();QTest.qWait(200)
