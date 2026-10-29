"""正式 B 寓言风格包与 `styles/examples/` 示例：清单、组件契约、示例可校验。"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from m2v.cli import main
from m2v.core import styles
from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_project
from m2v.types.general import explainer
from m2v.types.general.code_scenes import build_scene

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "styles" / "vibe-fable"
EXAMPLES = ROOT / "styles" / "examples"
COMPONENTS = {
    "kit", "fable-stage", "parallax-band", "instinct-gauge", "scene-note",
    "top-line", "counter-row", "callout", "rule-card", "title-fable", "screen-subtitle",
}


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_registry_lists_both_packages(capsys):
    assert main(["styles", "--json"]) == 0
    listed = {item["id"]: item for item in json.loads(capsys.readouterr().out)}
    assert set(listed) == {"vibe-fable", "vibe-night"}
    assert listed["vibe-fable"]["types"] == ["general"]
    assert listed["vibe-fable"]["frames"] == [{"width": 1920, "height": 1080}]


def test_reserved_examples_directory_is_not_a_package(tmp_path, monkeypatch):
    """`styles/examples/` 存放示例，不参与发现；即使里面放了合法清单也必须拒绝加载。"""
    assert "examples" in styles.RESERVED_DIRECTORIES
    assert EXAMPLES.is_dir()
    assert "examples" not in {entry["id"] for entry in styles.list_styles()}
    # 只靠「目录里恰好没有 style.json」通过是虚假覆盖：放一份合法清单进去仍须失败。
    base = tmp_path / "styles"
    reserved = base / "examples"
    reserved.mkdir(parents=True)
    (reserved / "GUIDE.md").write_text("示例", encoding="utf-8")
    write_json(reserved / "style.json", {
        "schemaVersion": 1, "id": "examples", "version": "1.0.0", "description": "伪装成包",
        "types": ["general"], "frames": [{"width": 1920, "height": 1080}], "guide": "GUIDE.md",
    })
    monkeypatch.setattr(styles, "STYLES_ROOT", base)
    with pytest.raises(M2VError, match="保留目录"):
        styles.load_style("examples")
    assert styles.list_styles() == []
    with pytest.raises(M2VError):
        styles.selected_style({"type": "general", "style": {"id": "examples"}})


def test_manifest_tokens_and_no_font_asset():
    package = styles.load_style("vibe-fable")
    manifest = package["manifest"]
    assert manifest["version"] == "1.0.0"
    assert set(package["components"]) == COMPONENTS
    assert manifest["requires"] == {"narration": "none"}
    # 本包不带字体：B 寓言用宿主已注册的无衬线字体。
    assert "assets" not in manifest
    tokens = package["tokens"]
    assert tokens["canvas"]["background"] == "#E6DCC4"
    assert tokens["colors"]["red"] == "#FC593F"
    assert tokens["gauge"]["redFrom"] == 100
    assert set(tokens["scenePalette"]) == {"beach", "desert", "desk", "reeds", "night"}
    assert "safeArea" not in tokens["layout"]


def test_selection_rejects_wrong_type_and_frame():
    with pytest.raises(M2VError, match="类型"):
        styles.selected_style({"type": "financial-timeseries", "style": {"id": "vibe-fable"}})
    with pytest.raises(M2VError, match="画幅"):
        styles.selected_style({"type": "general", "style": {"id": "vibe-fable"}}, width=1080, height=1920)
    styles.selected_style({"type": "general", "style": {"id": "vibe-fable"}}, width=1920, height=1080)


def test_components_are_frame_driven_and_self_contained():
    forbidden = ("Math.random", "Date.now", "setInterval", "setTimeout", "requestAnimationFrame", "@keyframes")
    for path in sorted((PACKAGE / "components").glob("*.tsx")):
        text = path.read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        code = re.sub(r"//[^\n]*", "", code)
        for token in forbidden:
            assert token not in code, f"{path.name} 使用了 {token}"
        for module in re.findall(r"from\s+['\"]([^'\"]+)['\"]", code):
            assert module.startswith(("react", "m2v/", "./")), f"{path.name} 导入了未批准模块 {module}"


def test_fingerprint_covers_every_package_file(tmp_path, monkeypatch):
    copy = tmp_path / "styles" / "vibe-fable"
    shutil.copytree(PACKAGE, copy)
    monkeypatch.setattr(styles, "STYLES_ROOT", tmp_path / "styles")
    first = styles.load_style("vibe-fable")["identity"]["fingerprint"]
    (copy / "GUIDE.md").write_text("changed", encoding="utf-8")
    second = styles.load_style("vibe-fable")["identity"]["fingerprint"]
    assert first != second


def test_example_changes_do_not_touch_the_package_fingerprint(tmp_path, monkeypatch):
    """示例与包分离是本次的核心设计：改示例不能让选了该风格的作品准备失效。"""
    base = tmp_path / "styles"
    base.mkdir()
    shutil.copytree(PACKAGE, base / "vibe-fable")
    examples = base / "examples" / "vibe-fable" / "pigeon"
    examples.mkdir(parents=True)
    (examples / "storyboard.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(styles, "STYLES_ROOT", base)
    before = styles.load_style("vibe-fable")["identity"]["fingerprint"]
    (examples / "storyboard.json").write_text('{"changed": true}', encoding="utf-8")
    (examples / "extra.tsx").write_text("export default () => null;", encoding="utf-8")
    after = styles.load_style("vibe-fable")["identity"]["fingerprint"]
    assert before == after


def test_style_requires_no_narration():
    from m2v.core.styles import check_requirements
    package = styles.load_style("vibe-fable")
    check_requirements(package, has_narration=False)
    with pytest.raises(M2VError, match="无旁白"):
        check_requirements(package, has_narration=True)


@pytest.mark.parametrize("slug,style_id", [
    ("vibe-night/fold", "vibe-night"),
    ("vibe-fable/pigeon", "vibe-fable"),
])
def test_shipped_style_example_uses_its_package(slug: str, style_id: str):
    """示例必须声明它演示的风格，且分镜通过 v8 契约校验。"""
    root = EXAMPLES / slug
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert project["type"] == "general"
    assert project["style"] == {"id": style_id}
    board = explainer.load(root, project)
    explainer.validate(board, root, project)
    assert board["version"] == 8 and board["schemaVersion"] == 8


@pytest.mark.parametrize("slug,style_id", [
    ("vibe-night/fold", "vibe-night"),
    ("vibe-fable/pigeon", "vibe-fable"),
])
def test_style_example_is_silent_with_screen_subtitles(slug: str, style_id: str):
    """两个示例都是无旁白作品：用屏幕字幕，不生成共享字幕层的旁白字幕。"""
    root = EXAMPLES / slug
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    board = explainer.load(root, project)
    for scene in board["scenes"]:
        assert scene["narrationSegments"] == [], f"{slug}/{scene['id']} 不应有旁白"
        props = scene["content"]["props"]
        assert props.get("screenSubtitles"), f"{slug}/{scene['id']} 没有屏幕字幕"
        for subtitle in props["screenSubtitles"]:
            assert subtitle["endFrame"] > subtitle["startFrame"]
            assert subtitle["text"].strip()
            # 屏幕字幕窗口必须落在本幕内；示例是回归工件，越界窗口不该靠人工发现。
            assert subtitle["endFrame"] <= scene["durationFrames"], (
                f"{slug}/{scene['id']} 字幕窗口 {subtitle['endFrame']} 超出本幕")
    # 风格包声明无旁白，示例选择它必须能通过硬约束。
    from m2v.core.styles import check_requirements, selected_style
    width, height = board["width"], board["height"]
    package = selected_style(project, width=width, height=height)
    check_requirements(package, has_narration=False)


@pytest.mark.parametrize("slug", ["vibe-night/fold", "vibe-fable/pigeon"])
def test_style_example_sources_do_not_expose_internal_paths(slug: str):
    """示例是仓库内的可分发材料：可见文案不得出现仓库路径或查阅指引。"""
    root = EXAMPLES / slug
    sources = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((root / "scenes").glob("*.tsx")))
    board = (root / "storyboard.json").read_text(encoding="utf-8")
    visible = sources + "\n" + board
    internal = re.compile(
        r"(?i)\b(?:examples|outputs|openspec|styles)/|\.agents/|"
        r"(?:详见|查看|参见)\s*(?:内部)?(?:来源|制作|项目)?(?:文档|文件|资料)")
    assert internal.search(visible) is None


def test_style_examples_are_not_discovered_as_style_packages():
    """示例目录里的 `project.json` 不会被误当成风格包清单。"""
    for path in EXAMPLES.rglob("style.json"):
        assert False, f"示例目录不应出现风格清单：{path}"
    assert not (EXAMPLES / "style.json").exists()


def test_pigeon_uses_global_act_and_event_sound_semantics():
    """示例必须用同一条全局行为轨迹，声音与画面引用同一批幕内事件。"""
    root = EXAMPLES / "vibe-fable" / "pigeon"
    board = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    source = (root / "scenes" / "pigeon.tsx").read_text(encoding="utf-8")
    assert "birdAct(" not in source, "行为不得再按幕 ID 分支"
    assert "clock.startSeconds" not in source
    assert "act(globalSeconds, firstTurnAt)" in source
    assert "events.frame('turn-1') / fps" in source
    for scene in board["scenes"]:
        props = scene["content"]["props"]
        assert props["capture"]["timebase"] == "global"
        assert props["capture"]["mode"] == "pure-time"
        assert "clock" not in props
        assert isinstance(scene.get("events"), list)
    declared = {(scene["id"], event["id"]) for scene in board["scenes"] for event in scene["events"]}
    effects = board["soundtrack"]["effects"]
    assert effects, "示例应保留声音设计"
    assert any(effect["sceneId"] == "wander" and effect["eventId"] == "turn-1"
               for effect in effects), "首个转圈的画面和声音必须引用同一事件"
    for effect in effects:
        assert "eventId" in effect, "音效必须引用语义事件"
        assert "offsetFrames" not in effect and "offsetMs" not in effect
        assert (effect["sceneId"], effect["eventId"]) in declared
    sound_map = (root / "SOUND.md").read_text(encoding="utf-8")
    for asset in {effect["assetId"] for effect in effects}:
        assert f"`{asset}`" in sound_map, f"SOUND.md 未登记 {asset}"


def test_pigeon_removes_unbacked_instinct_readout():
    """实验没有提供本能强度依据，示例不得再显示精确读数或挂载仪表。"""
    root = EXAMPLES / "vibe-fable" / "pigeon"
    board = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    source = (root / "scenes" / "pigeon.tsx").read_text(encoding="utf-8")
    for scene in board["scenes"]:
        assert "gauge" not in scene["content"]["props"]
    assert "InstinctGauge" not in source
    assert "instinct-gauge" not in source
    assert "FEED_INTERVAL = 15" in source
    assert "FEED_TIMES = [15, 30]" in source


@pytest.mark.slow
def test_fable_components_build_inside_package(tmp_path):
    if shutil.which("node") is None:
        pytest.skip("需要 Node.js")
    root = tmp_path / "content"
    create_project(root, "general", {"storyboard": "storyboard.json"},
                   output={"width": 1920, "height": 1080, "fps": 30})
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    project["style"] = {"id": "vibe-fable"}
    (root / "project.json").write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
    (root / "scenes").mkdir()
    (root / "scenes" / "all.tsx").write_text(
        """
