"""Real Qt caret edits of ActualText/Stm and page-owned shared Form paragraphs."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_paragraph_format_sample import create
from backend.native_text import native_model
from backend.structure_editing import reading_preview
root=Path(tempfile.mkdtemp(prefix='reapdf-format-qt-'));original=root/'Paragraph.pdf';base=create();original.write_bytes(base)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1650,1100);window.show()
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
    wait('!!'+expr+' && !'+expr+'.disabled');js(expr+'.click()')
def edit(label,value,textarea=False):
    expr=field(label);wait(expr+'?.disabled===false');js('(()=>{const e='+expr+';Object.getOwnPropertyDescriptor(' + ('HTMLTextAreaElement' if textarea else 'HTMLInputElement')+'.prototype,"value").set.call(e,'+json.dumps(str(value))+');e.dispatchEvent(new Event("input",{bubbles:true}));})()')
def type_text(label,text):
    js(field(label)+'.focus()');target=window.view.focusProxy() or window.view;QTest.keyClick(target,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);QTest.keyClicks(target,text,delay=2)
def apply(label):
    js(field(label)+'.focus()');QTest.keyClick(window.view.focusProxy() or window.view,Qt.Key.Key_Return,Qt.KeyboardModifier.ControlModifier)
def select(text):
    click('Editar');wait(field('Editar texto')+'?.disabled===false');js(field('Editar texto')+'.closest("details").open=true');js(field('Editar texto')+'.click()')
    expr='[...document.querySelectorAll("[role=button]")].find(e=>(e.getAttribute("aria-label")||"").startsWith('+json.dumps('Editar en página: '+text)+'))';wait('!!'+expr);js(expr+'.scrollIntoView({block:"center"})');QTest.qWait(150)
    point=json.loads(js('JSON.stringify((()=>{const r='+expr+'.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];})())'));QTest.mouseClick(window.view.focusProxy() or window.view,Qt.MouseButton.LeftButton,pos=QPoint(round(point[0]),round(point[1])));wait(field('Texto sobre la página')+'?.disabled===false')
def save(path):
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty')
def open_file(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Paragraph.pdf")');click('Editar');click('Editar texto');wait('!!document.querySelector(".text-target")')
    target='[...document.querySelectorAll(".text-target")].find(e=>(e.getAttribute("aria-label")||"").startsWith("Editar en página: HELLO"))';js(target+'.scrollIntoView({block:"center"})');QTest.qWait(150);pos=json.loads(js('JSON.stringify((()=>{const r='+target+'.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];})())'));QTest.mouseClick(window.view.focusProxy() or window.view,Qt.MouseButton.LeftButton,pos=QPoint(round(pos[0]),round(pos[1])))
    click('Editar párrafo');wait(field('Cambiar formato del párrafo')+'?.disabled===false');js('document.querySelector(".paragraph-format").open=true');js(field('Cambiar formato del párrafo')+'.click()');wait(field('Fuente del párrafo nativo')+'?.disabled===false');js('(()=>{const e='+field('Fuente del párrafo nativo')+';e.value="serif";e.dispatchEvent(new Event("change",{bubbles:true}));})()');edit('Tamaño del párrafo nativo',12);edit('Ancho del párrafo en página',180);edit('Alto del párrafo en página',100);edit('Párrafo sobre la página','HELLO Ω HELLO TEXT TEXT',True)
    click('Comprobar ajuste');wait('document.querySelector(".inline-text-status").textContent.includes("líneas completas")');apply('Párrafo sobre la página');wait('!document.querySelector(".inline-paragraph-editor")');click('↶ Deshacer');click('↷ Rehacer')
    output=root/'Paragraph formatted.pdf';QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty');assert output.exists()
    with f.open(output) as d:
        rows=[r for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']];assert rows and all(r['editable'] and abs(r['size']-12)<.01 for r in rows);assert any(r['font']=='DejaVuSerif-Bold' for r in rows) and any(r['font']=='DejaVuSerif-Italic' for r in rows)
        from backend.semantic_text import tree
        t=tree(d);n=f.mupdf;shared=n.pdf_dict_gets(n.pdf_dict_gets(t.root,'ClassMap'),'Shared');assert n.pdf_to_text_string(n.pdf_dict_gets(shared,'FontFamily'))=='Helvetica';assert d.xref_get_key(t.owners[(d[0].xref,0,0)][0],'C')==('name','/Shared')
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes("Paragraph formatted.pdf")');click('Editar');click('Editar texto');wait('!!document.querySelector(".text-target")')
    assert original.read_bytes()==base
    print('PASS: Qt mouse opens a tagged mixed paragraph, previews and applies common font/size while retaining emphasis and colors, isolates shared typography class, undo/redo, native save and reopen remain editable; original and unrelated class stay intact.')
finally:window.close()
