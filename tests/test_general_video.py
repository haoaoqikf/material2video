from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from a2v.core.errors import A2VError
from a2v.core.project import create_project, load_project, load_current_prepared
from a2v.types.general import adapter


def _project(tmp_path: Path, plan: dict) -> tuple[Path, dict]:
    root = tmp_path / "通用作品"
    create_project(root, "general")
    (root / "general-plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return load_project(root)


def test_compile_uses_one_frame_axis_and_rejects_three_way_overlap(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "a", "type": "graphic", "duration": {"frames": 60}},
        {"id": "b", "type": "graphic", "duration": {"frames": 60}, "transition": {"type": "crossfade", "frames": 12}},
        {"id": "c", "type": "graphic", "duration": {"frames": 60}, "transition": {"type": "crossfade", "frames": 12}},
    ]})
    adapter.validate(root, manifest)
    compiled = adapter._compile(adapter._plan(root, manifest))
    assert [scene["startFrame"] for scene in compiled["compiledScenes"]] == [0, 48, 96]
    assert compiled["durationInFrames"] == 156

    compiled["scenes"][1]["transition"]["frames"] = 30
    compiled["scenes"][2]["transition"]["frames"] = 30
    with pytest.raises(A2VError, match="三个场景同时重叠"):
        adapter._compile(compiled)


def test_prepare_binds_plan_and_reports_expired_when_material_changes(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "opening", "type": "graphic", "duration": {"frames": 45},
         "data": {"title": "标题"}},
    ]})
    prepared = adapter.prepare(root, manifest)
    assert prepared["durationInFrames"] == 45
    assert load_current_prepared(root, manifest)["preparedFingerprint"] == prepared["preparedFingerprint"]
    (root / "general-plan.json").write_text('{"schemaVersion":1,"scenes":[]}', encoding="utf-8")
    with pytest.raises(A2VError, match="材料已变化"):
        load_current_prepared(root, manifest)


def test_mux_audio_uses_frame_delays_and_overlap_fades(monkeypatch, tmp_path: Path) -> None:
    import a2v.types.general.adapter as general

    wav = tmp_path / "voice.wav"
    wav.write_bytes(b"wave")
    seen = {}
    def fake_run(command, **kwargs):
        seen["command"] = command
        return type("Result", (), {"returncode": 0, "stderr": ""})()
    monkeypatch.setattr(general.subprocess, "run", fake_run)
    general._mux_audio(tmp_path, tmp_path / "video.mp4", tmp_path / "out.mp4",
        [{"path": "voice.wav", "startFrame": 30, "durationInFrames": 120,
          "fadeInFrames": 12, "fadeOutFrames": 12,
          "sha256": hashlib.sha256(wav.read_bytes()).hexdigest()}], 30, 300)
    command = seen["command"]
    filters = command[command.index("-filter_complex") + 1]
    assert "adelay=1000|1000" in filters
    assert "afade=t=in" in filters and "afade=t=out" in filters


def test_code_scene_is_scanned_before_prepare(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "unsafe", "type": "code", "duration": {"frames": 30},
         "renderer": {"kind": "code", "module": "unsafe"}},
    ]})
    scenes = root / "scenes"
    scenes.mkdir()
    (scenes / "unsafe.tsx").write_text(
        "export default function Unsafe() { return fetch('https://example.invalid'); }\n",
        encoding="utf-8",
    )
    with pytest.raises(A2VError, match="网络 API"):
        adapter.validate(root, manifest)


def test_graphic_relations_and_data_are_bounded_and_referenced(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "chart", "type": "graphic", "duration": {"frames": 60}, "data": {
            "nodes": [{"id": "cause", "label": "原因"}, {"id": "effect", "label": "结果"}],
            "links": [{"from": "cause", "to": "effect", "label": "推动"}],
            "values": [{"label": "指标", "value": 12.5}],
        }},
    ]})
    adapter.validate(root, manifest)
    plan = adapter._plan(root, manifest)
    assert plan["scenes"][0]["data"]["links"][0]["to"] == "effect"

    broken = plan["scenes"][0]["data"]
    broken["links"][0]["to"] = "missing"
    with pytest.raises(A2VError, match="引用已声明节点"):
        adapter._validate_graphic_data("chart", broken)