import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import FableStage from 'm2v/style/components/fable-stage';
import ParallaxBand from 'm2v/style/components/parallax-band';
import InstinctGauge from 'm2v/style/components/instinct-gauge';
import SceneNote from 'm2v/style/components/scene-note';
import TopLine from 'm2v/style/components/top-line';
import CounterRow from 'm2v/style/components/counter-row';
import Callout from 'm2v/style/components/callout';
import RuleCard from 'm2v/style/components/rule-card';
import TitleFable from 'm2v/style/components/title-fable';
import ScreenSubtitle from 'm2v/style/components/screen-subtitle';
export default function All({width, height, fps, subtitleSafeArea}: CodeSceneProps) {
  const {ready, elapsedSeconds} = useSceneContext();
  useEffect(() => { document.fonts.ready.then(() => ready()); }, [ready]);
  const frame = Math.round(elapsedSeconds * fps);
  return <div style={{position: 'absolute', inset: 0, width, height}}>
    <FableStage scene="beach" width={width} height={height}/>
    <ParallaxBand frame={frame} startFrame={0} durationFrames={30}/>
    <InstinctGauge value={120} startValue={40} object="鸽子" frame={frame} startFrame={0} durationFrames={10}/>
    <SceneNote year="1948" place="实验室"/>
    <TopLine text="食物按时间来" frame={frame}/>
    <CounterRow items={[{label: '真的', value: 15}, {label: '夸张的', value: 120, exaggerated: true}]} frame={frame}/>
    <Callout text="食槽" at={{x: 900, y: 500}} label={{x: 1040, y: 470}}/>
    <RuleCard title="碰巧不等于因果" frame={frame} startFrame={0}/>
    <TitleFable text="鸽子的迷信" width={width} height={height} frame={frame} startFrame={0}/>
    <ScreenSubtitle frame={frame} safeArea={subtitleSafeArea}
      items={[{startFrame: 0, endFrame: 2, text: "食物按时间来"}]}/>
  </div>;
}
""",
        encoding="utf-8",
    )
    work = tmp_path / "build"
    work.mkdir()
    scene = {"id": "all", "content": {"entry": "scenes/all.tsx", "props": {}},
             "durationInFrames": 2, "segmentWindows": {}, "narrationSegments": []}
    inputs = build_scene(root, scene, work)
    assert inputs["style"] == styles.load_style("vibe-fable")["identity"]["fingerprint"]
    assert (work / "scene.js").is_file()


@pytest.mark.slow
def test_fable_frame_records_identically(tmp_path, chromium_ready):
    from _helpers import board, project as general_project
    from m2v.core import frames
    from m2v.types.general.code_scenes import record
    from test_code_scenes import code_scene, write_source

    root, manifest = general_project(tmp_path / "content", board())
    manifest["style"] = {"id": "vibe-fable"}
    manifest["output"].update(width=1920, height=1080, fps=30)
    (root / "project.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    write_source(root, "scenes/demo.tsx", """
