"""Prepare a local Reapdf checkout without changing global Python or Codex config.

Commands default to check/plan. REA configuration is a separate, explicit step.
"""
import argparse,json,os,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def executable(name):
    return shutil.which(name+'.cmd' if os.name=='nt' and name in ['npm','npx'] else name)


def version(name):
    binary=executable(name)
    if not binary:return None
    try:
        result=subprocess.run([binary,'--version'],capture_output=True,text=True,timeout=15,check=True)
        return result.stdout.strip()[:160]
    except (OSError,subprocess.SubprocessError):return None


def node_version(value):
    match=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)',value or '')
    return tuple(map(int,match.groups())) if match else None


def node_ready(value,rea=False):
    parsed=node_version(value)
    return bool(parsed and parsed[0]==24 and (not rea or parsed>=(24,22,1)))


def python_path(root=ROOT,windows=None):
    windows=os.name=='nt' if windows is None else windows
    return root/'.venv'/('Scripts/python.exe' if windows else 'bin/python')


def setup_commands(root=ROOT):
    if (root/'.venv').is_symlink():raise ValueError('La carpeta .venv es un enlace; usa un entorno propio del checkout.')
    interpreter=str(python_path(root));npm=executable('npm') or 'npm'
    commands=[]
    if not python_path(root).is_file():commands.append([sys.executable,'-m','venv',str(root/'.venv')])
    commands.extend([[interpreter,'-m','pip','install','-r','requirements-lock.txt','PySide6==6.8.3'],[npm,'ci'],[npm,'run','build']])
    return commands


def execute(commands,cwd=ROOT):
    for command in commands:
        print(json.dumps({'cwd':str(cwd),'command':command},ensure_ascii=False),flush=True)
        subprocess.run(command,cwd=cwd,check=True)


def check():
    node=version('node');py=python_path();qt=None
    if py.is_file():
        try:
            qt=subprocess.check_output([str(py),'-c',"import importlib.metadata as m;print(m.version('PySide6'))"],cwd=ROOT,text=True,stderr=subprocess.DEVNULL,timeout=15).strip()
        except (OSError,subprocess.SubprocessError):pass
    return {'platform':sys.platform,'python':sys.version.split()[0],'python_supported':sys.version_info[:2] in [(3,12),(3,13)],'node':node,'node_for_reapdf':node_ready(node),'node_for_pinned_rea':node_ready(node,rea=True),'npm_available':bool(executable('npm')),'git_available':bool(executable('git')),'codex_cli_available':bool(executable('codex')),'venv_python':str(py) if py.is_file() else None,'qt':qt,'frontend_built':(ROOT/'web/dist/index.html').is_file(),'note':'Codex puede usarse desde la aplicación o extensión aunque su CLI no esté en PATH. REA y Windows no se consideran verificados por este diagnóstico.'}


def rea_commands(apply=False):
    node=version('node')
    if not node_ready(node,rea=True):raise ValueError('REA 6.8.0 necesita Node 24 >=24.22.1 en este proyecto. Actualiza Node; no se fuerza una versión incompatible.')
    npx=executable('npx')
    if not npx:raise ValueError('No se encontró npx de la instalación Node.')
    reference=json.loads((ROOT/'tools/rea-reference.json').read_text(encoding='utf-8'))
    command=[npx,'--yes','rea-agents@'+reference['version'],'setup','--client','codex']
    if not apply:command+=['--dry-run','--json']
    return [command]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['check','setup','run','verify','rea-plan','rea-setup'],nargs='?',default='check');parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    try:
        if args.command=='check':print(json.dumps(check(),ensure_ascii=False,indent=2));return 0
        if args.command=='setup':
            if sys.version_info[:2] not in [(3,12),(3,13)]:raise ValueError('Usa Python 3.12 o 3.13 para preparar este proyecto.')
            if not node_ready(version('node')) or not executable('npm'):raise ValueError('Instala Node 24.x con npm antes de preparar el proyecto.')
            commands=setup_commands();cwd=ROOT
        elif args.command in ['rea-plan','rea-setup']:
            commands=rea_commands(apply=args.command=='rea-setup' and not args.dry_run)
            # Acquisition runs outside the target repo; npm cannot interpret the
            # target package as a workspace or alter its dependency manifest.
            cwd=Path.home()/'Reapdf-development-tools'
            if cwd.resolve()==ROOT:raise ValueError('La carpeta de herramientas debe estar fuera del repositorio.')
        else:
            interpreter=python_path()
            if not interpreter.is_file():raise ValueError('Prepara primero el entorno con setup.')
            cwd=ROOT
            commands=[[str(interpreter),'portable/launcher.py','--native-desktop','--require-desktop']] if args.command=='run' else [[str(interpreter),'scripts/check_desktop_candidate.py','--output','.local-state/desktop-validation']]
        if args.dry_run:print(json.dumps({'cwd':str(cwd),'commands':commands},ensure_ascii=False,indent=2));return 0
        if args.command.startswith('rea-'):cwd.mkdir(parents=True,exist_ok=True)
        execute(commands,cwd);return 0
    except (ValueError,OSError,subprocess.SubprocessError) as exc:print('No se completó: '+str(exc),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
