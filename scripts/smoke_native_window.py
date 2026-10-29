"""Exercise the actual Qt WebEngine host against the running local application."""
import base64,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtCore import QEventLoop,QTimer,QCoreApplication,Qt,QUrl
from PySide6.QtTest import QTest
from PySide6.QtPrintSupport import QPrintDialog,QPrinter
from PySide6.QtWidgets import QDialog
from portable.native_window import create_window

QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([])
window=create_window('http://127.0.0.1:8000');window.show()
QMessageBox.question=lambda *args:QMessageBox.StandardButton.Yes
root=Path(tempfile.mkdtemp(prefix='reapdf-native-check-'));output=root/'export.pdf';printed=root/'printed.pdf'

def evaluate(script):
    result=[];loop=QEventLoop()
    window.page.runJavaScript(script,lambda value:(result.append(value),loop.quit()))
    QTimer.singleShot(5000,loop.quit);loop.exec()
    assert result,'JavaScript callback timed out'
    return result[0]

def wait(script):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        if evaluate(script):return
        QTest.qWait(100)
    raise AssertionError(script)

try:
    wait('!![...document.querySelectorAll("input")].find(e=>e.getAttribute("aria-label")==="Archivo PDF")')
    print('STAGE: application loaded',flush=True)
    assert window.windowTitle()=='Reapdf'
    assert window.bridge.printPdf('invalid').startswith('error:')
    with f.open() as oversized:
        oversized.new_page(width=6001,height=6001)
        assert window.bridge.printPdf(base64.b64encode(oversized.tobytes()).decode()).startswith('error:')
    assert not window.page.acceptNavigationRequest(QUrl('https://example.com'),None,True)
    with f.open() as d:
        p=d.new_page();p.insert_text((45,100),'NATIVE PDF CHECK')
        p=d.new_page();p.draw_rect(f.Rect(30,30,300,300),color=(1,0,0),fill=(1,0,0))
        d.save(root/'native.pdf')
    QFileDialog.getOpenFileName=lambda *args,**kwargs:(str(root/'native.pdf'),'')
    window.open_action.trigger()
    wait('document.body.innerText.includes("native.pdf") && !!document.querySelector(".text-layer")')
    wait('[...document.images].some(i=>i.alt==="Página 1 del documento" && i.complete && i.naturalWidth>0)')
    print('STAGE: PDF loaded',flush=True)
    def select_printer(dialog):
        printer=dialog.printer();printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat);printer.setOutputFileName(str(printed));printer.setFromTo(2,2)
        return QDialog.DialogCode.Accepted
    QPrintDialog.exec=select_printer
    window.print_action.trigger()
    wait('document.body.innerText.includes("Documento enviado a impresión.")')
    assert printed.exists()
    with f.open(printed) as d:
        assert len(d)==1
        pix=d[0].get_pixmap();pixels=pix.samples
        assert sum(pixels[i]>200 and pixels[i+1]<100 and pixels[i+2]<100 for i in range(0,len(pixels),pix.n))>100
    QPrintDialog.exec=lambda *args:QDialog.DialogCode.Rejected
    window.print_action.trigger();wait('document.body.innerText.includes("Impresión cancelada.")')
    print('STAGE: page range printed and cancellation checked',flush=True)
    QFileDialog.getSaveFileName=lambda *args,**kwargs:(str(output),'')
    evaluate('(()=>{[...document.querySelectorAll("button")].find(b=>b.textContent.trim()==="Exportar copia").click();return true;})()')
    deadline=time.monotonic()+30
    while not output.exists() and time.monotonic()<deadline:QTest.qWait(100)
    assert output.exists()
    print('STAGE: download created',flush=True)
    # Downloads finish asynchronously after the destination file is created.
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        try:
            with f.open(output) as d:assert 'NATIVE PDF CHECK' in d[0].get_text()
            break
        except (RuntimeError,AssertionError):QTest.qWait(100)
    else:raise AssertionError('Incomplete PDF download')
    calls=[]
    QMessageBox.information=lambda *args:calls.append('busy')
    evaluate('window.__reapdfCloseState={dirty:false,busy:true}')
    window.close()
    deadline=time.monotonic()+5
    while not calls and time.monotonic()<deadline:QTest.qWait(100)
    assert window.isVisible() and calls==['busy']
    calls.clear()
    QMessageBox.question=lambda *args:(calls.append('cancel') or QMessageBox.StandardButton.Cancel)
    QTest.qWait(500)
    QFileDialog.getSaveFileName=lambda *args,**kwargs:('','')
    evaluate('(()=>{[...document.querySelectorAll("button")].find(b=>b.textContent.trim()==="Exportar copia").click();return true;})()')
    wait('document.body.innerText.includes("Guardado cancelado")')
    evaluate('window.__reapdfCloseState={dirty:true,busy:false}')
    window.close()
    deadline=time.monotonic()+5
    while not calls and time.monotonic()<deadline:QTest.qWait(100)
    assert window.isVisible() and calls==['cancel'],(window.isVisible(),calls)
    QMessageBox.question=lambda *args:QMessageBox.StandardButton.Discard
    window.close()
    deadline=time.monotonic()+5
    while window.isVisible() and time.monotonic()<deadline:QTest.qWait(100)
    assert not window.isVisible()
    print('PASS: Qt window, PDF upload/render, native download, busy guard, cancelled download protection, cancelled close and explicit discard.')
finally:
    window.allow_close=True;window.close();app.processEvents()
