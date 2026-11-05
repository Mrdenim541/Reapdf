import pytest
from scripts.compiled_close import wait_closed


class Process:
    code=None
    def poll(self):return self.code


class Clock:
    value=0
    def now(self):return self.value
    def tick(self,seconds):self.value+=seconds


def window(pid=7,title='Cambios pendientes',handle=10):return {'pid':pid,'title':title,'hwnd':handle,'class':'QtWindow'}


def test_discard_dialog_is_accepted_instead_of_timing_out():
    p=Process();c=Clock();keys=[]
    def key(handle,value):
        keys.append((handle,value))
        if keys==[(10,0x25),(10,0x0D)]:p.code=0
    assert wait_closed(p,7,lambda:[window()],key,clock=c.now,pause=c.tick)
    assert keys==[(10,0x25),(10,0x0D)]


def test_other_process_confirmation_is_never_touched():
    p=Process();c=Clock();keys=[]
    with pytest.raises(RuntimeError,match='no cerró'):wait_closed(p,7,lambda:[window(pid=8)],lambda *v:keys.append(v),timeout=.2,clock=c.now,pause=c.tick)
    assert not keys


def test_unknown_dialog_is_diagnosed_without_guessing_a_button():
    p=Process();c=Clock();keys=[]
    with pytest.raises(RuntimeError,match='Operación pendiente'):wait_closed(p,7,lambda:[window(title='Operación pendiente')],lambda *v:keys.append(v),timeout=.2,clock=c.now,pause=c.tick)
    assert not keys


def test_known_dialog_is_not_clicked_repeatedly_if_close_stalls():
    p=Process();c=Clock();keys=[]
    with pytest.raises(RuntimeError):wait_closed(p,7,lambda:[window()],lambda *v:keys.append(v),timeout=.5,clock=c.now,pause=c.tick)
    assert len(keys)==2


def test_already_closed_and_nonzero_exit_are_distinguished():
    p=Process();p.code=0
    assert not wait_closed(p,7,lambda:[],lambda *a:None)
    p.code=1
    with pytest.raises(RuntimeError,match='código de error'):wait_closed(p,7,lambda:[],lambda *a:None)
