"""Real Qt child: UI readiness, activation handoff and failed load cleanup."""
import sys
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from portable.desktop import NativeDesktopWindow


class MissingPage(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_error(404)
    def log_message(self,*args):pass


first=NativeDesktopWindow(None,'http://127.0.0.1:8000')
try:
    assert first.wait_ready()=='ready'
    assert first.process.poll() is None
    second=NativeDesktopWindow(None,'http://127.0.0.1:8000')
    try:
        assert second.wait_ready()=='forwarded'
        assert second.process.wait(timeout=10)==0
        assert first.process.poll() is None
    finally:second.close()
finally:first.close()

server=ThreadingHTTPServer(('127.0.0.1',0),MissingPage)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
failed=NativeDesktopWindow(None,f'http://127.0.0.1:{server.server_port}')
try:
    try:failed.wait_ready(10)
    except RuntimeError:pass
    else:raise AssertionError('404 must not mark the application ready')
    assert failed.process.wait(timeout=10)!=0
finally:failed.close();server.shutdown();server.server_close();thread.join(timeout=5)
print('PASS: real Qt frontend ready, separate child forwards activation, 404 fails before ready and exits.')
