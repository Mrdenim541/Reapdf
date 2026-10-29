import os
import time
import pytest
from portable.parent_pipe import parent_alive


def test_live_pipe_does_not_block_and_eof_is_observed():
    reader,writer=os.pipe()
    try:
        start=time.monotonic()
        for _ in range(50):assert parent_alive(reader)
        assert time.monotonic()-start<1
        os.close(writer);writer=None
        assert not parent_alive(reader)
    finally:
        os.close(reader)
        if writer is not None:os.close(writer)


def test_pipe_data_is_drained_then_parent_loss_detected():
    reader,writer=os.pipe()
    try:
        os.write(writer,b'heartbeat');assert parent_alive(reader)
        os.close(writer);writer=None
        for _ in range(20):
            if not parent_alive(reader):break
        else:pytest.fail('Pipe data must not hide EOF indefinitely')
    finally:
        os.close(reader)
        if writer is not None:os.close(writer)


def test_invalid_descriptor_is_parent_loss():assert not parent_alive(-1)
