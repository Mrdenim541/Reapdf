"""Owned isolated PDF worker. Only the parent's private input snapshot is read."""
from pathlib import Path
import json,sys,os
from threading import Event,Thread


def main():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from backend.scheduled_recipes import Queue,atomic
    from backend.automation import process_recipe
    from backend.engine import DocumentError
    from portable.parent_pipe import parent_alive
    folder=Path(sys.argv[1]);queue=Queue(folder.parent.parent)
    if queue.directory(folder.name).resolve()!=folder.resolve():return 2
    finished=Event()
    def watch():
        while not finished.wait(.25):
            if not parent_alive(sys.stdin.fileno()):os._exit(3)
    Thread(target=watch,name='reapdf-job-parent',daemon=True).start()
    try:
        row=queue.read(folder.name)
        if row['status']!='running':raise DocumentError('La tarea no está autorizada para ejecución.')
        result=process_recipe(queue.inputs(row),row['recipe']);atomic(folder/'candidate.zip',result)
        return 0
    except Exception as e:
        message=str(e) if isinstance(e,DocumentError) else 'No se pudo completar la conversión de la tarea local.'
        atomic(folder/'worker-error.json',json.dumps({'error':message[:2000]},ensure_ascii=False).encode());return 1
    finally:finished.set()


if __name__=='__main__':raise SystemExit(main())
