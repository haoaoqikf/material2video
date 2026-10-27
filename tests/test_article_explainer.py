from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from m2v.core.errors import M2VError
from m2v.core.project import load_current_prepared
from m2v.core import frames
from m2v.types.general import adapter, explainer, explainer_prepare as prepare, explainer_review as review

from _helpers import ENTRY, STARTER, board, fake_record, fake_tts, project, scene, scene_root

ROOT = Path(__file__).resolve().parents[1]


def prepared(tmp_path, monkeypatch, data=None):
    root, manifest = project(tmp_path, data)
    fake_tts(monkeypatch)
    fake_record(monkeypatch)
    return root, manifest, adapter.prepare(root, manifest)


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5, 6, 7])
def test_old_storyboards_rejected(tmp_path, version):
    data = board(); data.update(version=version, schemaVersion=version)
    with pytest.raises(M2VError, match="重新编排"):
        explainer.validate(data, scene_root(tmp_path))


def test_version_and_schema_version_must_agree(tmp_path):
    data = board(); data["schemaVersion"] = 7
    with pytest.raises(M2VError, match="只接受 v8"):
        explainer.validate(data, scene_root(tmp_path))


@pytest.mark.parametrize("width,height,expected", [
    (None, None, (1920, 1080)),
    (1920, 1080, (1920, 1080)),
    (1080, 1920, (1080, 1920)),
])
def test_frame_sizes_default_and_explicit(tmp_path, width, height, expected):
    data = board()
    if width is None:
        data.pop("width"); data.pop("height")
    else:
        data.update(width=width, height=height)
    explainer.validate(data, scene_root(tmp_path))
    assert frames.normalize(data.get("width"), data.get("height")) == expected


@pytest.mark.parametrize("width,height,match", [
    (1920, None, "同时省略"),
    (None, 1080, "同时省略"),
    (True, 1080, "width"),
    (1920, "1080", "height"),
    (1080, 1080, "仅支持"),
    (1920, 1920, "仅支持"),
    (3840, 2160, "仅支持"),
])
def test_invalid_frame_sizes(tmp_path, width, height, match):
    data = board(); data["width"] = width; data["height"] = height
    with pytest.raises(M2VError, match=match):
        explainer.validate(data, scene_root(tmp_path))


@pytest.mark.parametrize("mutation,match", [
    (lambda b: b.update(visual={"theme": "dark"}), "未知字段"),
    (lambda b: b["scenes"][0].update(template="point"), "template 必须是 code"),
    (lambda b: b["scenes"][0].update(aspectRatio="any"), "未知字段"),
    (lambda b: b["scenes"][0].update(world={}), "未知字段"),
    (lambda b: b["scenes"][0]["content"].update(summary={"text": "旧展示元素"}), "未知字段"),
    (lambda b: b.update(targetSeconds=0), "targetSeconds"),
    (lambda b: b.update(targetSeconds=601), "targetSeconds"),
    (lambda b: b.update(fps=25), "fps"),
    (lambda b: b.update(input={"kind": "video"}), "input.kind"),
    (lambda b: b["scenes"][0].update(transitionFrames=0), "transitionFrames"),
    (lambda b: b["scenes"].append(copy.deepcopy(b["scenes"][0])), "重复 ID"),
    (lambda b: b["scenes"][0]["content"].update(entry="assets/demo.tsx"), "scenes/"),
])
def test_invalid_material(tmp_path, mutation, match):
    data = board(); mutation(data)
    with pytest.raises(M2VError, match=match): explainer.validate(data, scene_root(tmp_path))


def test_first_scene_must_cut(tmp_path):
    data = board(); data["scenes"][0]["transition"] = "fade"
    with pytest.raises(M2VError, match="首幕必须 cut"): explainer.validate(data, scene_root(tmp_path))


def test_code_scene_may_have_no_narration(tmp_path):
    data = board(); data["scenes"][0]["narrationSegments"] = []
    explainer.validate(data, scene_root(tmp_path))


