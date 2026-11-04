"""正式 C 夜曲风格包：清单、资产、组件契约与构建边界。"""
from __future__ import annotations

import json
import re
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
COMPONENTS = {
    "kit", "night-backdrop", "spark", "comet", "glow-text", "chapter-mark",
    "title-night", "flash", "dip", "number-line", "screen-subtitle",
}


def test_manifest_tokens_and_assets():
    package = styles.load_style("vibe-night")
    manifest = package["manifest"]
    assert manifest["version"] == "1.0.0"
    assert set(package["components"]) == COMPONENTS
    assert package["tokens"]["canvas"]["background"] == "#010104"
    assert package["tokens"]["canvas"]["poolColor"] == "#0B1830"
    assert package["tokens"]["colors"]["text"] == "#F8F9F8"
    assert package["tokens"]["colors"]["gold"] == "#F8D893"
    assert package["tokens"]["colors"]["ice"] == "#64E3F6"
    assert package["tokens"]["colors"]["rose"] == "#E84B75"
    assert package["tokens"]["type"]["screenSubtitleMaxChars"] == 28
    assert package["tokens"]["motion"]["screenSubtitleFadeMs"] == 200
    assert "safeArea" not in package["tokens"]["layout"]
    font = Path(package["assets"]["serif"])
    assert font.read_bytes()[:4] == b"\x00\x01\x00\x00"
    assert "source" in manifest["assets"]["serif"] and "license" in manifest["assets"]["serif"]
    license_text = (PACKAGE / "assets" / "OFL-NotoSerifSC.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE" in license_text.upper()


def test_selection_rejects_wrong_type_and_frame():
    with pytest.raises(M2VError, match="类型"):
        styles.selected_style({"type": "financial-timeseries", "style": {"id": "vibe-night"}})
    with pytest.raises(M2VError, match="画幅"):
        styles.selected_style({"type": "general", "style": {"id": "vibe-night"}}, width=1080, height=1920)
    styles.selected_style({"type": "general", "style": {"id": "vibe-night"}}, width=1920, height=1080)


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
    copy = tmp_path / "styles" / "vibe-night"
    shutil.copytree(PACKAGE, copy, ignore=shutil.ignore_patterns("examples"))
    monkeypatch.setattr(styles, "STYLES_ROOT", tmp_path / "styles")
    first = styles.load_style("vibe-night")["identity"]["fingerprint"]
    (copy / "assets" / "OFL-NotoSerifSC.txt").write_text("changed", encoding="utf-8")
    second = styles.load_style("vibe-night")["identity"]["fingerprint"]
    assert first != second


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


def test_serif_font_covers_rendered_texts():
    from m2v.core.fonts import audit_fonts_strict
    package = styles.load_style("vibe-night")
    font = Path(package["assets"]["serif"])
    assert audit_fonts_strict(font, [("字幕", "夜空为什么是黑的"), ("数字", "138 亿年")]) == []
    missing = audit_fonts_strict(font, [("扩展字", "\U00020000")])
    assert missing and missing[0]["missing"] == ["\U00020000"]
