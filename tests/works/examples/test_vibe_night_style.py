"""正式 C 夜曲风格包：清单、资产、组件契约与构建边界。"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from m2v.core import styles
from m2v.core.errors import M2VError
from m2v.core.project import create_project
from m2v.types.general.code_scenes import build_scene

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "styles" / "vibe-night"


@pytest.fixture
def restored_style_font():
    manifest = json.loads((PACKAGE / 'style.json').read_text(encoding='utf-8'))
    if not (PACKAGE / manifest['assets']['serif']['path']).is_file():
        pytest.skip('字体未恢复；先运行 uv run python fonts/fetch.py')


@pytest.mark.usefixtures("restored_style_font")
def test_registered_font_has_source_and_license():
    package = styles.load_style("vibe-night")
    manifest = package["manifest"]
    font = Path(package["assets"]["serif"])
    assert font.read_bytes()[:4] == b"\x00\x01\x00\x00"
    assert "source" in manifest["assets"]["serif"] and "license" in manifest["assets"]["serif"]
    license_text = (PACKAGE / "assets" / "OFL-NotoSerifSC.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE" in license_text.upper()


@pytest.mark.usefixtures("restored_style_font")
@pytest.mark.slow
def test_all_components_build_inside_package(tmp_path):
    if shutil.which("node") is None:
        pytest.skip("需要 Node.js")
    root = tmp_path / "content"
    create_project(root, "general", {"storyboard": "storyboard.json"},
                   output={"width": 1920, "height": 1080, "fps": 30})
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    project["style"] = {"id": "vibe-night"}
    (root / "project.json").write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
    (root / "scenes").mkdir()
    (root / "scenes" / "all.tsx").write_text(
        """
