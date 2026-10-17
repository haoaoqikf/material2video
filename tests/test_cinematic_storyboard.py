"""cinematic 档位在分镜、准备与 CLI 上的落地；重点是 standard 行为不回归。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.core.project import load_project
from m2v.types.general import adapter, code_scenes, explainer
from test_article_explainer import board, fake_record, fake_tts, project, scene, scene_root


def prepare_with(tmp_path, monkeypatch, data, *, seconds=1, **options):
    root, manifest = project(tmp_path, data)
    fake_tts(monkeypatch, seconds=seconds)
    calls = fake_record(monkeypatch)
    prepared = adapter.prepare(root, manifest, **options)
    return root, manifest, prepared, calls


def shot(identity, tier, start, end, **extra):
    return {"id": identity, "target": identity, "tier": tier, "startFrame": start, "endFrame": end, **extra}


def cinematic_scene(shots, segments=None, identity="a", **extra):
    content = {"title": "观点", "entry": "scenes/opening.tsx", "props": {"shots": shots}}
    body = scene(identity, content=content,
                 narrationSegments=segments or [{"id": f"{identity}-line", "text": "观察结果，修正做法。"}])
    body.update(extra)
    return body


# ---------------------------------------------------------------- standard 回归


def test_standard_board_keeps_reading_hold_and_windows(tmp_path, monkeypatch):
    """未声明新字段时：1 秒旁白 + 24 帧阅读停留，时间窗从 0 开始。"""
    _, _, prepared, _ = prepare_with(tmp_path, monkeypatch, board())
    assert prepared["durationInFrames"] == 60 + 24
    windows = prepared["props"]["compiledScenes"][0]["segmentWindows"]
    assert windows["a-line"] == {"startFrame": 0, "endFrame": 60}
    assert prepared["props"]["productionProfile"] == "standard"
    assert prepared["props"]["productionProfileSource"] == "default"
    assert json.loads(prepared["inputs"]["profile"]) == {"profile": "standard", "source": "default"}


def test_standard_record_config_omits_cinematic_keys():
    """standard 且未声明 claims 时，缓存配置里不能出现新键，否则旧片段缓存全部失效。"""
    target = {"id": "a", "startFrame": 0, "durationInFrames": 84,
              "content": {"props": {"title": "x"}},
              "segmentWindows": {"a-line": {"startFrame": 0, "endFrame": 60}},
              "narrationSegments": [{"id": "a-line", "text": "x"}]}
    frame = {"width": 1920, "height": 1080, "subtitle": {"safeArea": {"x": 1, "y": 2, "width": 3, "height": 4}}}
    config = code_scenes.scene_config(target, frame, {"a": {"src": "/media/a.png"}})
    assert set(config) == {"props", "fps", "durationInFrames", "width", "height",
                           "subtitleSafeArea", "segmentWindows", "media"}


def test_cinematic_config_carries_profile_and_claims():
    target = {"id": "a", "startFrame": 0, "durationInFrames": 84,
              "content": {"props": {"title": "x"}},
              "segmentWindows": {"a-line": {"startFrame": 0, "endFrame": 60}},
              "narrationSegments": [{"id": "a-line", "text": "x", "claims": ["夜面灯光"]}]}
    frame = {"width": 1920, "height": 1080, "subtitle": {"safeArea": {"x": 1, "y": 2, "width": 3, "height": 4}}}
    config = code_scenes.scene_config(target, frame, {}, profile="cinematic")
    assert config["profile"] == "cinematic" and config["claims"] == [["夜面灯光"]]


# ---------------------------------------------------------------- 留白与阅读停留


def test_lead_in_tail_and_reading_hold_shift_the_timeline(tmp_path, monkeypatch):
    data = board(scenes=[scene(leadInFrames=120, tailFrames=60, readingHoldFrames=60)])
    _, _, prepared, _ = prepare_with(tmp_path, monkeypatch, data)
    compiled = prepared["props"]["compiledScenes"][0]
    assert prepared["durationInFrames"] == 120 + 60 + 60 + 60
    assert compiled["segmentWindows"]["a-line"] == {"startFrame": 120, "endFrame": 180}
    assert compiled["startFrame"] == 0


@pytest.mark.parametrize("extra,match", [
    ({"leadInFrames": -1}, "leadInFrames"),
    ({"leadInFrames": 1801}, "leadInFrames"),
    ({"leadInFrames": "120"}, "leadInFrames"),
    ({"tailFrames": 1801}, "tailFrames"),
    ({"readingHoldFrames": 361}, "readingHoldFrames"),
    ({"readingHoldFrames": True}, "readingHoldFrames"),
])
def test_out_of_range_padding_is_rejected(tmp_path, extra, match):
    with pytest.raises(M2VError, match=match):
        explainer.validate(board(scenes=[scene(**extra)]), scene_root(tmp_path))


def test_fixed_duration_must_cover_padding(tmp_path, monkeypatch):
    data = board(scenes=[scene(leadInFrames=600, durationFrames=60)])
    with pytest.raises(M2VError, match="不足以容纳旁白、留白"):
        prepare_with(tmp_path, monkeypatch, data)


# ---------------------------------------------------------------- 档位来源


def test_profile_comes_from_project_then_command_line(tmp_path, monkeypatch):
    root, manifest = project(tmp_path, board())
    manifest["productionProfile"] = "cinematic"
    (root / "project.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    root, manifest = load_project(root)
    fake_tts(monkeypatch)
    fake_record(monkeypatch)
    prepared = adapter.prepare(root, manifest)
    assert prepared["props"]["productionProfile"] == "cinematic"
    assert prepared["props"]["productionProfileSource"] == "project"
    prepared = adapter.prepare(root, manifest, profile="standard")
    assert prepared["props"]["productionProfile"] == "standard"
    assert prepared["props"]["productionProfileSource"] == "command-line"


def test_invalid_project_profile_is_rejected(tmp_path):
    root, manifest = project(tmp_path, board())
    manifest["productionProfile"] = "epic"
    with pytest.raises(M2VError, match="productionProfile"):
        adapter.validate(root, manifest)


def test_other_types_reject_the_profile_option():
    from m2v.types.financial import adapter as financial
    from m2v.types.housing import adapter as housing
    with pytest.raises(M2VError, match="不支持制作档位"):
        financial.prepare(Path("."), {}, profile="cinematic")
    with pytest.raises(M2VError, match="不支持制作档位"):
        housing.prepare(Path("."), {}, profile="cinematic")


def test_cli_rejects_unknown_profile_value(tmp_path):
    from m2v.cli import main
    with pytest.raises(SystemExit):
        main(["prepare", "--project", str(tmp_path), "--profile", "epic"])


# ---------------------------------------------------------------- 镜头、look 与 claims


def hero_shots():
    return [shot("earth", "hero", 0, 480), shot("saturn", "hero", 480, 960), shot("oort", "hero", 960, 1440)]


def test_shots_look_and_claims_validate(tmp_path):
    segments = [{"id": "a-line", "text": "观察结果，修正做法。", "claims": ["夜面灯光"]}]
    data = board(scenes=[cinematic_scene(hero_shots(), segments=segments)])
    data["scenes"][0]["content"]["props"]["look"] = {"profile": "deep-space", "grain": 0.3}
    explainer.validate(data, scene_root(tmp_path))


@pytest.mark.parametrize("mutate,match", [
    (lambda data: data["scenes"][0]["content"]["props"].update(shots=[shot("earth", "hero", 0, 480)]), "hero"),
    (lambda data: data["scenes"][0]["content"]["props"].update(look={"grain": 0.3}), "profile"),
    (lambda data: data["scenes"][0]["content"]["props"]["shots"][0].update(tier="epic"), "tier"),
    (lambda data: data["scenes"][0]["content"]["props"]["shots"][0].update(zoom=2), "未知字段"),
    (lambda data: data["scenes"][0]["narrationSegments"][0].update(claims=["a", "a"]), "重复"),
    (lambda data: data["scenes"][0]["narrationSegments"][0].update(claims=[""]), "非空"),
])
def test_invalid_cinematic_fields_are_rejected(tmp_path, mutate, match):
    data = board(scenes=[cinematic_scene(hero_shots())])
    mutate(data)
    with pytest.raises(M2VError, match=match):
        explainer.validate(data, scene_root(tmp_path))


def test_duplicate_shot_ids_across_scenes_are_rejected(tmp_path):
    data = board(scenes=[cinematic_scene(hero_shots()),
                         cinematic_scene([shot("earth", "major", 0, 60)], identity="b")])
    with pytest.raises(M2VError, match="重复镜头 ID"):
        explainer.validate(data, scene_root(tmp_path))


def test_shot_must_cover_the_declared_segment_before_recording(tmp_path, monkeypatch):
    """镜头时间窗只有拿到真实分段时长才能判定，且必须在录制之前失败。"""
    shots = [shot("earth", "hero", 0, 480, segment="a-line"),
             shot("saturn", "hero", 0, 480, segment="a-line"),
             shot("oort", "hero", 24, 504, segment="a-line")]
    data = board(scenes=[cinematic_scene(shots)])
    root, manifest = project(tmp_path, data)
    fake_tts(monkeypatch, seconds=8)
    calls = fake_record(monkeypatch)
    with pytest.raises(M2VError, match="没有覆盖声明的旁白段"):
        adapter.prepare(root, manifest)
    assert calls == []


def test_cold_open_shot_without_segment_is_allowed(tmp_path, monkeypatch):
    """冷开场没有旁白可依：不声明 segment 时只要求落在幕时长内。"""
    shots = [shot("sun", "minor", 0, 200),
             shot("earth", "hero", 200, 680, segment="a-line"),
             shot("saturn", "hero", 200, 680, segment="a-line"),
             shot("oort", "hero", 200, 680, segment="a-line")]
    data = board(scenes=[cinematic_scene(shots, leadInFrames=200, readingHoldFrames=0)])
    _, _, prepared, _ = prepare_with(tmp_path, monkeypatch, data, seconds=8)
    assert prepared["durationInFrames"] == 200 + 480
    windows = prepared["props"]["compiledScenes"][0]["segmentWindows"]
    assert windows["a-line"] == {"startFrame": 200, "endFrame": 680}
