import pytest
from portable.native_window import local_origin

@pytest.mark.parametrize('url',['https://example.com','http://localhost:123','http://127.0.0.1','http://user@127.0.0.1:123','file:///tmp/test','http://127.0.0.1:0'])
def test_reject_nonlocal_or_unbound_origins(url):
    with pytest.raises(ValueError):local_origin(url)

def test_accept_reserved_loopback_server():
    assert local_origin('http://127.0.0.1:12345/')=='http://127.0.0.1:12345'
