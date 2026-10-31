"""Native UI and cancelled-save replay against a generated cryptographic TSA.

The backend's transport is replaced only inside this test process. This is not
an Internet provider acceptance test and does not install a test hook in Reapdf.
"""
import os,json,time,tempfile,threading,socket,base64
from pathlib import Path
import uvicorn
from backend.app import app as web_app
from backend import timestamp_authority
from backend.digital_signatures import verify_signatures
from tests.signature_samples import document,identity
from tests.timestamp_samples import authority,transport,revocation
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from PySide6.QtTest import QTest
from portable.native_window import create_window
root=Path(tempfile.mkdtemp(prefix='reapdf-tsa-qt-'));source=root/'Original.pdf';base=document();source.write_bytes(base);tsa,tsa_root=authority();requests=[];timestamp_authority.exchange=transport(tsa,requests)
os.environ['REAPDF_DATA_DIR']=str(root/'state')
listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
server=uvicorn.Server(uvicorn.Config(web_app,host='127.0.0.1',port=port,log_level='warning'));thread=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=True);thread.start()
end=time.monotonic()+15
while not server.started:
    if time.monotonic()>end:raise AssertionError('Synthetic TSA UI backend did not start')
    time.sleep(.05)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([]);QMessageBox.question=lambda *a:QMessageBox.StandardButton.Yes
window=create_window(f'http://127.0.0.1:{port}',str(source));window.resize(1700,1150);window.show()
def js(script):
    values=[];loop=QEventLoop();window.page.runJavaScript('(()=>{try{return eval('+json.dumps(script)+');}catch(e){return {__error:String(e)};}})()',lambda value:(values.append(value),loop.quit()));QTimer.singleShot(5000,loop.quit);loop.exec()
    if not values:raise AssertionError('Qt did not respond')
    if isinstance(values[0],dict) and '__error' in values[0]:raise AssertionError(values[0]['__error'])
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
    QFileDialog.getSaveFileName=lambda *a,**kw:(str(path),'');window.save_as_action.trigger()
    wait('document.body.innerText.includes("PDF guardado.") && !window.__reapdfCloseState.dirty')
    assert path.exists()

def native_open(path):
    QFileDialog.getOpenFileName=lambda *a,**kw:(str(path),'');window.open_action.trigger()
    wait('document.querySelector(".document-bar")?.textContent.includes('+json.dumps(path.name)+')')

def upload(label,data,name):
    encoded=base64.b64encode(data).decode();js('(()=>{const input='+field(label)+';const dt=new DataTransfer();dt.items.add(new File([Uint8Array.from(atob('+json.dumps(encoded)+'),c=>c.charCodeAt(0))],'+json.dumps(name)+'));input.files=dt.files;input.dispatchEvent(new Event("change",{bubbles:true}));})()')

try:
    wait('document.querySelector(".document-bar")?.textContent.includes("Original.pdf") && !!document.querySelector(".text-layer")')
    tool('Formularios y firmas','Sellar documento');wait('!!'+field('URL de autoridad de tiempo'));edit('URL de autoridad de tiempo','https://tsa.synthetic.invalid/rfc3161');upload('Confianza de la autoridad de tiempo',tsa_root,'tsa.pem');click('Revisar copia para sellar');assert not requests
    QFileDialog.getSaveFileName=lambda *a,**kw:('','');click('Sellar y guardar copia');wait('document.body.innerText.includes("Guardado cancelado.")');assert len(requests)==2
    target=root/'Sealed.pdf';QFileDialog.getSaveFileName=lambda *a,**kw:(str(target),'');click('Guardar copia preparada');wait('document.body.innerText.includes("Copia comprobada y guardada.")');assert target.exists() and len(requests)==2
    assert target.read_bytes().startswith(source.read_bytes());row=verify_signatures(target.read_bytes(),[],tsa_root)['signatures'][0];assert row['type']=='document_timestamp' and row['timestamp']['time_accepted_offline']
    click('Cerrar');native_open(target);tool('Formularios y firmas','Verificar firmas digitales');upload('Certificados de confianza para verificar',tsa_root,'tsa.pem');js(field('Evidencias locales de revocación')+'.closest(\"details\").open=true');upload('Evidencias locales de revocación',revocation(),'tsa.crl');click('Comprobar firmas');wait('document.body.innerText.includes("Sello documental 1") && document.body.innerText.includes("revocación TSA vigentes")');click('Cerrar')
    native_open(source);tool('Formularios y firmas','Firmar con certificado');p12,signer_root,_=identity();upload('Certificado para firmar',p12,'identity.p12');edit('Contraseña del certificado digital','prueba');js(field('Añadir sello de tiempo de autoridad')+'.click()');wait('!!'+field('URL de autoridad de tiempo'));edit('URL de autoridad de tiempo','https://tsa.synthetic.invalid/rfc3161');upload('Confianza de la autoridad de tiempo',tsa_root,'tsa.pem');click('Revisar copia para firmar');assert len(requests)==2
    signed=root/'Signed.pdf';QFileDialog.getSaveFileName=lambda *a,**kw:(str(signed),'');click('Firmar y guardar copia');wait('document.body.innerText.includes("Copia comprobada y guardada.")');assert len(requests)==4 and signed.exists()
    checked=verify_signatures(signed.read_bytes(),[],tsa_root+signer_root)['signatures'][0];assert checked['chain_accepted'] and checked['timestamp']['time_accepted_offline']
    assert source.read_bytes()==base
    print('PASS: Qt document timestamp and P12 signature timestamp using generated TSA responses, review without requests, native cancel/retry with no repeat TSA call, atomic save/reopen and separate timestamp verification. No external provider was contacted.')
finally:
    window.allow_close=True;window.close();app.processEvents();server.should_exit=True;thread.join(timeout=8);listener.close()
