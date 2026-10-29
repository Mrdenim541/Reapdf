"""Construir un ZIP offline Windows x64, incluido Python y DLL de ejecución."""
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import ZipFile,ZIP_DEFLATED
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parent.parent


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_name(name):
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        raise ValueError('Ruta no válida en el archivo: '+name)
    return path


def pe_machine(data):
    if data[:2]!=b'MZ' or len(data)<64:raise ValueError('Binario Windows PE no válido.')
    offset=struct.unpack_from('<I',data,60)[0]
    if data[offset:offset+4]!=b'PE\x00\x00':raise ValueError('Cabecera PE no válida.')
    return struct.unpack_from('<H',data,offset+4)[0]


def copy_runtime(archive,destination):
    with ZipFile(archive) as z:
        for info in z.infolist():
            path=safe_name(info.filename)
            if info.is_dir() or not path.parts or path.parts[0]!='tools':continue
            if path.parts[1:3]==('Lib','site-packages') or path.parts[1:2]==('Scripts',):continue
            target=destination.joinpath(*path.parts[1:]);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(z.read(info))
    (destination/'python313._pth').write_text('.\nLib\nDLLs\nLib/site-packages\n../app\nimport site\n',encoding='utf-8')


def copy_wheel(archive,runtime):
    site=runtime/'Lib'/'site-packages'
    with ZipFile(archive) as z:
        for info in z.infolist():
            path=safe_name(info.filename)
            if info.is_dir():continue
            if path.parts[0].endswith('.data'):
                scheme=path.parts[1]
                if scheme in {'purelib','platlib'}:target=site.joinpath(*path.parts[2:])
                elif scheme=='data':target=runtime.joinpath(*path.parts[2:])
                elif scheme=='scripts':target=runtime/'Scripts'/Path(*path.parts[2:])
                else:raise ValueError('Esquema de wheel no admitido: '+scheme)
            else:target=site.joinpath(*path.parts)
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and target.read_bytes()!=z.read(info):raise ValueError('Conflicto al incorporar '+str(path))
            target.write_bytes(z.read(info))


def validate_payload(folder,config):
    required=['Reapdf.exe','runtime/python.exe','runtime/python313.dll','runtime/vcruntime140.dll','runtime/msvcp140.dll',
              'runtime/Lib/encodings/__init__.py','runtime/Lib/site-packages/pymupdf/mupdfcpp64.dll',
              'runtime/Lib/site-packages/pydantic_core/_pydantic_core.cp313-win_amd64.pyd',
              'runtime/Lib/site-packages/uvicorn/__init__.py','runtime/Lib/site-packages/colorama/__init__.py',
              'app/backend/app.py','app/web/dist/index.html','app/launcher.py','app/desktop.py','app/native_window.py','app/native_print.py','app/native_save.py','app/single_instance.py','app/parent_pipe.py','Iniciar-Reapdf.cmd','Abrir-en-navegador.cmd']
    for name in required:
        if not (folder/name).is_file():raise ValueError('Falta un archivo portable: '+name)
    for path in (folder/'runtime').rglob('*'):
        if path.is_file() and path.suffix.lower() in {'.dll','.pyd','.exe'} and pe_machine(path.read_bytes())!=0x8664:
            raise ValueError('Binario incompatible con Windows x64: '+str(path))
    native=(folder/'Reapdf.exe').read_bytes()
    if pe_machine(native)!=0x8664:raise ValueError('El lanzador debe ser Windows x64.')
    native_offset=struct.unpack_from('<I',native,60)[0]
    if struct.unpack_from('<H',native,native_offset+24+68)[0]!=2:raise ValueError('El lanzador debe ser GUI, sin consola.')
    for lang in ['eng','spa']:
        if not (folder/'app'/'resources'/'tessdata'/f'{lang}.traineddata').is_file():raise ValueError('Falta un idioma OCR.')
    for item in config['wheels']:
        expected=item['name'].replace('-','_')+'-'+item['version']+'.dist-info'
        if not (folder/'runtime'/'Lib'/'site-packages'/expected/'METADATA').is_file():raise ValueError('Dependencia incompleta: '+expected)


