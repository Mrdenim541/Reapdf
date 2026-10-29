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
    from PySide6.QtCore import QUrl
    from PySide6.QtWidgets import QMainWindow,QFileDialog,QMessageBox
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile
    origin=local_origin(url)

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
            self.setCentralWidget(self.view)
            self.profile.downloadRequested.connect(self.download)
            self.view.setUrl(QUrl(url))

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
