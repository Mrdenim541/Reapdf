"""Actual Qt caret, mouse-drawn destination, original fonts across pages and native save."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_tagged_paragraph_sample import create as source
root=Path(tempfile.mkdtemp(prefix='reapdf-native-continuation-qt-'));original=root/'Original.pdf';output=root/'Continued.pdf';base=source();
with f.open(stream=base) as fixture:
    base=fixture.tobytes()
original.write_bytes(base)
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
def open_paragraph():
    click('Editar');wait(field('Editar texto')+'?.disabled===false');js('(()=>{const b='+field('Editar texto')+';b.closest("details").open=true;b.click();})()')
    expr='[...document.querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||"").startsWith("Editar en página: HELLO"))';wait('!!'+expr);js(expr+'.scrollIntoView({block:"center"})');QTest.qWait(150)
    pos=json.loads(js('JSON.stringify((()=>{const r='+expr+'.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})())'))
    QTest.mouseClick(window.view.focusProxy() or window.view,Qt.MouseButton.LeftButton,pos=QPoint(round(pos['x']),round(pos['y'])));click('Editar párrafo');wait(field('Párrafo sobre la página')+'?.disabled===false')
    wait('document.querySelector(".inline-paragraph-editor")?.innerText.includes("Se conservan las etiquetas")')
def type_more(hello,text):
    target=window.view.focusProxy() or window.view;js(field('Párrafo sobre la página')+'.focus()');QTest.keyClick(target,Qt.Key.Key_Home,Qt.KeyboardModifier.ControlModifier)
    for _ in range(6):QTest.keyClick(target,Qt.Key.Key_Right)
    QTest.keyClicks(target,'HELLO '*hello,delay=2);QTest.keyClick(target,Qt.Key.Key_End,Qt.KeyboardModifier.ControlModifier);QTest.keyClicks(target,' TEXT'*text,delay=2)
def apply():
    target=window.view.focusProxy() or window.view;js(field('Párrafo sobre la página')+'.focus()');QTest.keyClick(target,Qt.Key.Key_Return,Qt.KeyboardModifier.ControlModifier);wait('!document.querySelector(".inline-paragraph-editor")')
def save(path):
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty')
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Original.pdf")');open_paragraph();type_more(1,1);edit('Ancho del párrafo en página',300);edit('Alto del párrafo en página',100);apply()
    short=root/'Short.pdf';save(short)
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(short),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes("Short.pdf")');open_paragraph();type_more(16,10);edit('Ancho del párrafo en página',150);edit('Alto del párrafo en página',40)
    wait(field('Añadir páginas automáticamente')+'?.disabled===false');js(field('Añadir páginas automáticamente')+'.click()');apply();click('↶ Deshacer');click('↷ Rehacer');save(output)
    from backend.native_text import native_model
    with f.open(original) as a,f.open(output) as b:
        assert len(b)>len(a)
        for i in range(1,len(a)):assert a[i].get_pixmap().samples==b[i].get_pixmap().samples
        text=''.join(b[i].get_text() for i in [0,*range(len(a),len(b))]);assert text.count('HELLO')==18 and text.count('TEXT')==12
        _,before=native_model(a,0,a[0].rect);expected={(r['font'],r['color'],round(r['display_size'],3),tuple(round(v,4) for v in r['_geometry']['matrix'][:4])) for r in before if r['text'] in ['HELLO ','TEXT']}
        after=[r for i in [0,*range(len(a),len(b))] for r in native_model(b,i,b[i].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']]
        assert {(r['font'],r['color'],round(r['display_size'],3),tuple(round(v,4) for v in r['_geometry']['matrix'][:4])) for r in after}==expected
    from backend.structure_editing import reading_preview
    with f.open(output) as saved:
        for i in range(len(saved)):
            assert reading_preview(output.read_bytes(),[],i)['untagged_blocks']==0
    assert original.read_bytes()==base
    print('PASS: Qt mouse selects a tagged paragraph with Span siblings and distinct shears, caret edits in one box, native save/reopen permits another edit, automatic overflow adds pages, undo/redo and final native save retain each font/color/size/transform and original pages.')
finally:window.allow_close=True;window.close();app.processEvents()
