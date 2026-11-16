"""Windows 瞬时目录占用有限重试，不覆盖目标或掩盖永久拒绝。"""
import os
from types import SimpleNamespace

import pytest

from m2v.core import security

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows目录占用行为')


@pytest.mark.parametrize('permanent,existing', [(False, False), (True, False), (True, True)])
def test_directory_publish_retries_only_transient_unpublished_target(tmp_path, monkeypatch, permanent, existing):
    source, target = tmp_path / 'stage', tmp_path / 'published'
    source.mkdir()
    (source / 'keep.txt').write_text('source', encoding='utf-8')
    if existing:
        target.mkdir()
        (target / 'keep.txt').write_text('destination', encoding='utf-8')
    replace = os.replace
    calls, pauses = [], []

    def busy(start, end):
        calls.append((start, end))
        if permanent or len(calls) == 1:
            error = PermissionError('temporarily held directory')
            error.winerror = 32
            raise error
        replace(start, end)

    monkeypatch.setattr(security.os, 'replace', busy)
    monkeypatch.setattr(security.time, 'sleep', pauses.append)
    monkeypatch.setattr(security, '_icacls', lambda *args: SimpleNamespace(returncode=0))
    monkeypatch.setattr(security, '_warn_if_still_unusable', lambda path: None)
    if permanent:
        with pytest.raises(PermissionError):
            security.deliver_directory(source, target)
        assert source.is_dir()
        assert len(calls) == (1 if existing else 4)
        if existing:
            assert (target / 'keep.txt').read_text(encoding='utf-8') == 'destination'
    else:
        assert security.deliver_directory(source, target) == target
        assert len(calls) == 2 and pauses == [0.05]
        assert (target / 'keep.txt').read_text(encoding='utf-8') == 'source'
