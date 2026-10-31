"""Verificar integridad en cualquier host; ejecutar la prueba nativa solo en Windows."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import argparse
import hashlib
import json
import os
import queue
import re
import subprocess
import struct
import socket
import shutil
import threading
import time
import urllib.request


def verify_archive(archive):
    from scripts.package_portable import safe_name, pe_machine
    prefix='Reapdf-portable/'
    with ZipFile(archive) as z:
        for info in z.infolist():safe_name(info.filename)
        manifest=json.loads(z.read(prefix+'MANIFIESTO.json'))
        actual={n[len(prefix):] for n in z.namelist() if not n.endswith('/') and n!=prefix+'MANIFIESTO.json'}
        if actual!=set(manifest['files']):raise ValueError('La lista de archivos no coincide con el manifiesto.')
        for name,expected in manifest['files'].items():
            data=z.read(prefix+name)
            if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Archivo alterado o incompleto: '+name)
            if (name.startswith('runtime/') or name=='Reapdf.exe') and name.endswith(('.exe','.dll','.pyd')) and pe_machine(data)!=0x8664:
                raise ValueError('Binario ajeno a Windows x64: '+name)
            if name=='Reapdf.exe':
                offset=struct.unpack_from('<I',data,60)[0]
                if struct.unpack_from('<H',data,offset+24+68)[0]!=2:raise ValueError('Reapdf.exe debe ser una aplicacion GUI.')
    return manifest


def native_check(folder, executable=None):
    bundled=executable is None
    executable=Path(executable) if executable else folder/'runtime'/'python.exe';launcher=folder/'app'/'launcher.py'
    result=subprocess.run([str(executable),'-I',str(launcher),'--self-test'],capture_output=True,text=True,timeout=45,check=True)
    report=json.loads(result.stdout.strip().splitlines()[-1]);assert report['portable_self_test']=='ok'
    process=subprocess.Popen([str(executable),'-I',str(launcher),'--no-browser'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env={**os.environ,'REAPDF_DATA_DIR':str(folder/'.verification-state')})
    lines=queue.Queue()
    def read_lines():
        for line in process.stdout:lines.put(line)
    threading.Thread(target=read_lines,daemon=True).start()
    try:
        url=None;deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('El portable terminó antes de abrir el servidor.')
            try:line=lines.get(timeout=.2)
            except queue.Empty:continue
            match=re.search(r'REAPDF_URL=(http://127\.0\.0\.1:\d+)',line)
            if match:url=match[1];break
        if not url:raise RuntimeError('No se recibió la dirección local del portable.')
        with urllib.request.urlopen(url,timeout=10) as r:assert b'root' in r.read()
        sample=(folder/'ejemplos'/'reapdf-demo.pdf').read_bytes();boundary='ReapdfPortableTestBoundary'
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="demo.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode()+sample+f'\r\n--{boundary}--\r\n'.encode())
        request=urllib.request.Request(url+'/api/documents',data=body,headers={'Content-Type':'multipart/form-data; boundary='+boundary})
        with urllib.request.urlopen(request,timeout=20) as r:doc=json.load(r)
        with urllib.request.urlopen(url+f"/api/documents/{doc['id']}/pages/0",timeout=20) as r:page=json.load(r)
        span=next(s for s in page['spans'] if s['text']=='Texto original')
        op={'type':'text','page':0,'span_id':span['id'],'text':'Portable','font':'tibo','size':18,'color':[1,0,0]}
        request=urllib.request.Request(url+f"/api/documents/{doc['id']}/export",data=json.dumps({'operations':[op]}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=20) as r:pdf=r.read()
        def post_json(path,payload):
            request=urllib.request.Request(url+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            return urllib.request.urlopen(request,timeout=30)
        payload={'operations':[op],'name':'Portable.pdf','page':0,'zoom':1,'base_changes':0}
        with post_json(f"/api/documents/{doc['id']}/project",payload) as r:project=r.read()
        assert project.startswith(b'PK')
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="demo.reapdf"\r\nContent-Type: application/zip\r\n\r\n'.encode()+project+f'\r\n--{boundary}--\r\n'.encode())
        request=urllib.request.Request(url+'/api/projects/open',data=body,headers={'Content-Type':'multipart/form-data; boundary='+boundary})
        with urllib.request.urlopen(request,timeout=30) as r:restored=json.load(r)
        assert restored['operations'][0]['text']=='Portable'
        with post_json(f"/api/documents/{doc['id']}/recovery",payload) as r:checkpoint=json.load(r)
        with post_json('/api/recovery/restore',{'revision':checkpoint['revision']}) as r:recovered=json.load(r)
        assert recovered['operations'][0]['text']=='Portable'
        with post_json(f"/api/documents/{doc['id']}/print",{'operations':[op]}) as r:assert r.read().startswith(b'%PDF')
        # Usar el mismo intérprete incluido: el verificador host no necesita PyMuPDF.
        check=folder/'comprobacion.pdf';check.write_bytes(pdf)
        subprocess.run([str(executable),'-I','-c',"import pymupdf as f,sys;d=f.open(sys.argv[1]);assert 'Portable' in d[0].get_text();assert 'Texto original' not in d[0].get_text()",str(check)],check=True,timeout=20)
        return {**report,'http_upload_export':'ok','projects_recovery_print':'ok','bundled_engine_verified':os.name=='nt' and bundled,'windows_execution_verified':False}
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)


def _compiled_window(folder):
    """Locate a real Qt top-level window owned by this package's interpreter."""
    import ctypes
    from ctypes import wintypes as w
    user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
    kernel.CloseHandle.argtypes=[w.HANDLE]
    callback=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM);found=[]
    user.EnumWindows.argtypes=[callback,w.LPARAM]
    user.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int]
    user.GetClassNameW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int]
    user.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)]
    def visit(hwnd,unused):
        title=ctypes.create_unicode_buffer(512);kind=ctypes.create_unicode_buffer(256)
        user.GetWindowTextW(hwnd,title,512);user.GetClassNameW(hwnd,kind,256)
        if title.value!='Reapdf' or not kind.value.startswith('Qt'):return True
        pid=w.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid));handle=kernel.OpenProcess(0x1000,False,pid.value)
        if not handle:return True
        try:
            value=ctypes.create_unicode_buffer(32768);size=w.DWORD(len(value))
            if kernel.QueryFullProcessImageNameW(handle,0,value,ctypes.byref(size)) and Path(value.value).resolve()==(folder/'runtime/python.exe').resolve():found.append((hwnd,pid.value))
        finally:kernel.CloseHandle(handle)
        return True
    user.EnumWindows(callback(visit),0)
    if len(found)!=1:raise RuntimeError('No se encontró una única ventana Qt del ejecutable incluido.')
    return found[0]


