"""Persistent, local-only recipe queue. No system cron, external writes or secrets.

Jobs run while Reapdf is open; pending due jobs resume on next start. A process
interrupted during execution leaves an explicit interrupted job, never a result
reported as complete. Inputs are private snapshots, independent of session IDs.
"""
from datetime import datetime,timezone,timedelta
from io import BytesIO
from pathlib import Path
from threading import RLock,Event,Thread
from uuid import uuid4
from zipfile import ZipFile,ZIP_DEFLATED,BadZipFile
import hashlib,json,os,re,shutil,subprocess,sys
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf
from .document_tools import editable
from .automation import validate_recipe

ID=re.compile(r'[0-9a-f]{32}');STATES={'queued','running','completed','failed','cancelled','interrupted'}
QUOTA=300*1024*1024


def now():return datetime.now(timezone.utc)
def digest(data):return hashlib.sha256(data).hexdigest()


def atomic(path,data):
    temp=path.with_name('.'+path.name+'-'+uuid4().hex+'.tmp')
    try:
        with temp.open('xb') as handle:
            try:os.chmod(temp,0o600)
            except OSError:pass
            handle.write(data);handle.flush();os.fsync(handle.fileno())
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)


class Queue:
    def __init__(self,root,clock=now):
        self.root=Path(root)/'scheduled-recipes';self.clock=clock;self.lock=RLock();self.stop=Event();self.thread=None;self.process=None

    def directory(self,identity):
        if not isinstance(identity,str) or not ID.fullmatch(identity):raise DocumentError('Identificador de tarea no válido.')
        path=self.root/identity
        if path.is_symlink():raise DocumentError('La tarea no puede apuntar a otro directorio.')
        return path

    def read(self,identity):
        path=self.directory(identity)/'state.json'
        try:
            if path.is_symlink() or path.stat().st_size>65536:raise ValueError()
            data=json.loads(path.read_bytes())
            if data['id']!=identity or data['version']!=1 or data['status'] not in STATES or not isinstance(data['documents'],list) or not 1<=len(data['documents'])<=10 or not isinstance(data['name'],str) or len(data['name'])>80:raise ValueError()
            instant=datetime.fromisoformat(data['run_at'])
            if instant.tzinfo is None:raise ValueError()
            validate_recipe(data['recipe'])
            return data
        except (OSError,ValueError,KeyError,TypeError):raise DocumentError('La tarea local está dañada o no existe; no se ejecuta.') from None

    def save(self,row):atomic(self.directory(row['id'])/'state.json',json.dumps(row,ensure_ascii=False,allow_nan=False).encode())

    def list(self):
        with self.lock:
            if not self.root.exists():return []
            rows=[]
            for path in sorted(self.root.iterdir()):
                if not ID.fullmatch(path.name) or not path.is_dir() or path.is_symlink():continue
                try:
                    row=self.read(path.name);rows.append({k:row.get(k) for k in ['id','name','status','run_at','created_at','finished_at','error','documents']})
                except DocumentError:rows.append({'id':path.name,'name':'Tarea dañada','status':'invalid','error':'No se ejecuta. Puedes eliminar sus archivos locales.'})
            return rows

    def size(self):
        if not self.root.exists():return 0
        return sum(p.stat().st_size for p in self.root.glob('*/*') if p.is_file() and not p.is_symlink())

    def create(self,items,recipe,run_at):
        recipe=validate_recipe(recipe)
        if any(s['type']=='protect' for s in recipe['steps']):raise DocumentError('Las tareas guardadas no conservan contraseñas. Ejecuta la protección manualmente al final.')
        try:instant=datetime.fromisoformat(run_at) if isinstance(run_at,str) else None
        except ValueError:instant=None
        if instant is None or instant.tzinfo is None or not self.clock()-timedelta(seconds=60)<=instant<=self.clock()+timedelta(days=30):raise DocumentError('Elige fecha y hora con zona horaria, desde ahora hasta 30 días.')
        if not isinstance(items,list) or not 1<=len(items)<=10:raise DocumentError('La tarea necesita entre 1 y 10 PDF.')
        prepared=[];total=0;pages=0;mutates=any(s['type'] not in ['text','docx'] for s in recipe['steps'])
        for index,item in enumerate(items,1):
            if not isinstance(item,(tuple,list)) or len(item)!=3 or not isinstance(item[0],str) or not 1<=len(item[0])<=255 or any(ord(c)<32 or ord(c)==127 or 0xd800<=ord(c)<=0xdfff for c in item[0]) or not isinstance(item[1],bytes):raise DocumentError('Documento de tarea no válido.')
            name,base,ops=item
            with open_pdf(base) as doc:
                if mutates:editable(doc)
                if recipe['steps'][-1]['type'] in ['text','docx'] and not doc.permissions&f.PDF_PERM_COPY:raise DocumentError('Un PDF no permite copiar el contenido de la tarea.')
            snapshot=export_pdf(base,ops);total+=len(snapshot)
            with open_pdf(snapshot) as d:pages+=len(d)
            if total>60*1024*1024 or pages>100:raise DocumentError('La tarea supera 60 MB o 100 páginas.')
            prepared.append((name,snapshot))
        stream=BytesIO();descriptors=[]
        with ZipFile(stream,'w',ZIP_DEFLATED) as z:
            for index,(name,data) in enumerate(prepared):
                file=f'{index}.pdf';z.writestr(file,data);descriptors.append({'name':name,'file':file,'sha256':digest(data)})
        packed=stream.getvalue()
        with self.lock:
            if len(self.list())>=20 or self.size()+len(packed)>QUOTA:raise DocumentError('La cola supera 20 tareas o 300 MB. Elimina tareas que ya no necesites.')
            identity=uuid4().hex;path=self.directory(identity);path.mkdir(parents=True,mode=0o700)
            row={'version':1,'id':identity,'name':recipe['name'],'status':'queued','created_at':self.clock().isoformat(),'run_at':instant.astimezone(timezone.utc).isoformat(),'recipe':recipe,'documents':descriptors,'input_sha256':digest(packed),'cancel_requested':False,'error':None,'finished_at':None}
            try:atomic(path/'inputs.zip',packed);self.save(row)
            except Exception:shutil.rmtree(path);raise
            return {k:row[k] for k in ['id','name','status','run_at','created_at','documents']}

    def inputs(self,row):
        path=self.directory(row['id'])/'inputs.zip'
        if path.is_symlink() or path.stat().st_size>70*1024*1024:raise DocumentError('La copia de entrada de la tarea no es válida.')
        data=path.read_bytes()
        if digest(data)!=row['input_sha256']:raise DocumentError('Los documentos guardados de la tarea cambiaron; no se ejecuta.')
        try:
            with ZipFile(BytesIO(data)) as z:
                files=z.infolist();names=[x.filename for x in files];expected=[str(i)+'.pdf' for i in range(len(row['documents']))]
                if names!=expected or sum(i.file_size for i in files)>60*1024*1024 or any(i.flag_bits&1 for i in files):raise ValueError()
                items=[]
                for i,descriptor in enumerate(row['documents']):
                    raw=z.read(expected[i])
                    if descriptor['file']!=expected[i] or digest(raw)!=descriptor['sha256']:raise ValueError()
                    items.append((descriptor['name'],raw,[]))
                return items
        except (OSError,ValueError,KeyError,BadZipFile,RuntimeError):raise DocumentError('No se pudieron verificar las entradas de la tarea local.') from None

    def tick(self):
        with self.lock:
            due=[r for r in self.list() if r['status']=='queued' and datetime.fromisoformat(r['run_at'])<=self.clock()]
            if not due:return False
            row=self.read(min(due,key=lambda r:r['run_at'])['id']);row['status']='running';self.save(row)
        try:
            output=self.execute(row)
            with self.lock:
                current=self.read(row['id'])
                if self.stop.is_set():current.update(status='interrupted',error='La aplicación se cerró durante la ejecución; no se presenta un resultado parcial.')
                elif current['cancel_requested']:current['status']='cancelled'
                else:
                    if self.size()+len(output)>QUOTA:raise DocumentError('La salida supera la cuota local de 300 MB; elimina tareas antiguas.')
                    atomic(self.directory(row['id'])/'result.zip',output);current.update(status='completed',output_sha256=digest(output))
                current['finished_at']=self.clock().isoformat();self.save(current)
        except Exception as e:
            with self.lock:
                current=self.read(row['id']);current.update(status='interrupted' if self.stop.is_set() else 'cancelled' if current['cancel_requested'] else 'failed',error=str(e) if isinstance(e,DocumentError) else 'No se pudo completar la tarea. No hay resultado parcial disponible.',finished_at=self.clock().isoformat());self.save(current)
        return True

    def execute(self,row):
        # PyMuPDF must not execute a scheduled conversion concurrently in a
        # background thread with the UI's PDF rendering. Use an owned process,
        # with an explicit trusted module path and no shell command strings.
        folder=self.directory(row['id']);candidate=folder/'candidate.zip';error=folder/'worker-error.json'
        candidate.unlink(missing_ok=True);error.unlink(missing_ok=True)
        kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
        process=subprocess.Popen([sys.executable,'-I',str(Path(__file__).with_name('scheduled_worker.py')),str(folder.resolve())],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**kwargs)
        self.process=process
        if self.stop.is_set():process.terminate()
        try:
            try:code=process.wait(timeout=600)
            except subprocess.TimeoutExpired:
                process.terminate();process.wait(timeout=10);raise DocumentError('La tarea superó diez minutos de ejecución; no se entrega un resultado parcial.')
            if code or not candidate.is_file() or candidate.is_symlink():
                message='La conversión local se interrumpió; no hay resultado parcial disponible.'
                if error.is_file() and not error.is_symlink() and error.stat().st_size<=10000:
                    try:message=json.loads(error.read_bytes())['error']
                    except (ValueError,KeyError,TypeError):pass
                raise DocumentError(message)
            if candidate.stat().st_size>100*1024*1024:raise DocumentError('La tarea supera 100 MB de salida.')
            return candidate.read_bytes()
        finally:
            self.process=None
            if process.poll() is None:process.terminate();process.wait(timeout=10)
            if process.stdin:process.stdin.close()
            candidate.unlink(missing_ok=True);error.unlink(missing_ok=True)

    def cancel(self,identity):
        with self.lock:
            row=self.read(identity)
            if row['status'] not in ['queued','running']:raise DocumentError('Solo se cancelan tareas pendientes o en ejecución.')
            row['cancel_requested']=True
            if row['status']=='queued':row.update(status='cancelled',finished_at=self.clock().isoformat())
            self.save(row);return {'status':row['status'],'cancel_requested':True}

    def delete(self,identity):
        with self.lock:
            path=self.directory(identity)
            if not path.is_dir():raise DocumentError('La tarea no existe.')
            try:row=self.read(identity)
            except DocumentError:row={'status':'invalid'}
            if row['status']=='running':raise DocumentError('Cancela la tarea y espera a que termine antes de eliminarla.')
            shutil.rmtree(path);return {'deleted':True}

    def result(self,identity):
        with self.lock:
            row=self.read(identity);path=self.directory(identity)/'result.zip'
            if row['status']!='completed' or path.is_symlink() or not path.is_file() or path.stat().st_size>100*1024*1024:raise DocumentError('La tarea no tiene un resultado completo disponible.')
            data=path.read_bytes()
            if digest(data)!=row.get('output_sha256'):raise DocumentError('El resultado guardado cambió; no se entrega.')
            return data

    def start(self):
        with self.lock:
            if self.thread is not None:return
            for info in self.list():
                if info['status']=='running':
                    row=self.read(info['id']);row.update(status='interrupted',error='La ejecución anterior se interrumpió. No se entrega una salida incompleta. Vuelve a programar la receta si la necesitas.');self.save(row)
            self.stop.clear()
            def run():
                while not self.stop.wait(1):
                    try:self.tick()
                    except Exception:pass  # A damaged job never stops the app.
            self.thread=Thread(target=run,name='reapdf-local-recipes',daemon=True);self.thread.start()

    def close(self):
        self.stop.set()
        process=self.process
        if process is not None and process.poll() is None:
            try:process.terminate()
            except OSError:pass
        if self.thread:self.thread.join(timeout=12)
