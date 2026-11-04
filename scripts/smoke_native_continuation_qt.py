"""Actual Qt caret, mouse-drawn destination, original fonts across pages and native save."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_native_continuation import source
root=Path(tempfile.mkdtemp(prefix='reapdf-native-continuation-qt-'));original=root/'Original.pdf';output=root/'Continued.pdf';base=source(rotation=90,nested=True);original.write_bytes(base)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1700,1150);window.show()
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
def edit(label,value):
    expr=field(label);wait(expr+'?.disabled===false');js('(()=>{const e='+expr+';Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(e,'+json.dumps(str(value))+');e.dispatchEvent(new Event("input",{bubbles:true}));})()');QTest.qWait(70)
def point(x,y):
    svg=field('Área de continuación sobre la página');return json.loads(js('JSON.stringify((()=>{const s='+svg+';const p=s.createSVGPoint();p.x='+str(x)+';p.y='+str(y)+';const q=p.matrixTransform(s.getScreenCTM());return {x:q.x,y:q.y};})())'))
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Original.pdf")');click('Editar');wait(field('Editar texto')+'?.disabled===false');js('(()=>{const b='+field('Editar texto')+';b.closest("details").open=true;b.click();})()')
    expr='[...document.querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||"").startsWith("Editar en página: HELLO"))';wait('!!'+expr);js(expr+'.scrollIntoView({block:"center",inline:"center"})');QTest.qWait(250);pos=json.loads(js('JSON.stringify((()=>{const r='+expr+'.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})())'));QTest.mouseClick(window.view.focusProxy() or window.view,Qt.MouseButton.LeftButton,pos=QPoint(round(pos['x']),round(pos['y'])));wait(field('Texto sobre la página')+'?.disabled===false');click('Seleccionar varios bloques');click('Editar en página: TEXT');click('Redistribuir selección');wait(field('Párrafo sobre la página')+'?.disabled===false')
    target=window.view.focusProxy() or window.view;js(field('Párrafo sobre la página')+'.focus()');QTest.keyClick(target,Qt.Key.Key_Home,Qt.KeyboardModifier.ControlModifier)
    for _ in range(6):QTest.keyClick(target,Qt.Key.Key_Right)
    QTest.keyClicks(target,'HELLO '*17,delay=3);QTest.keyClick(target,Qt.Key.Key_End,Qt.KeyboardModifier.ControlModifier);QTest.keyClicks(target,' TEXT'*11,delay=3)
    expected='HELLO '*18+'TEXT'+' TEXT'*11;wait(field('Párrafo sobre la página')+'.value==='+json.dumps(expected));edit('Ancho del párrafo en página',150);edit('Alto del párrafo en página',40);click('Continuar en otra página');wait(field('Texto del párrafo entre páginas')+'?.value==='+json.dumps(expected))
    js(field('Texto del párrafo entre páginas')+'.focus()');QTest.keyClick(target,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);QTest.keyClick(target,Qt.Key.Key_Backspace);wait(field('Texto del párrafo entre páginas')+'.value===""');QTest.keyClick(target,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier);wait(field('Texto del párrafo entre páginas')+'.value==='+json.dumps(expected));assert js(field('Estilo de continuación 2')+'.value')=='TEXT'+' TEXT'*11
    for name,value in [('X',20),('Y',20),('Ancho',300),('Alto',50)]:edit(name+' de continuación',value)
    js(field('Texto del párrafo entre páginas')+'.focus()');QTest.keyClick(target,Qt.Key.Key_Return,Qt.KeyboardModifier.ControlModifier);wait('document.body.innerText.includes("el área debe estar vacía")');assert js(field('Texto del párrafo entre páginas')+'.value')==expected
    wait('document.querySelector(".flow-page img")?.complete');js(field('Área de continuación sobre la página')+'.scrollIntoView({block:"center",inline:"center"})');QTest.qWait(250);a=point(40,150);b=point(520,600)
    QTest.mousePress(target,Qt.MouseButton.LeftButton,pos=QPoint(round(a['x']),round(a['y'])));QTest.mouseMove(target,QPoint(round(b['x']),round(b['y'])),delay=100);QTest.mouseRelease(target,Qt.MouseButton.LeftButton,pos=QPoint(round(b['x']),round(b['y'])));wait('Math.abs(Number('+field('Ancho de continuación')+'.value)-480)<2')
    js(field('Texto del párrafo entre páginas')+'.focus()');QTest.keyClick(target,Qt.Key.Key_Return,Qt.KeyboardModifier.ControlModifier);wait('!document.querySelector("dialog[open]")');click('↶ Deshacer');click('↷ Rehacer')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    with f.open(original) as a,f.open(output) as b:
        text=''.join((b[0].get_text()+b[1].get_text()).split());assert text.count('HELLO')==19 and text.count('TEXT')==15 and 'TEXT' in b[1].get_text()
        assert a[2].get_pixmap().samples==b[2].get_pixmap().samples and a[3].get_pixmap().samples==b[3].get_pixmap().samples
        for i in range(2):assert a[i].rotation==b[i].rotation;a[i].set_rotation(0);b[i].set_rotation(0)
        assert a[0].search_for('NEIGHBOR UNCHANGED')==b[0].search_for('NEIGHBOR UNCHANGED') and a[1].search_for('OTHER PAGE UNCHANGED')==b[1].search_for('OTHER PAGE UNCHANGED')
    assert original.read_bytes()==base
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes("Continued.pdf")')
    print('PASS: actual Qt caret and mixed-style undo, occupied-area failure retains draft, mouse-drawn destination on rotated page, direct Ctrl+Enter cross-page original-font continuation, document undo/redo, native atomic save/reopen; other appearances/pages and source intact.')
finally:window.allow_close=True;window.close();app.processEvents()
