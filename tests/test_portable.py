from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import shutil
import struct
import sys
import pymupdf as f
import pytest
from scripts.package_portable import safe_name,copy_wheel,pe_machine
from scripts.verify_portable_windows import verify_archive,native_check


@pytest.mark.parametrize('name',['../bad','/absolute','folder/../../bad','C:/outside','folder\\bad'])
def test_archive_paths_cannot_escape_destination(name):
    with pytest.raises(ValueError):safe_name(name)


def test_wheel_data_is_relocated_without_running_installers(tmp_path):
    archive=tmp_path/'runtime.whl'
    with ZipFile(archive,'w') as z:
        z.writestr('example/__init__.py','value=1')
        z.writestr('example-1.data/data/msvcp140.dll',b'dll')
        z.writestr('example-1.data/purelib/shared.py','value=2')
        z.writestr('example-1.dist-info/licenses/LICENSE','license')
    runtime=tmp_path/'runtime';copy_wheel(archive,runtime)
    assert (runtime/'msvcp140.dll').read_bytes()==b'dll'
    assert (runtime/'Lib/site-packages/example/__init__.py').is_file()
    assert (runtime/'Lib/site-packages/shared.py').is_file()
    assert (runtime/'Lib/site-packages/example-1.dist-info/licenses/LICENSE').is_file()


def test_reject_wrong_architecture_header_and_non_pe():
    data=bytearray(80);data[:2]=b'MZ';struct.pack_into('<I',data,60,64);data[64:68]=b'PE\0\0';struct.pack_into('<H',data,68,0x8664)
    assert pe_machine(data)==0x8664
    with pytest.raises(ValueError):pe_machine(b'not a binary')


@pytest.mark.parametrize('mode',['tampered','missing','extra'])
def test_manifest_detects_changes_missing_or_extra_files(tmp_path,mode):
    archive=tmp_path/'portable.zip';original=b'original'
    manifest={'version':'test','files':{'app/hello.txt':hashlib.sha256(original).hexdigest()}}
    with ZipFile(archive,'w') as z:
        z.writestr('Reapdf-portable/MANIFIESTO.json',json.dumps(manifest))
        if mode!='missing':z.writestr('Reapdf-portable/app/hello.txt',b'changed' if mode=='tampered' else original)
        if mode=='extra':z.writestr('Reapdf-portable/extra.txt','unlisted')
    with pytest.raises(ValueError):verify_archive(archive)


def test_launcher_self_test_http_and_export_in_staged_folder_with_spaces(tmp_path):
    root=Path(__file__).resolve().parent.parent
    folder=tmp_path/'Reapdf con espacios';app=folder/'app';app.mkdir(parents=True)
    shutil.copytree(root/'backend',app/'backend',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(root/'resources',app/'resources')
    # Archivos mínimos de interfaz, para probar independencia de cwd y paths.
    (app/'web/dist').mkdir(parents=True);(app/'web/dist/assets').mkdir()
    (app/'web/dist/index.html').write_text('<html><div id="root"></div></html>')
    shutil.copy2(root/'portable/launcher.py',app/'launcher.py')
    shutil.copy2(root/'portable/desktop.py',app/'desktop.py')
    (folder/'ejemplos').mkdir()
    with f.open() as d:
        p=d.new_page();p.insert_text((40,80),'Texto original',fontsize=18)
        d.save(folder/'ejemplos/reapdf-demo.pdf')
    report=native_check(folder,executable=sys.executable)
    assert report['portable_self_test']=='ok' and report['http_upload_export']=='ok'
    # Ejecutar con Python del host no certifica el binario Windows incluido.
    assert report['projects_recovery_print']=='ok'
    assert not report['windows_execution_verified']


@pytest.mark.parametrize('machine,subsystem,accepted',[(0x8664,2,True),(0x14c,2,False),(0x8664,3,False),(0x8664,0,False)])
def test_archive_checks_native_launcher_architecture_and_gui_subsystem(tmp_path,machine,subsystem,accepted):
    data=bytearray(256);data[:2]=b'MZ';struct.pack_into('<I',data,60,64);data[64:68]=b'PE\0\0';struct.pack_into('<H',data,68,machine);struct.pack_into('<H',data,64+24+68,subsystem)
    archive=tmp_path/'exe.zip';manifest={'version':'test','files':{'Reapdf.exe':hashlib.sha256(data).hexdigest()}}
    with ZipFile(archive,'w') as z:
        z.writestr('Reapdf-portable/MANIFIESTO.json',json.dumps(manifest));z.writestr('Reapdf-portable/Reapdf.exe',data)
    if accepted:assert verify_archive(archive)==manifest
    else:
        with pytest.raises(ValueError):verify_archive(archive)
