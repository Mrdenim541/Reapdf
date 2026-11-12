"""Real loopback peer resets must not leave server shutdown waiting on sockets."""
import asyncio
import socket
import struct
import sys

from portable.server_loop import factory


def test_server_peer_resets_close_without_policy_change():
    policy=asyncio.get_event_loop_policy()
    loop=factory();errors=[]
    loop.set_exception_handler(lambda unused,context:errors.append(context))
    writers=[]
    async def connected(reader,writer):
        writers.append(writer)
        try:await reader.read()
        except ConnectionResetError:pass
        finally:
            writer.close()
            try:await writer.wait_closed()
            except ConnectionResetError:pass
    async def exercise():
        server=await asyncio.start_server(connected,'127.0.0.1',0)
        address=server.sockets[0].getsockname()
        for _ in range(40):
            client=socket.socket();client.setblocking(False)
            await loop.sock_connect(client,address)
            # Windows linger uses two shorts; POSIX uses two ints.
            client.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('hh' if sys.platform=='win32' else 'ii',1,0))
            client.close()
            await asyncio.sleep(.005)
        server.close()
        await asyncio.wait_for(server.wait_closed(),2)
        assert writers and all(w.is_closing() for w in writers)
    try:loop.run_until_complete(exercise())
    finally:loop.close()
    assert not errors
    assert asyncio.get_event_loop_policy() is policy


def test_uvicorn_custom_factory_returns_a_running_loop_not_a_class():
    import uvicorn
    config=uvicorn.Config('backend.app:app',loop='portable.server_loop:factory')
    loop=config.get_loop_factory()()
    try:
        assert isinstance(loop,asyncio.AbstractEventLoop)
        assert loop.run_until_complete(asyncio.sleep(0,result='ready'))=='ready'
    finally:loop.close()
