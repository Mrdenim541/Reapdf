"""Wait for an owned candidate to close, acknowledging only its known discard dialog."""
import time


def wait_closed(process,pid,windows,key,timeout=25,clock=time.monotonic,pause=time.sleep):
    deadline=clock()+timeout;handled=set();observed=[]
    while process.poll() is None:
        observed=[w for w in windows() if w['pid']==pid]
        for window in observed:
            if window['title']=='Cambios pendientes' and window['hwnd'] not in handled:
                # The app explicitly defaults to Cancel. Left chooses the other
                # standard button (Discard), Enter confirms only this fixture.
                key(window['hwnd'],0x25);key(window['hwnd'],0x0D);handled.add(window['hwnd'])
        if clock()>=deadline:raise RuntimeError('El candidato no cerró; ventanas propias observadas: '+repr([(w['title'],w['class']) for w in observed]))
        pause(.1)
    if process.poll()!=0:raise RuntimeError('Reapdf.exe terminó con un código de error al cerrar.')
    return bool(handled)
