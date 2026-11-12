"""Exercise real TCP resets on the desktop backend's event loop on Windows/Linux."""
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
runpy.run_path(str(ROOT/'tests/test_server_loop.py'))['test_server_peer_resets_close_without_policy_change']()
print('PASS: peer resets release server sockets and preserve global event loop policy')
