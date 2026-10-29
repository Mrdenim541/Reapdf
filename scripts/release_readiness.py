"""Local validation receipt and an explicit, non-certifying release checklist.

A receipt binds logs and source hashes. It is a reproducibility record, not a
signed attestation, a security audit or a percentage of Acrobat compatibility.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import tempfile

ROOT=Path(__file__).resolve().parents[1]
EXTENSIONS={'.py','.js','.jsx','.mjs','.css','.json','.html','.txt','.sh','.cmd','.yml','.yaml','.c','.rc'}
REQUIRED_CRITERIA={'reader_pages','annotations','text_editing','office_conversion','complex_redaction','advanced_signatures','semantic_accessibility','automation','windows_execution','independent_corpus','advanced_forms','image_compression','professional_standards'}


def digest(data):return hashlib.sha256(data).hexdigest()


def snapshot(root):
    paths=set()
    for directory in ['backend','web/src','web/public','scripts','portable','.github/workflows','tests']:
        folder=root/directory
        if folder.exists():
            paths.update(p for p in folder.rglob('*') if p.is_file() and p.suffix in EXTENSIONS and '__pycache__' not in p.parts and not p.name.startswith('.check-'))
    for pattern in ['package*.json','requirements*.txt','*.cmd','web/vite.config.js','web/index.html','docs/release-criteria.json']:
        paths.update(root.glob(pattern))
    files={p.relative_to(root).as_posix():digest(p.read_bytes()) for p in sorted(paths)}
    return {'digest':digest(json.dumps(files,sort_keys=True).encode()),'files':files}


def build_snapshot(root):
    folder=root/'web/dist'
    files={p.relative_to(folder).as_posix():digest(p.read_bytes()) for p in sorted(folder.rglob('*')) if p.is_file()}
    if 'index.html' not in files:raise ValueError('Falta la compilación web de producción.')
    return files


def parse_logs(logs):
    py=re.search(r'\b(\d+) passed\b',logs['python'])
    js=re.search(r'(?:ℹ\s*)?pass\s+(\d+)\b',logs['javascript'])
    if not py or re.search(r'\b[1-9]\d* (?:failed|error)',logs['python']):raise ValueError('El registro Python no demuestra una ejecución aprobada.')
    if not js or not re.search(r'(?:ℹ\s*)?fail\s+0\b',logs['javascript']):raise ValueError('El registro JavaScript no demuestra una ejecución aprobada.')
    if not re.search(r'^PASS:',logs['browser'],re.M) or any(v in logs['browser'] for v in ['ExpectError:','FAIL:']):raise ValueError('Falta un recorrido de navegador aprobado.')
    if 'built in' not in logs['build'] or 'error during build' in logs['build'].lower():raise ValueError('Falta una compilación aprobada.')
    if int(py.group(1))<1 or int(js.group(1))<1 or re.search(r'(?:ℹ\s*)?fail\s+[1-9]\d*\b',logs['javascript']):raise ValueError('Los registros no contienen una suite completa aprobada.')
    return {'python':int(py.group(1)),'javascript':int(js.group(1)),'browser':True,'build':True}


def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as stream:
        temporary=Path(stream.name)
        try:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True);raise
    try:os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)


def record(root,receipt,log_paths):
    raw={key:Path(path).read_bytes() for key,path in log_paths.items()}
    validation=parse_logs({key:value.decode('utf-8',errors='replace') for key,value in raw.items()})
    sources=snapshot(root);build=build_snapshot(root)
    result={'schema':1,'version':json.loads((root/'package.json').read_text())['version'],
            'generated_at_utc':datetime.now(timezone.utc).isoformat(),'platform':platform.system(),
            'validation':validation,'sources':sources,'build_files':build,'evidence':{},
            'limitations':'Registro local sin firma: no certifica seguridad, paridad comercial ni ejecución en otra plataforma.'}
    for key,value in raw.items():
        name=key+'.log';atomic_write(receipt.parent/name,value);result['evidence'][key]={'file':name,'sha256':digest(value)}
    atomic_write(receipt,(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    return result


def audit(root,receipt):
    criteria=json.loads((root/'docs/release-criteria.json').read_text())
    if not isinstance(criteria,dict):raise ValueError('La matriz de cierre debe ser un objeto.')
    rows=criteria.get('criteria',[])
    if (criteria.get('schema')!=1 or not isinstance(rows,list) or not all(isinstance(r,dict) for r in rows)
            or {r.get('id') for r in rows}!=REQUIRED_CRITERIA or len(rows)!=len(REQUIRED_CRITERIA)
            or any(r.get('status') not in {'verified','partial','pending','unverified'} or not isinstance(r.get('remaining'),str) for r in rows)):
        raise ValueError('La matriz de cierre está incompleta o contiene estados no válidos.')
    errors=[];validation=None;proof=None
    try:
        proof=json.loads(receipt.read_text())
        if not isinstance(proof,dict):raise ValueError('La evidencia debe ser un objeto.')
        if proof.get('schema')!=1:raise ValueError('Versión de evidencia no compatible.')
        if proof.get('version')!=json.loads((root/'package.json').read_text())['version']:errors.append('La evidencia pertenece a otra versión.')
        if proof.get('sources')!=snapshot(root):errors.append('El código o los criterios cambiaron después de la validación.')
        if proof.get('build_files')!=build_snapshot(root):errors.append('La compilación cambió después de la validación.')
        logs={}
        for key in ['python','javascript','browser','build']:
            entry=proof['evidence'][key];name=entry['file']
            if not isinstance(name,str) or Path(name).name!=name:raise ValueError('Ruta de evidencia no válida.')
            data=(receipt.parent/name).read_bytes()
            if digest(data)!=entry['sha256']:errors.append(f'El registro {key} cambió después de guardarse.')
            logs[key]=data.decode('utf-8',errors='replace')
        validation=parse_logs(logs)
        if validation!=proof.get('validation'):errors.append('Los recuentos declarados no coinciden con los registros.')
    except (OSError,ValueError,KeyError,TypeError) as exc:errors.append(str(exc))
    pending=[r for r in rows if r['status']!='verified']
    windows=bool(proof and proof.get('platform')=='Windows' and not errors)
    if not windows and not any(r['id']=='windows_execution' for r in pending):
        pending.append({'id':'windows_execution','status':'unverified','remaining':'El registro local disponible no procede de Windows.'})
    return {'schema':1,'scope':criteria.get('scope'),'version':json.loads((root/'package.json').read_text())['version'],
            'local_regression_verified':not errors,'validation':validation,'evidence_errors':errors,
            'windows_execution_evidence':windows,'pending':pending,'ready_for_1_0':not errors and not pending,
            'note':'La lista combina evidencia técnica local y alcance declarado; no calcula un porcentaje comercial ni sustituye revisión humana.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--record',action='store_true');parser.add_argument('--receipt',type=Path,required=True)
    for key in ['python','javascript','browser','build']:parser.add_argument('--'+key+'-log',type=Path)
    parser.add_argument('--strict',action='store_true');args=parser.parse_args()
    try:
        if args.record:
            paths={key:getattr(args,key+'_log') for key in ['python','javascript','browser','build']}
            if not all(paths.values()):raise ValueError('Indica los cuatro registros de validación.')
            record(ROOT,args.receipt,paths)
        result=audit(ROOT,args.receipt);print(json.dumps(result,ensure_ascii=False,indent=2));return 2 if args.strict and not result['ready_for_1_0'] else 0
    except (OSError,ValueError,KeyError,TypeError) as exc:parser.error(str(exc))

if __name__=='__main__':raise SystemExit(main())
