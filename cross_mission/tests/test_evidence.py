"""Regression for observed FileProvider timeout/empty-read behavior."""
import hashlib
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from evidence import sha256

@pytest.mark.parametrize('failure',['timeout','premature_eof'])
def test_native_retry_preserves_nonempty_file_digest(tmp_path,monkeypatch,failure):
    path=tmp_path/'original bytes.bin';payload=b'original scientific bytes\x00\xff'*100
    path.write_bytes(payload)
    def bad_read(self):
        if failure=='timeout':raise TimeoutError(60,'Operation timed out')
        return b''
    monkeypatch.setattr(Path,'read_bytes',bad_read)
    assert sha256(path)==hashlib.sha256(payload).hexdigest()
