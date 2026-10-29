"""Build the small Windows GUI bootstrap with Zig 0.13.0 (including on Linux)."""
import argparse,importlib.util,json,os,shutil,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def icon_bytes():
    size=32;pixels=bytearray();glyph=['11110','10001','10001','11110','10100','10010','10001']
    for y in reversed(range(size)):
        for x in range(size):
            gx,gy=(x-8)//3,(y-5)//3
            white=0<=gx<5 and 0<=gy<7 and glyph[gy][gx]=='1'
            pixels.extend((255,255,255,255) if white else (83,104,28,255))
    bitmap=struct.pack('<IiiHHIIiiII',40,size,size*2,1,32,0,len(pixels),0,0,0,0)+pixels+bytes(size*4)
    return struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',size,size,0,0,1,32,len(bitmap),22)+bitmap


def build(output=None,zig=None):
    output=Path(output or ROOT/'entregas/build/Reapdf.exe').resolve();output.parent.mkdir(parents=True,exist_ok=True)
    zig=zig or os.environ.get('REAPDF_ZIG') or shutil.which('zig')
    if not zig:
        spec=importlib.util.find_spec('ziglang')
        if spec:zig=str(Path(spec.origin).parent/('zig.exe' if os.name=='nt' else 'zig'))
    if not zig:raise RuntimeError('Compilar Reapdf.exe requiere Zig 0.13.0: python -m pip install ziglang==0.13.0')
    version=subprocess.check_output([zig,'version'],text=True).strip()
    if version!='0.13.0':raise ValueError('Usa Zig 0.13.0 para reproducir este lanzador.')
    package=json.loads((ROOT/'package.json').read_text());parts=package['version'].split('.')
    if len(parts)!=3 or not all(p.isdigit() for p in parts):raise ValueError('Version de programa no compatible.')
    icon=output.with_suffix('.ico');icon.write_bytes(icon_bytes());resource=output.with_suffix('.rc')
    manifest=output.with_suffix('.manifest')
    manifest.write_text('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0"><trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"><security><requestedPrivileges><requestedExecutionLevel level="asInvoker" uiAccess="false"/></requestedPrivileges></security></trustInfo></assembly>',encoding='utf-8')
    resource.write_text('1 ICON "'+icon.name+'"\n1 24 "'+manifest.name+'"\n1 VERSIONINFO\nFILEVERSION '+','.join(parts+['0'])+'\nPRODUCTVERSION '+','.join(parts+['0'])+'\nFILETYPE 1\nBEGIN\n BLOCK "StringFileInfo"\n BEGIN\n BLOCK "040904b0"\n BEGIN\n VALUE "FileDescription", "Reapdf - editor PDF personal"\n VALUE "ProductName", "Reapdf"\n VALUE "FileVersion", "'+package['version']+'"\n VALUE "OriginalFilename", "Reapdf.exe"\n END\n END\n BLOCK "VarFileInfo"\n BEGIN\n VALUE "Translation", 0x0409, 1200\n END\nEND\n',encoding='utf-8')
    subprocess.run([zig,'cc','-target','x86_64-windows-gnu','-O2','-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-municode','-Wl,--subsystem,windows',str(ROOT/'portable/native/launcher.c'),resource.name,'-I',str(output.parent),'-luser32','-lgdi32','-lshell32','-o',str(output)],check=True,cwd=output.parent)
    from scripts.package_portable import pe_machine,digest
    if pe_machine(output.read_bytes())!=0x8664:raise ValueError('El lanzador no es Windows x64.')
    data=output.read_bytes();offset=struct.unpack_from('<I',data,60)[0]
    if struct.unpack_from('<H',data,offset+24+68)[0]!=2:raise ValueError('El lanzador debe usar el subsistema Windows GUI, sin consola.')
    report={'version':package['version'],'compiler':'Zig '+version,'target':'x86_64-windows-gnu','sha256':digest(output),'windows_execution_verified':False}
    output.with_suffix('.build.json').write_text(json.dumps(report,indent=2)+'\n');return output

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output');parser.add_argument('--zig');args=parser.parse_args()
    print(build(args.output,args.zig))
