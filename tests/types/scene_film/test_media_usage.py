"""画面采用规则在准备解析、台账和审计之间一致，真实编解码由媒体测试覆盖。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.engine import assets_audit, assets_tools
from m2v.types.scene_film import media_assets


@pytest.mark.parametrize("status,met,passed", [
    ("not-checked", None, True), ("no-explicit-restriction", None, True),
    ("conditional", True, True), ("conditional", False, True), ("prohibited", None, False),
    ("invalid-status", None, False),
])
def test_three_consumers_share_usage_decision(tmp_path, monkeypatch, status, met, passed):
    usage = {"status": status}
    if status in {"conditional", "no-explicit-restriction"}:
        usage.update(evidenceUrl="https://example.com/terms", checkedAt="2026-11-05", note="本次用途及条件记录")
    if met is not None:
        usage["conditionsMet"] = met
    file = tmp_path / "assets/media/photo.png"
    file.parent.mkdir(parents=True)
    file.write_bytes(b"fixture")
    entry = {"id": "photo", "kind": "image", "path": "assets/media/photo.png", "width": 64, "height": 32,
             "durationSeconds": None, "sha256": hashlib.sha256(b"fixture").hexdigest(),
             "license": "未知", "usage": usage}
    record = {"schemaVersion": 1, "assets": [entry]}
    (tmp_path / media_assets.RECORD).write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(media_assets, "probe", lambda *_: {"width": 64, "height": 32, "durationSeconds": None})
    monkeypatch.setattr(assets_audit, "describe", lambda *_: {"colorSpace": "srgb", "alpha": False})
    if passed:
        assert "photo" in media_assets.resolve(tmp_path)["media"]
    else:
        with pytest.raises(M2VError):
            media_assets.resolve(tmp_path)
    report = assets_tools.build_report(tmp_path)
    audit = assets_audit.audit(tmp_path, {"preparedFingerprint": "fixture"}, record)
    assert (report["status"] == "pass") is passed
    assert (audit["status"] == "pass") is passed
    if passed:
        assert report["assets"][0]["license"] == audit["assets"][0]["license"] == "未知"
        assert report["assets"][0]["usage"]["status"] == status


def test_policy_implementation_change_invalidates_preparation(monkeypatch):
    from m2v.core import media_policy
    from m2v.types.scene_film import code_scenes, explainer_prepare
    version = ["before"]
    policy_file = Path(media_policy.__file__).resolve()
    monkeypatch.setattr(explainer_prepare, "digest", lambda path: version[0] if Path(path) == policy_file else "fixed")
    monkeypatch.setattr(code_scenes, "implementation_inputs", lambda: {})
    before = explainer_prepare.implementation_digest()
    version[0] = "after"
    assert explainer_prepare.implementation_digest() != before
