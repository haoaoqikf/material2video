from __future__ import annotations
import copy
import json
import wave
from pathlib import Path
import pytest
from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_project, load_current_prepared
from m2v.types.article import adapter, explainer, explainer_prepare as prepare, explainer_review as review

ROOT = Path(__file__).resolve().parents[1]


def board():
    return {"version": 5, "schemaVersion": 5, "fps": 30, "width": 1080, "height": 1920,
        "title": "测试", "scenes": [{"id": "a", "template": "point",
        "content": {"title": "观点", "summary": {"text": "观察反馈", "segmentId": "a-line", "keywords": ["反馈"]}},
        "narrationSegments": [{"id": "a-line", "text": "观察结果，修正做法。"}]}]}


def project(tmp_path, data=None):
    root = tmp_path / "video"
    create_project(root, "article-narrative", {"storyboard": "storyboard.json"})
    (root / "storyboard.json").write_text(json.dumps(data or board(), ensure_ascii=False), encoding="utf-8")
    (root / "article.md").write_text("# 标题\n观察结果，根据反馈修正做法。", encoding="utf-8")
    root, manifest = load_project(root)
    record = review.template(root, manifest)
    record.update(status="pass", claim="反馈帮助改进", rationale="原文有清晰观点和操作方法", reviewer="测试夹具")
    (root / "outputs").mkdir()
    (root / "outputs/input-review.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return root, manifest


def fake_tts(monkeypatch, seconds=1):
    calls = []
    def speak(text, voice, rate, cache, **kwargs):
        calls.append((text, voice, rate, kwargs))
        wav = cache / "fixture.wav"
        hit = wav.exists()
        with wave.open(str(wav), "wb") as stream:
            stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            stream.writeframes(b"\x01\0" * round(seconds * 24000))
        return wav, [{"start": 0, "end": seconds, "text": text}], [], seconds, hit
    monkeypatch.setattr(prepare.tts, "scene_audio", speak)
    return calls


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_old_storyboards_rejected(tmp_path, version):
    data = board(); data.update(version=version, schemaVersion=version)
    with pytest.raises(M2VError, match="重新编排"):
        explainer.validate(data, tmp_path)


@pytest.mark.parametrize("mutation,match", [
    (lambda b: b["scenes"][0]["content"]["summary"].update(segmentId="unknown"), "segmentId"),
    (lambda b: b["scenes"][0]["content"]["summary"].update(keywords=["没有的词"]), "keywords"),
    (lambda b: b["scenes"].append(copy.deepcopy(b["scenes"][0])), "重复 ID"),
    (lambda b: b["scenes"][0].update(world={}), "未知字段"),
])
def test_invalid_material(tmp_path, mutation, match):
    data = board(); mutation(data)
    with pytest.raises(M2VError, match=match): explainer.validate(data, tmp_path)


def test_graph_rejects_cycles_and_computes_layers(tmp_path):
    data = json.loads((ROOT / "examples/buffer-smoothing/storyboard.json").read_text(encoding="utf-8"))
    scene = data["scenes"][-1]
    assert explainer.graph_levels(scene["content"]) == {"producer": 0, "buffer": 1, "consumer": 2}
    scene["content"]["links"].append({"from": "consumer", "to": "producer", "text": "循环", "segmentId": "buffer-cause-1"})
    with pytest.raises(M2VError, match="循环"): explainer.validate(data, tmp_path)


def test_missing_image_and_path_escape(tmp_path):
    data = board(); data["scenes"][0].update(template="image", content={"title": "图片", "src": "missing.png",
        "caption": {"text": "说明", "segmentId": "a-line"}})
    with pytest.raises(M2VError, match="本地文件"): explainer.validate(data, tmp_path)


@pytest.mark.parametrize("seconds,passes", [(59.6, True), (59.6 + 1/30, False)])
def test_exact_sixty_second_limit(tmp_path, monkeypatch, seconds, passes):
    root, manifest = project(tmp_path)
    fake_tts(monkeypatch, seconds)
    if passes:
        result = adapter.prepare(root, manifest)
        assert result["durationInFrames"] == 1800
    else:
        with pytest.raises(M2VError, match="超过 60 秒"): adapter.prepare(root, manifest)
        assert not (root / "outputs/prepared.json").exists()


def test_real_audio_axis_fade_and_cache(tmp_path, monkeypatch):
    data = board(); second = copy.deepcopy(data["scenes"][0]); second.update(id="b", transition="fade")
    second["narrationSegments"][0]["id"] = "b-line"; second["content"]["summary"]["segmentId"] = "b-line"
    data["scenes"].append(second)
    root, manifest = project(tmp_path, data)
    calls = fake_tts(monkeypatch)
    result = adapter.prepare(root, manifest, voice="zh-CN-YunxiNeural", rate="-6%")
    a,b = result["props"]["compiledScenes"]
    assert a["segmentWindows"]["a-line"] == {"startFrame": 0, "endFrame": 30}
    assert a["endFrame"] == 50 and b["startFrame"] == 42
    assert b["segmentWindows"]["b-line"]["startFrame"] == 50
    assert result["durationInFrames"] == 92
    assert calls[0][1:3] == ("zh-CN-YunxiNeural", "-6%")
    with wave.open(str(root / result["audio"]["segments"][0]["path"]), "rb") as wav:
        assert wav.getnframes() == 92 * 800
    next_result = adapter.prepare(root, manifest)
    assert next_result["audio"]["cacheHits"] == 2


@pytest.mark.parametrize("reference", ["article.md", "outputs/input-review.json"])
def test_referenced_files_invalidate_preparation(tmp_path, monkeypatch, reference):
    root, manifest = project(tmp_path); fake_tts(monkeypatch)
    adapter.prepare(root, manifest)
    (root / reference).write_text("变化", encoding="utf-8")
    with pytest.raises(M2VError, match="文件已变化"): load_current_prepared(root, manifest)


def test_unreviewed_input_blocks_prepare(tmp_path, monkeypatch):
    root, manifest = project(tmp_path)
    review.create_input(root, manifest)
    calls = fake_tts(monkeypatch)
    with pytest.raises(M2VError, match="未通过"): adapter.prepare(root, manifest)
    assert calls == []


def test_fixed_examples_cover_all_templates():
    found=set()
    for file in (ROOT / "examples").glob("*/storyboard.json"):
        data=json.loads(file.read_text(encoding="utf-8")); explainer.validate(data, file.parent)
        found.update(s["template"] for s in data["scenes"])
    assert found == explainer.TEMPLATES


def test_image_change_invalidates_child_and_parent(tmp_path, monkeypatch):
    from m2v.cli import _register_builtins
    from m2v.types.general import adapter as general
    from m2v.core.project import _write_json
    _register_builtins()
    parent = tmp_path / "parent"
    parent.mkdir()
    data = json.loads((ROOT / "examples/darts-trial-and-error/storyboard.json").read_text(encoding="utf-8"))
    child, manifest = project(parent, data)
    (child / "assets").mkdir()
    image = child / "assets/feedback.png"
    image.write_bytes((ROOT / "examples/darts-trial-and-error/assets/feedback.png").read_bytes())
    fake_tts(monkeypatch)
    prepared = adapter.prepare(child, manifest)
    # 仅为集成测试的人工评审替身，真实制作不会自动写 pass。
    preview_file = child / "outputs/previews/video.mp4"
    preview_file.parent.mkdir()
    preview_file.write_bytes(b"test preview fixture")
    import hashlib
    preview = {"path": "outputs/previews/video.mp4", "sha256": hashlib.sha256(preview_file.read_bytes()).hexdigest(),
               "frames": prepared["durationInFrames"], "preparedFingerprint": prepared["preparedFingerprint"]}
    _write_json(child / "outputs/preview-record.json", preview)
    _write_json(child / "outputs/review.json", {"schemaVersion": 1, "status": "pass", "projectId": manifest["id"],
        "preparedFingerprint": prepared["preparedFingerprint"], "preview": preview,
        "criteria": review.criteria(child, manifest, prepared),
        "evidence": {key: "集成测试人工评审替身" for key in review.criteria(child, manifest, prepared)}})
    create_project(parent, "general", {"plan": "general-plan.json"})
    _write_json(parent / "general-plan.json", {"schemaVersion": 1, "scenes": [{"id": "article", "type": "article-narrative", "project": "video"}]})
    parent, project_manifest = load_project(parent)
    result = general.prepare(parent, project_manifest)
    scene = result["props"]["compiledScenes"][0]
    assert scene["embeddedComposition"] == "ArticleExplainer"
    assert scene["embeddedProps"]["version"] == 5
    assert scene["durationInFrames"] == prepared["durationInFrames"]
    assert result["audio"]["segments"][0]["durationInFrames"] == prepared["durationInFrames"]
    image.write_bytes(b"changed")
    with pytest.raises(M2VError, match="文件已变化"):
        load_current_prepared(parent, project_manifest)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_browser_layout_and_random_seek(tmp_path, monkeypatch, chromium_ready, theme):
    from m2v.types.article.explainer_render import layout_check
    from m2v.engine.contract_page import serve_contract_page
    from playwright.sync_api import sync_playwright
    data = board(); data["visual"] = {"theme": theme}
    root, manifest = project(tmp_path, data); fake_tts(monkeypatch)
    prepared = adapter.prepare(root, manifest)
    assert layout_check(root, prepared)["status"] == "pass"
    props = root / "outputs/browser-props.json"
    props.write_text(json.dumps(prepared["props"], ensure_ascii=False), encoding="utf-8")
    with serve_contract_page(props, root) as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width":1080, "height":1920})
            page.goto(url + "&m2v-explainer=1"); page.wait_for_function("window.__M2V__?.version === 5")
            page.evaluate("async () => await window.__M2V__.ready()")
            samples = {}
            for frame in [0,8,30,41,15,8,0,41]:
                page.evaluate("async f => await window.__M2V__.seekToFrame(f)", frame)
                image = page.screenshot()
                if frame in samples: assert samples[frame] == image
                samples[frame] = image
        finally: browser.close()


def test_browser_blocks_overflow(tmp_path, monkeypatch, chromium_ready):
    from m2v.types.article.explainer_render import layout_check
    data = board(); data["scenes"][0]["content"]["summary"]["text"] = "很长的摘要" * 150
    data["scenes"][0]["content"]["summary"]["keywords"] = []
    root,manifest = project(tmp_path,data);fake_tts(monkeypatch)
    prepared=adapter.prepare(root,manifest)
    with pytest.raises(M2VError,match="排版量测失败"): layout_check(root,prepared)
