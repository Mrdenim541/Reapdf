"""Real Qt paragraph typing and direct apply, retaining original mixed styles."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_type3_fonts import glyphs
from tests.test_cff_forms_mixed import mixed_pdf

root=Path(tempfile.mkdtemp(prefix='reapdf-mixed-qt-'));original=root/'Original.pdf';output=root/'Edited.pdf';base=mixed_pdf();original.write_bytes(base)
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
    wait('!!'+expr);js(expr+'.dispatchEvent(new MouseEvent("click",{bubbles:true}))');wait(field('Texto sobre la página')+'?.disabled===false');click('Editar párrafo')
    wait(field('Párrafo sobre la página')+'?.disabled===false')
    assert not js('document.querySelector(".inline-original-runs").closest("details").open')
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
        assert 'HELLOHELLOTEXT' in ''.join(b[0].get_text(sort=True).split())
        styles={(s['font'],round(s['size']),s['color']) for block in b[0].get_text('dict')['blocks'] for line in block.get('lines',[]) for s in line['spans'] if s['text']!='UNCHANGED'}
        assert styles=={('Helvetica-Bold',18,0xcc0000),('Helvetica-Oblique',14,0x0000cc)}
        assert a[0].search_for('UNCHANGED')==b[0].search_for('UNCHANGED')
    assert original.read_bytes()==base
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger()
    wait('document.querySelector(".document-bar")?.textContent.includes("Edited.pdf")')
    print('PASS: own Qt mixed paragraph uses one on-page text field, actual caret insertion and browser undo/redo preserve original styles, Ctrl+Enter applies without a separate preview step, native atomic save/reopen and original intact.')
finally:window.allow_close=True;window.close();app.processEvents()
