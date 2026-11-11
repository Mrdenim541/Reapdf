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
        # Execute the real owned worker from the bundle's flat app layout.
        from datetime import datetime,timezone
        from io import BytesIO
        recipe={'format':'reapdf-recipe','version':1,'name':'Bundled local worker','filename':'{name}','steps':[{'type':'text','pages':'1'}]}
        with post_json('/api/scheduled-recipes',{'documents':[{'id':doc['id'],'name':'demo.pdf','operations':[op]}],'recipe':recipe,'run_at':datetime.now(timezone.utc).isoformat()}) as r:job=json.load(r)
        deadline=time.monotonic()+40
        while True:
            with urllib.request.urlopen(url+'/api/scheduled-recipes',timeout=10) as r:state=next(v for v in json.load(r) if v['id']==job['id'])
            if state['status'] in ['completed','failed','interrupted','cancelled']:break
            if time.monotonic()>deadline:raise RuntimeError('La tarea del paquete no terminó dentro del plazo.')
            time.sleep(.2)
        assert state['status']=='completed',state
        with urllib.request.urlopen(url+'/api/scheduled-recipes/'+job['id']+'/result',timeout=10) as r:archive=r.read()
        with ZipFile(BytesIO(archive)) as z:
            entry=json.loads(z.read('manifest.json'))['documents'][0]
            assert 'Portable' in z.read(entry['file']).decode('utf-8')
        with urllib.request.urlopen(urllib.request.Request(url+'/api/scheduled-recipes/'+job['id'],method='DELETE'),timeout=10) as r:assert r.status==200
        # Run the current split engine inside the actual bundled runtime.
        fixture=folder/'split-sample.pdf'
        subprocess.run([str(executable),'-I',str(Path(__file__).with_name('create_split_sample.py')),str(fixture)],check=True,timeout=40)
        split_source=fixture.read_bytes()
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="split.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode()+split_source+f'\r\n--{boundary}--\r\n'.encode())
        with urllib.request.urlopen(urllib.request.Request(url+'/api/documents',data=body,headers={'Content-Type':'multipart/form-data; boundary='+boundary}),timeout=30) as r:splitdoc=json.load(r)
        split_config={'operations':[],'size':1,'names':[f'1.46 PINTURA {i:03d}' for i in range(1,43)],'manifest':True}
        with post_json(f"/api/documents/{splitdoc['id']}/split-plan",split_config) as r:review=json.load(r)
        split_config['review_token']=review['review_token']
        request=urllib.request.Request(url+f"/api/documents/{splitdoc['id']}/split",data=json.dumps(split_config).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=120) as r:split_result=r.read()
        split_archive=folder/'verified-split.zip';split_archive.write_bytes(split_result)
        with ZipFile(BytesIO(split_result)) as z:
            receipt=json.loads(z.read('reapdf-division.json'));assert len(receipt['parts'])==42 and receipt['native_content_verified']
            assert all(p['tagged'] and p['name']==f'1.46 PINTURA {i:03d}.pdf' for i,p in enumerate(receipt['parts'],1))
        subprocess.run([str(executable),'-I','-c',"import pymupdf as f,sys;from zipfile import ZipFile;s=f.open(sys.argv[1]);z=ZipFile(sys.argv[2]);assert len(z.namelist())==43;\nfor i in range(42):\n d=f.open(stream=z.read(f'1.46 PINTURA {i+1:03d}.pdf'));assert len(d)==1 and d[0].get_text()==s[i].get_text() and d[0].get_pixmap().samples==s[i].get_pixmap().samples;assert d.xref_get_key(d.pdf_catalog(),'StructTreeRoot')[0]!='null'",str(fixture),str(split_archive)],check=True,timeout=45)
        # Usar el mismo intérprete incluido: el verificador host no necesita PyMuPDF.
        check=folder/'comprobacion.pdf';check.write_bytes(pdf)
        subprocess.run([str(executable),'-I','-c',"import pymupdf as f,sys;d=f.open(sys.argv[1]);assert 'Portable' in d[0].get_text();assert 'Texto original' not in d[0].get_text()",str(check)],check=True,timeout=20)
        return {**report,'http_upload_export':'ok','projects_recovery_print':'ok','packaged_scheduled_worker':'ok','packaged_split_workflow':'ok','packaged_split_pages':42,'bundled_engine_verified':os.name=='nt' and bundled,'windows_execution_verified':False}
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


