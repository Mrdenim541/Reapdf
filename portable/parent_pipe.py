"""Poll the launcher's pipe without buffered readers or shutdown threads."""
import os


def readable_bytes(fd):
    if os.name!='nt':
        import select
        return 1 if select.select([fd],[],[],0)[0] else 0
    # Windows select cannot inspect anonymous pipes. PeekNamedPipe is
    # nonblocking and does not consume data; Popen supplies a byte-mode pipe.
    import ctypes,msvcrt
    from ctypes import wintypes
    peek=ctypes.WinDLL('kernel32',use_last_error=True).PeekNamedPipe
    peek.argtypes=[wintypes.HANDLE,wintypes.LPVOID,wintypes.DWORD,wintypes.LPVOID,ctypes.POINTER(wintypes.DWORD),wintypes.LPVOID]
    peek.restype=wintypes.BOOL;available=wintypes.DWORD()
    if not peek(wintypes.HANDLE(msvcrt.get_osfhandle(fd)),None,0,None,ctypes.byref(available),None):raise OSError(ctypes.get_last_error(),'No se pudo consultar el conducto del lanzador.')
    return min(available.value,64)


def parent_alive(fd):
    try:
        available=readable_bytes(fd)
        return not available or bool(os.read(fd,available))
    except (OSError,ValueError):return False