def test_topic_input_requires_keywords_and_no_article(tmp_path):
    data = board(); data["input"] = {"kind": "topic", "topic": "缓冲机制"}
    with pytest.raises(M2VError, match="keywords"): explainer.validate(data, scene_root(tmp_path))
    for item in data["scenes"]:
        item["keywords"] = ["缓冲"]
    explainer.validate(data, scene_root(tmp_path))
    root, manifest = project(tmp_path, data)
    (root / "article.md").unlink()
    source = explainer.load(root, manifest)
    assert explainer.topic_input(source)
    # 主题输入不伪造原文语义审查：没有 article.md 也能准备。
    assert adapter.validate(root, manifest) is None


def test_topic_input_must_declare_topic_text(tmp_path):
    data = board(); data["input"] = {"kind": "topic"}
    for item in data["scenes"]:
        item["keywords"] = ["缓冲"]
    with pytest.raises(M2VError, match="input.topic"):
        explainer.validate(data, scene_root(tmp_path))


@pytest.mark.parametrize("seconds,samples,passes", [
    (599.6, .1, True), (599.6 + 1/60, .1, False),
])
def test_exact_six_hundred_second_limit(tmp_path, monkeypatch, seconds, samples, passes):
    root, manifest = project(tmp_path)
    fake_tts(monkeypatch, seconds, samples=samples)
    fake_record(monkeypatch)
    if passes:
        result = adapter.prepare(root, manifest)
        assert result["durationInFrames"] == 36000
    else:
        with pytest.raises(M2VError, match="超过 600 秒"): adapter.prepare(root, manifest)
        assert not (root / "outputs/prepared.json").exists()


def test_real_audio_axis_fade_and_cache(tmp_path, monkeypatch):
    data = board(); second = scene("b", transition="fade")
    data["scenes"].append(second)
    root, manifest = project(tmp_path, data)
    calls = fake_tts(monkeypatch)
    fake_record(monkeypatch)
    result = adapter.prepare(root, manifest, voice="zh-CN-YunxiNeural", rate="-6%")
    a, b = result["props"]["compiledScenes"]
    assert a["segmentWindows"]["a-line"] == {"startFrame": 0, "endFrame": 60}
    assert a["endFrame"] == 84 and b["startFrame"] == 68
    assert b["segmentWindows"]["b-line"] == {"startFrame": 84, "endFrame": 144}
    assert result["durationInFrames"] == 168
    assert result["props"]["subtitleCues"] == [
        {"startFrame": 0, "endFrame": 60, "text": data["scenes"][0]["narrationSegments"][0]["text"]},
        {"startFrame": 84, "endFrame": 144, "text": data["scenes"][1]["narrationSegments"][0]["text"]},
    ]
    assert result["subtitles"] == result["props"]["subtitleCues"]
    assert calls[0][1:3] == ("zh-CN-YunxiNeural", "-6%")
    import wave
    with wave.open(str(root / result["audio"]["segments"][0]["path"]), "rb") as wav:
        assert wav.getnframes() == 168 * 400
    next_result = adapter.prepare(root, manifest)
    assert next_result["audio"]["cacheHits"] == 2


def test_segment_holds_are_read_from_each_scene(tmp_path, monkeypatch):
    """每幕段间留白必须用本幕声明，不能沿用第一遍循环最后一幕的列表。"""
    first = scene("a", narrationSegments=[
        {"id": "a1", "text": "甲。", "holdFrames": 30}, {"id": "a2", "text": "乙。"}])
    second = scene("b", narrationSegments=[
        {"id": "b1", "text": "丙。", "holdFrames": 6}, {"id": "b2", "text": "丁。"}])
    root, manifest = project(tmp_path, board(scenes=[first, second]))
    fake_tts(monkeypatch)
    fake_record(monkeypatch)
    result = adapter.prepare(root, manifest)
    a, b = result["props"]["compiledScenes"]
    assert a["segmentWindows"]["a2"] == {"startFrame": 90, "endFrame": 150}
    assert b["segmentWindows"]["b2"] == {"startFrame": 240, "endFrame": 300}


def test_narration_overlap_is_rejected(tmp_path, monkeypatch):
    """旁白不得重叠：淡化帧数不小于前一幕时长时准备失败。"""
    data = board()
    data["scenes"].append(scene("b", transition="crossfade", transitionFrames=84))
    root, manifest = project(tmp_path, data); fake_tts(monkeypatch); fake_record(monkeypatch)
    with pytest.raises(M2VError, match="转场过长"):
        adapter.prepare(root, manifest)


