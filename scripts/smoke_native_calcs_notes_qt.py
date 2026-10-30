"""Exercise native PDF calculations and actual Word footnotes through the Qt app."""
import hashlib,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_native_calculations import source
from tests.test_docx_notes import source as note_source,p as paragraph,reference
from backend.docx_import import import_docx
import base64

root=Path(tempfile.mkdtemp(prefix='reapdf-native-notes-qt-'));original=root/'Original.pdf';output=root/'Editado.pdf';original.write_bytes(source());digest=hashlib.sha256(original.read_bytes()).hexdigest()
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


def edit(label,value):
    wait(field(label)+'?.disabled===false')
    js('(()=>{const e='+field(label)+';Object.getOwnPropertyDescriptor((e.tagName==="TEXTAREA"?HTMLTextAreaElement:HTMLInputElement).prototype,"value").set.call(e,'+json.dumps(value)+');e.dispatchEvent(new Event("input",{bubbles:true}));})()')
    QTest.qWait(50)


def tool(label):
    wait(field(label)+'?.disabled===false');js('(()=>{const b='+field(label)+';b.closest("details").open=true;b.click();})()')


def file_ready(path):
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        if path.exists() and path.stat().st_size:return
        QTest.qWait(100)
    raise AssertionError('Native download did not finish: '+str(path))


try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Original.pdf")')
    click('Formularios y firmas');tool('Rellenar formulario');edit('Valor del formulario','7.25')
    click('Aplicar formulario');wait('!document.querySelector(".form-dialog[open]")')
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(output),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    with f.open(original) as a,f.open(output) as b:
        values={w.field_name:w.field_value for p in b for w in p.widgets() or []};assert values['Total']=='10' and values['Final']=='20' and '20,00' in b[1].get_text()
        old={w.field_name:a.xref_get_key(w.xref,'AA/C/JS') for p in a for w in p.widgets() or []};new={w.field_name:b.xref_get_key(w.xref,'AA/C/JS') for p in b for w in p.widgets() or []};assert old==new
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    word=root/'Notes.docx';word.write_bytes(note_source(body=paragraph('Texto anterior de prueba. '*140)+reference('footnote',1,'NEARBOUNDARY')+paragraph('Texto posterior de prueba. '*90)+reference('endnote',2,'FINALREFERENCE')));word_digest=hashlib.sha256(word.read_bytes()).hexdigest()
    js('document.querySelector(".file-menu").open=true');click('Crear PDF desde Word');wait('!!'+field('Archivo Word para convertir'))
    encoded=base64.b64encode(word.read_bytes()).decode()
    js('(()=>{const raw=atob('+json.dumps(encoded)+');const bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));const data=new DataTransfer();data.items.add(new File([bytes],"Notes.docx",{type:"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}));const input='+field('Archivo Word para convertir')+';input.files=data.files;input.dispatchEvent(new Event("change",{bubbles:true}));})()')
    click('Convertir y revisar Word');wait('!!'+field('Página de Word importado'))
    pages=int(js(field('Página de Word importado')+'.options.length'))
    for index in range(pages):
        js('(()=>{const e='+field('Página de Word importado')+';e.value='+json.dumps(str(index))+';e.dispatchEvent(new Event("change",{bubbles:true}));})()')
        label='Revisé Word página '+str(index+1);wait(field(label)+'?.disabled===false');js(field(label)+'.click()')
    js(field('Aceptar diferencias de importación Word')+'.click()');click('Abrir PDF convertido');wait('!document.querySelector(".advanced-dialog[open]")')
    notes_output=root/'Notes.pdf';QFileDialog.getSaveFileName=lambda *a,**kw:(str(notes_output),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty');file_ready(notes_output)
    with f.open(notes_output) as d:
        ref=next(p.number for p in d if p.search_for('NEARBOUNDARY'));note=next(p.number for p in d if p.search_for('FOOTNOTEALPHA'));assert ref==note
        assert any(p.search_for('ENDNOTEBETA') for p in d) and len([l for p in d for l in p.get_links() if l['kind']==f.LINK_GOTO])>=4
    assert hashlib.sha256(word.read_bytes()).hexdigest()==word_digest
    print('PASS: actual Qt app recalculated native PDF fields across pages and saved atomically with original actions/source preserved; imported and reviewed Word foot/endnotes, saved through native PDF dialog, verified same-page footnote/reference and return links with original Word unchanged.')
except Exception:
    print(js("document.body.innerText"));raise
finally:window.allow_close=True;window.close();app.processEvents()
