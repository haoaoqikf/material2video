from __future__ import annotations
import copy
import hashlib
import json
import shutil
import wave
from pathlib import Path
import pytest
from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_project, load_current_prepared
from m2v.types.general import adapter, explainer, explainer_prepare as prepare, explainer_review as review

ROOT = Path(__file__).resolve().parents[1]


def board():
    return {"version": 7, "schemaVersion": 7, "fps": 30, "width": 1080, "height": 1920,
        "title": "测试", "input": {"kind": "article"}, "targetSeconds": 60,
        "scenes": [{"id": "a", "template": "point",
        "content": {"title": "观点", "summary": {"text": "观察反馈", "segmentId": "a-line", "keywords": ["反馈"]}},
        "keywords": ["反馈"],
        "narrationSegments": [{"id": "a-line", "text": "观察结果，修正做法。"}]}]}


def project(tmp_path, data=None):
    root = tmp_path / "video"
    create_project(root, "general", {"storyboard": "storyboard.json"})
    manifest_path = root / "project.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["tts"] = {"voice": "zh-CN-YunxiNeural"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (root / "storyboard.json").write_text(json.dumps(data or board(), ensure_ascii=False), encoding="utf-8")
    (root / "article.md").write_text("# 标题\n观察结果，根据反馈修正做法。", encoding="utf-8")
    root, manifest = load_project(root)
    record = review.template(root, manifest)
    record.update(status="pass", claim="反馈帮助改进", rationale="原文有清晰观点和操作方法", reviewer="测试夹具")
    (root / "outputs").mkdir()
    (root / "outputs/input-review.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return root, manifest


def fake_tts(monkeypatch, seconds=1, samples=None):
    """假合成：可声明与落盘长度不同的时长，用于快速验证帧账本。"""
    calls = []
    def speak(text, voice, rate, cache, **kwargs):
        calls.append((text, voice, rate, kwargs))
        wav = cache / "fixture.wav"
        hit = wav.exists()
        with wave.open(str(wav), "wb") as stream:
            stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            stream.writeframes(b"\x01\0" * round((seconds if samples is None else samples) * 24000))
        return wav, [{"start": 0, "end": seconds, "text": text}], [], seconds, hit
    monkeypatch.setattr(prepare.tts, "scene_audio", speak)
    return calls


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5, 6])
def test_old_storyboards_rejected(tmp_path, version):
    data = board(); data.update(version=version, schemaVersion=version)
    with pytest.raises(M2VError, match="重新编排"):
        explainer.validate(data, tmp_path)


def test_version_and_schema_version_must_agree(tmp_path):
    data = board(); data["schemaVersion"] = 5
    with pytest.raises(M2VError, match="只接受 v7"):
        explainer.validate(data, tmp_path)


@pytest.mark.parametrize("mutation,match", [
    (lambda b: b["scenes"][0]["content"]["summary"].update(segmentId="unknown"), "segmentId"),
    (lambda b: b["scenes"][0]["content"]["summary"].update(keywords=["没有的词"]), "keywords"),
    (lambda b: b["scenes"].append(copy.deepcopy(b["scenes"][0])), "重复 ID"),
    (lambda b: b["scenes"][0].update(world={}), "未知字段"),
    (lambda b: b.update(targetSeconds=0), "targetSeconds"),
    (lambda b: b.update(targetSeconds=601), "targetSeconds"),
    (lambda b: b.update(input={"kind": "video"}), "input.kind"),
    (lambda b: b["scenes"][0].update(transitionFrames=0), "transitionFrames"),
])
def test_invalid_material(tmp_path, mutation, match):
    data = board(); mutation(data)
    with pytest.raises(M2VError, match=match): explainer.validate(data, tmp_path)


def test_card_template_requires_narration(tmp_path):
    data = board(); data["scenes"][0]["narrationSegments"] = []
    with pytest.raises(M2VError, match="只有图片、视频或代码幕允许无旁白"):
        explainer.validate(data, tmp_path)


