"""Atomic writes to destinations selected in the desktop UI."""
import base64,hashlib
from pathlib import Path


def atomic_save(path,encoded):
    from PySide6.QtCore import QSaveFile,QIODevice
    if not isinstance(encoded,str) or len(encoded)>96*1024*1024:raise ValueError('El archivo supera el límite de guardado.')
    data=base64.b64decode(encoded,validate=True)
    if not data:raise ValueError('El archivo está vacío.')
    target=QSaveFile(str(path));target.setDirectWriteFallback(False)
    if not target.open(QIODevice.OpenModeFlag.WriteOnly):raise OSError(target.errorString())
    if target.write(data)!=len(data):
        message=target.errorString();target.cancelWriting();raise OSError(message)
    if not target.commit():raise OSError(target.errorString())
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