def test_silent_scene_takes_target_remainder(tmp_path, monkeypatch):
    """无旁白镜头按固定帧数或目标剩余时长分配，不靠截断口播凑时长——也不要求关键词。"""
    data = board()
    data["scenes"].append(scene("shot", narrationSegments=[]))
    root, manifest = project(tmp_path, data); fake_tts(monkeypatch); fake_record(monkeypatch)
    result = adapter.prepare(root, manifest)
    shot = result["props"]["compiledScenes"][1]
    assert result["durationInFrames"] == 3600
    assert shot["durationInFrames"] == 3600 - 84
    assert shot["segmentWindows"] == {}


def test_prepare_binds_frame_subtitle_and_media(tmp_path, monkeypatch):
    """画幅、字幕几何与媒体映射都进准备产物与录制配置。"""
    data = board(width=1080, height=1920)
    root, manifest, result = prepared(tmp_path / "p", monkeypatch, data)
    assert (result["width"], result["height"]) == (1080, 1920)
    assert result["props"]["subtitle"] == frames.spec(1080, 1920)["subtitle"]
    assert result["props"]["width"] == 1080 and result["props"]["height"] == 1920
    assert "visual" not in result["props"]
    assert result["inputs"]["frame"] == "1080x1920"


def test_narration_audio_starts_after_lead_in_frames(tmp_path, monkeypatch):
    """前导留白必须写进音轨；否则整片旁白会比字幕和画面提前。"""
    import wave
    data = board()
    data["scenes"][0]["leadInFrames"] = 30
    root, manifest, result = prepared(tmp_path / "lead", monkeypatch, data)
    master = root / result["audio"]["segments"][0]["path"]
    with wave.open(str(master), "rb") as stream:
        rate = stream.getframerate()
        bytes_per_frame = stream.getsampwidth() * stream.getnchannels()
        raw = stream.readframes(stream.getnframes())
    first = next((index for index in range(0, len(raw), 2) if raw[index] or raw[index + 1]), None)
    expected_start = data["scenes"][0]["leadInFrames"] / result["fps"]
    assert first is not None and abs(first / bytes_per_frame / rate - expected_start) < 0.05


def test_record_receives_the_declared_frame(tmp_path, monkeypatch):
    data = board()
    root, manifest = project(tmp_path, data)
    fake_tts(monkeypatch)
    calls = fake_record(monkeypatch)
    prepared_record = adapter.prepare(root, manifest)
    assert calls == []
    prepare.code_scenes.materialize(root, prepared_record, 0, 30)
    assert calls[0]["frame"]["width"] == 1920
    assert calls[0]["frame"]["subtitle"]["safeArea"] == frames.spec(1920, 1080)["subtitle"]["safeArea"]
    assert calls[0]["media"] == {}


@pytest.mark.parametrize("reference", ["article.md", "outputs/input-review.json"])
def test_referenced_files_invalidate_preparation(tmp_path, monkeypatch, reference):
    root, manifest, _ = prepared(tmp_path, monkeypatch)
    (root / reference).write_text("变化", encoding="utf-8")
    with pytest.raises(M2VError, match="文件已变化"): load_current_prepared(root, manifest)


def test_unreviewed_input_blocks_prepare(tmp_path, monkeypatch):
    root, manifest = project(tmp_path)
    review.create_input(root, manifest)
    calls = fake_tts(monkeypatch)
    with pytest.raises(M2VError, match="未通过"): adapter.prepare(root, manifest)
    assert calls == []


def test_code_change_invalidates_preparation(tmp_path, monkeypatch):
    root, manifest, _ = prepared(tmp_path, monkeypatch)
    (root / ENTRY).write_text("export default () => null;\n", encoding="utf-8")
    with pytest.raises(M2VError, match="已变化"): load_current_prepared(root, manifest)