def compiled_gui_check(folder):
    if os.name!='nt':raise RuntimeError('La comprobación del ejecutable exige Windows.')
    root=Path(__file__).resolve().parents[1];node=shutil.which('node')
    if not node or not (root/'node_modules/@playwright/test').is_dir():raise RuntimeError('La verificación gráfica interna requiere Node y npm ci en el checkout de pruebas.')
    with socket.socket() as reserved:reserved.bind(('127.0.0.1',0));port=reserved.getsockname()[1]
    sample=folder/'ejemplos/reapdf-demo.pdf';original=sample.read_bytes();output=folder/'comprobacion-ventana.pdf'
    env={**os.environ,'REAPDF_DATA_DIR':str(folder/'.gui-verification-state'),'REAPDF_INSTANCE_NAMESPACE':str(folder/'.gui-verification-state'),'QTWEBENGINE_REMOTE_DEBUGGING':f'127.0.0.1:{port}'}
    process=subprocess.Popen([str(folder/'Reapdf.exe'),str(sample)],cwd=folder.parent,env=env)
    endpoint=f'http://127.0.0.1:{port}'
    try:
        deadline=time.monotonic()+65
        while True:
            if process.poll() is not None:raise RuntimeError('Reapdf.exe terminó antes de abrir su ventana.')
            try:
                with urllib.request.urlopen(endpoint+'/json/list',timeout=1) as r:targets=json.load(r)
                if any(t.get('type')=='page' and t.get('url','').startswith('http://127.0.0.1:') for t in targets):break
            except (OSError,ValueError):pass
            if time.monotonic()>deadline:raise RuntimeError('La ventana incluida no quedó disponible para su verificación.')
            time.sleep(.1)
        hwnd,pid=_compiled_window(folder)
        run=subprocess.run([node,str(root/'scripts/smoke_packaged_window.mjs'),endpoint,str(output)],cwd=root,capture_output=True,text=True,timeout=100)
        if run.returncode or 'PASS:' not in run.stdout:raise RuntimeError('Falló el recorrido del ejecutable: '+run.stdout+run.stderr)
        subprocess.run([str(folder/'runtime/python.exe'),'-I','-c',"import pymupdf as f,sys;d=f.open(sys.argv[1]);assert len(d)==2;assert 'Ejecutable' in d[0].get_text();assert 'Texto original' not in d[0].get_text();assert 'Segunda pagina' in d[1].get_text()",str(output)],check=True,timeout=20)
        if sample.read_bytes()!=original:raise RuntimeError('La comprobación modificó el PDF de origen.')
        import ctypes
        from ctypes import wintypes as w
        user=ctypes.WinDLL('user32');user.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];user.PostMessageW(hwnd,0x0010,0,0)
        if process.wait(timeout=25)!=0:raise RuntimeError('Reapdf.exe no cerró normalmente.')
        print(run.stdout.strip())
        return {'compiled_exe_window_and_edit':'ok','compiled_exe_normal_close':'ok','qt_process_pid':pid,'external_browser_used':False,'native_save_in_this_check':False,'windows_execution_verified':True}
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=10)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive');parser.add_argument('--static-only',action='store_true');parser.add_argument('--report',type=Path);args=parser.parse_args()
    manifest=verify_archive(args.archive)
    if args.static_only:
        print(json.dumps({'integrity':'ok','files':len(manifest['files']),'version':manifest['version'],'windows_execution_verified':False}));return
    if os.name!='nt':raise SystemExit('La ejecución nativa requiere Windows. Usa --static-only para comprobar integridad.')
    with TemporaryDirectory(prefix='Reapdf prueba con espacios ') as tmp:
        with ZipFile(args.archive) as z:z.extractall(tmp)
        folder=Path(tmp)/'Reapdf-portable';result={**native_check(folder),**compiled_gui_check(folder),'archive_sha256':hashlib.sha256(Path(args.archive).read_bytes()).hexdigest(),'physical_print_verified':False,'human_acceptance':False}
        from scripts.publish_windows_report import source_objects
        root=Path(__file__).resolve().parents[1]
        result.update(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),source_git_objects=source_objects(root),source_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()))
        if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result))

if __name__=='__main__':main()
