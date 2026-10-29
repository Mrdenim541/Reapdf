#!/usr/bin/env python3
"""Run a Reapdf JSON recipe locally; no server or browser required."""
import argparse
import getpass
import json
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.automation import process_recipe, validate_recipe, MAX_INPUT
from backend.engine import DocumentError


def publish(path,data,overwrite=False):
    if not path.parent.is_dir():raise ValueError('La carpeta de salida no existe.')
    with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.reapdf-',delete=False) as stream:
        temporary=Path(stream.name)
        try:stream.write(data);stream.flush();os.fsync(stream.fileno())
        except BaseException:temporary.unlink(missing_ok=True);raise
    try:
        if overwrite:os.replace(temporary,path)
        else:os.link(temporary,path) # Exclusive publication: never overwrite a concurrent file.
    finally:temporary.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe',type=Path,required=True,help='Receta JSON exportada de Reapdf.')
    parser.add_argument('--output',type=Path,required=True,help='ZIP de copias o JSON si se usa --review.')
    parser.add_argument('--review',action='store_true',help='Solo revisar: produce un informe JSON sin copias.')
    parser.add_argument('--overwrite',action='store_true',help='Permitir reemplazar el archivo de salida.')
    parser.add_argument('inputs',type=Path,nargs='+',help='Entre 1 y 10 PDF locales.')
    args=parser.parse_args()
    try:
        if not 1<=len(args.inputs)<=10:raise ValueError('Selecciona entre 1 y 10 PDF.')
        output=args.output.resolve();sources=[p.resolve() for p in args.inputs]
        if output in sources or output==args.recipe.resolve():raise ValueError('La salida no puede reemplazar una entrada ni la receta.')
        if output.exists() and not args.overwrite:raise ValueError('La salida ya existe. Elige otro nombre o usa --overwrite.')
        if args.recipe.stat().st_size>65536:raise ValueError('La receta supera 64 KB.')
        recipe=validate_recipe(json.loads(args.recipe.read_text(encoding='utf-8')))
        if len(set(sources))!=len(sources):raise ValueError('No repitas documentos de entrada.')
        if sum(p.stat().st_size for p in sources)>MAX_INPUT:raise ValueError('El lote supera 60 MB de entrada.')
        secrets=None
        if recipe['steps'][-1]['type']=='protect':
            if not sys.stdin.isatty():raise ValueError('Para proteger, usa una consola interactiva e introduce las contraseñas cuando se soliciten.')
            secrets={'password':getpass.getpass('Contraseña de apertura: '),'owner_password':getpass.getpass('Contraseña de propietario: ')}
        result=process_recipe([(p.name,p.read_bytes(),[]) for p in sources],recipe,secrets,review=args.review)
        if args.review:
            for row in result['documents']:row.pop('preview',None)
            result['review_only']=True
            result=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        publish(output,result,args.overwrite)
        print(f'{"Revisión" if args.review else "Copias"} guardada: {output}')
        return 0
    except (OSError,ValueError,DocumentError) as exc:parser.exit(2,f'Error: {exc}\n')

if __name__=='__main__':raise SystemExit(main())
