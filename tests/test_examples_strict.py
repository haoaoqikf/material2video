"""仓库只分发固定的三个示例，且每份分镜、每个设计稿都必须符合 v8 契约。"""
from __future__ import annotations

import json
import re
import subprocess
import shutil
from pathlib import Path

import pytest

from m2v.types.general import explainer

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
STORYBOARDS = sorted(EXAMPLES.glob("*/storyboard.json"))
EXPECTED_EXAMPLES = {"american-science-milestones", "traffic-jam-wave", "solar-system-journey"}
#: 两横一竖：画幅是作品设计的一部分，示例必须覆盖两种。
EXPECTED_FRAMES = {"american-science-milestones": (1920, 1080), "solar-system-journey": (1920, 1080),
                   "traffic-jam-wave": (1080, 1920)}
APPROVED_COMPONENTS = {
    "Motion": ("motion", "motion/react"),
    "ECharts": ("Chart", "echarts"),
    "GSAP": ("gsap",),
    "Three.js": ("THREE", "three"),
    "React Three Fiber": ("Canvas", "@react-three/fiber"),
    "Drei": ("Float", "Stars", "PerspectiveCamera", "@react-three/drei"),
}


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
    assert data["fps"] == 60


@pytest.mark.parametrize("path", STORYBOARDS, ids=lambda item: item.parent.name)
def test_core_demonstrations_follow_their_declared_storytelling_mode(path: Path) -> None:
    """示例应按各自契约使用旁白，或明确采用无声技术短片。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    if path.parent.name == "american-science-milestones":
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
        if path.parent.name == "traffic-jam-wave":
            # 重制后的生活困惑结构与主线/补充分工。
            assert [scene["id"] for scene in data["scenes"]] == [
                "empty", "rewind", "brake", "relay", "density", "return"
            ]
            assert not data.get("soundtrack", {}).get("music")
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


def test_examples_cover_approved_component_families() -> None:
    sources = "\n".join(_sources(name) for name in EXPECTED_EXAMPLES)
    for family, markers in APPROVED_COMPONENTS.items():
        assert any(marker in sources for marker in markers), f"缺少组件演示：{family}"


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


@pytest.mark.parametrize("name", sorted(EXPECTED_EXAMPLES))
def test_examples_document_their_visual_design(name: str) -> None:
    """示例说明必须记录论点、旁白、画面与组件对应关系和视觉设计依据。"""
    design = (EXAMPLES / name / "DESIGN.md").read_text(encoding="utf-8")
    for section in ("画幅", "配色", "构图", "声音"):
        assert section in design, f"{name}/DESIGN.md 缺少「{section}」"
    readme = (EXAMPLES / name / "README.md").read_text(encoding="utf-8")
    storyboard = json.loads((EXAMPLES / name / "storyboard.json").read_text(encoding="utf-8"))
    for scene in storyboard["scenes"]:
        assert scene["id"] in readme, f"{name}/README.md 没有记录 {scene['id']}"
        for segment in scene["narrationSegments"]:
            assert segment["id"] in readme, f"{name}/README.md 没有记录 {segment['id']}"


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
    ranges = {"solar-system-journey": (120, 600), "traffic-jam-wave": (1, 600)}
    minimum, maximum = ranges.get(name, (120, 180))
    assert minimum <= seconds <= maximum, f"{name} 实际 {seconds:.1f} 秒，超出 {minimum}～{maximum} 秒"
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


def test_no_generated_media_is_tracked() -> None:
    """成片、配音、预演与代码片段缓存都是派生产物，不得进版本控制。"""
    if shutil.which("git") is None:
        pytest.skip("环境里没有 git")
    listed = subprocess.run(["git", "ls-files", "examples"], cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=True).stdout.splitlines()
    # `assets/media/` 下的导入素材是内容寻址且已记录来源与许可的固定输入，按约定入库；
    # 其余视频与 `outputs/` 下的任何东西都是派生产物。
    generated = [name for name in listed
                 if "/outputs/" in name
                 or (name.endswith((".mp4", ".mov", ".webm", ".mp3")) and "/assets/media/" not in name)]
    assert generated == [], f"示例里有生成媒体被跟踪：{generated}"
