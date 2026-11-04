"""正式 B 寓言风格包与 `styles/<style>/examples/` 示例：清单、组件契约、示例可校验。"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from m2v.core import styles
from m2v.core.errors import M2VError
from m2v.core.project import create_project
from m2v.types.general import explainer
from m2v.types.general.code_scenes import build_scene
from helpers.examples import EXAMPLE_PATHS

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "styles" / "vibe-fable"


def test_nested_examples_are_not_packages(tmp_path, monkeypatch):
    base = tmp_path / "styles"
    package = base / "vibe-fable"
    shutil.copytree(PACKAGE, package, ignore=shutil.ignore_patterns("examples"))
    # 即使嵌套示例内放入合法清单，发现仍只检查 styles 的直接子目录。
    nested = package / "examples" / "fake"
    shutil.copytree(package, nested, ignore=shutil.ignore_patterns("examples"))
    monkeypatch.setattr(styles, "STYLES_ROOT", base)
    assert [entry["id"] for entry in styles.list_styles()] == ["vibe-fable"]
    with pytest.raises(M2VError, match="不是风格"):
        styles.load_style("examples")


def test_package_uses_host_font_and_disallows_narration():
    package = styles.load_style("vibe-fable")
    manifest = package["manifest"]
    assert manifest["requires"] == {"narration": "none"}
    # 本包不带字体：B 寓言用宿主已注册的无衬线字体。
    assert "assets" not in manifest


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
    root = EXAMPLE_PATHS[slug.split("/")[-1]]
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    if style_id == 'vibe-night':
        manifest = json.loads((ROOT / 'styles/vibe-night/style.json').read_text(encoding='utf-8'))
        if not (ROOT / 'styles/vibe-night' / manifest['assets']['serif']['path']).is_file():
            pytest.skip('字体未恢复；先运行 uv run python fonts/fetch.py')
    assert project["type"] == "general"
    assert project["style"] == {"id": style_id}
    board = explainer.load(root, project)
    explainer.validate(board, root, project)
    assert board["version"] == 8 and board["schemaVersion"] == 8


@pytest.mark.parametrize("slug", ["vibe-night/fold", "vibe-fable/pigeon"])
def test_style_example_sources_do_not_expose_internal_paths(slug: str):
    """示例是仓库内的可分发材料：可见文案不得出现仓库路径或查阅指引。"""
    root = EXAMPLE_PATHS[slug.split("/")[-1]]
    sources = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((root / "scenes").glob("*.tsx")))
    board = (root / "storyboard.json").read_text(encoding="utf-8")
    visible = sources + "\n" + board
    internal = re.compile(
        r"(?i)\b(?:examples|outputs|openspec|styles)/|\.agents/|"
        r"(?:详见|查看|参见)\s*(?:内部)?(?:来源|制作|项目)?(?:文档|文件|资料)")
    assert internal.search(visible) is None


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
    from helpers.general import board, project as general_project
    from m2v.core import frames
    from m2v.types.general.code_scenes import record
    from helpers.general import code_scene, write_source

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
