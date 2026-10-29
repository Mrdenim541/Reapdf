"""Qt-owned application window. No installed Chrome/Edge is required."""
from pathlib import Path
import json
import sys
from urllib.parse import urlsplit


def local_origin(url):
    parsed=urlsplit(url)
    if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port or parsed.username or parsed.password:
        raise ValueError('La ventana requiere el servidor local de Reapdf.')
    return f'http://127.0.0.1:{parsed.port}'


def create_window(url,initial_file=None):
    from PySide6.QtCore import QUrl,QObject,Slot,QFile,QIODevice,QTimer
    from PySide6.QtGui import QAction,QKeySequence
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWidgets import QMainWindow,QFileDialog,QMessageBox
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineScript
    origin=local_origin(url)

    class Bridge(QObject):
        @Slot(str,str,str,bool,result=str)
        def saveFile(self,encoded,name,key,save_as):
            conflict=False
            try:
                try:from .native_save import atomic_save,file_digest
                except ImportError:from native_save import atomic_save,file_digest
                name=Path(name).name;extension=Path(name).suffix.lower()
                if extension not in {'.pdf','.reapdf'} or len(name)>255 or len(key)>200:raise ValueError('Formato de guardado no admitido.')
                window=self.parent();identity=(key,extension);previous=window.save_targets.get(identity)
                path=None if save_as or not previous else previous[0]
                if path and path.exists() and file_digest(path)!=previous[1]:
                    conflict=True
                    QMessageBox.information(window,'Archivo modificado','El archivo cambió fuera de Reapdf. Elige un destino y revisa si deseas reemplazarlo.');path=None
                if path is None:
                    selected,_=QFileDialog.getSaveFileName(window,'Guardar archivo',name,options=QFileDialog.Option.DontConfirmOverwrite)
                    if not selected:return json.dumps({'status':'cancelled','conflict':conflict})
                    path=Path(selected)
                    if path.suffix.lower()!=extension:path=Path(str(path)+extension)
                    if path.exists() and QMessageBox.question(window,'Reemplazar archivo',f'¿Reemplazar {path.name}?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return json.dumps({'status':'cancelled','conflict':conflict})
                digest=atomic_save(path,encoded)
                window.save_targets[identity]=(path,digest);window.unfinished_save=False
                return json.dumps({'status':'saved','name':path.name})
            except Exception as exc:return json.dumps({'status':'error','message':str(exc)})

        @Slot(str,result=str)
        def printPdf(self,encoded):
            try:
                try:from .native_print import print_pdf
                except ImportError:from native_print import print_pdf
                return print_pdf(encoded,self.parent())
            except Exception as exc:return 'error:'+str(exc)

    class Page(QWebEnginePage):
        def javaScriptConfirm(self,security_origin,message):
            return QMessageBox.question(self.view_window,'Reapdf',message,QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes

        def acceptNavigationRequest(self,target,kind,main):
            value=target.toString()
            return value==origin or value.startswith(origin+'/') or value.startswith('blob:'+origin+'/') or value=='about:blank'

    class Window(QMainWindow):
        def __init__(self):
            super().__init__();self.allow_close=False;self.checking_close=False;self.unfinished_save=False;self.save_targets={}
            self.setWindowTitle('Reapdf');self.resize(1320,900)
            self.view=QWebEngineView(self)
            self.profile=QWebEngineProfile(self) # Off-the-record profile, owned by this window.
            self.page=Page(self.profile,self.view);self.page.view_window=self;self.view.setPage(self.page)
            self.channel=QWebChannel(self.page);self.bridge=Bridge(self)
            self.channel.registerObject('reapdf',self.bridge);self.page.setWebChannel(self.channel)
            resource=QFile(':/qtwebchannel/qwebchannel.js')
            if not resource.open(QIODevice.OpenModeFlag.ReadOnly):raise RuntimeError('No se pudo cargar la conexión de escritorio.')
            script=QWebEngineScript();script.setName('Reapdf desktop')
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setSourceCode(bytes(resource.readAll()).decode()+"\nwindow.reapdfDesktop=new Promise(resolve=>new QWebChannel(qt.webChannelTransport,c=>resolve(c.objects.reapdf))); ")
            self.page.scripts().insert(script);resource.close()
            self.setCentralWidget(self.view)
            menu=self.menuBar().addMenu('Archivo')
            self.open_action=QAction('Abrir PDF…',self);self.open_action.setShortcut(QKeySequence.StandardKey.Open)
            self.open_action.triggered.connect(self.open_pdf);menu.addAction(self.open_action)
            self.save_action=QAction('Guardar PDF',self);self.save_action.setShortcut(QKeySequence.StandardKey.Save)
            self.save_action.triggered.connect(lambda:self.page.runJavaScript('window.dispatchEvent(new Event("reapdf-save"))'));menu.addAction(self.save_action)
            self.save_as_action=QAction('Guardar PDF como…',self);self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
            self.save_as_action.triggered.connect(lambda:self.page.runJavaScript('window.dispatchEvent(new Event("reapdf-save-as"))'));menu.addAction(self.save_as_action)
            self.print_action=QAction('Imprimir…',self);self.print_action.setShortcut(QKeySequence.StandardKey.Print)
            self.print_action.triggered.connect(lambda:self.page.runJavaScript('window.dispatchEvent(new Event("reapdf-print"))'));menu.addAction(self.print_action)
            close=menu.addAction('Cerrar');close.triggered.connect(self.close)
            self.profile.downloadRequested.connect(self.download)
            self.pending_file=initial_file;self.external_files=[];self.probing_file=False;self.opening_file=False;self.initial_attempts=0;self.initial_timer=QTimer(self)
            self.initial_timer.setInterval(100);self.initial_timer.timeout.connect(self.try_initial_file)
            if initial_file:self.initial_timer.start()
            self.view.setUrl(QUrl(url))

        def try_initial_file(self):
            if self.probing_file or self.opening_file:return
            self.probing_file=True
            self.initial_attempts+=1
            if self.allow_close or self.initial_attempts>100:
                self.initial_timer.stop()
                if not self.allow_close:QMessageBox.warning(self,'Abrir PDF','La aplicación no terminó de cargar. Abre el archivo desde el menú.')
                return
            def ready(found):
                self.probing_file=False
                if found=='busy':self.initial_attempts=0;return
                if found=='ready':
                    file=self.pending_file or (self.external_files.pop(0) if self.external_files else None)
                    self.pending_file=None;self.initial_attempts=0
                    if not self.external_files:self.initial_timer.stop()
                    if file:self.open_path(file)
            self.page.runJavaScript('window.__reapdfCloseState?.busy || document.querySelector("dialog[open]")?"busy":[...document.querySelectorAll("input")].some(e=>e.getAttribute("aria-label")==="Archivo PDF")?"ready":"loading"',ready)

        def enqueue_file(self,file):
            if self.allow_close:raise ValueError('La ventana se está cerrando; vuelve a abrir el archivo.')
            if file:
                if len(self.external_files)>=10:raise ValueError('Hay demasiados archivos pendientes.')
                self.external_files.append(file);self.initial_attempts=0;self.initial_timer.start()
            if self.isMinimized():self.showNormal()
            self.raise_();self.activateWindow()

        def open_pdf(self):
            def checked(state):
                if state:
                    QMessageBox.information(self,'Reapdf','Termina o cancela la operación o edición actual antes de abrir otro archivo.');return
                self.choose_pdf()
            self.page.runJavaScript('!!(window.__reapdfCloseState?.busy || document.querySelector("dialog[open]"))',checked)

        def choose_pdf(self):
            path,_=QFileDialog.getOpenFileName(self,'Abrir PDF','','Documentos PDF (*.pdf)')
            if not path:return
            self.open_path(path)

        def open_path(self,path):
            try:
                import base64
                file=Path(path)
                if file.stat().st_size>60*1024*1024:raise ValueError('El PDF supera 60 MB.')
                data=base64.b64encode(file.read_bytes()).decode()
                self.opening_file=True
                def opened(ready):
                    self.opening_file=False
                    if not ready:QMessageBox.information(self,'Reapdf','Espera a que termine de cargar la aplicación.')
                self.page.runJavaScript('(()=>{const input=[...document.querySelectorAll("input")].find(e=>e.getAttribute("aria-label")==="Archivo PDF");if(!input)return false;const dt=new DataTransfer();dt.items.add(new File([Uint8Array.from(atob('+json.dumps(data)+'),c=>c.charCodeAt(0))],'+json.dumps(file.name)+',{type:"application/pdf"}));input.files=dt.files;input.dispatchEvent(new Event("change",{bubbles:true}));return true;})()',opened)
            except (OSError,ValueError) as exc:QMessageBox.warning(self,'No se pudo abrir',str(exc))

        def download(self,request):
            name=Path(request.suggestedFileName()).name or 'documento.pdf'
            if Path(name).suffix.lower() in {'.pdf','.reapdf'}:
                self.unfinished_save=True
                def finished():
                    if request.state()==type(request).DownloadState.DownloadCompleted:self.unfinished_save=False
                request.isFinishedChanged.connect(finished)
            path,_=QFileDialog.getSaveFileName(self,'Guardar archivo',name)
            if not path:request.cancel();return
            target=Path(path);request.setDownloadDirectory(str(target.parent));request.setDownloadFileName(target.name);request.accept()

        def closeEvent(self,event):
            if self.allow_close:event.accept();return
            event.ignore()
            if self.checking_close:return
            self.checking_close=True
            def checked(state):
                self.checking_close=False
                try:
                    state=json.loads(state)
                    if not isinstance(state,dict) or type(state.get('dirty')) is not bool or type(state.get('busy')) is not bool:raise ValueError()
                except (ValueError,TypeError):state={'dirty':True,'busy':False}
                if state and state.get('busy'):
                    QMessageBox.information(self,'Reapdf','Espera a que termine la operación antes de cerrar.');return
                if state and (state.get('dirty') or self.unfinished_save):
                    choice=QMessageBox.question(self,'Cambios pendientes','Hay cambios sin guardar o contenido sin aplicar. ¿Cerrar y descartarlos?',QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)
                    if choice!=QMessageBox.StandardButton.Discard:return
                self.allow_close=True;self.close()
            self.page.runJavaScript('JSON.stringify({dirty:!!(window.__reapdfCloseState?.dirty || document.querySelector("dialog[open]")),busy:!!window.__reapdfCloseState?.busy})',checked)

    return Window()


def main():
    from PySide6.QtCore import QCoreApplication,Qt
    from PySide6.QtWidgets import QApplication
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app=QApplication(sys.argv[:1]);app.setApplicationName('Reapdf');app.setOrganizationName('Reapdf')
    try:from .single_instance import SingleInstance
    except ImportError:from single_instance import SingleInstance
    instance=SingleInstance(sys.argv[2] if len(sys.argv)>2 else None)
    if not instance.owner:return 0
    try:
        window=create_window(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None);window.show()
        instance.set_handler(window.enqueue_file)
        return app.exec()
    finally:instance.close()


if __name__=='__main__':sys.exit(main())