def build(wheelhouse=None,cache=None,output=None):
    config=json.loads((ROOT/'portable'/'dependencies-windows.json').read_text())
    out=ROOT/'entregas';out.mkdir(exist_ok=True)
    cache=Path(cache or out/'cache');cache.mkdir(parents=True,exist_ok=True)
    runtime=cache/f"python.{config['python']['version']}.nupkg"
    if not runtime.is_file():
        with urllib.request.urlopen(config['python']['url'],timeout=60) as response:runtime.write_bytes(response.read())
    if digest(runtime)!=config['python']['sha256']:raise ValueError('La descarga de Python no coincide con el SHA256 fijado.')
    wheelhouse=Path(wheelhouse or cache/'windows-wheels');wheelhouse.mkdir(parents=True,exist_ok=True)
    if not all((wheelhouse/w['filename']).is_file() for w in config['wheels']):
        subprocess.run([sys.executable,'-m','pip','download','--only-binary=:all:','--require-hashes','--no-deps',
                        '--platform','win_amd64','--python-version','313','--implementation','cp','--abi','cp313',
                        '--dest',str(wheelhouse),'-r',str(ROOT/'portable'/'requirements-windows.lock')],check=True)
    for item in config['wheels']:
        if digest(wheelhouse/item['filename'])!=item['sha256']:raise ValueError('Wheel no verificado: '+item['filename'])
    if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
    from scripts.build_windows_launcher import build as build_launcher
    native=build_launcher()
    with TemporaryDirectory(prefix='reapdf-portable-') as temporary:
        folder=Path(temporary)/'Reapdf-portable';folder.mkdir()
        shutil.copy2(native,folder/'Reapdf.exe')
        shutil.copy2(native.with_suffix('.build.json'),folder/'LANZADOR.json')
        copy_runtime(runtime,folder/'runtime')
        for item in config['wheels']:copy_wheel(wheelhouse/item['filename'],folder/'runtime')
        app=folder/'app';app.mkdir()
        shutil.copytree(ROOT/'resources',app/'resources')
        shutil.copytree(ROOT/'backend',app/'backend',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copytree(ROOT/'web'/'dist',app/'web'/'dist')
        shutil.copytree(ROOT/'web'/'src',app/'web'/'src')
        for name in ['package.json','package-lock.json','requirements-lock.txt']:shutil.copy2(ROOT/name,app/name)
        shutil.copy2(ROOT/'portable'/'launcher.py',app/'launcher.py')
        for module in ['desktop.py','native_window.py','native_print.py','native_save.py','single_instance.py','parent_pipe.py','windows_association.py']:
            shutil.copy2(ROOT/'portable'/module,app/module)
        shutil.copytree(ROOT/'docs',folder/'docs')
        shutil.copy2(ROOT/'portable'/'LEEME.md',folder/'LEEME.md')
        shutil.copy2(ROOT/'portable'/'dependencies-windows.json',folder/'DEPENDENCIAS.json')
        shutil.copy2(ROOT/'portable'/'requirements-windows.lock',folder/'requirements-windows.lock')
        source=folder/'fuentes';source.mkdir()
        for directory in ['scripts','tests','portable','.github']:
            shutil.copytree(ROOT/directory,source/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for directory in ['backend','docs','resources']:
            shutil.copytree(ROOT/directory,source/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copytree(ROOT/'web'/'src',source/'web'/'src')
        for name in ['index.html','vite.config.js']:shutil.copy2(ROOT/'web'/name,source/'web'/name)
        for name in ['README.md','requirements.txt','requirements-dev.txt','requirements-lock.txt','requirements-desktop.txt','package.json','package-lock.json','.gitignore']:
            shutil.copy2(ROOT/name,source/name)
        for name in ['index.html','vite.config.js']:shutil.copy2(ROOT/'web'/name,app/'web'/name)
        demo=folder/'ejemplos'/'reapdf-demo.pdf';demo.parent.mkdir()
        subprocess.run([sys.executable,str(ROOT/'scripts'/'create_sample.py'),str(demo)],check=True,capture_output=True)
        subprocess.run([sys.executable,str(ROOT/'scripts'/'create_form_sample.py'),str(demo.parent/'reapdf-formulario.pdf')],check=True,capture_output=True)
        subprocess.run([sys.executable,str(ROOT/'scripts'/'create_advanced_form_sample.py'),str(demo.parent/'reapdf-formulario-avanzado.pdf')],check=True,capture_output=True)
        subprocess.run([sys.executable,str(ROOT/'scripts'/'create_scan_sample.py'),str(demo.parent/'reapdf-escaneado.pdf')],check=True,capture_output=True)
        subprocess.run([sys.executable,str(ROOT/'scripts'/'create_styled_text_sample.py'),str(demo.parent/'reapdf-texto-con-estilos.pdf')],check=True,capture_output=True)
        subprocess.run([sys.executable,str(ROOT/'scripts'/'create_review_sample.py'),str(demo.parent/'reapdf-recorrido.pdf')],check=True,capture_output=True)
        launcher='@echo off\r\nsetlocal DisableDelayedExpansion\r\ncd /d "%~dp0"\r\n"%~dp0runtime\\python.exe" -I "%~dp0app\\launcher.py"\r\nif errorlevel 1 pause\r\n'
        (folder/'Iniciar-Reapdf.cmd').write_bytes(launcher.replace('app\\launcher.py"','app\\launcher.py" --native-desktop').encode('ascii'))
        (folder/'Abrir-en-navegador.cmd').write_bytes(launcher.encode('ascii'))
        diagnostic=launcher.replace('app\\launcher.py"','app\\launcher.py" --self-test').replace('if errorlevel 1 pause','pause')
        (folder/'Diagnosticar.cmd').write_bytes(diagnostic.encode('ascii'))
        validate_payload(folder,config)
        manifest={'version':json.loads((ROOT/'package.json').read_text())['version'],
                  'target':'Windows 10/11 x64','python':config['python'],'windows_execution_verified':False,'presentation':'Reapdf.exe GUI bootstrap + integrated Qt window','native_launcher':json.loads(native.with_suffix('.build.json').read_text()),
                  'files':{p.relative_to(folder).as_posix():digest(p) for p in sorted(folder.rglob('*')) if p.is_file()}}
        (folder/'MANIFIESTO.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        output=Path(output) if output else out/('Reapdf-'+manifest['version']+'-Windows-x64.zip')
        output.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(output,'w',ZIP_DEFLATED) as z:
            for path in sorted(folder.rglob('*')):
                if path.is_file():z.write(path,Path(folder.name)/path.relative_to(folder))
        with ZipFile(output) as z:
            assert z.testzip() is None
        output.with_name(output.name+'.sha256').write_text(digest(output)+'  '+output.name+'\n')
        print(output);print('bytes',output.stat().st_size);print('SHA256',digest(output))
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--wheelhouse');parser.add_argument('--cache');parser.add_argument('--output');args=parser.parse_args()
    build(args.wheelhouse,args.cache,args.output)