def close_diagnostics(launcher_pid,qt_pid):
    """Owned process names and this synthetic candidate's startup log only."""
    try:
        command=(f'$reapdfIds=@({int(launcher_pid)},{int(qt_pid)});'
                 '$reapdfRows=@(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name);'
                 'for($reapdfDepth=0;$reapdfDepth -lt 8;$reapdfDepth++){'
                 '$reapdfChildren=@($reapdfRows | Where-Object {$reapdfIds -contains $_.ParentProcessId} | ForEach-Object {$_.ProcessId});'
                 '$reapdfIds=@($reapdfIds+$reapdfChildren | Select-Object -Unique)};'
                 '$reapdfRows | Where-Object {$reapdfIds -contains $_.ProcessId} | ConvertTo-Json -Compress')
        try:
            run=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=10)
            print('CLOSE_PROCESS_DIAGNOSTICS:',run.stdout.strip() or run.stderr.strip(),flush=True)
        except (OSError,subprocess.TimeoutExpired) as exc:print('PROCESS_DIAGNOSTICS_UNAVAILABLE:',type(exc).__name__,flush=True)
        import ctypes
        from ctypes import wintypes as w
        user=ctypes.WinDLL('user32');callback=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM);observed=[]
        user.EnumWindows.argtypes=[callback,w.LPARAM];user.EnumChildWindows.argtypes=[w.HWND,callback,w.LPARAM]
        user.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)];user.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int]
        def text(handle):
            value=ctypes.create_unicode_buffer(2048);user.GetWindowTextW(handle,value,2048);return value.value
        def visit(handle,unused):
            owner=w.DWORD();user.GetWindowThreadProcessId(handle,ctypes.byref(owner))
            if owner.value not in [launcher_pid,qt_pid]:return True
            children=[]
            def child(handle,unused):
                if len(children)<32:children.append(text(handle))
                return True
            user.EnumChildWindows(handle,callback(child),0);observed.append({'pid':owner.value,'title':text(handle),'children':children});return True
        user.EnumWindows(callback(visit),0);print('OWNED_WINDOW_DIAGNOSTICS:',json.dumps(observed,ensure_ascii=True),flush=True)
        root=os.environ.get('LOCALAPPDATA')
        if root:
            log=Path(root)/'Reapdf/logs'/f'inicio-{int(launcher_pid)}.log'
            if log.is_file():print('CLOSE_OWNED_STARTUP_LOG:',log.read_bytes()[-8000:].decode('utf-8',errors='replace').encode('ascii',errors='backslashreplace').decode('ascii'),flush=True)
    except Exception as exc:print('CLOSE_DIAGNOSTICS_UNAVAILABLE:',type(exc).__name__,str(exc),flush=True)


