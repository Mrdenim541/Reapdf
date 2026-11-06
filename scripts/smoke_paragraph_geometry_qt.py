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
root=Path(tempfile.mkdtemp(prefix='reapdf-format-qt-'));original=root/'Paragraph.pdf';base=create(geometry=True);original.write_bytes(base)
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
    print('UI_FAILURE',js('JSON.stringify({error:window.__reflowFailure,alerts:[...document.querySelectorAll(\"[role=alert]\")].map(e=>e.textContent)})'),flush=True);raise AssertionError(script)
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
    wait('document.querySelector(".document-bar")?.textContent.includes("Paragraph.pdf")');js("(()=>{const old=window.fetch;window.fetch=async(...args)=>{const r=await old(...args);if(String(args[0]).includes('/reflow-affine')&&!r.ok)window.__reflowFailure={request:JSON.parse(args[1].body),response:await r.clone().json()};return r;};})()");select('HELLO');click('Editar párrafo')
    wait(field('Cambiar formato del párrafo')+'?.disabled===false');js('document.querySelector(".paragraph-format").open=true');js(field('Cambiar formato del párrafo')+'.click()');wait(field('Fuente del párrafo nativo')+'?.disabled===false')
    js('(()=>{const e='+field('Fuente del párrafo nativo')+';e.value="serif";e.dispatchEvent(new Event("change",{bubbles:true}));})()');edit('Tamaño del párrafo nativo',22);edit('Ancho del párrafo en página',200);edit('Alto del párrafo en página',180);edit('Párrafo sobre la página','HELLO HELLO TEXT TEXT',True)
    QTest.qWait(300);assert js('(()=>{const r=document.querySelector(".inline-paragraph-editor").getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;})()')
    click('Comprobar ajuste');wait('document.querySelector(".inline-text-status").textContent.includes("líneas completas")');apply('Párrafo sobre la página');wait('!document.querySelector(".inline-paragraph-editor")');click('↶ Deshacer');click('↷ Rehacer');output=root/'Geometry formatted.pdf';save(output)
    from backend.semantic_text import tree
    from backend.text_typography import declarations
    with f.open(output) as d:
        n=f.mupdf;t=tree(d);boxes=0
        for rec in t.records.values():
            for _,_,_,attr in declarations(d,rec['object']):
                bbox=n.pdf_dict_gets(attr,'BBox')
                if n.pdf_is_null(bbox):continue
                boxes+=1;assert n.pdf_to_real(n.pdf_dict_gets(attr,'Height'))>20
        assert boxes==2 and all(r['editable'] for r in native_model(d,0,d[0].rect)[1])
    open_file(output);select('HELLO');click('Cancelar')
    # Continue a second paragraph whose geometry must migrate to page-local leaves.
    original2=root/'Continuation.pdf';original2.write_bytes(create(geometry=True));open_file(original2);select('HELLO');click('Editar párrafo');wait(field('Cambiar formato del párrafo')+'?.disabled===false');js('document.querySelector(".paragraph-format").open=true');js(field('Cambiar formato del párrafo')+'.click()');wait(field('Fuente del párrafo nativo')+'?.disabled===false');js('(()=>{const e='+field('Fuente del párrafo nativo')+';e.value="serif";e.dispatchEvent(new Event("change",{bubbles:true}));})()');edit('Tamaño del párrafo nativo',12);edit('Ancho del párrafo en página',130);edit('Alto del párrafo en página',30);edit('Párrafo sobre la página','HELLO '*15+'TEXT '*15,True)
    click('Continuar en otra página');wait(field('Texto del párrafo entre páginas')+'?.disabled===false');assert js(field('Cambiar formato del párrafo')+'.checked');assert js(field('Fuente del párrafo nativo')+'.value')=='serif'
    # Changing a carried format and checking again must invalidate its preview.
    js('document.querySelector(".paragraph-format").open=true');edit('Tamaño del párrafo nativo',13);edit('Y de continuación',150);click('Comprobar distribución');wait('document.querySelector(".flow-dialog [role=status]")?.parentElement.innerText.includes("Ajuste completo:")');click('Aplicar continuación completa');wait('!document.querySelector(".flow-dialog")');click('↶ Deshacer');click('↷ Rehacer');continued=root/'Continuation formatted.pdf';save(continued)
    with f.open(continued) as d:
        assert sum(p.get_text().count('HELLO') for p in d)==15
        for number in [0,1]:
            rows=[r for r in native_model(d,number,d[number].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']];assert rows and all(r['editable'] and abs(r['size']-13)<.01 and r['font'].startswith('DejaVuSerif') for r in rows)
    from backend.text_geometry import validate
    with f.open(continued) as d:
        t=tree(d);boxes=0
        for owner,rec in t.records.items():
            for _,_,_,attr in declarations(d,rec['object']):
                box=validate(attr)
                if box is not None:
                    assert len({pg for pg,_,_ in t.refs[owner]})==1;boxes+=1
        assert boxes>=2
    open_file(continued);select('HELLO');assert original.read_bytes()==base
    print('PASS: page-local continued geometry and Qt mouse edits geometric mixed paragraph, reachable expanded controls at 1366x900, checks updated bounds, undo/redo, native save/reopen; carries font into manual continuation, changes it in that dialog, previews and saves complete editable text on both pages.')
finally:window.allow_close=True;window.close();app.processEvents()
