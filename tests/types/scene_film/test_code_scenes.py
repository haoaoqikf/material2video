"""本地 React 代码场景：入口边界、构建隔离、逐帧录制与缓存复用。"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from film_runtime.core.errors import VideoError
from m2v.core.project import load_current_prepared, load_project
from m2v.types.scene_film import adapter, explainer
from film_runtime.types.scene_film import code_scenes
from film_runtime.types.scene_film.code_scenes import workspace
from helpers.scene_film import (
    SOURCE, board, code_scene, fake_tts, prepare_build, project, requires_node,
    scene_page, scene_root, write_source,
)


def test_recording_workspace_reaps_only_abandoned_owned_directories(tmp_path, monkeypatch):
    cache = tmp_path / "outputs" / "code-cache"
    root = cache / ".recordings"
    root.mkdir(parents=True)
    abandoned = root / "code-9931-11111111"
    parent_alive = root / "code-9932-22222222"
    worker_alive = root / "code-9931-33333333"
    recent = root / "code-9931-44444444"
    unknown = root / "code-unsupported"
    for directory in (abandoned, parent_alive, worker_alive, recent, unknown):
        directory.mkdir()
        (directory / "frame-000000.png").write_bytes(b"scratch")
    (worker_alive / ".worker-9933").touch()
    old = time.time() - workspace.STALE_SECONDS - 1
    for directory in (abandoned, parent_alive, worker_alive, unknown):
        os.utime(directory, (old, old))
    published = cache / "published.mp4"
    published.touch()
    monkeypatch.setattr(workspace, "recording_ended", lambda pid, *_args, **_kwargs: pid not in (9932, 9933))

    with pytest.raises(RuntimeError, match="capture interrupted"):
        with workspace.recording_workspace(cache) as directory:
            assert not abandoned.exists()
            assert all(item.exists() for item in (parent_alive, worker_alive, recent, unknown, published))
            workspace.register_worker(directory)
            marker = directory / f".worker-{os.getpid()}"
            assert marker.is_file()
            marker.write_text("previous-process-start", encoding="ascii")
            workspace.register_worker(directory)
            assert marker.read_text(encoding="ascii") == workspace.process_start(os.getpid())
            raise RuntimeError("capture interrupted")
    assert not directory.exists()


def storyboard(scene: dict) -> dict:
    """只保留这一幕，便于按片段数量断言录制与缓存复用。"""
    data = board()
    data["scenes"] = [scene]
    return data


def test_code_scene_without_narration_is_accepted(tmp_path):
    write_source(tmp_path, "scenes/demo.tsx")
    explainer.validate(storyboard(code_scene()), scene_root(tmp_path))


def test_global_timebase_injects_timeline_only_when_declared():
    from m2v.core import frames
    compiled = {"id": "a", "startFrame": 100, "endFrame": 220, "durationInFrames": 120,
                "segmentWindows": {}, "content": {"entry": "scenes/demo.tsx", "props": {}}}
    plain = code_scenes.scene_config(compiled, frames.spec(1920, 1080), {}, fps=30)
    assert "timeline" not in plain
    opted = {**compiled, "content": {"entry": "scenes/demo.tsx",
                                     "props": {"capture": {"timebase": "global"}}}}
    config = code_scenes.scene_config(opted, frames.spec(1920, 1080), {}, fps=30)
    assert config["timeline"] == {"sceneStartFrame": 100, "sceneEndFrame": 220,
                                  "durationInFrames": 120}


def test_capture_timebase_rejects_unknown_values_and_fields():
    with pytest.raises(VideoError, match="timebase"):
        code_scenes.capture_settings({"capture": {"timebase": "wall"}})
    with pytest.raises(VideoError, match="未知字段"):
        code_scenes.capture_settings({"capture": {"timebase": "global", "foo": 1}})
    with pytest.raises(VideoError, match="pure-time 场景必须使用全局时间"):
        code_scenes.capture_settings({"capture": {"mode": "pure-time", "timebase": "local"}})
    with pytest.raises(VideoError, match="jobs"):
        code_scenes.capture_settings({"capture": {"mode": "pure-time", "jobs": 5}})
    with pytest.raises(VideoError, match="verifyFrames"):
        code_scenes.capture_settings({"capture": {"mode": "pure-time", "verifyFrames": 1}})


def test_pure_time_implies_global_timeline_and_hides_runtime_fields_from_cache():
    from m2v.core import frames
    compiled = {"id": "a", "startFrame": 100, "endFrame": 220, "durationInFrames": 120,
                "segmentWindows": {}, "content": {"entry": "scenes/demo.tsx",
                "props": {"capture": {"mode": "pure-time", "jobs": 2, "blockFrames": 30,
                                      "verifyFrames": 3}}}}
    config = code_scenes.scene_config(compiled, frames.spec(1920, 1080), {}, fps=30)
    assert config["captureMode"] == "pure-time"
    assert config["timeline"]["sceneStartFrame"] == 100
    assert "jobs" not in config["props"]["capture"]
    assert "blockFrames" not in config["props"]["capture"]
    assert "verifyFrames" not in config["props"]["capture"]


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


@pytest.mark.slow
@requires_node
def test_build_allows_approved_packages_and_records_sources(tmp_path):
    project_dir, output, result = prepare_build(tmp_path, SOURCE)
    assert result.returncode == 0, result.stderr
    assert (output / "scene.js").is_file()
    reachable = {Path(name).resolve() for name in json.loads((output / "inputs.json").read_text(encoding="utf-8"))}
    assert (project_dir / "scenes/demo.tsx").resolve() in reachable


@pytest.mark.slow
@requires_node
def test_build_ignores_unbound_ambient_tsconfig(tmp_path):
    (tmp_path / 'tsconfig.json').write_text('{ invalid ambient configuration', encoding='utf-8')
    _, output, result = prepare_build(tmp_path, SOURCE)
    assert result.returncode == 0, result.stderr
    assert (output / 'input-digests.json').is_file()


@pytest.mark.parametrize("source,match", [
    ("import _ from 'lodash';\nexport default () => _.chunk([1, 2], 1);\n", "未登记的作品依赖"),
    ("import 'lodash';\nexport default () => null;\n", "未登记的作品依赖"),
    ("import x from '../../outside';\nexport default () => x;\n", "作品导入越界"),
    ("import x from 'https://example.com/x.js';\nexport default () => x;\n", "未登记的作品依赖"),
    ("import css from 'katex/dist/katex.min.css?raw';\nexport default () => css;\n", "未登记的作品依赖"),
])
@pytest.mark.slow
@requires_node
def test_build_rejects_unapproved_imports(tmp_path, source, match):
    _project, output, result = prepare_build(tmp_path, source)
    assert result.returncode != 0
    assert match in result.stderr
    assert not (output / "scene.js").exists()


@pytest.mark.slow
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
    with pytest.raises(VideoError, match="文件已变化"):
        load_current_prepared(root, manifest)
    assert recorded(root, manifest)["props"]["compiledScenes"][-1]["mediaPath"] != relative
    assert len(list((root / "outputs/code-cache").glob("*.mp4"))) == 2


PURE_SOURCE = """import {useEffect} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
export default function Demo({width, height}: CodeSceneProps) {
  const {ready, elapsedSeconds} = useSceneContext();
  useEffect(() => {ready();}, [ready]);
  return <div style={{position: 'absolute', inset: 0, width, height, background: '#000'}}>
    <div style={{position: 'absolute', left: 20 + elapsedSeconds * 400, top: 40,
      width: 30, height: 30, background: '#fff'}}/>
  </div>;
}
"""


PURE_MOTION_SOURCE = """import {useEffect} from 'react';
import {growSeries, motionCurve, useSceneContext, type CodeSceneProps} from 'm2v/code-scene';
export default function Demo({width, height}: CodeSceneProps) {
  const {ready, elapsedSeconds} = useSceneContext();
  useEffect(() => {ready();}, [ready]);
  const bars = growSeries({values: [40, 70], progress: elapsedSeconds * 5,
    easing: motionCurve('linear'), stagger: 0.25});
  return <svg width={width} height={height} style={{background: '#000'}}>
    {bars.values.map((bar, index) => <rect key={index} x={20 + index * 25}
      y={100 - bar} width={18} height={bar} fill="#fff"/>)}
  </svg>;
}
"""


def pure_scene(duration=12, **capture):
    return {"id": "pure", "template": "code", "durationFrames": duration, "durationInFrames": duration,
            "startFrame": 0, "endFrame": duration, "segmentWindows": {}, "narrationSegments": [],
            "content": {"title": "纯时间", "entry": "scenes/demo.tsx",
                        "props": {"capture": {"mode": "pure-time", "verifyFrames": 3, **capture}}}}


@pytest.mark.slow
@requires_node
def test_pure_time_capture_seeks_directly_and_reuses_blocks(tmp_path, chromium_ready):
    root = tmp_path / "project"
    write_source(root, "scenes/demo.tsx", PURE_SOURCE)
    frame = {"width": 320, "height": 240,
             "subtitle": {"safeArea": {"x": 0, "y": 200, "width": 320, "height": 40}}}
    scene = pure_scene()
    first = code_scenes.record(root, scene, {}, frame=frame, media={}, media_digest="empty",
                               capture_range=(3, 9), fps=30)
    first_clip = root / first
    code_scenes._verify_clip(first_clip, 6)
    receipt = json.loads(first_clip.with_suffix(".json").read_text(encoding="utf-8"))
    assert receipt["contract"] == code_scenes.PURE_CONTRACT
    assert receipt["verified"] is True
    assert receipt["probes"] and receipt["minPsnr"] is None  # 完全相同
    complete = code_scenes.record(root, scene, {}, frame=frame, media={}, media_digest="empty",
                                  capture_range=(0, 12), fps=30)
    code_scenes._verify_clip(root / complete, 12)
    clips = list((root / "outputs/code-cache").glob("*.mp4"))
    assert len(clips) == 4  # 0–3、3–9、9–12 与拼接后的 0–12
    assert any(path.stem.endswith("-3-9") for path in clips)


@pytest.mark.slow
@requires_node
def test_pure_time_evaluates_motion_primitives(tmp_path, chromium_ready):
    with scene_page(tmp_path, PURE_MOTION_SOURCE, frames=6, extra={"captureMode": "pure-time"}) as (page, _):
        frames = {}
        for frame in (0, 2, 5, 2, 0, 5):
            page.evaluate("(frame) => window.__M2V_CODE__.seekToSubframe(frame, 0, 1)", frame)
            screenshot = page.screenshot()
            assert frames.setdefault(frame, screenshot) == screenshot
        assert frames[0] != frames[5]


@pytest.mark.slow
@requires_node
def test_pure_time_parallel_chunks_reassemble_in_order(tmp_path, chromium_ready):
    root = tmp_path / "project"
    write_source(root, "scenes/demo.tsx", PURE_SOURCE)
    frame = {"width": 320, "height": 240,
             "subtitle": {"safeArea": {"x": 0, "y": 200, "width": 320, "height": 40}}}
    scene = pure_scene(duration=6, jobs=2, blockFrames=2)
    relative = code_scenes.record(root, scene, {}, frame=frame, media={}, media_digest="empty",
                                  capture_range=(0, 6), fps=30, jobs=2)
    clip = root / relative
    code_scenes._verify_clip(clip, 6)
    receipts = sorted((root / "outputs/code-cache").glob("*.json"))
    assert any(item.stem.endswith("-0-2") for item in receipts)
    assert any(item.stem.endswith("-4-6") for item in receipts)


@pytest.mark.slow
@requires_node
def test_pure_time_rejects_self_driven_scene(tmp_path, chromium_ready):
    root = tmp_path / "project"
    write_source(root, "scenes/demo.tsx",
                 "import {useFrame} from 'm2v/code-scene';\n"
                 "export default function Bad() { useFrame(() => {}); return null; }\n")
    frame = {"width": 320, "height": 240,
             "subtitle": {"safeArea": {"x": 0, "y": 200, "width": 320, "height": 40}}}
    with pytest.raises(VideoError, match="pure-time 场景含自走动画"):
        code_scenes.record(root, pure_scene(), {}, frame=frame, media={},
                           media_digest="empty", capture_range=(0, 3), fps=30)


@pytest.mark.slow
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
    with pytest.raises(VideoError, match="代码场景"):
        recorded(root, manifest)
    assert (root / "outputs/prepared.json").exists()


@pytest.mark.slow
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


@pytest.mark.slow
@requires_node
def test_scene_that_never_readies_fails_without_a_record(tmp_path, monkeypatch, chromium_ready):
    """资源没就绪就调用 ready()：录制超时失败，且不发布有效准备记录。"""
    from m2v.types.scene_film import code_scenes as module
    # 录制超时住在采集模块里：包上的名字只是重导出，改它不会影响真正读常量的地方。
    monkeypatch.setattr(module.capture, "READY_TIMEOUT_MS", 1200)
    root, manifest = project(tmp_path, storyboard(code_scene(durationFrames=20)))
    write_source(root, "scenes/demo.tsx",
                 "export default function Never() { return <div style={{width: '100%', height: '100%'}}/>; }\n")
    fake_tts(monkeypatch)
    with pytest.raises(VideoError, match="就绪失败"):
        recorded(root, manifest)
    assert (root / "outputs/prepared.json").exists()
    assert not list((root / "outputs/code-cache").glob("*.mp4"))


@pytest.mark.slow
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


@pytest.mark.slow
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


def test_scene_cache_prunes_only_unreferenced_old_pairs(tmp_path, monkeypatch):
    from film_runtime.types.scene_film.code_scenes import cache as storage

    cache = tmp_path / "outputs/code-cache"
    cache.mkdir(parents=True)
    monkeypatch.setattr(storage, "CACHE_BYTES", 21)
    oldest, pinned, latest = (cache / (char * 64 + "-0-9.mp4") for char in "abc")
    for index, video in enumerate((oldest, pinned, latest)):
        video.write_bytes(b"x" * 9)
        video.with_suffix(".json").write_bytes(b"{}")
        os.utime(video, (100 + index, 100 + index))
    (cache.parent / "materialized.json").write_text(json.dumps({
        "path": latest.relative_to(tmp_path).as_posix(),
    }), encoding="utf-8")
    (cache.parent / "visual-notes.md").write_text(pinned.name, encoding="utf-8")

    with storage.scene_cache(tmp_path):
        assert not oldest.exists()
        assert not oldest.with_suffix(".json").exists()
        with storage.scene_cache(tmp_path):
            assert pinned.is_file() and latest.is_file()
