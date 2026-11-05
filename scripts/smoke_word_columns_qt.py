"""Import/review/save a multi-column DOCX with bookmarks in the actual Qt app."""
import base64,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from scripts.create_word_columns_sample import create
root=Path(tempfile.mkdtemp(prefix='reapdf-columns-qt-'));word=root/'Columns.docx';word.write_bytes(create());original=word.read_bytes();output=root/'Columns.pdf'
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window('http://127.0.0.1:8000');window.resize(1500,1100);window.show()
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
try:
    wait('!!document.querySelector(".file-menu")');js('document.querySelector(".file-menu").open=true');click('Crear PDF desde Word');wait('!!'+field('Archivo Word para convertir'))
    encoded=base64.b64encode(original).decode()
    js('(()=>{const raw=atob('+json.dumps(encoded)+');const bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));const data=new DataTransfer();data.items.add(new File([bytes],"Columns.docx",{type:"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}));const e='+field('Archivo Word para convertir')+';e.files=data.files;e.dispatchEvent(new Event("change",{bubbles:true}));})()')
    click('Convertir y revisar Word');wait('!!'+field('Página de Word importado'));wait('document.body.innerText.includes("Columnas por sección: 2")&&document.body.innerText.includes("enlaces internos a marcadores")')
    pages=int(js(field('Página de Word importado')+'.options.length'));assert pages>=2
    for index in range(pages):
        js('(()=>{const e='+field('Página de Word importado')+';e.value='+json.dumps(str(index))+';e.dispatchEvent(new Event("change",{bubbles:true}));})()')
        label='Revisé Word página '+str(index+1);wait(field(label)+'?.disabled===false');js(field(label)+'.click()')
    js(field('Aceptar diferencias de importación Word')+'.click()');click('Abrir PDF convertido');wait('!document.querySelector(".advanced-dialog[open]")')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_as_action.trigger();wait('document.body.innerText.includes("PDF guardado.")&&!window.__reapdfCloseState.dirty')
    with f.open(output) as d:
        assert len(d)==pages;text=''.join(page.get_text() for page in d)
        for i in range(45):assert text.count(f'ITEM{i:03d}')==1
        destination=next(page.number for page in d if page.search_for('DESTINATIONWORD'))
        links=[l for page in d for l in page.get_links() if l['kind']==f.LINK_GOTO];assert len(links)==1 and links[0]['page']==destination
        assert len({round(r.x0) for r in d[0].search_for('ITEM')})==2
        assert all(len([g for g in page.get_drawings() if g['rect'].height>100 and g['rect'].width<1])==1 for page in d)
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(output),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes("Columns.pdf")')
    assert word.read_bytes()==original
    print('PASS: actual Qt imports and reviews all column pages, shows column/link summary and limits, opens, saves through native dialog and reopens; saved PDF retains ordered selectable text, separator lines and native internal bookmark link, with source DOCX unchanged.')
except Exception:
    print(js('document.body.innerText'));raise
finally:window.allow_close=True;window.close();app.processEvents()
