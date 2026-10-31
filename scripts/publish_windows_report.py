"""Publish source-bound Windows CI evidence on a separate, fast-forward Git branch.

Runs only in the trusted GitHub Actions reporting job. It never edits the source
worktree, never force-pushes, and never includes personal PDF files.
"""
import argparse,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path

BRANCH='validation/desktop-windows'


def source_objects(root):
    raw=subprocess.check_output(['git','ls-files','--stage','-z','--','backend','portable','web/src','scripts','tests','resources'],cwd=root)
    return {path:meta.split()[1] for record in raw.decode().split('\0') if record for meta,path in [record.split('\t',1)]}


def assess(directory,sha,expected_objects,expected_checks):
    path=directory/'desktop-report.json';problems=[]
    if not path.is_file():return {'verified':False,'source_commit':sha,'problems':['No se generó un informe de escritorio Windows.']}
    report=json.loads(path.read_text(encoding='utf-8'))
    if report.get('source_commit')!=sha:problems.append('El informe pertenece a otra revisión.')
    if report.get('platform')!='Windows':problems.append('La ejecución no corresponde a Windows.')
    if report.get('source_dirty') is not False or report.get('source_dirty_after') is not False:problems.append('La fuente no quedó limpia antes y después de la ejecución.')
    if report.get('source_git_objects')!=expected_objects:problems.append('Los objetos Git de la fuente no coinciden.')
    checks=report.get('checks',[])
    if [c.get('name') for c in checks]!=expected_checks or not report.get('passed'):problems.append('La batería no está completa o tiene fallos.')
    for check in checks:
        log=check.get('log','')
        if not isinstance(log,str) or Path(log).name!=log or not log.endswith('.log'):problems.append('Nombre de evidencia no válido.');continue
        file=directory/log
        if not file.is_file() or file.stat().st_size>4*1024*1024:problems.append('Falta una evidencia o excede el presupuesto.');continue
        data=file.read_bytes()
        if check.get('returncode')!=0 or check.get('passed') is not True or hashlib.sha256(data).hexdigest()!=check.get('sha256') or b'PASS:' not in data:problems.append('Una evidencia no coincide o indica fallo.')
    return {'verified':not problems,'source_commit':sha,'platform':report.get('platform'),'checks':len(checks),'problems':problems,'human_acceptance':False,'distributable_built':False}


def publish(root,directory,sha,run,attempt):
    if os.environ.get('GITHUB_ACTIONS')!='true' or not re.fullmatch(r'[0-9a-f]{40}',sha) or not str(run).isdigit() or not str(attempt).isdigit():raise ValueError('Publicación reservada a una ejecución CI identificada.')
    # Import from the sibling script whether executed as a module or a file.
    try:from .check_desktop_candidate import CHECKS
    except ImportError:from check_desktop_candidate import CHECKS
    receipt=assess(directory,sha,source_objects(root),CHECKS)
    receipt.update(run_id=str(run),run_attempt=str(attempt))
    directory.mkdir(parents=True,exist_ok=True);receipt_path=directory/'receipt.json';receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    allowed=['receipt.json']
    if (directory/'desktop-report.json').is_file():
        report=json.loads((directory/'desktop-report.json').read_text(encoding='utf-8'));allowed.append('desktop-report.json')
        allowed += [c['log'] for c in report.get('checks',[]) if isinstance(c.get('log'),str) and Path(c['log']).name==c['log'] and c['log'].endswith('.log') and (directory/c['log']).is_file() and (directory/c['log']).stat().st_size<=4*1024*1024]
    with tempfile.TemporaryDirectory(prefix='reapdf-evidence-index-') as work:
        env=os.environ.copy();env.update(GIT_INDEX_FILE=str(Path(work)/'index'),GIT_AUTHOR_NAME='Reapdf CI',GIT_AUTHOR_EMAIL='ci@reapdf.invalid',GIT_COMMITTER_NAME='Reapdf CI',GIT_COMMITTER_EMAIL='ci@reapdf.invalid')
        def git(*args,input=None):return subprocess.check_output(['git',*args],cwd=root,env=env,input=input,text=True).strip()
        prior=git('ls-remote','--heads','origin','refs/heads/'+BRANCH)
        if prior:
            git('fetch','--no-tags','origin','refs/heads/'+BRANCH);parent=git('rev-parse','FETCH_HEAD');git('read-tree',parent)
        else:parent=None;git('read-tree','--empty')
        for name in allowed:
            if (directory/name).stat().st_size>4*1024*1024:continue
            blob=git('hash-object','-w','--',str((directory/name).resolve()));target=f'reports/{sha}/{run}-{attempt}/{name}'
            git('update-index','--add','--cacheinfo',f'100644,{blob},{target}')
        tree=git('write-tree');args=['commit-tree',tree]+(['-p',parent] if parent else [])
        commit=git(*args,input=f'Windows desktop source evidence for {sha}\n')
        git('push','origin',commit+':refs/heads/'+BRANCH)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True);args=parser.parse_args()
    result=publish(Path(__file__).resolve().parents[1],args.directory,os.environ['SOURCE_COMMIT'],os.environ['GITHUB_RUN_ID'],os.environ.get('GITHUB_RUN_ATTEMPT','1'));print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
