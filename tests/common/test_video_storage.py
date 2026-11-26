"""存储预览遵守引用和文件身份，执行拒绝过期清单。"""
from __future__ import annotations

import os
import time

import pytest

from m2v.core.errors import M2VError
from m2v.production import video_storage as storage


def test_storage_plan_preserves_references_and_refuses_changed_files(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    recordings = root / "outputs/code-cache/.recordings"
    recordings.mkdir(parents=True)
    obsolete = recordings / "code-9931-deadbeef"
    referenced = recordings / "code-9932-cafebabe"
    old = time.time() - storage.RECORDING_SETTLE_NS / 10**9 - 60
    for case in (obsolete, referenced):
        case.mkdir()
        (case / "frame-000000.png").write_bytes(b"scratch")
        os.utime(case, (old, old))
    (root / "outputs/visual-notes.md").write_text(
        referenced.relative_to(root).as_posix(), encoding="utf-8",
    )
    monkeypatch.setattr(storage, "recording_ended", lambda *_a, **_k: True)

    plan = storage.cleanup_plan(root)
    assert [entry["path"] for entry in plan["candidates"]] == [obsolete.relative_to(root).as_posix()]
    assert [entry["path"] for entry in plan["skipped"]] == [referenced.relative_to(root).as_posix()]
    assert not (root / "outputs/production").exists()

    (obsolete / "frame-000000.png").write_bytes(b"modified scratch")
    with pytest.raises(M2VError, match="清单已变化"):
        storage.apply_cleanup(root, plan["planSha256"])
    assert obsolete.is_dir()

    current = storage.cleanup_plan(root)
    result = storage.apply_cleanup(root, current["planSha256"])
    assert result["removedBytes"] == len(b"modified scratch")
    assert not obsolete.exists()
    assert referenced.exists()


def test_windows_fallback_distinguishes_reused_pid_from_same_process(tmp_path, monkeypatch):
    from m2v.core import recording_identity

    marker = tmp_path / ".worker-183"
    marker.write_text("epoch:3500250000", encoding="ascii")
    monkeypatch.setattr(recording_identity, "process_start", lambda _pid: "epoch-ms:3500")
    assert not recording_identity.recording_ended(183, marker)
    monkeypatch.setattr(recording_identity, "process_start", lambda _pid: "epoch-ms:4200")
    assert recording_identity.recording_ended(183, marker)
    monkeypatch.setattr(recording_identity, "process_start", lambda _pid: recording_identity.UNKNOWN)
    assert not recording_identity.recording_ended(183, marker)
