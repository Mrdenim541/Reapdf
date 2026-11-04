"""Real Qt transformed mixed paragraph typing, native save and shared Form isolation."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_type3_fonts import glyphs
from tests.test_cross_path_reflow import source

root=Path(tempfile.mkdtemp(prefix='reapdf-multi-object-qt-'));original=root/'Original.pdf';output=root/'Edited.pdf';base=source(rotation=90,nested=True);original.write_bytes(base)
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


try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Original.pdf")')
    click('Editar');wait('!!'+field('Editar texto'))
    js('(()=>{const b='+field('Editar texto')+';b.closest("details").open=true;b.click();})()')
    expr='[...document.querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||"").startsWith("Editar en página: HELLO"))'
    wait('!!'+expr);js(expr+'.scrollIntoView({block:"center",inline:"center"})');QTest.qWait(200)
    point=json.loads(js('JSON.stringify((()=>{const r='+expr+'.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})())'))
    QTest.mouseClick(window.view.focusProxy() or window.view,Qt.MouseButton.LeftButton,pos=QPoint(round(point['x']),round(point['y'])))
    wait(field('Texto sobre la página')+'?.disabled===false');click('Seleccionar varios bloques');click('Editar en página: TEXT');wait('document.body.innerText.includes("2 seleccionados")');click('Redistribuir selección')
    wait(field('Párrafo sobre la página')+'?.disabled===false')
    wait('document.body.innerText.includes("La selección combina 2 objetos internos distintos")')
    assert not js('document.querySelector(".inline-original-runs").closest("details").open')
    js('(()=>{const e='+field('Ancho del párrafo en página')+';Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(e,"130");e.dispatchEvent(new Event("input",{bubbles:true}));})()')
    js('(()=>{const e='+field('Alto del párrafo en página')+';Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(e,"180");e.dispatchEvent(new Event("input",{bubbles:true}));})()')
    js(field('Párrafo sobre la página')+'.focus()')
    target=window.view.focusProxy() or window.view
    QTest.keyClick(target,Qt.Key.Key_Home,Qt.KeyboardModifier.ControlModifier)
    for _ in range(6):QTest.keyClick(target,Qt.Key.Key_Right)
    QTest.keyClicks(target,'HELLO ',delay=20)
    wait(field('Párrafo sobre la página')+'.value==="HELLO HELLO TEXT"')
    QTest.keyClick(target,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(target,Qt.Key.Key_Backspace)
    wait(field('Párrafo sobre la página')+'.value===""')
    QTest.keyClick(target,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier)
    wait(field('Párrafo sobre la página')+'.value==="HELLO HELLO TEXT"')
    assert js(field('Fragmento original 2')+'.value')=='TEXT'
    QTest.keyClick(target,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.ShiftModifier)
    wait(field('Párrafo sobre la página')+'.value===""')
    QTest.keyClick(target,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier)
    wait(field('Párrafo sobre la página')+'.value==="HELLO HELLO TEXT"')
    assert js(field('Fragmento original 2')+'.value')=='TEXT'
    # Apply directly: the backend still checks space, fonts and obstacles.
    QTest.keyClick(target,Qt.Key.Key_Return,Qt.KeyboardModifier.ControlModifier)
    wait('!'+field('Párrafo sobre la página'))
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger()
    wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    with f.open(original) as a,f.open(output) as b:
        assert b[0].get_text().count('HELLO')==3 and b[0].get_text().count('TEXT')==4
        original_styles={(s['font'],round(s['size'],3),s['color']) for block in a[0].get_text('dict')['blocks'] for line in block.get('lines',[]) for s in line['spans'] if s['font'] in ['Helvetica-Bold','Helvetica-Oblique']}
        styles={(s['font'],round(s['size'],3),s['color']) for block in b[0].get_text('dict')['blocks'] for line in block.get('lines',[]) for s in line['spans'] if s['font'] in ['Helvetica-Bold','Helvetica-Oblique']}
        assert styles==original_styles and a[0].rotation==b[0].rotation
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        a[0].set_rotation(0);b[0].set_rotation(0)
        assert a[0].search_for('NEIGHBOR UNCHANGED')==b[0].search_for('NEIGHBOR UNCHANGED')
    assert original.read_bytes()==base
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger()
    wait('document.querySelector(".document-bar")?.textContent.includes("Edited.pdf")')
    print('PASS: own Qt cross-path explicit selection of separated text blocks across separate nested Forms uses one on-page text field, actual caret insertion and browser undo/redo preserve original styles, Ctrl+Enter applies without a separate preview step, native atomic save/reopen and original intact.')
finally:window.allow_close=True;window.close();app.processEvents()
