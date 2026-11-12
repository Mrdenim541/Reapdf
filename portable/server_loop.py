"""Event loop for the loopback HTTP engine, separate from Qt and job processes."""
import asyncio


def factory():
    # This engine uses synchronous subprocess.Popen for isolated jobs, not
    # asyncio subprocess/pipe transports. On Windows Proactor's socket shutdown
    # can raise after a peer reset, before detaching the socket from its server,
    # leaving Server.wait_closed() pending forever. Selector closes/detaches in
    # a finally block. Choose it only for this server; do not change global policy.
    return asyncio.SelectorEventLoop()
