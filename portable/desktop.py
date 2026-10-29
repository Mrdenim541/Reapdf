"""Ventana de aplicación con un Chromium instalado y un perfil exclusivo temporal."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile


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
    def __init__(self,unused,url):
        self.process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('native_window.py')),url],stdin=subprocess.DEVNULL)

    def wait(self):return self.process.wait()

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
