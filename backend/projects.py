"""Proyectos portables y un punto de recuperación local con escritura atómica."""
import base64
from datetime import datetime, timezone
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
from threading import RLock
from uuid import uuid4
from zipfile import ZipFile, BadZipFile, ZIP_DEFLATED
from .engine import DocumentError, open_pdf, export_pdf, finite, MAX_OPERATIONS

MAX_BASE = 60 * 1024 * 1024
MAX_OPERATIONS_BYTES = 5 * 1024 * 1024
MAX_PROJECT = 70 * 1024 * 1024
FILES = {'manifest.json', 'base.pdf', 'operations.json'}


def validate_state(state, count):
    if not isinstance(state, dict):
        raise DocumentError('Estado de proyecto no válido.')
    name = state.get('name')
    page, zoom = state.get('page', 0), state.get('zoom', 1)
    changes = state.get('base_changes', 0)
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 200 or any(ord(c) < 32 for c in name):
        raise DocumentError('Nombre de proyecto no válido.')
    if type(page) is not int or not 0 <= page < count:
        raise DocumentError('Página de proyecto no válida.')
    if not finite(zoom) or not .05 <= zoom <= 4:
        raise DocumentError('Zoom de proyecto no válido.')
    if type(changes) is not int or not 0 <= changes <= 1_000_000:
        raise DocumentError('Contador de cambios no válido.')
    return {'name': name.strip(), 'page': page, 'zoom': zoom, 'base_changes': changes}


def project_operations(operations):
    # El motor permite operaciones sin metadatos de interfaz. Los proyectos deben
    # restaurar selecciones seguras y dimensiones reales, no datos del remitente.
    from .images import image_dimensions
    session_types = {'textbox','stamp','link','image','ink','line','arrow','rectangle','highlight','underline','strikeout','note'}
    normalized, seen = [], set()
    for original in operations:
        op = dict(original)
        if op.get('type') in session_types:
            identity = op.get('id', uuid4().hex)
            if not isinstance(identity, str) or not 1 <= len(identity) <= 100 or identity in seen:
                raise DocumentError('Las marcas del proyecto necesitan identificadores únicos válidos.')
            seen.add(identity); op['id'] = identity
        else:
            op.pop('id', None)
        if op.get('type') == 'image':
            op['pixels'] = list(image_dimensions(base64.b64decode(op['data'], validate=True)))
            name = op.get('name')
            op['name'] = name[:180] if isinstance(name, str) and name.strip() and not any(ord(c) < 32 for c in name) else 'Imagen insertada'
        normalized.append(op)
    return normalized


def build_project(base, operations, state):
    if len(base) > MAX_BASE:
        raise DocumentError('El PDF base del proyecto supera 60 MB. Exporta una copia PDF para conservarlo.')
    with open_pdf(base) as doc:
        state = validate_state(state, len(doc))
    # Comprobar las operaciones contra el original antes de guardar, sin aplanarlas.
    export_pdf(base, operations)
    operations = project_operations(operations)
    try:
        encoded = json.dumps(operations, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()
    except (ValueError, TypeError) as exc:
        raise DocumentError('Los cambios contienen datos no serializables.') from exc
    if len(encoded) > MAX_OPERATIONS_BYTES:
        raise DocumentError('Los cambios del proyecto superan 5 MB. Exporta una copia PDF.')
    manifest = {'format': 'reapdf-project', 'version': 1, 'state': state,
                'saved_at': datetime.now(timezone.utc).isoformat(),
                'sha256': {'base.pdf': sha256(base).hexdigest(), 'operations.json': sha256(encoded).hexdigest()}}
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=True).encode())
        archive.writestr('base.pdf', base)
        archive.writestr('operations.json', encoded)
    return output.getvalue(), manifest


