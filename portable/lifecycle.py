"""Opt-in process-stage diagnostics without document names or contents."""
import json
import os
import sys
import time


def trace(stage):
    if os.environ.get('REAPDF_TRACE_LIFECYCLE')=='1':
        print('REAPDF_LIFECYCLE '+json.dumps({'pid':os.getpid(),'at':round(time.monotonic(),6),'stage':stage},ensure_ascii=True),file=sys.stderr,flush=True)


def observe_shutdown(server):
    """Opt-in diagnostics; never cancel work or change graceful shutdown limits."""
    if os.environ.get('REAPDF_TRACE_LIFECYCLE')!='1':return
    import asyncio
    import faulthandler
    original=server.shutdown

    async def shutdown(sockets=None):
        trace('backend.shutdown.entered')
        async def pending():
            await asyncio.sleep(8)
            state=server.server_state
            trace('backend.shutdown.pending:'+json.dumps({
                'connections':len(state.connections),'requests':len(state.tasks),
                'coroutines':sorted(type(t.get_coro()).__name__+':'+getattr(t.get_coro(),'__qualname__','unknown') for t in asyncio.all_tasks() if not t.done()),
            },sort_keys=True))
        diagnostic=asyncio.create_task(pending())
        # A blocked event loop cannot run the coroutine above. The independent
        # watchdog emits stacks (no frame locals/document data), without killing it.
        faulthandler.dump_traceback_later(8)
        try:
            await original(sockets=sockets)
            trace('backend.shutdown.finished')
        finally:
            faulthandler.cancel_dump_traceback_later()
            diagnostic.cancel()
            try:await diagnostic
            except asyncio.CancelledError:pass
    server.shutdown=shutdown