def test_topic_input_requires_keywords_and_no_article(tmp_path):
    data = board(); data["input"] = {"kind": "topic", "topic": "缓冲机制"}
    for scene in data["scenes"]:
        scene.pop("keywords")
    with pytest.raises(M2VError, match="keywords"): explainer.validate(data, tmp_path)
    for scene in data["scenes"]:
        scene["keywords"] = ["缓冲"]
    explainer.validate(data, tmp_path)
    root, manifest = project(tmp_path, data)
    (root / "article.md").unlink()
    source = explainer.load(root, manifest)
    assert explainer.topic_input(source)
    # 主题输入不伪造原文语义审查：没有 article.md 也能准备。
    assert adapter.validate(root, manifest) is None


def test_topic_input_must_declare_topic_text(tmp_path):
    data = board(); data["input"] = {"kind": "topic"}
    for scene in data["scenes"]:
        scene["keywords"] = ["缓冲"]
    with pytest.raises(M2VError, match="input.topic"):
        explainer.validate(data, tmp_path)


def test_graph_rejects_cycles_and_computes_layers(tmp_path):
    data = json.loads((ROOT / "examples/buffer-smoothing/storyboard.json").read_text(encoding="utf-8"))
    scene = next(item for item in data["scenes"] if item["template"] == "cause")
    # 只验证图，不让示例中的代码入口和音床依赖临时目录中的文件。
    data["scenes"] = [scene]
    data.pop("soundtrack", None)
    nodes = scene["content"]["nodes"]
    assert explainer.graph_levels(scene["content"]) == {node["id"]: i for i, node in enumerate(nodes)}
    scene["content"]["links"].append({"from": nodes[-1]["id"], "to": nodes[0]["id"], "text": "循环", "segmentId": "buffer-cause-1"})
    with pytest.raises(M2VError, match="循环"): explainer.validate(data, tmp_path)


def test_missing_image_and_path_escape(tmp_path):
    data = board(); data["scenes"][0].update(template="image", content={"title": "图片", "src": "missing.png",
        "caption": {"text": "说明", "segmentId": "a-line"}})
    with pytest.raises(M2VError, match="本地文件"): explainer.validate(data, tmp_path)


def test_media_scene_without_caption_or_narration():
    """图片与视频幕允许无旁白、无配文，只保留标题。"""
    assert explainer.elements({"template": "video", "content": {"title": "空镜"}}) == []
    assert explainer.elements({"template": "image", "content": {"title": "空镜"}}) == []


@pytest.mark.parametrize("seconds,samples,passes", [
    (599.6, .1, True), (599.6 + 1/30, .1, False),
])
def test_exact_six_hundred_second_limit(tmp_path, monkeypatch, seconds, samples, passes):
    root, manifest = project(tmp_path)
    fake_tts(monkeypatch, seconds, samples=samples)
    if passes:
        result = adapter.prepare(root, manifest)
        assert result["durationInFrames"] == 18000
    else:
        with pytest.raises(M2VError, match="超过 600 秒"): adapter.prepare(root, manifest)
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
    assert a["endFrame"] == 42 and b["startFrame"] == 34
    assert b["segmentWindows"]["b-line"] == {"startFrame": 42, "endFrame": 72}
    assert result["durationInFrames"] == 84
    assert result["props"]["subtitleCues"] == [
        {"startFrame": 0, "endFrame": 30, "text": data["scenes"][0]["narrationSegments"][0]["text"]},
        {"startFrame": 42, "endFrame": 72, "text": data["scenes"][1]["narrationSegments"][0]["text"]},
    ]
    assert result["subtitles"] == result["props"]["subtitleCues"]
    assert calls[0][1:3] == ("zh-CN-YunxiNeural", "-6%")
    with wave.open(str(root / result["audio"]["segments"][0]["path"]), "rb") as wav:
        assert wav.getnframes() == 84 * 800
    next_result = adapter.prepare(root, manifest)
    assert next_result["audio"]["cacheHits"] == 2


def test_narration_overlap_is_rejected(tmp_path, monkeypatch):
    """旁白不得重叠：淡化帧数不小于前一幕时长时准备失败。"""
    data = board(); second = copy.deepcopy(data["scenes"][0])
    second.update(id="b", transition="crossfade", transitionFrames=42)
    second["narrationSegments"][0]["id"] = "b-line"; second["content"]["summary"]["segmentId"] = "b-line"
    data["scenes"].append(second)
    root, manifest = project(tmp_path, data); fake_tts(monkeypatch)
    with pytest.raises(M2VError, match="转场过长"):
        adapter.prepare(root, manifest)


