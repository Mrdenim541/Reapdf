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


def create_window(url):
    from PySide6.QtCore import QUrl,QObject,Slot,QFile,QIODevice
    from PySide6.QtGui import QAction,QKeySequence
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWidgets import QMainWindow,QFileDialog,QMessageBox
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineScript
    origin=local_origin(url)

    class Bridge(QObject):
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
            super().__init__();self.allow_close=False;self.checking_close=False;self.unfinished_save=False
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
            self.print_action=QAction('Imprimir…',self);self.print_action.setShortcut(QKeySequence.StandardKey.Print)
            self.print_action.triggered.connect(lambda:self.page.runJavaScript('window.dispatchEvent(new Event("reapdf-print"))'));menu.addAction(self.print_action)
            close=menu.addAction('Cerrar');close.triggered.connect(self.close)
            self.profile.downloadRequested.connect(self.download)
            self.view.setUrl(QUrl(url))

        def open_pdf(self):
            def checked(state):
                if state:
                    QMessageBox.information(self,'Reapdf','Termina o cancela la operación o edición actual antes de abrir otro archivo.');return
                self.choose_pdf()
            self.page.runJavaScript('!!(window.__reapdfCloseState?.busy || document.querySelector("dialog[open]"))',checked)

        def choose_pdf(self):
            path,_=QFileDialog.getOpenFileName(self,'Abrir PDF','','Documentos PDF (*.pdf)')
            if not path:return
            try:
                import base64
                file=Path(path)
                if file.stat().st_size>60*1024*1024:raise ValueError('El PDF supera 60 MB.')
                data=base64.b64encode(file.read_bytes()).decode()
                self.page.runJavaScript('(()=>{const input=[...document.querySelectorAll("input")].find(e=>e.getAttribute("aria-label")==="Archivo PDF");if(!input)return false;const dt=new DataTransfer();dt.items.add(new File([Uint8Array.from(atob('+json.dumps(data)+'),c=>c.charCodeAt(0))],'+json.dumps(file.name)+',{type:"application/pdf"}));input.files=dt.files;input.dispatchEvent(new Event("change",{bubbles:true}));return true;})()',lambda ready:None if ready else QMessageBox.information(self,'Reapdf','Espera a que termine de cargar la aplicación.'))
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
    window=create_window(sys.argv[1]);window.show()
    return app.exec()


if __name__=='__main__':sys.exit(main())
