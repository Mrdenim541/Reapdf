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
        return {**report,'http_upload_export':'ok','projects_recovery_print':'ok','windows_execution_verified':os.name=='nt' and bundled}
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive');parser.add_argument('--static-only',action='store_true');args=parser.parse_args()
    manifest=verify_archive(args.archive)
    if args.static_only:
        print(json.dumps({'integrity':'ok','files':len(manifest['files']),'version':manifest['version'],'windows_execution_verified':False}));return
    if os.name!='nt':raise SystemExit('La ejecución nativa requiere Windows. Usa --static-only para comprobar integridad.')
    with TemporaryDirectory(prefix='Reapdf prueba con espacios ') as tmp:
        with ZipFile(args.archive) as z:z.extractall(tmp)
        print(json.dumps(native_check(Path(tmp)/'Reapdf-portable')))

if __name__=='__main__':main()