def test_silent_media_scene_takes_target_remainder(tmp_path, monkeypatch):
    """无旁白镜头按固定帧数或目标剩余时长分配，不靠截断口播凑时长。"""
    data = board()
    data["scenes"].append({"id": "shot", "template": "image", "narrationSegments": [],
                           "content": {"title": "空镜", "src": "assets/media/x.png"}})
    root, manifest = project(tmp_path, data); fake_tts(monkeypatch)
    (root / "assets/media").mkdir(parents=True)
    (root / "assets/media/x.png").write_bytes(b"fixture")
    # 素材实测契约由 media 测试覆盖，这里只验证无旁白幕的帧分配。
    monkeypatch.setattr("m2v.types.general.media_assets.validate_scene",
                        lambda root, scene: {"width": 1080, "height": 1920, "durationSeconds": None})
    result = adapter.prepare(root, manifest)
    shot = result["props"]["compiledScenes"][1]
    assert result["durationInFrames"] == 1800
    assert shot["durationInFrames"] == 1800 - 42
    assert shot["segmentWindows"] == {}


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


def test_media_change_invalidates_general_prepared(tmp_path, monkeypatch):
    source = ROOT / "examples/darts-trial-and-error"
    data = json.loads((source / "storyboard.json").read_text(encoding="utf-8"))
    root, manifest = project(tmp_path, data)
    shutil.copytree(source / "assets", root / "assets")
    shutil.copytree(source / "scenes", root / "scenes")
    fake_tts(monkeypatch)
    adapter.prepare(root, manifest)
    next((root / "assets/media").glob("*.png")).write_bytes(b"changed")
    with pytest.raises(M2VError, match="文件已变化"):
        load_current_prepared(root, manifest)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_browser_layout_and_random_seek(tmp_path, monkeypatch, chromium_ready, theme):
    from m2v.types.general.explainer_render import layout_check
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
            page.goto(url + "&m2v-explainer=1"); page.wait_for_function("window.__M2V__?.version === 6")
            page.evaluate("async () => await window.__M2V__.ready()")
            samples = {}
            for frame in [0,8,29,30,41,15,8,0,41]:
                page.evaluate("async f => await window.__M2V__.seekToFrame(f)", frame)
                assert page.evaluate("window.__M2V__.currentFrame()") == frame
                subtitle = page.locator('[data-m2v-subtitle]')
                assert subtitle.inner_text() == (data["scenes"][0]["narrationSegments"][0]["text"] if frame < 30 else "")
                if frame < 30:
                    assert subtitle.evaluate("""el => {
                        const range = document.createRange(); range.selectNodeContents(el);
                        return Array.from(range.getClientRects()).filter(r => r.width && r.height).every(r =>
                            el.contains(document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)));
                    }""")
                    # 实际量测已检查正文安全区；此处补充主题前景与背景对比度。
                    assert page.evaluate("""() => {
                        const el = document.querySelector('[data-m2v-subtitle]');
                        const rgb = value => value.match(/[\\d.]+/g).slice(0, 3).map(Number);
                        const luminance = color => rgb(color).map(v => {
                            v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
                        }).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
                        let bg = el.parentElement;
                        while (getComputedStyle(bg).backgroundColor === 'rgba(0, 0, 0, 0)') bg = bg.parentElement;
                        const a = luminance(getComputedStyle(el).color);
                        const b = luminance(getComputedStyle(bg).backgroundColor);
                        return (Math.max(a,b) + .05) / (Math.min(a,b) + .05) >= 4.5;
                    }""")
                image = page.screenshot()
                if frame in samples: assert samples[frame] == image
                samples[frame] = image
        finally: browser.close()


