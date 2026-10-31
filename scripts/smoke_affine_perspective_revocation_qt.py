"""Own Qt window: affine edit/save, perspective review and local revocation UI."""
import base64,json,tempfile,time
from pathlib import Path
import pymupdf as f
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
from tests.test_affine_perspective_revocation import affine,perspective_table,pki
from tests.test_table_regions import source
from backend.digital_signatures import sign_document
root=Path(tempfile.mkdtemp(prefix='reapdf-affine-qt-'));original=root/'Affine.pdf';original.write_bytes(affine());output=root/'Edited.pdf';table,quad=perspective_table();tablefile=root/'Perspective.pdf';tablefile.write_bytes(table)
identity,trust,proof=pki();signed=root/'Signed.pdf';signed.write_bytes(sign_document(source(),[],identity,'',{}))
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


def edit(label,value,select=False):
    expr=field(label);wait(expr+'?.disabled===false');prototype='HTMLSelectElement' if select else 'HTMLTextAreaElement' if js(expr+'.tagName')=='TEXTAREA' else 'HTMLInputElement'
    js('(()=>{const e='+expr+';Object.getOwnPropertyDescriptor('+prototype+'.prototype,"value").set.call(e,'+json.dumps(value)+');e.dispatchEvent(new Event("'+('change' if select else 'input')+'",{bubbles:true}));})()');QTest.qWait(60)


def tool(area,label):
    click(area);wait(field(label)+'?.disabled===false');js('(()=>{const b='+field(label)+';b.closest("details").open=true;b.click();})()')


def native_save(path):
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');window.save_action.trigger();wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty');assert path.exists()


def native_open(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger();wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')


def upload(label,name,data):
    wait('!!'+field(label))
    js('(()=>{const e='+field(label)+';const d=new DataTransfer();d.items.add(new File([Uint8Array.from(atob('+json.dumps(base64.b64encode(data).decode())+'),c=>c.charCodeAt(0))],'+json.dumps(name)+'));e.files=d.files;e.dispatchEvent(new Event("change",{bubbles:true}));})()')


try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Affine.pdf")');tool('Editar','Editar texto');click('Editar en página: ALPHA BETA GAMMA');wait(field('Texto sobre la página')+'?.disabled===false');click('Distribuir en líneas');edit('Ancho de reflujo afín','110');edit('Alto de reflujo afín','130');edit('Texto sobre la página','ALPHA BETA\nGAMMA ALPHA');click('Aplicar');wait('!'+field('Texto sobre la página'));native_save(output)
    with f.open(output) as d:assert 'GAMMA ALPHA' in d[0].get_text()
    native_open(tablefile);tool('Convertir y OCR','Extraer tabla por región');js('[...document.querySelectorAll("summary")].find(e=>e.textContent==="Área en puntos PDF").click()')
    for label,value in [('X','40'),('Y','50'),('Ancho','470'),('Alto','220')]:edit(label+' de tabla',value)
    js(field('Corregir perspectiva de tabla')+'.click()');js('[...document.querySelectorAll("summary")].find(e=>e.textContent==="Opciones de reconocimiento").click()');edit('Idioma OCR de tabla','eng',True);edit('Resolución OCR de tabla','300',True)
    for i,(x,y) in enumerate(quad):
        values=json.loads(js('JSON.stringify((()=>{const s='+field('Seleccionar tabla y separadores')+';const r=s.getBoundingClientRect(),c=s.querySelector('+json.dumps('[data-corner="'+str(i)+'"]')+').getBoundingClientRect();return [c.x+c.width/2,c.y+c.height/2,r.x+'+str(x)+'/540*r.width,r.y+'+str(y)+'/325*r.height];})())'))
        target=window.view.focusProxy() or window.view
        QTest.mouseMove(target,QPoint(round(values[0]),round(values[1])));QTest.mousePress(target,Qt.MouseButton.LeftButton,pos=QPoint(round(values[0]),round(values[1])));QTest.mouseMove(target,QPoint(round(values[2]),round(values[3])),100);QTest.mouseRelease(target,Qt.MouseButton.LeftButton,pos=QPoint(round(values[2]),round(values[3])));QTest.qWait(100)
    click('Extraer y revisar');wait(field('Celda 2, 1')+'?.value==="BOLT"');assert js('!!document.querySelector('+json.dumps('img[alt="Tabla rectificada para revisar"]')+')');edit('Celda 2, 1','REVIEWED');click('Cerrar')
    native_open(signed);QTest.qWait(300);tool('Formularios y firmas','Verificar firmas digitales');wait('!!document.querySelector("dialog[open]")');upload('Certificados de confianza para verificar','Trust.pem',trust);js('[...document.querySelectorAll("summary")].find(e=>e.textContent==="Revocación con evidencias locales (opcional)").click()');upload('Evidencias locales de revocación','Proof.crl',proof);click('Comprobar firmas');wait('document.body.innerText.includes("Cadena y revocación aceptadas con evidencia local")')
    print('PASS: own Qt Linux window affine reflow and atomic PDF save; perspective corner controls/OCR and corrected cell review; explicit trust and local CRL verification. Windows not tested.')
finally:
    window.allow_close=True;window.close();QTest.qWait(200)
