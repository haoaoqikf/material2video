"""仓库只分发固定的三个示例，且每份分镜、每个设计稿都必须符合 v8 契约。"""
from __future__ import annotations

import json
import subprocess
import shutil
from pathlib import Path

import pytest

from m2v.types.general import explainer

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
STORYBOARDS = sorted(EXAMPLES.glob("*/storyboard.json"))
EXPECTED_EXAMPLES = {"buffer-smoothing", "darts-trial-and-error", "solar-system-journey"}
#: 两横一竖：画幅是作品设计的一部分，示例必须覆盖两种。
EXPECTED_FRAMES = {"buffer-smoothing": (1920, 1080), "solar-system-journey": (1920, 1080),
                   "darts-trial-and-error": (1080, 1920)}
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
def test_core_demonstrations_explain_the_article_with_narration(path: Path) -> None:
    """每一幕都由真实旁白驱动，不能退化成固定时长的无声技术幕。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    article = (path.parent / "article.md").read_text(encoding="utf-8")
    sources = _sources(path.parent.name)
    assert "segmentWindows" in sources, "画面没有使用旁白时间窗"
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
            assert segment["text"] in article, f"{scene['id']} 的旁白不在原文里"
    assert "示意" in sources, "示意数据没有标注"


def test_examples_cover_approved_component_families() -> None:
    sources = "\n".join(_sources(name) for name in EXPECTED_EXAMPLES)
    for family, markers in APPROVED_COMPONENTS.items():
        assert any(marker in sources for marker in markers), f"缺少组件演示：{family}"


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
    minimum, maximum = (120, 150) if name == "solar-system-journey" else (120, 180)
    assert minimum <= seconds <= maximum, f"{name} 实际 {seconds:.1f} 秒，超出 {minimum}～{maximum} 秒"
    assert (data["width"], data["height"]) == EXPECTED_FRAMES[name]
    assert data["subtitles"], f"{name} 没有烧录字幕的来源字幕"


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
