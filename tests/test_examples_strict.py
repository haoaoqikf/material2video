"""仓库只分发固定的三个示例，且每份分镜、每个设计稿都必须符合 v8 契约。"""
from __future__ import annotations

import json
import re
import subprocess
import shutil
import sys
from pathlib import Path

import pytest

from m2v.types.general import explainer

from example_catalog import COVERED_COMPONENTS, EXAMPLES, EXPECTED_EXAMPLES, EXPECTED_FRAMES, STORYBOARDS

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def _restore_compound_media():
    """示例媒体不入库；校验前按配方恢复，保证新 checkout 也能过 v8 校验。"""
    script = EXAMPLES / 'compound-interest' / 'assets' / 'fetch.py'
    if script.is_file():
        subprocess.run([sys.executable, str(script)], cwd=script.parent, check=True)


def _declared_version(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8")).get("version")


def _sources(name: str) -> str:
    return "\n".join(file.read_text(encoding="utf-8") for file in sorted((EXAMPLES / name / "scenes").glob("*.tsx")))


def test_examples_are_fixed_and_capped() -> None:
    discovered = {path.name for path in EXAMPLES.iterdir() if path.is_dir()}
    assert len(discovered) <= 3, f"示例目录超过上限：{sorted(discovered)}"
    assert discovered == EXPECTED_EXAMPLES, (
        f"示例目录必须固定为 {sorted(EXPECTED_EXAMPLES)}，实际为 {sorted(discovered)}"
    )
    assert {path.parent.name for path in STORYBOARDS} == EXPECTED_EXAMPLES


@pytest.mark.parametrize("path", STORYBOARDS, ids=lambda item: item.parent.name)
def test_every_shipped_example_declares_v8(path: Path) -> None:
    assert _declared_version(path) == 8, f"{path.parent.name} 未声明 v8"


@pytest.mark.parametrize("path", STORYBOARDS, ids=lambda item: item.parent.name)
def test_shipped_example_matches_the_v8_contract(path: Path) -> None:
    explainer.validate(json.loads(path.read_text(encoding="utf-8")), path.parent)


@pytest.mark.parametrize("path", STORYBOARDS, ids=lambda item: item.parent.name)
def test_shipped_example_uses_the_declared_frame(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert (data["width"], data["height"]) == EXPECTED_FRAMES[path.parent.name]
    expected_fps = 30 if path.parent.name == "compound-interest" else 60
    assert data["fps"] == expected_fps


@pytest.mark.parametrize("path", STORYBOARDS, ids=lambda item: item.parent.name)
def test_core_demonstrations_follow_their_declared_storytelling_mode(path: Path) -> None:
    """示例应按各自契约使用旁白，或明确采用无声技术短片。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    name = path.parent.name
    if name == "compound-interest":
        # 30秒复利：固定帧预算，无旁白；8秒进入的环境床 + 事件音。
        assert data["input"]["kind"] == "topic" and data["input"]["topic"].strip()
        assert len(data["scenes"]) == 1
        scene = data["scenes"][0]
        assert scene["template"] == "code"
        assert data["targetSeconds"] == 30
        assert data["soundtrack"]["music"]["sourceRef"].endswith("bed.wav")
        assert len(data["soundtrack"]["effects"]) == 28
        assert scene["durationFrames"] == 900
        assert not scene["narrationSegments"]
        assert scene["content"]["entry"] == "scenes/compound.tsx"
        source = (path.parent / scene["content"]["entry"]).read_text(encoding="utf-8")
        assert "useSceneContext" in source and "elapsedSeconds" in source
        assert not (path.parent / "article.md").exists()
        return
    if name == "american-science-milestones":
        assert data["input"]["kind"] == "topic"
        assert not data.get("soundtrack")
        assert sum(scene["durationFrames"] for scene in data["scenes"]) == 30 * 60
        assert len(data["scenes"]) == 12
        assert [scene["durationFrames"] for scene in data["scenes"]] == [
            120, 120, 120, 180, 120, 150, 150, 180, 150, 120, 270, 120
        ]
        for scene in data["scenes"]:
            assert not scene["narrationSegments"]
            assert scene["durationFrames"] >= 120
            chapter = scene["content"]["props"]["chapter"]
            assert chapter["id"] == scene["id"]
            if scene["id"] != "closing":
                assert chapter["title"]
            assert chapter["caption"]
        return
    article = (path.parent / "article.md")
    sources = _sources(path.parent.name)
    assert "segmentWindows" in sources, "画面没有使用旁白时间窗"
    if data["input"]["kind"] == "topic":
        # 主题输入没有原文可对照；画面与图表必须明确标注示意，并仍按旁白推进。
        assert data["input"]["topic"].strip()
        assert not article.exists(), f"{path.parent.name} 采用主题输入，不应再放一份原文"
        assert "示意" in sources
    else:
        article_text = article.read_text(encoding="utf-8")
        assert "示意" in sources, "示意数据没有标注"
    for scene in data["scenes"]:
        assert scene["template"] == "code"
        assert scene["narrationSegments"], f"{scene['id']} 没有旁白"
        if path.parent.name == "solar-system-journey":
            # 导览需要独立的视觉预算；TTS 仍须实际量测，超预算由 prepare 拒绝。
            assert scene["durationFrames"] > scene["leadInFrames"] + scene["tailFrames"]
            assert scene["tailFrames"] >= 45
        else:
            assert "durationFrames" not in scene, "讲解示例由实际旁白决定幕长"
        source = (path.parent / scene["content"]["entry"]).read_text(encoding="utf-8")
        assert "useNarration" in source, f"{scene['id']} 没有按旁白推进"
        for segment in scene["narrationSegments"]:
            if data["input"]["kind"] == "article":
                assert segment["text"] in article_text, f"{scene['id']} 的旁白不在原文里"


def test_examples_cover_actual_component_families() -> None:
    """覆盖检查反映三支示例实际使用的组件；不为了覆盖清单引入无关效果。"""
    sources = "\n".join(_sources(name) for name in EXPECTED_EXAMPLES)
    for family, markers in COVERED_COMPONENTS.items():
        assert any(marker in sources for marker in markers), f"缺少组件演示：{family}"
    assert "gsap" not in sources, "GSAP 随拥堵波示例退役；覆盖说明不应再声称演示它"


@pytest.mark.parametrize("name", sorted(EXPECTED_EXAMPLES))
def test_video_copy_does_not_expose_internal_references(name: str) -> None:
    """观众文案不得要求查阅仓库材料或暴露内部文件路径。"""
    example = EXAMPLES / name
    sources = _sources(name)
    storyboard = json.dumps(json.loads((example / "storyboard.json").read_text(encoding="utf-8")),
                            ensure_ascii=False)
    visible_copy_sources = sources + "\n" + storyboard
    internal_paths = re.compile(
        r"(?i)\b(?:examples|outputs|openspec)/|\.agents/|"
        r"(?:详见|查看|参见)\s*(?:内部)?(?:来源|制作|项目)?(?:文档|文件|资料)"
    )
    match = re.search(r"\bSOURCES(?:\.md)?\b", visible_copy_sources) or internal_paths.search(visible_copy_sources)
    assert match is None, f"{name} 的分镜或场景源码出现内部资料引用：{match.group(0) if match else ''}"


@pytest.mark.parametrize("path", STORYBOARDS, ids=lambda item: item.parent.name)
def test_screen_titles_do_not_repeat_narration(path: Path) -> None:
    """画面标题只是元数据：不得等同于旁白，也不得代替旁白。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    for scene in data["scenes"]:
        title = scene["content"].get("title")
        if title:
            narration = "".join(part["text"] for part in scene.get("narrationSegments", []))
            assert title != narration, f"{path.parent.name}/{scene['id']} 的画面标题照抄了旁白"


def test_static_direct_examples_keep_existing_storyboard_contract() -> None:
    """导演意图留在 DESIGN.md，已分发的 v8 分镜不因此新增字段。"""
    for slug in sorted(EXPECTED_EXAMPLES):
        data = json.loads((EXAMPLES / slug / "storyboard.json").read_text(encoding="utf-8"))
        assert data["version"] == 8
        assert data["schemaVersion"] == 8
        assert "director" not in data
        for scene in data["scenes"]:
            assert "director" not in scene
            assert "direction" not in scene


@pytest.mark.parametrize("name", sorted(EXPECTED_EXAMPLES))
def test_example_media_is_content_addressed_and_recorded(name: str) -> None:
    """示例引用的素材必须已导入并留证，且通过代码里的素材 ID 取用。"""
    design = _sources(name)
    referenced = [entry["id"] for entry in
                  json.loads((EXAMPLES / name / "assets/media-sources.json").read_text(encoding="utf-8"))["assets"]] \
        if (EXAMPLES / name / "assets/media-sources.json").is_file() else []
    for identity in referenced:
        assert f"useMediaAsset('{identity}')" in design or f'useMediaAsset("{identity}")' in design, \
            f"{name} 没有通过素材 ID 使用 {identity}"
    for storyboard in [json.loads((EXAMPLES / name / "storyboard.json").read_text(encoding="utf-8"))]:
        # 素材不再写进分镜：v8 的场景内容只有 title/entry/props。
        for scene in storyboard["scenes"]:
            assert "src" not in scene["content"]


@pytest.mark.parametrize("name", sorted(EXPECTED_EXAMPLES))
def test_shipped_example_actual_duration(name: str) -> None:
    """实际时长以真实配音准备结果为准；没有准备产物时跳过，不伪造结论。"""
    prepared = EXAMPLES / name / "outputs/prepared.json"
    if not prepared.is_file():
        pytest.skip("本地没有准备产物；准备后本用例会核对实际时长")
    data = json.loads(prepared.read_text(encoding="utf-8"))
    seconds = data["durationInFrames"] / data["fps"]
    assert (data["width"], data["height"]) == EXPECTED_FRAMES[name]
    if name == "american-science-milestones":
        assert seconds == 30
        assert not data["subtitles"]
        return
    if name == "compound-interest":
        assert seconds == 30, "复利固定为30秒、900帧"
        assert not data["subtitles"], "无旁白示例不应生成字幕"
        return
    assert 120 <= seconds <= 600, f"{name} 实际 {seconds:.1f} 秒，超出 120～600 秒"
    assert data["subtitles"], f"{name} 没有烧录字幕的来源字幕"


@pytest.mark.parametrize("name", sorted(EXPECTED_EXAMPLES))
def test_example_video_assets_cover_their_scene(name: str) -> None:
    """导入的视频片段不得短于使用它的幕，否则镜头末段会停在片尾。"""
    board = json.loads((EXAMPLES / name / "storyboard.json").read_text(encoding="utf-8"))
    sources = EXAMPLES / name / "assets/media-sources.json"
    media = {item["id"]: item for item in
             json.loads(sources.read_text(encoding="utf-8"))["assets"]} if sources.is_file() else {}
    for scene in board["scenes"]:
        asset = (scene.get("content", {}).get("props", {}).get("chapter") or {}).get("asset")
        if asset and media.get(asset, {}).get("kind") == "video":
            seconds = scene["durationFrames"] / board["fps"]
            assert media[asset]["durationSeconds"] >= seconds - 0.05, (
                f"{name}/{scene['id']} 需要 {seconds:.2f} 秒，{asset} 只有 "
                f"{media[asset]['durationSeconds']:.2f} 秒")


def test_no_generated_or_example_media_is_tracked() -> None:
    """成片、配音、预演与代码片段缓存都是派生产物；示例媒体按配方恢复，都不进版本控制。"""
    if shutil.which("git") is None:
        pytest.skip("环境里没有 git")
    listed = subprocess.run(["git", "ls-files", "examples", "web/src/assets/fonts"], cwd=ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", check=True).stdout.splitlines()
    generated = [name for name in listed
                 if "/outputs/" in name
                 or (name.endswith((".mp4", ".mov", ".webm", ".mp3")) and "/assets/media/" not in name)]
    restored = [name for name in listed if "/assets/media/" in name]
    assert generated == [], f"示例里有生成媒体被跟踪：{generated}"
    assert restored == [], f"示例媒体应按 assets/fetch.py 恢复而非入库：{restored}"
    assert any(name.startswith("web/src/assets/fonts/") for name in listed), "公共字体必须保留在版本控制中"
