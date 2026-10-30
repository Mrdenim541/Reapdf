"""Edit a synthetic Type3 transformed Form through the actual Qt UI and native save."""
import hashlib,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_type3_fonts import type3_pdf,glyphs

root=Path(tempfile.mkdtemp(prefix='reapdf-fonts-qt-'));original=root/'Original.pdf';output=root/'Editado.pdf';original.write_bytes(type3_pdf(90,'1 .2 .3 1',True));digest=hashlib.sha256(original.read_bytes()).hexdigest()
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
    click('Editar en página: ABC ABC');wait(field('Texto sobre la página')+'?.disabled===false')
    assert js(field('Fuente de edición directa')+'.disabled')
    js('(()=>{const e='+field('Texto sobre la página')+';Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,"value").set.call(e,"CBA AB");e.dispatchEvent(new Event("input",{bubbles:true}));})()')
    click('Aplicar');wait('!'+field('Texto sobre la página'))
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    with f.open(original) as a,f.open(output) as b:
        assert 'CBA AB' in b[0].get_text() and b[0].get_text().count('ABC ABC')==1
        assert glyphs(a)==glyphs(b)
        assert a[0].rotation==b[0].rotation and a[0].cropbox==b[0].cropbox and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        left={v[3]:a.extract_font(v[0])[3] for v in a[0].get_fonts()};right={v[3]:b.extract_font(v[0])[3] for v in b[0].get_fonts()};assert left==right
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    print('PASS: actual Qt window opened a sheared shared Type3 Form, edited original text on page and saved atomically; original file/glyph programs/rotation/crop/other occurrence and page preserved.')
finally:window.allow_close=True;window.close();app.processEvents()