def test_browser_velvet_theme_reaches_the_frame(tmp_path, monkeypatch, chromium_ready):
    """新增主题要有真实验收：颜色、排版与动效都得落到画面上，而不只是写在清单里。

    这里不比对同一帧两次截图的字节相等，那一条由 dark/light 守着。velvet 的入场有
    36 帧，非单调 seek 下 Chrome 对亚像素偏移的合成层会复用不同的光栅缓存，
    面板圆角处会出现 1 像素、约 1 个色阶的差异——是光栅缓存而不是画面状态，
    因此改用可观察的计算样式与入场进度来判定。
    """
    from m2v.types.general.explainer_render import layout_check
    from m2v.engine.contract_page import serve_contract_page
    from playwright.sync_api import sync_playwright
    data = board(); data["visual"] = {"theme": "velvet"}
    root, manifest = project(tmp_path, data); fake_tts(monkeypatch)
    prepared = adapter.prepare(root, manifest)
    assert layout_check(root, prepared)["status"] == "pass"
    props = root / "outputs/browser-props.json"
    props.write_text(json.dumps(prepared["props"], ensure_ascii=False), encoding="utf-8")
    with serve_contract_page(props, root) as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width":1080, "height":1920})
            page.goto(url + "&m2v-explainer=1"); page.wait_for_function("window.__M2V__?.version === 6")
            page.evaluate("async () => await window.__M2V__.ready()")
            page.evaluate("async f => await window.__M2V__.seekToFrame(f)", 0)
            # 颜色来自主题色板
            assert page.evaluate("getComputedStyle(document.querySelector('[data-m2v-scene]')).backgroundColor") == "rgb(10, 10, 10)"
            # 字阶与字距来自主题：标题 120px（与正文 40px 构成 3:1），字距 0.15em = 18px
            assert page.evaluate("""() => {const s = getComputedStyle(document.querySelector('[data-m2v-scene] [data-m2v-box]'));
                return [s.fontWeight, s.fontSize, s.letterSpacing];}""") == ["300", "120px", "18px"]
            # 取形来自主题：面板近直角（组件现值是 24px）
            assert page.evaluate("""() => getComputedStyle(
                document.querySelectorAll('[data-m2v-scene] [data-m2v-box]')[1]).borderTopLeftRadius""") == "2px"
            # 构图来自主题：居中
            assert page.evaluate("getComputedStyle(document.querySelector('[data-m2v-scene]')).textAlign") == "center"
            # 入场时长与缓动都来自主题：36 帧的 easeInOutSine。
            # 第 9 帧是进场 1/4 处，缓动给约 0.147；线性会给 0.25，两者可区分。
            for frame, expected in ((9, 0.147), (18, 0.5), (36, 1)):
                page.evaluate("async f => await window.__M2V__.seekToFrame(f)", frame)
                opacity = float(page.evaluate("getComputedStyle(document.querySelector('[data-m2v-reveal]')).opacity"))
                assert abs(opacity - expected) < 0.02, f"第 {frame} 帧入场进度 {opacity}，期望 {expected}"
        finally:
            browser.close()


def test_browser_blocks_overflow(tmp_path, monkeypatch, chromium_ready):
    from m2v.types.general.explainer_render import layout_check
    data = board(); data["scenes"][0]["content"]["summary"]["text"] = "很长的摘要" * 150
    data["scenes"][0]["content"]["summary"]["keywords"] = []
    root,manifest = project(tmp_path,data);fake_tts(monkeypatch)
    prepared=adapter.prepare(root,manifest)
    with pytest.raises(M2VError,match="排版量测失败"): layout_check(root,prepared)


def test_browser_detects_covered_subtitle(tmp_path, monkeypatch, chromium_ready):
    from m2v.types.general import explainer_render
    root, manifest = project(tmp_path); fake_tts(monkeypatch)
    prepared = adapter.prepare(root, manifest)
    # 重现缺失层级：文字与包围盒仍存在，但场景背景盖在字幕之上。
    monkeypatch.setattr(explainer_render, "MEASURE_BODY", explainer_render.MEASURE_BODY.replace(
        "const problems = [];", "const problems = []; document.querySelector('[data-m2v-subtitle]').style.zIndex = 'auto';"))
    with pytest.raises(M2VError, match="字幕被遮挡"):
        explainer_render.layout_check(root, prepared)
