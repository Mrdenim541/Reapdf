"""Run the actual Qt source application checks without building a distributable.

The JSON report binds platform, source revision, test logs and their hashes.
Windows CI is distinct from human acceptance and physical-printer verification.
"""
import argparse,hashlib,json,os,platform,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CHECKS=['smoke_native_save.py','smoke_native_document_set.py','smoke_single_instance.py','smoke_native_window.py','smoke_vector_print.py','smoke_native_readiness.py','smoke_native_launcher.py','smoke_parent_exit.py','smoke_text_states_native.py','smoke_extended_workflows_qt.py','smoke_portfolio_schema_qt.py','smoke_search_curves_qt.py']


def healthy():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=2) as r:return json.load(r).get('status')=='ok'
    except (OSError,ValueError):return False


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--reuse-server',action='store_true');args=parser.parse_args()
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True);env=os.environ.copy();env.update(QT_QPA_PLATFORM='offscreen',QT_OPENGL='software',QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --disable-dev-shm-usage',PYTHONPATH=str(ROOT))
    report={'platform':platform.system(),'platform_release':platform.release(),'python':platform.python_version(),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),'checks':[],'human_acceptance':False,'physical_print_verified':False,'distributable_built':False};server=None;log=None
    with tempfile.TemporaryDirectory(prefix='reapdf-desktop-check-') as state:
        env['REAPDF_DATA_DIR']=state;env['REAPDF_INSTANCE_NAMESPACE']=state;env['XDG_CACHE_HOME']=str(Path(state)/'cache')
        try:
            if not args.reuse_server:
                if healthy():raise RuntimeError('El puerto 8000 ya contiene un servidor. Usa --reuse-server solo si es el servidor de este proyecto.')
                if not (ROOT/'web/dist/index.html').is_file():raise RuntimeError('Compila antes con npm run build.')
                log=(output/'server.log').open('wb');server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
                deadline=time.monotonic()+25
                while not healthy():
                    if server.poll() is not None or time.monotonic()>deadline:raise RuntimeError('El backend de prueba no quedó disponible.')
                    time.sleep(.1)
            elif not healthy():raise RuntimeError('No hay un servidor Reapdf listo en el puerto 8000.')
            for name in CHECKS:
                path=output/(Path(name).stem+'.log');print('Checking',name,flush=True)
                with path.open('wb') as handle:
                    try:run=subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=ROOT,env=env,stdout=handle,stderr=subprocess.STDOUT,timeout=150);code=run.returncode
                    except subprocess.TimeoutExpired:code=-1
                data=path.read_bytes();passed=code==0 and b'PASS:' in data
                report['checks'].append({'name':name,'passed':passed,'returncode':code,'log':path.name,'sha256':hashlib.sha256(data).hexdigest()})
                if not passed:break
        except Exception as exc:report['error']=str(exc)
        finally:
            if server is not None and server.poll() is None:
                server.terminate()
                try:server.wait(timeout=15)
                except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
            if log:log.close()
    try:from .publish_windows_report import source_objects
    except ImportError:from publish_windows_report import source_objects
    report['source_git_objects']=source_objects(ROOT)
    report['source_dirty_after']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    report['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['backend','portable','web/src','scripts'] for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix in ['.py','.js','.jsx','.css','.mjs']}
    manual=ROOT/'docs/funciones-uso.json'
    report['source_sha256']['docs/funciones-uso.json']=hashlib.sha256(manual.read_bytes()).hexdigest()
    report['passed']=len(report['checks'])==len(CHECKS) and all(c['passed'] for c in report['checks']) and 'error' not in report
    (output/'desktop-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
