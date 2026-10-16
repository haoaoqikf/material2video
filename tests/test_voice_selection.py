"""选音门禁与旁白上下文；所有媒体由本地替身生成。"""
import copy
import hashlib
import json

import pytest

from m2v.core.errors import M2VError
from m2v.core.project import load_current_prepared
from m2v.core.preview import require_preview
from m2v.engine import tts


def selected(texts):
    return {"tts": {"voice": "zh-CN-YunxiNeural", "selection": {
        "mode": "assistant", "rationale": "旁白面向学习者，采用活泼讲解风格。",
        "narrationSha256": tts.narration_digest(texts)}}}


def test_digest_preserves_order_boundaries_and_ignores_empty():
    texts = ["第一句。", "第二句。"]
    expected = hashlib.sha256(json.dumps(texts, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    assert tts.narration_digest(texts) == expected
    assert tts.narration_digest(["", *texts, " "]) == expected
    assert tts.narration_digest(texts[::-1]) != expected
    assert tts.narration_digest(["".join(texts)]) != expected


def test_assistant_selection_and_visual_change():
    project = selected(["第一句。"])
    before = tts.preparation(project, ["第一句。"])
    project["visual"] = {"theme": "light"}
    assert tts.preparation(project, ["第一句。"]) == before
    assert before["source"] == "assistant"
    assert before["selection"] == project["tts"]["selection"]
    assert before["rate"] == "+0%"
    with pytest.raises(M2VError, match="选择已过期"):
        tts.preparation(project, ["另一句。"])


def test_manual_override_skips_stale_selection_and_never_carries_reason():
    project = selected(["旧内容。"])
    project["tts"]["rate"] = "-6%"
    result = tts.preparation(project, ["新内容。"], voice="zh-CN-YunyangNeural")
    assert result == {"backend": "edge-tts", "voice": "zh-CN-YunyangNeural", "rate": "-6%", "source": "command-line"}
    assert tts.preparation(project, ["新内容。"], voice="zh-CN-YunxiNeural")["source"] == "command-line"
    with pytest.raises(M2VError, match="选择已过期"):
        tts.preparation(project, ["新内容。"], rate="+5%")
    project["tts"].pop("selection")
    assert tts.preparation(project, ["新内容。"])["source"] == "project"


@pytest.mark.parametrize("selection", [None, {}, "auto", {"mode": "rule"},
    {"mode": "assistant", "rationale": " ", "narrationSha256": "a" * 64},
    {"mode": "assistant", "rationale": "理由", "narrationSha256": "bad"}])
def test_invalid_selection(selection):
    with pytest.raises(M2VError, match="tts.selection"):
        tts.settings({"tts": {"voice": "zh-CN-YunxiNeural", "selection": selection}})


def test_missing_voice_and_invalid_command_line():
    assert tts.preparation({}, []) == {}
    assert tts.preparation({}, [" ", ""]) == {}
    for project in ({}, {"tts": {"rate": "-6%"}}):
        with pytest.raises(M2VError, match="--voice"):
            tts.preparation(project, ["旁白"])
    with pytest.raises(M2VError, match="音色名"):
        tts.preparation({}, ["旁白"], voice="invalid")
    with pytest.raises(M2VError, match="百分比"):
        tts.preparation({}, ["旁白"], voice="zh-CN-YunxiNeural", rate="invalid")
    with pytest.raises(M2VError, match="同时声明"):
        tts.settings({"tts": {"selection": selected(["旁白"])["tts"]["selection"]}})


def test_voice_and_rate_change_cache_keys():
    key = tts.scene_cache_key("旁白", "zh-CN-YunxiNeural", "+0%", 5)
    assert key != tts.scene_cache_key("旁白", "zh-CN-YunyangNeural", "+0%", 5)
    assert key != tts.scene_cache_key("旁白", "zh-CN-YunxiNeural", "-6%", 5)


def test_article_requires_voice_and_binds_actual_selection(tmp_path, monkeypatch):
    from test_article_explainer import project, fake_tts, board
    from m2v.types.general import adapter
    root, manifest = project(tmp_path)
    calls = fake_tts(monkeypatch)
    manifest.pop("tts")
    with pytest.raises(M2VError, match="尚未选择"):
        adapter.prepare(root, manifest)
    assert not calls
    texts = [s["text"] for scene in board()["scenes"] for s in scene["narrationSegments"]]
    manifest.update(selected(texts))
    (root / "project.json").write_text(json.dumps(manifest), encoding="utf-8")
    result = adapter.prepare(root, manifest)
    record = json.loads(result["inputs"]["tts"])
    assert record["source"] == "assistant"
    assert record["voice"] == calls[0][1]
    old = copy.deepcopy(result)
    # 绑定真实的旧预演，证明阻断来自指纹过期，而不是文件缺失。
    preview_file = root / "outputs/previews/video.mp4"
    preview_file.parent.mkdir()
    preview_file.write_bytes(b"old full preview")
    (root / "outputs/preview-record.json").write_text(json.dumps({
        "path": "outputs/previews/video.mp4", "sha256": hashlib.sha256(preview_file.read_bytes()).hexdigest(),
        "frames": old["durationInFrames"], "preparedFingerprint": old["preparedFingerprint"]}), encoding="utf-8")
    require_preview(root, old, verify_media=False)
    # 新准备指纹不能使用旧预演；配置改变也使旧准备失效。
    manifest["tts"]["voice"] = "zh-CN-YunyangNeural"
    (root / "project.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(M2VError, match="作品描述已变化"):
        load_current_prepared(root, manifest)
    second = adapter.prepare(root, manifest, voice="zh-CN-YunyangNeural", rate="-6%")
    assert second["preparedFingerprint"] != old["preparedFingerprint"]
    assert json.loads(second["inputs"]["tts"])["source"] == "command-line"
    with pytest.raises(M2VError):
        require_preview(root, second, verify_media=False)


def test_general_silent_has_no_voice_requirement(tmp_path):
    import shutil
    from pathlib import Path
    from test_article_explainer import project
    from m2v.types.general import adapter
    source = Path(__file__).resolve().parents[1] / "examples/darts-trial-and-error"
    data = json.loads((source / "storyboard.json").read_text(encoding="utf-8"))
    scene = next(s for s in data["scenes"] if s["template"] == "image")
    scene["narrationSegments"] = []
    scene["content"].pop("caption", None)
    scene["durationFrames"] = 30
    scene["transition"] = "cut"
    scene.pop("transitionFrames", None)
    data["scenes"] = [scene]
    data.pop("soundtrack", None)
    root, manifest = project(tmp_path, data)
    shutil.copytree(source / "assets", root / "assets")
    manifest.pop("tts")
    (root / "project.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert json.loads(adapter.prepare(root, manifest)["inputs"]["tts"]) == {}
