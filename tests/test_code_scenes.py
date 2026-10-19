"""本地 React 代码场景：入口边界、构建隔离、逐帧录制与缓存复用。"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.core.project import load_current_prepared, load_project
from m2v.types.general import adapter, code_scenes, explainer
from test_article_explainer import board, fake_tts, project, scene, scene_root

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
SOURCE = """import {motion, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
import {useEffect} from 'react';

export default function Demo({props}: CodeSceneProps) {
  const {ready, running} = useSceneContext();
  useEffect(() => {ready();}, []);
  return <motion.div animate={running ? {opacity: 1} : {opacity: 0}}>{String(props.label ?? '演示')}</motion.div>;
}
"""
requires_node = pytest.mark.skipif(
    shutil.which("node") is None or not (WEB / "node_modules" / "esbuild").is_dir(),
    reason="需要 Node 与前端依赖才能验证代码场景构建")


def code_scene(entry: str = "scenes/demo.tsx", props: object = None, **extra) -> dict:
    scene = {"id": "code-demo", "template": "code", "keywords": ["演示"],
             "content": {"title": "代码演示", "entry": entry, "props": {} if props is None else props},
             "narrationSegments": []}
    scene.update(extra)
    return scene


def storyboard(scene: dict) -> dict:
    """只保留这一幕，便于按片段数量断言录制与缓存复用。"""
    data = board()
    data["scenes"] = [scene]
    return data


def write_source(root: Path, entry: str, source: str = SOURCE) -> None:
    file = root / entry
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(source, encoding="utf-8")


def test_code_scene_without_narration_is_accepted(tmp_path):
    write_source(tmp_path, "scenes/demo.tsx")
    explainer.validate(storyboard(code_scene()), scene_root(tmp_path))


@pytest.mark.parametrize("entry", ["C:/outside.tsx", "scenes\\demo.tsx", "assets/demo.tsx",
                                   "scenes/../outside.tsx", "scenes/demo.txt", "scenes/missing.tsx"])
def test_entry_outside_the_scenes_directory_is_rejected(tmp_path, entry):
    write_source(tmp_path, "scenes/demo.tsx")
    (tmp_path / "outside.tsx").write_text(SOURCE, encoding="utf-8")
    (tmp_path / "assets").mkdir(exist_ok=True)
    with pytest.raises(M2VError, match="scenes/"):
        explainer.validate(storyboard(code_scene(entry=entry)), scene_root(tmp_path))


@pytest.mark.parametrize("props,match", [([], "JSON 对象"), ({"label": float("nan")}, "有限 JSON")])
def test_props_must_be_finite_json_object(tmp_path, props, match):
    write_source(tmp_path, "scenes/demo.tsx")
    with pytest.raises(M2VError, match=match):
        explainer.validate(storyboard(code_scene(props=props)), scene_root(tmp_path))


def test_code_content_has_no_extra_fields(tmp_path):
    write_source(tmp_path, "scenes/demo.tsx")
    scene = code_scene()
    scene["content"]["module"] = "entry"
    with pytest.raises(M2VError, match="未知字段"):
        explainer.validate(storyboard(scene), scene_root(tmp_path))


def build(project_dir: Path, entry: str, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([shutil.which("node") or "node", str(WEB / "scripts/build-code-scene.mjs"),
                           str(project_dir), entry, str(output)], cwd=WEB, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=180)


def prepare_build(tmp_path: Path, source: str) -> tuple[Path, Path, subprocess.CompletedProcess[str]]:
    project_dir, output = tmp_path / "work", tmp_path / "out"
    (project_dir / "scenes").mkdir(parents=True)
    output.mkdir()
    (project_dir / "scenes/demo.tsx").write_text(source, encoding="utf-8")
    return project_dir, output, build(project_dir, "scenes/demo.tsx", output)


@requires_node
def test_build_allows_approved_packages_and_records_sources(tmp_path):
    project_dir, output, result = prepare_build(tmp_path, SOURCE)
    assert result.returncode == 0, result.stderr
    assert (output / "scene.js").is_file()
    reachable = {Path(name).resolve() for name in json.loads((output / "inputs.json").read_text(encoding="utf-8"))}
    assert (project_dir / "scenes/demo.tsx").resolve() in reachable


@pytest.mark.parametrize("source,match", [
    ("import _ from 'lodash';\nexport default () => _.chunk([1, 2], 1);\n", "未批准的作品依赖"),
    ("import 'lodash';\nexport default () => null;\n", "未批准的作品依赖"),
    ("import x from '../../outside';\nexport default () => x;\n", "作品导入越界"),
    ("import x from 'https://example.com/x.js';\nexport default () => x;\n", "未批准的作品依赖"),
])
@requires_node
def test_build_rejects_unapproved_imports(tmp_path, source, match):
    _project, output, result = prepare_build(tmp_path, source)
    assert result.returncode != 0
    assert match in result.stderr
    assert not (output / "scene.js").exists()


@requires_node
def test_prepare_records_code_scene_and_reuses_the_accepted_clip(tmp_path, monkeypatch, chromium_ready):
    """准备录制真实片段；重复准备复用缓存，源码变化让旧准备失效。"""
    root, manifest = project(tmp_path, storyboard(code_scene(durationFrames=30)))
    write_source(root, "scenes/demo.tsx")
    fake_tts(monkeypatch)
    prepared = adapter.prepare(root, manifest)
    assert not (root / "outputs/code-cache").exists()
    prepared = code_scenes.materialize(root, prepared, 0, prepared["durationInFrames"])
    relative = prepared["props"]["compiledScenes"][-1]["mediaPath"]
    clip = root / relative
    assert clip.is_file() and clip.parent.name == "code-cache"
    assert "file:" + relative not in prepared["inputs"]
    assert recorded(root, manifest)["props"]["compiledScenes"][-1]["mediaPath"] == relative
    assert len(list((root / "outputs/code-cache").glob("*.mp4"))) == 1
    write_source(root, "scenes/demo.tsx", SOURCE + "// 变化\n")
    with pytest.raises(M2VError, match="文件已变化"):
        load_current_prepared(root, manifest)
    assert recorded(root, manifest)["props"]["compiledScenes"][-1]["mediaPath"] != relative
    assert len(list((root / "outputs/code-cache").glob("*.mp4"))) == 2


@requires_node
def test_scene_failure_keeps_no_prepared_record(tmp_path, monkeypatch, chromium_ready):
    """场景运行异常或请求外网时准备失败，不保存有效准备记录。"""
    root, manifest = project(tmp_path, storyboard(code_scene(durationFrames=30)))
    write_source(root, "scenes/demo.tsx",
                 "import {useEffect} from 'react';\n"
                 "import {useSceneContext} from 'm2v/code-scene';\n"
                 "export default function External() {\n"
                 "  const {ready} = useSceneContext();\n"
                 "  useEffect(() => {ready(); void fetch('https://example.com/x.json');}, []);\n"
                 "  return null;\n"
                 "}\n")
    fake_tts(monkeypatch)
    with pytest.raises(M2VError, match="代码场景"):
        recorded(root, manifest)
    assert (root / "outputs/prepared.json").exists()


@requires_node
def test_recorded_clip_has_no_audio_stream(tmp_path, monkeypatch, chromium_ready):
    """素材原声不进入母版：录制片段本身不带音轨，成片声音只来自统一音轨。"""
    root, manifest = project(tmp_path, storyboard(code_scene(durationFrames=20)))
    write_source(root, "scenes/demo.tsx")
    fake_tts(monkeypatch)
    clip = root / recorded(root, manifest)["props"]["compiledScenes"][-1]["mediaPath"]
    from imageio_ffmpeg import get_ffmpeg_exe
    probed = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(clip)], capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    assert "Audio:" not in probed.stderr, "录制片段不该带音轨"
    assert "Video:" in probed.stderr


@requires_node
def test_scene_that_never_readies_fails_without_a_record(tmp_path, monkeypatch, chromium_ready):
    """资源没就绪就调用 ready()：录制超时失败，且不发布有效准备记录。"""
    from m2v.types.general import code_scenes as module
    # 录制超时住在采集模块里：包上的名字只是重导出，改它不会影响真正读常量的地方。
    monkeypatch.setattr(module.capture, "READY_TIMEOUT_MS", 1200)
    root, manifest = project(tmp_path, storyboard(code_scene(durationFrames=20)))
    write_source(root, "scenes/demo.tsx",
                 "export default function Never() { return <div style={{width: '100%', height: '100%'}}/>; }\n")
    fake_tts(monkeypatch)
    with pytest.raises(M2VError, match="就绪失败"):
        recorded(root, manifest)
    assert (root / "outputs/prepared.json").exists()
    assert not list((root / "outputs/code-cache").glob("*.mp4"))


@requires_node
def test_frame_change_records_a_new_clip(tmp_path, monkeypatch, chromium_ready):
    """画幅变了即使源码没变也要重新录制：viewport 与片段尺寸都跟着画幅。"""
    root, manifest = project(tmp_path, storyboard(code_scene(durationFrames=20)))
    write_source(root, "scenes/demo.tsx")
    fake_tts(monkeypatch)
    landscape = root / recorded(root, manifest)["props"]["compiledScenes"][-1]["mediaPath"]
    board_data = storyboard(code_scene(durationFrames=20))
    board_data.update(width=1080, height=1920)
    (root / "storyboard.json").write_text(json.dumps(board_data, ensure_ascii=False), encoding="utf-8")
    _root, manifest = load_project(root)
    portrait = recorded(root, manifest)
    assert portrait["props"]["compiledScenes"][-1]["mediaPath"] != landscape.relative_to(root).as_posix()
    assert (portrait["width"], portrait["height"]) == (1080, 1920)
    assert len(list((root / "outputs/code-cache").glob("*.mp4"))) == 2


def recorded(root, manifest):
    prepared = adapter.prepare(root, manifest)
    return code_scenes.materialize(root, prepared, 0, prepared["durationInFrames"])


@requires_node
def test_partial_recording_is_reused_when_completing_scene(tmp_path, monkeypatch, chromium_ready):
    root, manifest = project(tmp_path, storyboard(code_scene(durationFrames=8)))
    write_source(root, "scenes/demo.tsx")
    fake_tts(monkeypatch)
    prepared = adapter.prepare(root, manifest)
    original = code_scenes._capture
    captured = []
    def count(*args, **kwargs):
        captured.extend(kwargs["selected_frames"])
        return original(*args, **kwargs)
    monkeypatch.setattr(code_scenes.capture, "_capture", count)
    code_scenes.materialize(root, prepared, 2, 5)
    completed = code_scenes.materialize(root, prepared, 0, 8)
    code_scenes.materialize(root, prepared, 0, 8)
    assert sorted(captured) == list(range(8)), "已有区间不得再次采集"
    clip = root / completed["props"]["compiledScenes"][0]["mediaPath"]
    code_scenes._verify_clip(clip, 8)
