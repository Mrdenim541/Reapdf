"""Select Type3 text with actual Qt mouse input, edit, save and reopen generated PDFs."""
import json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_type3_fonts import glyphs
from tests.test_type3_extended import matrix_source,image_source

root=Path(tempfile.mkdtemp(prefix='reapdf-type3-qt-'))
cases=[('Matrix',matrix_source('[.002 0 0 .001 .05 .05]',90,True)),('Colour',image_source(False)),('Mask',image_source(True,True,270))]
for name,data in cases:(root/(name+'.pdf')).write_bytes(data)
original=root/'Matrix.pdf'
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
    for name,base in cases:
        original=root/(name+'.pdf');output=root/(name+'-edited.pdf')
        if name!='Matrix':
            QFileDialog.getOpenFileName=lambda *a,**kw:(str(original),'');window.open_action.trigger()
        wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(original.name)+')')
        click('Editar');wait('!!'+field('Editar texto'))
        js('(()=>{const b='+field('Editar texto')+';b.closest("details").open=true;b.click();})()')
        expr='[...document.querySelectorAll("button,[role=button]")].find(e=>e.getAttribute("aria-label")==="Editar en página: ABC ABC")'
        wait('!!'+expr)
        js(expr+'.scrollIntoView({block:"center",inline:"center"})');QTest.qWait(250)
        point=json.loads(js('JSON.stringify((()=>{const r='+expr+'.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})())'))
        QTest.mouseClick(window.view.focusProxy() or window.view,Qt.MouseButton.LeftButton,pos=QPoint(round(point['x']),round(point['y'])))
        wait(field('Texto sobre la página')+'?.disabled===false')
        js('(()=>{const e='+field('Texto sobre la página')+';Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,"value").set.call(e,"CBA AB");e.dispatchEvent(new Event("input",{bubbles:true}));})()')
        click('Aplicar');wait('!'+field('Texto sobre la página'))
        QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger()
        wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
        assert output.exists() and original.read_bytes()==base
        with f.open(original) as a,f.open(output) as b:
            assert 'CBA AB' in b[0].get_text() and glyphs(a)==glyphs(b)
            assert a[0].rotation==b[0].rotation and a[0].cropbox==b[0].cropbox
            if len(a)>1:assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
            images=lambda d:{d.xref_stream_raw(x) for x in range(1,d.xref_length()) if d.xref_get_key(x,'Subtype')[1]=='/Image'}
            assert images(a)==images(b)
        QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger()
        wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(output.name)+')')
        wait('document.querySelector(".text-layer")?.textContent.includes("CBA AB")')
    print('PASS: own Qt window, physical mouse selects original Type3 text, edits nonstandard font matrix/colour bitmap/mask bitmap, native atomic save and reopen; original files, glyphs/images and other pages preserved.')
finally:window.allow_close=True;window.close();app.processEvents()
