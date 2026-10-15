"""导出依赖当前完整预演，人工画面评审只在主动调用时验证。"""
import hashlib
import json
import subprocess
from dataclasses import replace

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.cli import main, _register_builtins, _status
from m2v.core.errors import M2VError
from m2v.core.preview import require_preview
from m2v.types import registry


def preview_fixture(root):
    outputs = root / "outputs"
    outputs.mkdir(parents=True)
    video = outputs / "preview.mp4"
    video.write_bytes(b"full-preview")
    prepared = {"preparedFingerprint": "current", "durationInFrames": 6,
                "width": 64, "height": 96, "fps": 30, "audio": {"segments": []}}
    record = {"preparedFingerprint": "current", "frames": 6,
              "path": "outputs/preview.mp4", "sha256": hashlib.sha256(video.read_bytes()).hexdigest()}
    (outputs / "preview-record.json").write_text(json.dumps(record), encoding="utf-8")
    return prepared, record, video


@pytest.mark.parametrize("kind", ["article-narrative", "general", "housing-timeseries", "stock-montage"])
@pytest.mark.parametrize("review_state", [None, "pending", "fail", "empty-evidence", "stale"])
def test_all_types_export_without_manual_review(tmp_path, monkeypatch, kind, review_state):
    _register_builtins()
    root = tmp_path / kind
    prepared, record, _ = preview_fixture(root)
    manifest = {"id": "demo", "type": kind}
    if review_state:
        (root / "outputs/review.json").write_text(json.dumps({
            "status": review_state, "evidence": {}, "preparedFingerprint": "old"}), encoding="utf-8")
    original = registry.get(kind)
    final = root / "outputs/final.mp4"

    def render(*_):
        final.write_bytes(b"final")
        return final

    monkeypatch.setattr(registry, "_registry", {kind: replace(original, render=render,
                        prepared_check=lambda *_: prepared)})
    monkeypatch.setattr("m2v.cli.load_project", lambda *_: (root, manifest))
    monkeypatch.setattr("m2v.cli.load_current_prepared", lambda *_: prepared)
    monkeypatch.setattr("m2v.core.preview.output_validation.verify_output", lambda *a, **kw: None)
    # Article source review is deliberately independent of the optional visual review.
    monkeypatch.setattr("m2v.types.article.adapter.validate", lambda *_: None)
    monkeypatch.setattr("m2v.types.article.explainer_review.require_input", lambda *_: None)
    monkeypatch.setattr("m2v.types.article.explainer_render.current", lambda *_: prepared)
    assert main(["render", "--project", str(root)]) == 0
    assert final.read_bytes() == b"final"
    if review_state is None:
        assert not (root / "outputs/review.json").exists()


@pytest.mark.parametrize("damage", ["missing-record", "missing-video", "limited", "old-fingerprint",
                                     "changed-video", "bad-json", "non-object", "bool-frames"])
def test_invalid_preview_blocks_export(tmp_path, monkeypatch, damage):
    prepared, record, video = preview_fixture(tmp_path)
    path = tmp_path / "outputs/preview-record.json"
    if damage == "missing-record":
        path.unlink()
    elif damage == "missing-video":
        video.unlink()
    elif damage == "changed-video":
        video.write_bytes(b"replaced")
    elif damage == "bad-json":
        path.write_text("{", encoding="utf-8")
    elif damage == "non-object":
        path.write_text("[]", encoding="utf-8")
    else:
        if damage == "limited": record["frames"] = 3
        if damage == "bool-frames": record["frames"] = True
        if damage == "old-fingerprint": record["preparedFingerprint"] = "old"
        path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(M2VError, match="完整预演"):
        require_preview(tmp_path, prepared)


def test_decode_checks_actual_frames_even_if_record_claims_full_length(tmp_path):
    prepared, record, video = preview_fixture(tmp_path)
    subprocess.run([get_ffmpeg_exe(), "-v", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=black:s=64x96:r=30", "-frames:v", "3", "-pix_fmt", "yuv420p",
                    "-color_range", "tv", "-c:v", "libx264", str(video)], check=True)
    record["sha256"] = hashlib.sha256(video.read_bytes()).hexdigest()
    (tmp_path / "outputs/preview-record.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(M2VError, match="帧数不匹配"):
        require_preview(tmp_path, prepared)
    prepared["durationInFrames"] = record["frames"] = 3
    (tmp_path / "outputs/preview-record.json").write_text(json.dumps(record), encoding="utf-8")
    require_preview(tmp_path, prepared)


def test_status_reports_optional_review_independently(tmp_path, monkeypatch):
    _register_builtins()
    prepared, record, video = preview_fixture(tmp_path)
    monkeypatch.setattr("m2v.cli._prepared", lambda *_: prepared)
    manifest = {"id": "demo", "type": "stock-montage"}
    result = _status(tmp_path, manifest)
    assert result["review"] == {"status": "optional", "required": False}
    assert result["preview"]["status"] == "current"
    video.write_bytes(b"changed")
    result = _status(tmp_path, manifest)
    assert result["preview"]["status"] == "stale"
    assert result["review"]["required"] is False