def compiled_gui_check(folder,journey='basic'):
    if os.name!='nt':raise RuntimeError('La comprobación del ejecutable exige Windows.')
    root=Path(__file__).resolve().parents[1];node=shutil.which('node')
    if not node or not (root/'node_modules/@playwright/test').is_dir():raise RuntimeError('La verificación gráfica interna requiere Node y npm ci en el checkout de pruebas.')
    with socket.socket() as reserved:reserved.bind(('127.0.0.1',0));port=reserved.getsockname()[1]
    sample=folder/'ejemplos/reapdf-demo.pdf'
    if journey in ['spacing_flow','pagination']:
        from tests.test_mixed_paragraph_spacing import source
        sample=folder/(journey+'-fixture.pdf');sample.write_bytes(source(nested=True))
    if journey=='colored_ranges':
        sample=folder/'colored-range-fixture.pdf'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_colored_form_sample.py'),str(sample)],check=True,timeout=30)
    if journey=='shared_choices':
        sample=folder/'shared-choices-fixture.pdf'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_shared_choice_sample.py'),str(sample)],check=True,timeout=30)
    if journey=='form_datetime':
        sample=folder/'form-datetime-fixture.pdf'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_datetime_form_sample.py'),str(sample)],check=True,timeout=30)
    if journey=='byte_split':
        sample=folder/'byte-split-fixture.pdf'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_byte_split_sample.py'),str(sample)],check=True,timeout=30)
    if journey=='paragraph_geometry':
        sample=folder/'paragraph-geometry-fixture.pdf'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_paragraph_format_sample.py'),str(sample),'--geometry','--css'],check=True,timeout=30)
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_paragraph_format_sample.py'),str(sample)+'.continuation.pdf','--geometry','--css'],check=True,timeout=30)
    if journey=='paragraph_format':
        sample=folder/'paragraph-format-fixture.pdf'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_paragraph_format_sample.py'),str(sample)],check=True,timeout=30)
    if journey=='quick_text':
        sample=folder/'quick-text-fixture.pdf'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_semantic_text_sample.py'),str(sample),'quick'],check=True,timeout=30)
    if journey in ['semantic_stream','semantic_outer','native_format']:
        sample=folder/(journey+'-fixture.pdf')
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_semantic_text_sample.py'),str(sample),'stream' if journey!='semantic_outer' else 'outer'],check=True,timeout=30)
    if journey=='tagged_paragraph':
        sample=folder/'tagged-paragraph-fixture.pdf'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_tagged_paragraph_sample.py'),str(sample)],check=True,timeout=30)
    if journey=='variable_shear':
        sample=folder/'variable-shear-fixture.pdf'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_sheared_paragraph_sample.py'),str(sample)],check=True,timeout=30)
    if journey=='tagged_images':
        sample=folder/'tagged-images-fixture.pdf'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_tagged_image_sample.py'),str(sample)],check=True,timeout=30)
    if journey=='word_manual_columns':
        word=folder/'word-manual-columns-fixture.docx'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_word_manual_columns_sample.py'),str(word)],check=True,timeout=30)
    if journey=='word_columns':
        word=folder/'word-columns-fixture.docx'
        subprocess.run([str(folder/'runtime/python.exe'),'-I',str(root/'scripts/create_word_columns_sample.py'),str(word)],check=True,timeout=30)
    original=sample.read_bytes();output=folder/('comprobacion-'+journey+('.zip' if journey=='byte_split' else '.pdf'))
    from uuid import uuid4
    state=folder/('.gui-verification-state-'+uuid4().hex)
    env={**os.environ,'REAPDF_DATA_DIR':str(state),'REAPDF_INSTANCE_NAMESPACE':str(state),'QTWEBENGINE_REMOTE_DEBUGGING':f'127.0.0.1:{port}','REAPDF_TRACE_LIFECYCLE':'1'}
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
        driver='smoke_packaged_colored_ranges.mjs' if journey=='colored_ranges' else 'smoke_packaged_shared_choices.mjs' if journey=='shared_choices' else 'smoke_packaged_form_datetime.mjs' if journey=='form_datetime' else 'smoke_packaged_byte_split.mjs' if journey=='byte_split' else 'smoke_packaged_paragraph_geometry.mjs' if journey=='paragraph_geometry' else 'smoke_packaged_paragraph_format.mjs' if journey=='paragraph_format' else 'smoke_packaged_quick_text.mjs' if journey=='quick_text' else 'smoke_packaged_semantic_text.mjs' if journey in ['semantic_stream','semantic_outer','native_format'] else 'smoke_packaged_word_columns.mjs' if journey in ['word_columns','word_manual_columns'] else 'smoke_packaged_tagged_images.mjs' if journey=='tagged_images' else 'smoke_packaged_spacing_flow.mjs' if journey in ['spacing_flow','pagination','variable_shear','tagged_paragraph'] else 'smoke_packaged_window.mjs'
        run=subprocess.run([node,str(root/'scripts'/driver),endpoint,str(output)]+([str(sample)] if journey=='paragraph_geometry' else ['pagination'] if journey=='pagination' else ['shear'] if journey=='variable_shear' else ['tagged'] if journey=='tagged_paragraph' else [str(word),'manual'] if journey=='word_manual_columns' else [str(word)] if journey=='word_columns' else ['format' if journey=='native_format' else 'stream' if journey=='semantic_stream' else 'outer'] if journey in ['semantic_stream','semantic_outer','native_format'] else []),cwd=root,capture_output=True,text=True,timeout=100)
        if run.returncode or 'PASS:' not in run.stdout:raise RuntimeError('Falló el recorrido del ejecutable: '+run.stdout+run.stderr)
        verification="import pymupdf as f,sys;d=f.open(sys.argv[1]);assert len(d)==2;assert 'Ejecutable' in d[0].get_text();assert 'Texto original' not in d[0].get_text();assert 'Segunda pagina' in d[1].get_text()"
        if journey=='spacing_flow':verification="import pymupdf as f,sys;d=f.open(sys.argv[1]);a=f.open(sys.argv[2]);assert len(d)==3;v=''.join((d[0].get_text()+d[2].get_text()).split());assert v.count('HELLO')==13 and v.count('TEXT')==9;assert 'HELLO' in d[2].get_text() and 'TEXT' in d[2].get_text();assert a[1].get_pixmap().samples==d[1].get_pixmap().samples"
        if journey=='variable_shear':verification="import pymupdf as f,sys;from backend.native_text import native_model;d=f.open(sys.argv[1]);a=f.open(sys.argv[2]);assert len(d)==3;v=''.join((d[0].get_text()+d[2].get_text()).split());assert v.count('HELLO')==12 and v.count('TEXT')==6;assert a[1].get_pixmap().samples==d[1].get_pixmap().samples;before=[r for r in native_model(a,0,a[0].rect)[1] if r['text'] in ['HELLO ','TEXT']];after=[r for i in [0,2] for r in native_model(d,i,d[i].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']];key=lambda r:(r['font'],r['color'],round(r['display_size'],3),tuple(round(v,4) for v in r['_geometry']['matrix'][:4]));assert all(r['editable'] for r in after);assert {key(r) for r in before}=={key(r) for r in after}"
        if journey=='tagged_paragraph':
            verification="import pymupdf as f,sys;from backend.structure_editing import reading_preview;from backend.native_text import native_model;d=f.open(sys.argv[1]);a=f.open(sys.argv[2]);assert len(d)==3;v=''.join((d[0].get_text()+d[2].get_text()).split());assert v.count('HELLO')==12 and v.count('TEXT')==6;assert a[1].get_pixmap().samples==d[1].get_pixmap().samples;assert all(reading_preview(open(sys.argv[1],'rb').read(),[],i)['untagged_blocks']==0 for i in range(len(d)));before=[r for r in native_model(a,0,a[0].rect)[1] if r['text'] in ['HELLO ','TEXT']];after=[r for i in [0,2] for r in native_model(d,i,d[i].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']];key=lambda r:(r['font'],r['color'],round(r['display_size'],3),tuple(round(v,4) for v in r['_geometry']['matrix'][:4]));assert all(r['editable'] for r in after);assert {key(r) for r in before}=={key(r) for r in after}"
        if journey=='word_columns':
            verification="import pymupdf as f,sys;d=f.open(sys.argv[1]);text=''.join(p.get_text() for p in d);assert len(d)>=2;assert all(text.count(f'ITEM{i:03d}')==1 for i in range(45));target=next(p.number for p in d if p.search_for('DESTINATIONWORD'));links=[l for p in d for l in p.get_links() if l['kind']==f.LINK_GOTO];assert len(links)==1 and links[0]['page']==target;assert len({round(r.x0) for r in d[0].search_for('ITEM')})==2;assert all(len([g for g in p.get_drawings() if g['rect'].height>100 and g['rect'].width<1])==1 for p in d)"
        if journey=='colored_ranges':
            verification="""import pymupdf as f,sys
from backend.forms import form_model
a=f.open(sys.argv[2]);old=next(a[0].widgets())
for path,value,display,color in [(sys.argv[1],'-12.5','(12.50 EUR)',(1,0,0)),(sys.argv[1]+'.positive.pdf','4','4.00 EUR',(0,0,0))]:
 d=f.open(path);r=form_model(d)['fields'][0];w=next(d[0].widgets())
 assert r['editable'] and r['value']==value and r['display_value']==display and tuple(w.text_color)==color and display in d[0].get_text()
 assert a[1].get_pixmap().samples==d[1].get_pixmap().samples
 assert all(a.xref_get_key(old.xref,'AA/'+e+'/JS')==d.xref_get_key(w.xref,'AA/'+e+'/JS') for e in ['F','K','V'])
"""
        if journey=='shared_choices':
            verification="import pymupdf as f,sys;from backend.forms import form_model;a=f.open(sys.argv[2]);d=f.open(sys.argv[1]);r=form_model(d)['fields'];assert len(r)==2 and all(v['editable'] and v['value']=='LIM' and v['group_size']==2 for v in r);assert d.xref_get_key(r[0]['group'],'V')==('string','LIM') and d.xref_get_key(r[0]['group'],'I')==('array','[1]');assert all(d.xref_get_key(v['xref'],'V')[0]=='null' and d.xref_get_key(v['xref'],'I')[0]=='null' and 'Lima' in d[v['page']].get_text() for v in r);assert a[2].get_pixmap().samples==d[2].get_pixmap().samples"
        if journey=='form_datetime':
            verification="""import pymupdf as f,sys
from backend.forms import form_model
from backend.form_actions import actions
from backend.form_structure import field_structure
a=f.open(sys.argv[2]);d=f.open(sys.argv[1]);old=form_model(a)['fields'][0];row=form_model(d)['fields'][0];assert row['editable'] and row['value']=='06/11/2026 10:30:45' and row['display_value']==row['value'] and row['value'] in d[0].get_text();assert a[1].get_pixmap().samples==d[1].get_pixmap().samples
_,own_a,_,_=field_structure(a);_,own_b,_,_=field_structure(d);assert actions(a,own_a[old['xref']]['chain'])==actions(d,own_b[row['xref']]['chain'])
for event in ['F','K']:
 kind,ref=d.xref_get_key(row['xref'],'AA/'+event+'/JS');assert kind=='xref' and d.xref_is_stream(int(ref.split()[0]))
"""
        if journey=='word_manual_columns':
            verification="""import pymupdf as f,sys
d=f.open(sys.argv[1]);assert len(d)==2
labels=['FIRSTCOLLINK','SECONDCOLLINK','NEXTPAGELEFT','NEXTPAGERIGHT','DESTINATIONWORD'];locations={word:[(p.number,r) for p in d for r in p.search_for(word)] for word in labels}
assert all(len(v)==1 for v in locations.values())
assert [locations[word][0][0] for word in labels]==[0,0,1,1,1]
assert locations['FIRSTCOLLINK'][0][1].x0<locations['SECONDCOLLINK'][0][1].x0 and locations['NEXTPAGELEFT'][0][1].x0<locations['NEXTPAGERIGHT'][0][1].x0
assert abs(locations['FIRSTCOLLINK'][0][1].x0-locations['NEXTPAGELEFT'][0][1].x0-18)<1
links=[l for p in d for l in p.get_links() if l['kind']==f.LINK_GOTO];assert len(links)==2 and all(l['page']==1 for l in links)
spans=[s for p in d for b in p.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'] if 'COLLINK' in s['text']];assert len(spans)==2 and all('Bold' in s['font'] and s['color']==0x214eaa for s in spans)
"""
        if journey=='byte_split':
            verification="""import pymupdf as f,sys,json
from zipfile import ZipFile
source=f.open(sys.argv[2])
with ZipFile(sys.argv[1]) as z:
 r=json.loads(z.read('reapdf-division.json'));assert r['max_bytes_per_pdf']==60000 and r['native_content_verified'] and len(r['parts'])==3
 for i,p in enumerate(r['parts']):
  data=z.read(p['name']);assert len(data)==p['bytes']<=60000 and p['source_pages']==[i+1] and p['name']==f'1.46 PINTURA {i+1:03d}.pdf'
  with f.open(stream=data) as d:assert len(d)==1 and d[0].get_pixmap().samples==source[i].get_pixmap().samples and d[0].get_text()==source[i].get_text()
"""
        if journey=='paragraph_geometry':
            verification="""import pymupdf as f,sys
from backend.native_text import native_model
from backend.semantic_text import tree
from backend.text_typography import declarations
from backend.affine_text import polygon,bounds
d=f.open(sys.argv[1]);a=f.open(sys.argv[2]);n=f.mupdf;rows=native_model(d,0,d[0].rect)[1];t=tree(d);boxes=0
for owner,rec in t.records.items():
 for _,_,_,attr in declarations(d,rec['object']):
  box=n.pdf_dict_gets(attr,'BBox')
  if n.pdf_is_null(box):continue
  boxes+=1;actual=f.Rect([n.pdf_to_real(n.pdf_array_get(box,i)) for i in range(4)]);expected=f.Rect()
  for r in rows:
   leaf=r['_semantic_identity']
   if owner in t.records[leaf]['chain']+[leaf]:
    assert r['editable'] and abs(r['size']-22)<.01;expected|=bounds(polygon(r['_geometry']))*~d[0].transformation_matrix
  assert max(abs(x-y) for x,y in zip(actual,expected))<.05
  assert abs(n.pdf_to_real(n.pdf_dict_gets(attr,'Width'))-actual.width)<.02 and abs(n.pdf_to_real(n.pdf_dict_gets(attr,'Height'))-actual.height)<.02
assert boxes==2 and a[1].get_pixmap().samples==d[1].get_pixmap().samples
assert sum(1 for rec in t.records.values() for _,_,_,attr in declarations(d,rec['object']) if n.pdf_to_name(n.pdf_dict_gets(attr,'O'))=='CSS-1.00' and n.pdf_to_text_string(n.pdf_dict_gets(attr,'font-family'))=='DejaVu Serif')>=2
c=f.open(sys.argv[1]+'.continued.pdf');assert sum(p.get_text().count('HELLO') for p in c)==15
for number in [0,1]:
 changed=[r for r in native_model(c,number,c[number].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']]
 assert changed and all(r['editable'] and abs(r['size']-13)<.01 and r['font'].startswith('DejaVuSerif') for r in changed)
assert a[2].get_pixmap().samples==c[2].get_pixmap().samples
ct=tree(c);boxes=0
for owner,rec in ct.records.items():
 for _,_,_,attr in declarations(c,rec['object']):
  box=n.pdf_dict_gets(attr,'BBox')
  if n.pdf_is_null(box):continue
  assert len({pg for pg,_,_ in ct.refs[owner]})==1;boxes+=1
assert boxes>=2
"""
        if journey=='paragraph_format':
            verification="import pymupdf as f,sys;from backend.native_text import native_model;from backend.semantic_text import tree;d=f.open(sys.argv[1]);a=f.open(sys.argv[2]);rows=[r for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text']];assert rows and all(r['editable'] and abs(r['size']-12)<.01 for r in rows);assert any(r['font']=='DejaVuSerif-Bold' for r in rows) and any(r['font']=='DejaVuSerif-Italic' for r in rows);assert 'Ω' in d[0].get_text();t=tree(d);n=f.mupdf;assert n.pdf_to_text_string(n.pdf_dict_gets(n.pdf_dict_gets(n.pdf_dict_gets(t.root,'ClassMap'),'Shared'),'FontFamily'))=='Helvetica';assert d.xref_get_key(t.owners[(d[0].xref,0,0)][0],'C')==('name','/Shared');assert a[1].get_pixmap().samples==d[1].get_pixmap().samples"
        if journey=='native_format':
            verification="import pymupdf as f,sys;from backend.native_text import native_model;from backend.semantic_text import capture;d=f.open(sys.argv[1]);a=f.open(sys.argv[2]);r=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HOLA Ω');assert r['editable'] and r['stream_tagged'] and r['font']=='DejaVuSerif-Bold' and abs(r['size']-13)<.01 and r['accessible_text']=='Updated accessible';assert a[1].get_pixmap().samples==d[1].get_pixmap().samples;assert capture(a,0)['graph']['graph']==capture(d,0)['graph']['graph'];assert a[0].search_for('UNCHANGED')==d[0].search_for('UNCHANGED')"
        if journey=='semantic_stream':
            verification="import pymupdf as f,sys;from backend.native_text import native_model;from backend.semantic_text import capture;d=f.open(sys.argv[1]);a=f.open(sys.argv[2]);assert len(d)==len(a)==2;assert 'Updated accessible' in d[0].get_text();r=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HOLA');assert r['editable'] and r['stream_tagged'] and r['accessible_text']=='Updated accessible';assert capture(a,0)['graph']['graph']==capture(d,0)['graph']['graph'];assert a[1].get_pixmap().samples==d[1].get_pixmap().samples;assert a[0].search_for('UNCHANGED')==d[0].search_for('UNCHANGED')"
        if journey=='semantic_outer':
            verification="import pymupdf as f,sys;from backend.structure_editing import reading_preview;from backend.native_text import native_model;d=f.open(sys.argv[1]);a=f.open(sys.argv[2]);assert len(d)==len(a)==2;assert d[0].get_text().count('HELLO')==1;assert sum(p.get_text().count('HOLA') for p in d)==20;assert all(b['tagged'] for b in reading_preview(open(sys.argv[1],'rb').read(),[],1)['blocks'] if 'HOLA' in b['text']);assert a[0].search_for('UNCHANGED')==d[0].search_for('UNCHANGED');assert a[1].search_for('OTHER PAGE')==d[1].search_for('OTHER PAGE');assert a[0].search_for('HELLO')[-1]==d[0].search_for('HELLO')[-1]"
        if journey=='quick_text':
            verification="import pymupdf as f,sys;from backend.native_text import native_model;d=f.open(sys.argv[1]);gone=f.open(sys.argv[1]+'.deleted.pdf');assert '1000000002' in d[0].get_text() and '1000000001' not in d[0].get_text();r=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='1000000002');assert r['accessible_text']=='1000000002';assert '1000000002' not in gone[0].get_text() and '1000000002' not in gone[0].get_text(flags=f.TEXTFLAGS_TEXT|f.TEXT_IGNORE_ACTUALTEXT);assert 'UNCHANGED' in gone[0].get_text()"
        if journey not in ['pagination','tagged_images']:subprocess.run([str(folder/'runtime/python.exe'),'-I','-c',verification,str(output),str(sample)],check=True,timeout=20)
        if journey=='pagination':
            subprocess.run([str(folder/'runtime/python.exe'),'-I','-c',"import pymupdf as f,sys;d=f.open(sys.argv[1]);a=f.open(sys.argv[2]);assert len(d)>len(a);v=''.join((d[0].get_text()+''.join(d[i].get_text() for i in range(len(a),len(d)))).split());assert v.count('HELLO')==13 and v.count('TEXT')==9;assert all(a[i].get_pixmap().samples==d[i].get_pixmap().samples for i in range(1,len(a)))",str(output),str(sample)],check=True,timeout=20)
        if journey=='tagged_images':
            check_script="""import pymupdf as f,sys
source=f.open(sys.argv[1]);before=source[0].get_image_info(hashes=True);moved=None
for index,path in enumerate(sys.argv[2:]):
 d=f.open(path);assert len(d)==2 and d[0].get_text('dict',flags=f.TEXTFLAGS_TEXT)==source[0].get_text('dict',flags=f.TEXTFLAGS_TEXT);assert d[1].get_pixmap().samples==source[1].get_pixmap().samples
 images=d[0].get_image_info(hashes=True);assert len(images)==(2 if index<2 else 1);assert images[-1]['bbox']==before[1]['bbox'] and images[-1]['digest']==before[1]['digest']
 n=f.mupdf;pdf=f._as_pdf_document(d);root=n.pdf_dict_gets(n.pdf_dict_gets(n.pdf_trailer(pdf),'Root'),'StructTreeRoot');figures=[]
 def walk(v):
  if n.pdf_is_array(v):
   for i in range(n.pdf_array_len(v)):walk(n.pdf_array_get(v,i))
  elif n.pdf_is_dict(v):
   if n.pdf_to_name(n.pdf_dict_gets(v,'S'))=='Figure':figures.append(v)
   walk(n.pdf_dict_gets(v,'K'))
 walk(n.pdf_dict_gets(root,'K'));assert len(figures)==(2 if index<2 else 1)
 assert n.pdf_to_text_string(n.pdf_dict_gets(figures[-1],'Alt'))=='Other diagram'
 if index==0:assert images[0]['digest']==before[0]['digest'] and images[0]['bbox']!=before[0]['bbox'];moved=images[0]['bbox']
 if index==1:assert images[0]['bbox']==moved and images[0]['digest']!=before[0]['digest'];assert n.pdf_to_text_string(n.pdf_dict_gets(figures[0],'Alt'))=='New green diagram'
 if index==2:
  nums=n.pdf_dict_gets(n.pdf_dict_gets(root,'ParentTree'),'Nums');row=n.pdf_array_get(nums,1);assert n.pdf_is_null(n.pdf_array_get(row,1));assert b'MCID 1' not in d[0].read_contents()
"""
            subprocess.run([str(folder/'runtime/python.exe'),'-I','-c',check_script,str(sample),str(output.with_name(output.stem+'-moved.pdf')),str(output.with_name(output.stem+'-replaced.pdf')),str(output)],check=True,timeout=30)
        if sample.read_bytes()!=original:raise RuntimeError('La comprobación modificó el PDF de origen.')
        import ctypes
        from ctypes import wintypes as w
        user=ctypes.WinDLL('user32');user.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];user.PostMessageW(hwnd,0x0010,0,0)
        def windows():
            result=[];callback=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
            user.EnumWindows.argtypes=[callback,w.LPARAM];user.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int];user.GetClassNameW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int];user.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)]
            def visit(handle,unused):
                owner=w.DWORD();user.GetWindowThreadProcessId(handle,ctypes.byref(owner))
                if owner.value==pid:
                    title=ctypes.create_unicode_buffer(512);kind=ctypes.create_unicode_buffer(256);user.GetWindowTextW(handle,title,512);user.GetClassNameW(handle,kind,256);result.append({'hwnd':handle,'pid':owner.value,'title':title.value,'class':kind.value})
                return True
            user.EnumWindows(callback(visit),0);return result
        def key(handle,value):
            user.PostMessageW(handle,0x0100,value,0);user.PostMessageW(handle,0x0101,value,0)
        from scripts.compiled_close import wait_closed
        discarded=wait_closed(process,pid,windows,key)
        print('CLOSE:',journey,'native discard confirmation:',discarded,flush=True)
        if journey in ['variable_shear','tagged_paragraph'] and not discarded:raise RuntimeError('El recorrido nuevo no comprobó la confirmación nativa de descartar el borrador de prueba.')
        print(run.stdout.strip())
        return {'compiled_exe_window_and_edit':'ok','compiled_exe_normal_close':'ok',**({'compiled_exe_affine_spacing_flow':'ok'} if journey=='spacing_flow' else {'compiled_exe_automatic_pagination':'ok'} if journey=='pagination' else {'compiled_exe_tagged_images':'ok'} if journey=='tagged_images' else {'compiled_exe_variable_shear':'ok'} if journey=='variable_shear' else {'compiled_exe_tagged_paragraph':'ok'} if journey=='tagged_paragraph' else {'compiled_exe_word_manual_columns':'ok'} if journey=='word_manual_columns' else {'compiled_exe_word_columns':'ok'} if journey=='word_columns' else {'compiled_exe_semantic_stream':'ok'} if journey=='semantic_stream' else {'compiled_exe_semantic_outer':'ok'} if journey=='semantic_outer' else {'compiled_exe_colored_ranges':'ok'} if journey=='colored_ranges' else {'compiled_exe_shared_choices':'ok'} if journey=='shared_choices' else {'compiled_exe_form_datetime':'ok'} if journey=='form_datetime' else {'compiled_exe_byte_split':'ok'} if journey=='byte_split' else {'compiled_exe_paragraph_geometry':'ok'} if journey=='paragraph_geometry' else {'compiled_exe_paragraph_format':'ok'} if journey=='paragraph_format' else {'compiled_exe_native_format':'ok'} if journey=='native_format' else {'compiled_exe_quick_text':'ok'} if journey=='quick_text' else {}),'qt_process_pid':pid,'external_browser_used':False,'native_save_in_this_check':False,'native_discard_confirmation':discarded,'windows_execution_verified':True}
    except Exception:
        close_diagnostics(process.pid,locals().get('pid',process.pid))
        raise
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
        folder=Path(tmp)/'Reapdf-portable';native=native_check(folder);basic=compiled_gui_check(folder);spacing=compiled_gui_check(folder,'spacing_flow');gui=compiled_gui_check(folder,'pagination');images=compiled_gui_check(folder,'tagged_images');shear=compiled_gui_check(folder,'variable_shear');tagged=compiled_gui_check(folder,'tagged_paragraph');word_columns=compiled_gui_check(folder,'word_columns');semantic_stream=compiled_gui_check(folder,'semantic_stream');semantic_outer=compiled_gui_check(folder,'semantic_outer');quick_text=compiled_gui_check(folder,'quick_text');native_format=compiled_gui_check(folder,'native_format');paragraph_format=compiled_gui_check(folder,'paragraph_format');paragraph_geometry=compiled_gui_check(folder,'paragraph_geometry');byte_split=compiled_gui_check(folder,'byte_split');manual_columns=compiled_gui_check(folder,'word_manual_columns');form_datetime=compiled_gui_check(folder,'form_datetime');shared_choices=compiled_gui_check(folder,'shared_choices');colored_ranges=compiled_gui_check(folder,'colored_ranges');basic_repetitions=[basic,compiled_gui_check(folder),compiled_gui_check(folder)];result={**native,**spacing,**gui,**images,**shear,**tagged,**word_columns,**semantic_stream,**semantic_outer,**quick_text,**native_format,**paragraph_format,**paragraph_geometry,**byte_split,**manual_columns,**form_datetime,**shared_choices,**colored_ranges,'compiled_gui_independent_runs':20,'compiled_basic_repetitions':len(basic_repetitions),'archive_sha256':hashlib.sha256(Path(args.archive).read_bytes()).hexdigest(),'physical_print_verified':False,'human_acceptance':False}
        from scripts.publish_windows_report import source_objects
        root=Path(__file__).resolve().parents[1]
        result.update(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),source_git_objects=source_objects(root),source_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()))
        if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result))

if __name__=='__main__':main()
