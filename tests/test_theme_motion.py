"""主题动效：帧数来自共享清单，并按其声明覆盖或让位于分镜。"""
from __future__ import annotations

import json

import pytest

from m2v.core.errors import M2VError
from m2v.engine import themes
from m2v.types.general import adapter, explainer, explainer_prepare as prepare

from test_article_explainer import fake_tts, project


def two_scenes(theme=None, transition_frames=None):
    """两幕：首幕 cut，次幕 crossfade。转场时长可显式声明以验证优先级。"""
    second = {"id": "b", "template": "point", "transition": "crossfade",
        "content": {"title": "做法", "summary": {"text": "修正做法", "segmentId": "b-line"}},
        "narrationSegments": [{"id": "b-line", "text": "根据反馈修正下一次的做法。"}]}
    if transition_frames is not None:
        second["transitionFrames"] = transition_frames
    data = {"version": 7, "schemaVersion": 7, "fps": 30, "width": 1080, "height": 1920, "title": "测试",
        "input": {"kind": "article"}, "targetSeconds": 60,
        "scenes": [
            {"id": "a", "template": "point",
             "content": {"title": "观点", "summary": {"text": "观察反馈", "segmentId": "a-line"}},
             "narrationSegments": [{"id": "a-line", "text": "观察结果，修正做法。"}]},
            second]}
    if theme is not None:
        data["visual"] = {"theme": theme}
    return data


def prepared(tmp_path, monkeypatch, data):
    root, manifest = project(tmp_path, data)
    fake_tts(monkeypatch)
    return adapter.prepare(root, manifest)


def test_主题名单与默认值来自共享清单():
    names = themes.names()
    assert "dark" in names and "light" in names and "velvet" in names
    assert themes.default() == "dark"
    assert themes.manifest_path().name == "themes.json"


def test_未知主题被拒绝并列出可选值(tmp_path):
    with pytest.raises(M2VError, match="只支持"):
        explainer.validate(two_scenes(theme="nope"), tmp_path)


def test_velvet_主题被契约接受(tmp_path):
    explainer.validate(two_scenes(theme="velvet"), tmp_path)


def test_未声明转场帧数的主题让位给分镜(tmp_path, monkeypatch):
    """dark/light 没有 transitionFrames：分镜声明多少就是多少，行为与从前一致。"""
    dark = prepared(tmp_path / "d", monkeypatch, two_scenes(theme="dark", transition_frames=30))
    assert dark["props"]["compiledScenes"][1]["transitionFrames"] == 30


def test_声明了转场帧数的主题覆盖分镜(tmp_path, monkeypatch):
    """velvet 声明 45 帧：分镜写的 30 不再生效。"""
    velvet = prepared(tmp_path / "v", monkeypatch, two_scenes(theme="velvet", transition_frames=30))
    assert velvet["props"]["compiledScenes"][1]["transitionFrames"] == 45


def test_主题接管阅读停留(tmp_path, monkeypatch):
    """阅读停留进 `minimum` 判据：velvet 的 90 帧比默认 12 帧长得多。"""
    dark = prepared(tmp_path / "d", monkeypatch, two_scenes(theme="dark"))
    velvet = prepared(tmp_path / "v", monkeypatch, two_scenes(theme="velvet"))
    # 两幕各 30 帧旁白，各自再加一次阅读停留。
    assert dark["durationInFrames"] == 2 * (30 + 12)
    assert velvet["durationInFrames"] == 2 * (30 + 90)


def test_入场帧数只在主题里声明():
    assert themes.motion("dark")["entranceFrames"] == 8
    assert themes.motion("velvet")["entranceFrames"] == 36


def test_主题动效字段非法时失败(monkeypatch):
    def manifest_with(motion_body):
        monkeypatch.setattr(themes, "manifest", lambda repo_root=None: {"default": "dark", "themes": {"dark": {"motion": motion_body}}})
    good = {"entranceFrames": 8, "holdFrames": 12}
    manifest_with(good)
    assert themes.motion("dark") == good

    manifest_with({"entranceFrames": 8})
    with pytest.raises(M2VError, match="缺少 holdFrames"):
        themes.motion("dark")

    manifest_with({**good, "swayFrames": 3})
    with pytest.raises(M2VError, match="未知字段"):
        themes.motion("dark")

    manifest_with({**good, "holdFrames": 0})
    with pytest.raises(M2VError, match="必须为正整数"):
        themes.motion("dark")


def test_主题清单结构非法时明确失败(tmp_path, monkeypatch):
    """清单级校验要在 `manifest` 里做，不能靠 patch 掉它来绕过。"""
    path = tmp_path / "themes.json"
    monkeypatch.setattr(themes, "manifest_path", lambda repo_root=None: path)

    path.write_text(json.dumps({"default": "dark"}), encoding="utf-8")
    with pytest.raises(M2VError, match="缺少非空的 themes"):
        themes.manifest()

    path.write_text(json.dumps({"default": "nope", "themes": {"dark": {}}}), encoding="utf-8")
    with pytest.raises(M2VError, match="default 不在 themes 里"):
        themes.manifest()

    path.write_text("{不是 JSON", encoding="utf-8")
    with pytest.raises(M2VError, match="不是合法 JSON"):
        themes.manifest()


def test_主题清单是合法JSON且字段齐全():
    data = json.loads(themes.manifest_path().read_text(encoding="utf-8"))
    for name, spec in data["themes"].items():
        assert set(spec["colors"]) == {"bg", "ink", "muted", "panel", "border", "accent"}, name
        assert set(spec["typography"]) == {"titleWeight", "titleTracking", "titleTransform", "bodyLineHeight"}, name
