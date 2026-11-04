"""A slow frontend must not lose its initial PDF or block the event loop on timeout."""
import tempfile,time,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from PySide6.QtCore import QCoreApplication,Qt,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from portable.native_window import create_window

class SlowPage(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/':time.sleep(12)
        body=b'<input aria-label="Archivo PDF" type="file"><script>window.__reapdfCloseState={busy:false,dirty:false};document.querySelector("input").onchange=e=>document.body.dataset.uploaded=e.target.files[0].name;</script>'
        self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(body)
    def log_message(self,*a):pass

server=ThreadingHTTPServer(('127.0.0.1',0),SlowPage);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts);app=QApplication([])
root=Path(tempfile.mkdtemp(prefix='reapdf-initial-wait-'));file=root/'Initial.pdf';file.write_bytes(b'%PDF-test-upload')
window=create_window(f'http://127.0.0.1:{server.server_port}/',str(file));window.show()
def js(script):
    values=[];loop=QEventLoop();window.page.runJavaScript(script,lambda value:(values.append(value),loop.quit()));QTimer.singleShot(3000,loop.quit);loop.exec();return values[0] if values else None
try:
    deadline=time.monotonic()+28
    while js('document.body?.dataset.uploaded')!='Initial.pdf':
        assert time.monotonic()<deadline,'Slow startup lost its initial file'
        assert not hasattr(window,'initial_warning'),'No premature ten-second warning'
        QTest.qWait(100)
    while window.opening_file or window.probing_file:QTest.qWait(50)
    window.pending_file=str(file);window.initial_deadline=0;window.try_initial_file()
    assert not window.probing_file and not window.initial_timer.isActive()
    assert js('2+2')==4,'The timeout warning must not block Qt JavaScript callbacks'
    window.initial_warning.close();window.enqueue_file(str(file));assert window.initial_deadline>time.monotonic() and window.initial_timer.isActive()
    deadline=time.monotonic()+5
    while window.external_files or window.opening_file or window.pending_file:
        assert time.monotonic()<deadline,'Retry remained locked after timeout';QTest.qWait(100)
    print('PASS: slow frontend (>10s) opens its initial file; timed-out startup warning is asynchronous, readiness lock clears and queued retry works.')
finally:
    window.allow_close=True;window.close();app.processEvents();server.shutdown();server.server_close();thread.join(timeout=3)