def read_project(data, *, validate_pdf=True):
    if not data or len(data) > MAX_PROJECT:
        raise DocumentError('El proyecto está vacío o supera 70 MB.')
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) != 3 or {entry.filename for entry in entries} != FILES:
                raise DocumentError('El proyecto debe contener exactamente su manifiesto, PDF base y operaciones.')
            limits = {'base.pdf': MAX_BASE, 'operations.json': MAX_OPERATIONS_BYTES, 'manifest.json': 16 * 1024}
            if any(entry.flag_bits & 1 or entry.file_size > limits[entry.filename] or entry.is_dir() for entry in entries):
                raise DocumentError('El proyecto contiene archivos cifrados o de tamaño no permitido.')
            manifest = json.loads(archive.read('manifest.json'))
            if not isinstance(manifest, dict) or manifest.get('format') != 'reapdf-project' or type(manifest.get('version')) is not int or manifest['version'] != 1:
                raise DocumentError('Formato o versión de proyecto no compatible.')
            if not isinstance(manifest.get('saved_at'), str) or len(manifest['saved_at']) > 80:
                raise DocumentError('Fecha de proyecto no válida.')
            base, encoded = archive.read('base.pdf'), archive.read('operations.json')
            checksums = manifest.get('sha256')
            if not isinstance(checksums, dict) or checksums.get('base.pdf') != sha256(base).hexdigest() or checksums.get('operations.json') != sha256(encoded).hexdigest():
                raise DocumentError('El proyecto está incompleto o fue alterado; no se reemplazó el documento abierto.')
            operations = json.loads(encoded)
            if not isinstance(operations, list) or len(operations) > MAX_OPERATIONS:
                raise DocumentError('Operaciones del proyecto no válidas.')
            if validate_pdf:
                with open_pdf(base) as doc:
                    manifest['state'] = validate_state(manifest.get('state'), len(doc))
                export_pdf(base, operations)
                operations = project_operations(operations)
            return base, operations, manifest
    except DocumentError:
        raise
    except (BadZipFile, ValueError, KeyError, TypeError, RuntimeError, EOFError, OSError, NotImplementedError) as exc:
        raise DocumentError('No se pudo abrir el proyecto Reapdf. Comprueba que esté completo y sea compatible.') from exc


def data_directory():
    configured = os.environ.get('REAPDF_DATA_DIR')
    if configured:
        return Path(configured)
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'Reapdf'
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local' / 'state'))) / 'reapdf'


class RecoveryConflict(DocumentError):
    pass


class RecoveryStore:
    def __init__(self, directory):
        self.path = Path(directory) / 'recovery.reapdf'
        self.lock = RLock()

    @contextmanager
    def _write_lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # El bloqueo del SO se libera incluso si el proceso termina inesperadamente.
        descriptor = os.open(self.path.parent / '.recovery.lock', os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, 'r+b') as stream:
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b'\0'); stream.flush()
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def _current(self):
        if not self.path.exists():
            return None, None
        if self.path.stat().st_size > MAX_PROJECT:
            raise DocumentError('El punto de recuperación supera 70 MB. Conserva el archivo y guarda un proyecto aparte.')
        data = self.path.read_bytes()
        return data, sha256(data).hexdigest()

    def status(self):
        with self.lock:
            data, revision = self._current()
            if data is None:
                return {'available': False, 'revision': None}
            try:
                _, _, manifest = read_project(data)
                return {'available': True, 'revision': revision, 'state': manifest['state'], 'saved_at': manifest['saved_at']}
            except DocumentError as exc:
                return {'available': False, 'revision': revision, 'error': str(exc)}

    def read(self, expected):
        with self.lock:
            data, revision = self._current()
            if revision != expected:
                raise RecoveryConflict('La recuperación cambió en otra ventana. Recarga la aplicación antes de continuar.')
            if data is None:
                raise DocumentError('No hay una sesión disponible para recuperar.')
            return read_project(data)

    def save(self, data, expected):
        with self.lock, self._write_lock():
            _, revision = self._current()
            if revision != expected:
                raise RecoveryConflict('Otra ventana actualizó la recuperación. Guarda un proyecto y recarga para continuar.')
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name('.recovery-' + uuid4().hex + '.tmp')
            try:
                # Solo datos locales del usuario, sin escritura en el directorio de instalación.
                with temporary.open('xb') as stream:
                    try:os.chmod(temporary, 0o600)
                    except OSError:pass
                    stream.write(data); stream.flush(); os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            finally:
                temporary.unlink(missing_ok=True)
            return sha256(data).hexdigest()

    def delete(self, expected):
        with self.lock, self._write_lock():
            _, revision = self._current()
            if revision != expected:
                raise RecoveryConflict('La recuperación cambió en otra ventana. Recarga antes de descartarla.')
            self.path.unlink(missing_ok=True)
