"""Opt-in process-stage diagnostics without document names or contents."""
import json
import os
import time


def trace(stage):
    if os.environ.get('REAPDF_TRACE_LIFECYCLE')=='1':
        print('REAPDF_LIFECYCLE '+json.dumps({'pid':os.getpid(),'at':round(time.monotonic(),6),'stage':stage},ensure_ascii=True),flush=True)