import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import FableStage from 'm2v/style/components/fable-stage';
import InstinctGauge from 'm2v/style/components/instinct-gauge';
import ScreenSubtitle from 'm2v/style/components/screen-subtitle';
export default function Demo({width, height, fps, subtitleSafeArea}: CodeSceneProps) {
  const {ready, elapsedSeconds} = useSceneContext();
  useEffect(() => { document.fonts.ready.then(() => ready()); }, [ready]);
  const frame = Math.round(elapsedSeconds * fps);
  return <div style={{position: 'absolute', inset: 0, width, height}}>
    <FableStage scene="beach" width={width} height={height}/>
    <InstinctGauge value={120} startValue={40} object="鸽子" frame={frame} startFrame={0} durationFrames={10}/>
    <ScreenSubtitle frame={frame} safeArea={subtitleSafeArea}
      items={[{startFrame: 0, endFrame: 2, text: "食物按时间来"}]}/>
  </div>;
}
""")
    scene = code_scene()
    scene.update(startFrame=0, durationInFrames=2, segmentWindows={})
    frame = frames.spec(1920, 1080)
    first = record(root, scene, {}, frame=frame, media={}, media_digest="empty", fps=30)
    second = record(root, scene, {}, frame=frame, media={}, media_digest="empty-second", fps=30)
    assert first != second
    assert (root / first).read_bytes() == (root / second).read_bytes()
