"""Per-user, per-installation local handoff, protected by a process lock."""
import getpass,hashlib,json,os,tempfile,time
from pathlib import Path


def message(file):
    if file is None:return {'version':1,'file':None}
    path=Path(file).resolve(strict=True)
    if path.suffix.lower()!='.pdf' or not path.is_file() or path.stat().st_size>60*1024*1024:raise ValueError('Selecciona un PDF de hasta 60 MB.')
    return {'version':1,'file':str(path)}


class SingleInstance:
    def __init__(self,file=None,namespace=None):
        from PySide6.QtCore import QLockFile
        from PySide6.QtNetwork import QLocalServer,QLocalSocket
        identity=str(Path(__file__).resolve().parent)+'|'+getpass.getuser()+'|'+str(namespace or '')
        name='reapdf-'+hashlib.sha256(identity.encode()).hexdigest()[:24]
        root=Path(tempfile.gettempdir())/name
        name+='-ipc'
        if root.is_symlink():raise RuntimeError('La carpeta de comunicación no es válida.')
        root.mkdir(mode=0o700,exist_ok=True)
        if hasattr(os,'getuid') and root.stat().st_uid!=os.getuid():raise RuntimeError('La carpeta de comunicación pertenece a otro usuario.')
        self.lock=QLockFile(str(root/'instance.lock'));self.lock.setStaleLockTime(0)
        self.owner=self.lock.tryLock(0);self.server=None;self.sockets=[];self.buffers={};self.pending=[];self.handler=None
        payload=message(file)
        if self.owner:
            QLocalServer.removeServer(name) # Only the lock owner removes its stale socket.
            self.server=QLocalServer();self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
            if not self.server.listen(name):self.lock.unlock();raise RuntimeError(self.server.errorString())
            self.server.newConnection.connect(self.accept)
        else:
            socket=QLocalSocket();socket.connectToServer(name)
            if not socket.waitForConnected(3000):raise RuntimeError('La instancia de Reapdf no responde. No se abrirá una copia adicional.')
            socket.write((json.dumps(payload)+'\n').encode())
            if not socket.waitForBytesWritten(3000) and socket.bytesToWrite():raise RuntimeError('No se pudo enviar el archivo.')
            if not socket.waitForReadyRead(10000):raise RuntimeError('La instancia no confirmó la solicitud.')
            data=bytes(socket.readAll());deadline=time.monotonic()+10
            while b'\n' not in data:
                if len(data)>8192 or time.monotonic()>=deadline or not socket.waitForReadyRead(1000):raise RuntimeError('La respuesta de la instancia está incompleta.')
                data+=bytes(socket.readAll())
            if len(data)>8192:raise RuntimeError('La respuesta de la instancia es demasiado larga.')
            response=json.loads(data.decode())
            socket.disconnectFromServer()
            if not response.get('accepted'):raise RuntimeError(response.get('error','No se pudo abrir el archivo.'))

    def accept(self):
        from PySide6.QtCore import QTimer
        while self.server.hasPendingConnections():
            socket=self.server.nextPendingConnection()
            if len(self.sockets)>=16:socket.abort();socket.deleteLater();continue
            self.sockets.append(socket);self.buffers[socket]=b''
            timer=QTimer(socket);timer.setSingleShot(True);timer.timeout.connect(lambda s=socket:s.abort());timer.start(3000)
            socket.readyRead.connect(lambda s=socket:self.read(s))
            socket.disconnected.connect(lambda s=socket:self.release(s))
            self.read(socket)

    def release(self,socket):
        if socket in self.sockets:self.sockets.remove(socket)
        self.buffers.pop(socket,None)
        socket.deleteLater()

    def read(self,socket):
        data=self.buffers.get(socket,b'')+bytes(socket.readAll())
        self.buffers[socket]=data
        try:
            if len(data)>8192:raise ValueError('Solicitud demasiado larga.')
            if b'\n' not in data:return
            value=json.loads(data.decode())
            if not isinstance(value,dict) or set(value)!={'version','file'} or type(value['version']) is not int or value['version']!=1:raise ValueError('Solicitud no válida.')
            if value['file'] is not None and not isinstance(value['file'],str):raise ValueError('Archivo no válido.')
            value=message(value['file'])
            if len(self.pending)>=10:raise ValueError('Hay demasiados archivos pendientes.')
            if self.handler:self.handler(value['file'])
            else:self.pending.append(value['file'])
            response={'accepted':True}
        except (ValueError,OSError,TypeError,RuntimeError) as exc:response={'accepted':False,'error':str(exc)}
        socket.write((json.dumps(response)+'\n').encode());socket.flush();socket.disconnectFromServer()

    def set_handler(self,handler):
        self.handler=handler
        for value in self.pending:handler(value)
        self.pending.clear()

    def close(self):
        if self.owner:
            for socket in list(self.sockets):socket.abort()
            self.server.close();self.lock.unlock();self.owner=False
