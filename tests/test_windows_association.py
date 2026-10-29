import pytest
from portable.windows_association import registration,removal

def test_open_with_per_user_preserves_default_reader():
    text=registration(r'C:\Program Files\Reapdf\Reapdf.exe')
    assert 'HKEY_LOCAL_MACHINE' not in text and 'UserChoice' not in text
    assert 'OpenWithProgids' in text and '\\"%1\\"' in text
    assert '[HKEY_CURRENT_USER\\Software\\Classes\\.pdf]\r\n@=' not in text
    undo=removal();assert '"Reapdf.PDF"=-' in undo
    assert '[-HKEY_CURRENT_USER\\Software\\Classes\\.pdf]' not in undo

@pytest.mark.parametrize('path',['Reapdf.exe',r'C:\app\other.exe','C:\\bad"\\Reapdf.exe','C:\\bad\n\\Reapdf.exe'])
def test_reject_ambiguous_or_injected_executable(path):
    with pytest.raises(ValueError):registration(path)
