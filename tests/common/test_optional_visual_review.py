"""候选生成与技术验收不依赖可选人工评审或旧预演。"""
import json
from dataclasses import replace
import pytest
from m2v.cli import main, _register_builtins
from m2v.commands import _status
from m2v.core import delivery
from m2v.type_system import registry


@pytest.mark.parametrize("kind", ["text-motion", "data-evolution", "principle-metaphor", "spatial-3d", "documentary-edit"])
@pytest.mark.parametrize("review_state", [None, "pending", "fail", "stale"])
def test_types_export_without_preview_or_manual_review(tmp_path, monkeypatch, kind, review_state):
    _register_builtins()
    root = tmp_path / kind
    outputs = root / "outputs"
    outputs.mkdir(parents=True)
    manifest = {"id": "demo", "type": kind}
    prepared = {"preparedFingerprint": "current"}
    if review_state:
        (outputs / "review.json").write_text(json.dumps({"status": review_state}), encoding="utf-8")
    final = outputs / "final.mp4"
    def render(*_):
        final.write_bytes(b"final")
        return final
    original = registry.get(kind)
    monkeypatch.setattr(registry, "_registry", {kind: replace(original, render=render,
        pre_render_check=None, prepared_check=lambda *_: prepared)})
    monkeypatch.setattr("m2v.commands.load_project", lambda *_: (root, manifest))
    assert main(["render", "--project", str(root)]) == 0
    assert final.read_bytes() == b"final"


def test_status_reports_candidate_failure_and_review_independently(tmp_path, monkeypatch):
    _register_builtins()
    prepared = {"preparedFingerprint": "current"}
    monkeypatch.setattr("m2v.commands._prepared", lambda *_: prepared)
    manifest = {"id": "demo", "type": "text-motion"}
    assert _status(tmp_path, manifest)["stage"] == "prepared"
    video = tmp_path / "outputs/candidates/test.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"candidate")
    record = {"preparedFingerprint": "current", "path": str(video),
              "sha256": delivery.digest(video), "status": "validation-failed", "error": "probe failed"}
    (tmp_path / "outputs/delivery.json").write_text(json.dumps(record), encoding="utf-8")
    result = _status(tmp_path, manifest)
    assert result["stage"] == "validation-failed"
    assert result["candidate"]["error"] == "probe failed"
    assert result["production"]["complete"] is False
    video.write_bytes(b"damaged")
    assert _status(tmp_path, manifest)["candidate"]["status"] == "stale"
