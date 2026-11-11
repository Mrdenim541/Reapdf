"""Real Qt print profile inspection, native preparation, undo/redo/save/reopen."""
import base64,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_press_sample import create,profile
root=Path(tempfile.mkdtemp(prefix='reapdf-press-qt-'));original=root/'Press.pdf';base=create(embedded=True);original.write_bytes(base);output=root/'Prepared.pdf';icc=profile()
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1366,900);window.show()
def js(script):
    values=[];loop=QEventLoop();window.page.runJavaScript(script,lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec()
    if not values:raise AssertionError('Qt did not respond')
    return values[0]
def wait(script):
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        if js(script):return
        QTest.qWait(100)
    print('UI_FAILURE',js('document.body.innerText.slice(-10000)'),flush=True);raise AssertionError(script)
def field(label):return 'document.querySelector('+json.dumps('[aria-label="'+label+'"]')+')'
def click(label):
    expr='[...document.querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+json.dumps(label)+')'
    wait('!!'+expr+' && !'+expr+'.disabled');js(expr+'.click()')
def edit(label,value):
    expr=field(label);wait(expr+'?.disabled===false');js('(()=>{const e='+expr+';Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(e,'+json.dumps(str(value))+');e.dispatchEvent(new Event("input",{bubbles:true}));})()');QTest.qWait(50)
def tool():
    click('Proteger');wait(field('Inspección de impresión')+'?.disabled===false');js(field('Inspección de impresión')+'.closest("details").open=true');js(field('Inspección de impresión')+'.click()');wait(field('Perfil de inspección de impresión')+'?.disabled===false')
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Press.pdf")');tool();js('(()=>{const e='+field('Perfil de inspección de impresión')+';e.value="x4-2010";e.dispatchEvent(new Event("change",{bubbles:true}));})()');click('Inspeccionar PDF');wait(field('Resultado preparatorio PDF X')+'?.textContent.includes("bloqueos detectados")');click('Preparar copia')
    edit('Sangrado en mm',4);click('Revisar preparación');wait('document.querySelector(".press-preparation [role=alert]")?.textContent.includes("margen")');assert js(field('Sangrado en mm')+'.value')=='4';edit('Sangrado en mm',3)
    js('(()=>{const bytes=Uint8Array.from(atob('+json.dumps(base64.b64encode(icc).decode())+'),c=>c.charCodeAt(0));const dt=new DataTransfer();dt.items.add(new File([bytes],"synthetic-test-only.icc"));const e='+field('Perfil ICC de impresión')+';e.files=dt.files;e.dispatchEvent(new Event("change",{bubbles:true}));})()');wait(field('Condición de salida')+'?.value==="synthetic-test-only"');click('Revisar preparación');wait(field('Revisión de preparación de impresión')+'?.textContent.includes("0 bloqueos")');js(field('Confirmar preparación de impresión')+'.click()');edit('Margen de corte en mm',4);wait('!'+field('Revisión de preparación de impresión'));edit('Margen de corte en mm',3);click('Revisar preparación');wait(field('Confirmar preparación de impresión')+'?.disabled===false');assert not js(field('Confirmar preparación de impresión')+'.checked');js(field('Confirmar preparación de impresión')+'.click()');click('Aplicar preparación a una copia');wait('!document.querySelector("dialog[open].advanced-dialog")');click('↶ Deshacer');click('↷ Rehacer')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty')
    with f.open(output) as d,f.open(stream=base) as a:
        for p,q in zip(d,a):
            assert p.read_contents()==q.read_contents() and p.get_text()==q.get_text()
            assert p.rect==q.rect and max(abs(v-w) for v,w in zip(p.get_pixmap().samples,q.get_pixmap().samples))<=1
        n=f.mupdf;pdf=f._as_pdf_document(d);intent=n.pdf_array_get(n.pdf_dict_gets(n.pdf_load_object(pdf,d.pdf_catalog()),'OutputIntents'),0);x=n.pdf_to_num(n.pdf_dict_gets(intent,'DestOutputProfile'));assert d.xref_stream(x)==icc
        assert all(d.xref_get_key(p.xref,'TrimBox')[0]=='array' and d.xref_get_key(p.xref,'BleedBox')[0]=='array' for p in d)
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes("Prepared.pdf")');tool();click('Preparar copia');assert original.read_bytes()==base
    print('PASS: Qt PDF/X preparation inspection, invalid bleed draft retained, explicit synthetic local ICC, preview invalidation and renewed acknowledgement, apply, undo/redo, native save/reopen, preserved text/content and original; synthetic ICC rendering differs by at most one channel level; no conformance claim or color conversion.')
finally:window.allow_close=True;window.close();app.processEvents()