@pytest.mark.slow
@pytest.mark.parametrize("size", [(1920, 1080), (1080, 1920)], ids=["横屏", "竖屏"])
def test_browser_subtitle_layout_and_random_seek(tmp_path, monkeypatch, chromium_ready, size):
    """两种画幅各跑一遍：安全区、静音隐藏、可见性与随机访问确定性都要成立。"""
    from m2v.types.general.explainer_render import layout_check
    from m2v.engine.contract_page import serve_contract_page
    from playwright.sync_api import sync_playwright
    data = board(width=size[0], height=size[1])
    root, manifest = project(tmp_path, data)
    fake_tts(monkeypatch)
    # 这一条用真实录制：字幕要压在真实片段上，量测才有意义。
    prepared_record = adapter.prepare(root, manifest)
    assert layout_check(root, prepared_record)["status"] == "pass"
    props = root / "outputs/browser-props.json"
    from m2v.types.general.code_scenes import materialize
    prepared_record = materialize(root, prepared_record, 0, prepared_record["durationInFrames"])
    props.write_text(json.dumps(prepared_record["props"], ensure_ascii=False), encoding="utf-8")
    with serve_contract_page(props, root) as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": size[0], "height": size[1]})
            page.goto(url + "&m2v-explainer=1"); page.wait_for_function("window.__M2V__?.version === 6")
            page.evaluate("async () => await window.__M2V__.ready()")
            safe = frames.spec(*size)["subtitle"]["safeArea"]
            samples = {}
            for frame in [0, 16, 59, 60, 83, 30, 16, 0, 83]:
                page.evaluate("async f => await window.__M2V__.seekToFrame(f)", frame)
                assert page.evaluate("window.__M2V__.currentFrame()") == frame
                subtitle = page.locator('[data-m2v-subtitle]')
                assert subtitle.evaluate("el => [el.getBoundingClientRect().left, el.getBoundingClientRect().top]") == [safe["x"], safe["y"]]
                assert subtitle.evaluate("el => [el.getBoundingClientRect().width, el.getBoundingClientRect().height]") == [safe["width"], safe["height"]]
                # 无讲话的帧不显示字幕：静音区间隐藏，而不是留下一条空底板。
                assert subtitle.inner_text() == (data["scenes"][0]["narrationSegments"][0]["text"] if frame < 60 else "")
                text = subtitle.inner_text()
                if text:
                    assert page.evaluate("""() => {
                        const el = document.querySelector('[data-m2v-subtitle]');
                        const range = document.createRange();
                        range.selectNodeContents(el.querySelector('[data-m2v-copy]'));
                        return Array.from(range.getClientRects()).filter(r => r.width && r.height).every(r =>
                            el.contains(document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)));
                    }""")
                    # 字幕样式独立于作品配色：白字配不透明深色底板，任何背景上都可读。
                    assert page.evaluate("""() => {
                        const el = document.querySelector('[data-m2v-copy]');
                        const plate = getComputedStyle(el).backgroundColor;
                        return [getComputedStyle(el).color, plate.slice(0, 3) === 'rgb'];
                    }""") == ["rgb(255, 255, 255)", True]
                image = page.screenshot()
                if frame in samples: assert samples[frame] == image
                samples[frame] = image
        finally: browser.close()


@pytest.mark.slow
def test_browser_blocks_subtitle_overflow(tmp_path, monkeypatch, chromium_ready):
    """字幕换行宽度就是安全区宽度：文字放不下时量测必须失败。"""
    from m2v.types.general.explainer_render import layout_check
    root, manifest = project(tmp_path)
    fake_tts(monkeypatch, 1)
    prepared_record = adapter.prepare(root, manifest)
    prepared_record["props"]["subtitleCues"][0]["text"] = "很长的字幕" * 200
    with pytest.raises(M2VError, match="字幕量测失败"): layout_check(root, prepared_record)


@pytest.mark.slow
def test_browser_detects_covered_subtitle(tmp_path, monkeypatch, chromium_ready):
    from m2v.types.general import explainer_render
    root, manifest = project(tmp_path)
    fake_tts(monkeypatch, 1)
    prepared_record = adapter.prepare(root, manifest)
    # 重现缺失层级：字幕仍在，但被一层不透明覆盖物压在下面。
    monkeypatch.setattr(explainer_render, "MEASURE_BODY", explainer_render.MEASURE_BODY.replace(
        "const problems = [];",
        "const problems = []; const cover = document.createElement('div');"
        " cover.style.cssText = 'position:absolute;inset:0;z-index:9;background:#000';"
        " document.querySelector('[data-m2v-subtitle]').parentElement.appendChild(cover);"))
    with pytest.raises(M2VError, match="字幕被遮挡"):
        explainer_render.layout_check(root, prepared_record)
