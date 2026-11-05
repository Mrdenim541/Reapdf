"""Real Qt edits on a dense, tagged page with pre-existing metric-box overlap."""
import json,tempfile,time
from pathlib import Path
from collections import Counter
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from backend.basic_tagging import candidates,create
from backend.native_text import native_model
from backend.affine_mixed_reflow import stable_key
from backend.tagged_text_integrity import snapshot
root=Path(tempfile.mkdtemp(prefix='reapdf-tagged-dense-qt-'));original=root/'Dense.pdf';output=root/'Edited.pdf'
with f.open() as d:
    p=d.new_page(width=600,height=800)
    for n in range(180):p.insert_text((30+(n//60)*140,30+(n%60)*8),f'ITEM-{n:03d}',fontsize=7)
    base=d.tobytes()
info=candidates(base,[]);base=create(base,[],[{'id':r['id'],'role':'P'} for r in info['entries']],reviewed=True)[0]
with f.open(stream=base) as d:
    for n in range(180,240):d[0].insert_text((30+(n//60)*140,30+(n%60)*8),f'ITEM-{n:03d}',fontsize=7)
    base=d.tobytes(garbage=2)
original.write_bytes(base)
with f.open(stream=base) as d:_,before=native_model(d,0,d[0].rect,context=True);tag_state=snapshot(d,0)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000',str(original));window.resize(1700,1150);window.show()
def js(script):
    result=[];loop=QEventLoop();window.page.runJavaScript(script,lambda v:(result.append(v),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec();return result[0] if result else None
def wait(script):
    end=time.monotonic()+40
    while time.monotonic()<end:
        if js(script):return
        QTest.qWait(100)
    raise AssertionError(script)
def field(label):return 'document.querySelector('+json.dumps('[aria-label="'+label+'"]')+')'
def click(label):
    e='[...document.querySelectorAll("button,[role=button]")].find(e=>(e.getAttribute("aria-label")||e.textContent.trim())==='+json.dumps(label)+')';wait('!!'+e+'&&!'+e+'.disabled');js(e+'.dispatchEvent(new MouseEvent("click",{bubbles:true}))')
try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Dense.pdf")');click('Editar');wait('!!'+field('Editar texto'));js(field('Editar texto')+'.closest("details").open=true');js(field('Editar texto')+'.click()')
    e='[...document.querySelectorAll("[role=button]")].find(e=>e.getAttribute("aria-label")==="Editar en página: ITEM-100")';wait('!!'+e);js(e+'.scrollIntoView({block:"center",inline:"center"})');QTest.qWait(250)
    point=json.loads(js('JSON.stringify((()=>{const b='+e+'.getBoundingClientRect();return [b.x+b.width/2,b.y+b.height/2];})())'));target=window.view.focusProxy() or window.view;QTest.mouseClick(target,Qt.MouseButton.LeftButton,pos=QPoint(round(point[0]),round(point[1])));wait(field('Texto sobre la página')+'?.disabled===false')
    js(field('Texto sobre la página')+'.focus()');QTest.keyClick(target,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);QTest.keyClicks(target,'ITEM-900');QTest.keyClick(target,Qt.Key.Key_Return,Qt.KeyboardModifier.ControlModifier);wait('!document.querySelector(".inline-text-editor")')
    click('Editar en página: ITEM-900');wait(field('Texto sobre la página')+'?.disabled===false');assert not js('[...document.querySelectorAll("button")].find(e=>e.textContent==="Seleccionar varios bloques").disabled');click('Editar párrafo');wait(field('Párrafo sobre la página')+'?.disabled===false');assert not js(field('Añadir páginas automáticamente')+'.disabled');assert js('document.querySelector(".inline-paragraph-editor").innerText.includes("Se conservan las etiquetas")')
    js(field('Párrafo sobre la página')+'.focus()');QTest.keyClick(target,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);QTest.keyClicks(target,'ITEM-901');QTest.keyClick(target,Qt.Key.Key_Return,Qt.KeyboardModifier.ControlModifier);wait('!document.querySelector(".inline-paragraph-editor")')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty')
    with f.open(output) as d:
        _,after=native_model(d,0,d[0].rect,context=True);assert any(r['text']=='ITEM-901' for r in after);assert snapshot(d,0)==tag_state
        assert not (Counter(stable_key(r) for r in before if r['text']!='ITEM-100')-Counter(stable_key(r) for r in after))
    assert original.read_bytes()==base
    print('PASS: actual Qt selects/caret-edits a dense 240-fragment tagged page with existing metric-box overlap; edits its single native paragraph; allows verified tagged paragraph selection/pagination; native save preserves every other text placement/style and the complete tag graph/marked-content scopes, with source bytes untouched.')
except Exception:
    print(js('[...document.querySelectorAll(".banner.error,.inline-text-status")].map(e=>e.textContent)'));raise
finally:window.allow_close=True;window.close();app.processEvents()
