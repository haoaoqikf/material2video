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


@pytest.mark.parametrize(("field", "message"), [
    ("duration", "保留完整时间轴"),
    ("narration", "保留自身声音"),
])
def test_embedded_scene_rejects_parent_trim_or_narration(tmp_path: Path, field: str, message: str) -> None:
    scene = {"id": "embedded", "type": "article-narrative", "project": "child"}
    scene[field] = {"frames": 30} if field == "duration" else "不能覆盖片段声音"
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [scene]})
    with pytest.raises(A2VError, match=message):
        adapter._plan(root, manifest)


def test_embedded_scene_rejects_reference_cycle_and_transition_overflow(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "cycle", "type": "article-narrative", "project": "."},
    ]})
    with pytest.raises(A2VError, match="project"):
        adapter._plan(root, manifest)

    root, manifest = _project(tmp_path / "overflow", {"schemaVersion": 1, "scenes": [
        {"id": "first", "type": "graphic", "duration": {"frames": 12}},
        {"id": "second", "type": "graphic", "duration": {"frames": 20},
         "transition": {"type": "crossfade", "frames": 12}},
    ]})
    with pytest.raises(A2VError, match="淡化不能超过前一场景时长"):
        adapter._plan(root, manifest)


def test_embedded_article_code_modules_are_namespaced_and_fingerprint_checked(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "story-one", "type": "article-narrative", "project": "one"},
        {"id": "story-two", "type": "article-narrative", "project": "two"},
    ]})
    from a2v.core.project import create_project, load_project as load_child, save_prepared

    for name in ("one", "two"):
        child = root / name
        create_project(child, "article-narrative")
        child_root, child_manifest = load_child(child)
        source = {"schemaVersion": 4, "world": {"renderer": {"kind": "code", "module": "water-tank"}}}
        (child_root / "storyboard.json").write_text(json.dumps(source), encoding="utf-8")
        (child_root / "scenes").mkdir()
        code = child_root / "scenes" / "water-tank.tsx"
        code.write_text("export default function Scene() { return null; }", encoding="utf-8")
        save_prepared(child_root, project=child_manifest, composition_id="A2V", props=source,
            width=1080, height=1920, fps=30, duration_in_frames=60, inputs={
                "storyboard": hashlib.sha256((child_root / "storyboard.json").read_bytes()).hexdigest(),
            })

    plan = adapter._plan(root, manifest)
    first, second = plan["scenes"]
    first_module = first["embeddedProps"]["world"]["renderer"]["module"]
    second_module = second["embeddedProps"]["world"]["renderer"]["module"]
    assert first_module != second_module
    assert first["embeddedCodeModules"][0]["id"] == first_module
    modules = adapter._embedded_modules(root, plan["scenes"])
    assert {module_id for module_id, _path in modules} == {first_module, second_module}

    first_path = modules[0][1]
    first_path.write_text("export default function Changed() { return null; }", encoding="utf-8")
    with pytest.raises(A2VError, match="重新 prepare"):
        adapter._embedded_modules(root, plan["scenes"], {
            f"embedded-module:{module['id']}": module["sha256"]
            for scene in plan["scenes"] for module in scene["embeddedCodeModules"]
        })


def test_narration_derive_maps_subtitles_and_rejects_fixed_capacity_overflow(tmp_path: Path, monkeypatch) -> None:
    from types import SimpleNamespace

    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "spoken", "type": "graphic", "narration": "一段口播。", "data": {"title": "口播"}},
    ]})

    def fake_speech(_text: str, cache: Path):
        wav = cache / "fake.wav"
        wav.write_bytes(b"wav")
        return wav, [{"start": 0.0, "end": 0.5, "text": "字幕"}], [], 1.5, False

    monkeypatch.setattr(adapter.registry, "get", lambda _name: SimpleNamespace(prepare_narration=fake_speech))
    prepared = adapter.prepare(root, manifest)
    assert prepared["durationInFrames"] == 57
    assert prepared["subtitles"] == [{"startFrame": 0, "endFrame": 15, "text": "字幕"}]

    fixed_root, fixed_manifest = _project(tmp_path / "fixed", {"schemaVersion": 1, "scenes": [
        {"id": "fixed", "type": "graphic", "duration": {"frames": 30},
         "narration": "口播放不下。", "data": {"title": "固定容量"}},
    ]})
    with pytest.raises(A2VError, match="超出固定帧容量"):
        adapter.prepare(fixed_root, fixed_manifest)