import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import NightBackdrop from 'm2v/style/components/night-backdrop';
import Spark from 'm2v/style/components/spark';
import Comet from 'm2v/style/components/comet';
import GlowText from 'm2v/style/components/glow-text';
import ChapterMark from 'm2v/style/components/chapter-mark';
import TitleNight from 'm2v/style/components/title-night';
import Flash from 'm2v/style/components/flash';
import Dip from 'm2v/style/components/dip';
import NumberLine from 'm2v/style/components/number-line';
import {loadNightSerif} from 'm2v/style/components/kit';
export default function All({width, height}: CodeSceneProps) {
  const {ready, elapsedSeconds} = useSceneContext();
  useEffect(() => { loadNightSerif().then(() => ready()); }, [ready]);
  const frame = Math.round(elapsedSeconds * 30);
  return <div style={{position: 'absolute', inset: 0, width, height}}>
    <NightBackdrop width={width} height={height} frame={frame}/>
    <Spark x={300} y={300} size={6} frame={frame}/>
    <Comet x={700} y={400} angle={-20} length={260} frame={frame}/>
    <GlowText text="夜空为什么是黑的" x={width / 2} y={700}/>
    <ChapterMark index={1} character="暗" frame={frame}/>
    <TitleNight text="夜空的黑暗" width={width} height={height} frame={frame}/>
    <Flash frame={frame} startFrame={0}/>
    <Dip frame={frame} startFrame={0}/>
    <NumberLine x={360} y={760} width={1200} min={0} max={138} marker={138}
      frame={frame} revealFrames={20}/>
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
    assert inputs["style"] == styles.load_style("vibe-night")["identity"]["fingerprint"]
    assert (work / "scene.js").is_file()


@pytest.mark.usefixtures("restored_style_font")
@pytest.mark.slow
def test_same_frame_records_identically(tmp_path, chromium_ready):
    from helpers.general import board, project as general_project
    from m2v.core import frames
    from m2v.types.general.code_scenes import record
    from helpers.general import code_scene, write_source

    root, manifest = general_project(tmp_path / "content", board())
    manifest["style"] = {"id": "vibe-night"}
    (root / "project.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    write_source(root, "scenes/demo.tsx", """
import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import NightBackdrop from 'm2v/style/components/night-backdrop';
import Spark from 'm2v/style/components/spark';
import TitleNight from 'm2v/style/components/title-night';
import GlowText from 'm2v/style/components/glow-text';
import ScreenSubtitle from 'm2v/style/components/screen-subtitle';
import {loadNightSerif} from 'm2v/style/components/kit';
export default function Demo({width, height, fps, subtitleSafeArea}: CodeSceneProps) {
  const {ready, elapsedSeconds} = useSceneContext();
  useEffect(() => { loadNightSerif().then(() => ready()); }, [ready]);
  const frame = Math.round(elapsedSeconds * fps);
  return <div style={{position: 'absolute', inset: 0, width, height}}>
    <NightBackdrop width={width} height={height} frame={frame} seed="determinism"/>
    <Spark x={400} y={300} size={6} frame={frame} seed="one"/>
    <TitleNight text="夜空" width={width} height={height} frame={frame} startFrame={0} durationFrames={20}/>
    <GlowText text="为什么是黑的" x={width / 2} y={720}/>
    <ScreenSubtitle frame={frame} safeArea={subtitleSafeArea}
      items={[{startFrame: 0, endFrame: 2, text: "夜空为什么是黑的"}]}/>
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


@pytest.mark.usefixtures("restored_style_font")
@pytest.mark.slow
def test_unregistered_component_import_fails(tmp_path):
    if shutil.which("node") is None:
        pytest.skip("需要 Node.js")
    root = tmp_path / "content"
    create_project(root, "general", {"storyboard": "storyboard.json"},
                   output={"width": 1920, "height": 1080, "fps": 30})
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    project["style"] = {"id": "vibe-night"}
    (root / "project.json").write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
    (root / "scenes").mkdir()
    (root / "scenes" / "bad.tsx").write_text(
        "import Missing from 'm2v/style/components/missing';\nexport default () => <Missing/>;\n",
        encoding="utf-8")
    work = Path(tempfile.mkdtemp(prefix="vibe-bad-"))
    scene = {"id": "bad", "content": {"entry": "scenes/bad.tsx", "props": {}},
             "durationInFrames": 2, "segmentWindows": {}, "narrationSegments": []}
    with pytest.raises(M2VError, match="未登记的风格入口"):
        build_scene(root, scene, work)


@pytest.mark.usefixtures("restored_style_font")
def test_style_requires_no_narration():
    from m2v.core.styles import check_requirements
    package = styles.load_style("vibe-night")
    check_requirements(package, has_narration=False)
    with pytest.raises(M2VError, match="无旁白"):
        check_requirements(package, has_narration=True)


def test_screen_subtitles_reject_narration(tmp_path):
    from helpers.general import board, scene_root
    from m2v.types.general import explainer
    data = board()
    data["scenes"][0]["content"]["props"] = {
        "screenSubtitles": [{"startFrame": 0, "endFrame": 30, "text": "夜空"}]}
    with pytest.raises(M2VError, match="有旁白的幕"):
        explainer.validate(data, scene_root(tmp_path))


def test_screen_subtitles_allow_silent_scene(tmp_path):
    from helpers.general import board, scene_root
    from m2v.types.general import explainer
    data = board()
    data["scenes"][0]["narrationSegments"] = []
    data["scenes"][0]["content"]["props"] = {
        "screenSubtitles": [{"startFrame": 0, "endFrame": 30, "text": "夜空"}]}
    explainer.validate(data, scene_root(tmp_path))


@pytest.mark.usefixtures("restored_style_font")
def test_serif_font_covers_rendered_texts():
    from m2v.core.fonts import audit_fonts_strict
    package = styles.load_style("vibe-night")
    font = Path(package["assets"]["serif"])
    assert audit_fonts_strict(font, [("字幕", "夜空为什么是黑的"), ("数字", "138 亿年")]) == []
    missing = audit_fonts_strict(font, [("扩展字", "\U00020000")])
    assert missing and missing[0]["missing"] == ["\U00020000"]
