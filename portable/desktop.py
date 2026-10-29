"""Ventana de aplicación con un Chromium instalado y un perfil exclusivo temporal."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import json
import time


def find_browser():
    candidates = []
    if sys.platform == 'win32':
        for variable in ['PROGRAMFILES(X86)', 'PROGRAMFILES', 'LOCALAPPDATA']:
            folder = os.environ.get(variable)
            if folder:
                candidates.extend([Path(folder)/'Microsoft/Edge/Application/msedge.exe', Path(folder)/'Google/Chrome/Application/chrome.exe'])
    else:
        candidates.extend(Path(found) for name in ['microsoft-edge','google-chrome','chromium','chromium-browser'] if (found:=shutil.which(name)))
        if sys.platform == 'darwin':
            candidates.append(Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'))
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def browser_command(executable, url, profile):
    return [str(executable), '--app='+url, '--user-data-dir='+str(profile), '--no-first-run',
            '--no-default-browser-check', '--disable-background-mode', '--disable-extensions', '--disable-sync']


class DesktopWindow:
    def __init__(self, executable, url):
        self.profile = tempfile.TemporaryDirectory(prefix='reapdf-window-', ignore_cleanup_errors=True)
        try:
            self.process = subprocess.Popen(browser_command(executable,url,self.profile.name), stdin=subprocess.DEVNULL,
                                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except Exception:
            self.profile.cleanup()
            raise

    def wait(self):
        return self.process.wait()

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill();self.process.wait(timeout=5)
        self.profile.cleanup()


class NativeDesktopWindow:
    def __init__(self,unused,url,initial_file=None):
        self.state=tempfile.TemporaryDirectory(prefix='reapdf-native-',ignore_cleanup_errors=True)
        self.ready_path=Path(self.state.name)/'ready.json'
        env=os.environ.copy();env['REAPDF_NATIVE_READY_FILE']=str(self.ready_path)
        try:self.process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('native_window.py')),url,*([str(initial_file)] if initial_file else [])],stdin=subprocess.DEVNULL,env=env)
        except Exception:self.state.cleanup();raise

    def wait_ready(self,timeout=25):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if self.ready_path.exists():
                try:state=json.loads(self.ready_path.read_text(encoding='utf-8'))
                except (OSError,ValueError) as exc:raise RuntimeError('La ventana devolvió una confirmación de inicio no válida.') from exc
                if state!={'version':1,'pid':self.process.pid,'state':'ready'} and state!={'version':1,'pid':self.process.pid,'state':'forwarded'}:raise RuntimeError('La confirmación no corresponde a esta ventana.')
                return state['state']
            if self.process.poll() is not None:raise RuntimeError('La ventana terminó antes de cargar la interfaz.')
            time.sleep(.05)
        raise RuntimeError('La interfaz de Reapdf no terminó de cargar a tiempo.')

    def wait(self):return self.process.wait()

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
        self.state.cleanup()
