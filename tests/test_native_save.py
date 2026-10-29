import base64
import pytest
pytest.importorskip('PySide6.QtCore')
from portable.native_save import atomic_save,file_digest

def test_atomic_replace_and_report_exact_saved_digest(tmp_path):
    path=tmp_path/'document.pdf';path.write_bytes(b'original')
    digest=atomic_save(path,base64.b64encode(b'%PDF replacement').decode())
    assert path.read_bytes()==b'%PDF replacement' and digest==file_digest(path)

@pytest.mark.parametrize('encoded',['!',''])
def test_invalid_payload_preserves_existing_file(tmp_path,encoded):
    path=tmp_path/'document.pdf';path.write_bytes(b'original')
    with pytest.raises(ValueError):atomic_save(path,encoded)
    assert path.read_bytes()==b'original'

def test_failed_destination_does_not_damage_other_file(tmp_path):
    kept=tmp_path/'keep.pdf';kept.write_bytes(b'original')
    with pytest.raises(OSError):atomic_save(tmp_path/'absent'/'out.pdf',base64.b64encode(b'valid bytes').decode())
    assert kept.read_bytes()==b'original'
