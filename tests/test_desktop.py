from pathlib import Path
import subprocess
import sys
import time
import pytest
from portable import desktop,launcher


def test_window_arguments_use_private_profile_and_no_shell():
    command=desktop.browser_command(Path('C:/Program Files/Edge/msedge.exe'),'http://127.0.0.1:1234','C:/Mis perfiles/perfil')
    assert command[0]=='C:/Program Files/Edge/msedge.exe'
    assert '--app=http://127.0.0.1:1234' in command
    assert '--user-data-dir=C:/Mis perfiles/perfil' in command
    assert not any('no-sandbox' in arg for arg in command)


def test_finds_installed_windows_edge_without_requiring_install(tmp_path,monkeypatch):
    monkeypatch.setattr(desktop.sys,'platform','win32')
    monkeypatch.setenv('PROGRAMFILES',str(tmp_path));monkeypatch.delenv('PROGRAMFILES(X86)',raising=False);monkeypatch.delenv('LOCALAPPDATA',raising=False)
    executable=tmp_path/'Microsoft/Edge/Application/msedge.exe';executable.parent.mkdir(parents=True);executable.write_bytes(b'test executable')
    assert desktop.find_browser()==executable


def test_missing_browser_is_explicit(tmp_path,monkeypatch):
    monkeypatch.setattr(desktop.sys,'platform','win32')
    for key in ['PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA']:monkeypatch.setenv(key,str(tmp_path))
    assert desktop.find_browser() is None


def test_launch_failure_cleans_own_profile(tmp_path,monkeypatch):
    profiles=[]
    real=desktop.tempfile.TemporaryDirectory
    def temporary(**kwargs):
        result=real(dir=tmp_path,**kwargs);profiles.append(Path(result.name));return result
    monkeypatch.setattr(desktop.tempfile,'TemporaryDirectory',temporary)
    with pytest.raises(OSError):desktop.DesktopWindow(tmp_path/'absent-browser','http://127.0.0.1:1234')
    assert not profiles[0].exists()


def test_close_only_terminates_owned_browser_and_removes_profile(monkeypatch):
    # Proceso controlado para probar el ciclo de vida, sin fingir una ventana real.
    real=desktop.subprocess.Popen
    def process(*args,**kwargs):return real([sys.executable,'-c','import time;time.sleep(60)'],**kwargs)
    monkeypatch.setattr(desktop.subprocess,'Popen',process)
    window=desktop.DesktopWindow(Path('browser'),'http://127.0.0.1:1234');profile=Path(window.profile.name)
    assert profile.is_dir() and window.process.poll() is None
    window.close();assert window.process.poll() is not None and not profile.exists()


def test_desktop_child_normal_exit_stops_local_server(tmp_path,monkeypatch,capsys):
    import desktop as runtime_desktop
    closed=[]
    class ControlledWindow:
        def __init__(self,executable,url):self.url=url
        def wait(self):return 0
        def close(self):closed.append(True)
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path))
    monkeypatch.setattr(runtime_desktop,'find_browser',lambda:Path('controlled-browser'))
    monkeypatch.setattr(runtime_desktop,'DesktopWindow',ControlledWindow)
    launcher.serve(desktop=True)
    assert closed==[True] and 'REAPDF_PRESENTATION=desktop' in capsys.readouterr().out


def test_missing_desktop_browser_falls_back_to_normal_browser(tmp_path,monkeypatch,capsys):
    import desktop as runtime_desktop
    import uvicorn
    server=[];opened=[];real=uvicorn.Server
    def create(config):
        result=real(config);server.append(result);return result
    def open_browser(url):
        opened.append(url);server[0].should_exit=True;return True
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path))
    monkeypatch.setattr(runtime_desktop,'find_browser',lambda:None)
    monkeypatch.setattr(uvicorn,'Server',create)
    monkeypatch.setattr(launcher.webbrowser,'open',open_browser)
    launcher.serve(desktop=True)
    assert opened[0].startswith('http://127.0.0.1:')
    assert 'No se encontró Edge/Chrome' in capsys.readouterr().out


def test_executable_requires_desktop_and_never_silently_falls_back(tmp_path,monkeypatch):
    import desktop as runtime_desktop
    monkeypatch.setattr(runtime_desktop,'find_browser',lambda:None)
    monkeypatch.setattr(launcher.webbrowser,'open',lambda url:pytest.fail('No abrir una pestana al fallar el exe'))
    with pytest.raises(RuntimeError,match='Edge o Chrome'):launcher.serve(desktop=True,require_desktop=True,ready_file=tmp_path/'ready')
    assert not (tmp_path/'ready').exists()


@pytest.mark.parametrize('code',[0,7])
def test_executable_readiness_is_written_after_window_launch_and_child_exit_is_checked(tmp_path,monkeypatch,code):
    import desktop as runtime_desktop
    ready=tmp_path/'ready';closed=[]
    class Window:
        def __init__(self,executable,url):
            assert not ready.exists();self.url=url
        def wait(self):
            assert ready.read_text()==self.url;return code
        def close(self):closed.append(True)
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'state'))
    monkeypatch.setattr(runtime_desktop,'find_browser',lambda:Path('controlled-browser'))
    monkeypatch.setattr(runtime_desktop,'DesktopWindow',Window)
    monkeypatch.setattr(launcher.webbrowser,'open',lambda url:pytest.fail('No abrir una pestana al fallar el exe'))
    if code:
        with pytest.raises(RuntimeError,match='ventana de Reapdf'):launcher.serve(desktop=True,require_desktop=True,ready_file=ready)
    else:launcher.serve(desktop=True,require_desktop=True,ready_file=ready)
    assert closed==[True] and ready.read_text().startswith('http://127.0.0.1:')


def test_executable_window_launch_failure_stops_server_without_readiness(tmp_path,monkeypatch):
    import desktop as runtime_desktop
    def failed(*args):raise OSError('Inicio de ventana bloqueado')
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'state'))
    monkeypatch.setattr(runtime_desktop,'find_browser',lambda:Path('controlled-browser'))
    monkeypatch.setattr(runtime_desktop,'DesktopWindow',failed)
    monkeypatch.setattr(launcher.webbrowser,'open',lambda url:pytest.fail('No abrir una pestana al fallar el exe'))
    ready=tmp_path/'ready'
    with pytest.raises(RuntimeError,match='bloqueado'):launcher.serve(desktop=True,require_desktop=True,ready_file=ready)
    assert not ready.exists()
