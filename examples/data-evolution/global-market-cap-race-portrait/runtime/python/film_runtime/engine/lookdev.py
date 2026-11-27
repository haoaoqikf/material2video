"""作品本地的代表静帧采集与合成：只使用作品源码、依赖、资源和 composition。

制作工具通过本地执行协议请求本命令，读取本产物的籍贯、尺寸与帧号；主项目不再
使用自己的渲染根构建作品画面。
"""
from __future__ import annotations

import json
import logging
import math
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from film_runtime.types.scene_film.code_scenes.cache import using_scene_cache
from film_runtime.core.errors import VideoError
from film_runtime.core.project import _write_json
from film_runtime.engine import remotion
from film_runtime.engine.http_server import LocalServer

logger = logging.getLogger(__name__)

STILL_SCALE = 2


def _size(prepared: dict) -> tuple[int, int]:
    return prepared["width"], prepared["height"]


def _frame_config(prepared: dict) -> dict:
    return {"width": prepared["width"], "height": prepared["height"], "subtitle": prepared["props"]["subtitle"]}


def native_stills(root: Path, prepared: dict, frames: list[int], work: Path, *,
                  scale: int = STILL_SCALE) -> dict[tuple[str, int], Path]:
    """从零连续推进每幕时钟，只保存选定帧；不触碰准备阶段的片段缓存。"""
    from film_runtime.types.scene_film import code_scenes, media_assets
    props = prepared["props"]
    frame_config = _frame_config(prepared)
    media = media_assets.resolve(root)["media"]
    captured: dict[tuple[str, int], Path] = {}
    with sync_playwright() as pw:
        for index, scene in enumerate(props["compiledScenes"]):
            selected = [frame - scene["startFrame"] for frame in frames
                        if scene["startFrame"] <= frame < scene["endFrame"]]
            if not selected:
                continue
            directory = work / f"native-{index}"
            directory.mkdir(parents=True)
            code_scenes.build_scene(root, scene, directory)
            config = code_scenes.scene_config(scene, frame_config, media, fps=prepared["fps"])
            config["captureScale"] = scale
            try:
                code_scenes._capture(pw, root, directory, config, selected_frames=selected, verify_frames=0)
            except VideoError as exc:
                raise VideoError(f"lookdev 场景 {scene['id']}（{scene['content']['entry']}）：{exc}") from exc
            for frame in selected:
                captured[(scene["id"], frame + scene["startFrame"])] = directory / f"frame-{frame:06d}.png"
    for frame in frames:
        if not any(key[1] == frame for key in captured):
            raise VideoError(f"lookdev 第 {frame} 帧不属于任何已准备场景")
    return captured


def still_props(root: Path, prepared: dict, captured: dict[tuple[str, int], Path], frame: int, media_base: str) -> dict:
    """只保留当前活跃场景，避免未采样幕引用尚未物化的片段。"""
    props = dict(prepared["props"])
    compiled = []
    for scene in props["compiledScenes"]:
        if scene["startFrame"] <= frame < scene["endFrame"]:
            entry = dict(scene)
            path = captured[(scene["id"], frame)].resolve()
            if not path.is_relative_to(root.resolve()):
                raise VideoError("静帧采集产物越过作品目录")
            entry["stillPath"] = media_base + path.relative_to(root.resolve()).as_posix()
            compiled.append(entry)
    if not compiled:
        raise VideoError(f"lookdev 第 {frame} 帧不属于任何已准备场景")
    props["compiledScenes"] = compiled
    props["mediaBase"] = media_base
    return props


def background_stills(root: Path, storyboard: Path, prepared: dict, frames: list[int], work: Path) -> dict[int, Path]:
    """直接使用幕静帧；只有转场重叠的帧需要再走一次合成。"""
    captured = native_stills(root, prepared, frames, work, scale=1)
    samples: dict[int, list[Path]] = {}
    for (_, frame), path in captured.items():
        samples.setdefault(frame, []).append(path)
    result = {frame: paths[0] for frame, paths in samples.items() if len(paths) == 1}
    overlaps = [frame for frame in frames if frame not in result]
    if overlaps:
        with LocalServer(root, cors=True) as server:
            with remotion.bundle(
                web_dir=remotion.web_dir(), out_dir=work / "bundle", storyboard_path=storyboard,
                content_root=root.parent, workspace_root=root.parent, cache=True,
            ) as bundle:
                for frame in overlaps:
                    props = still_props(root, prepared, captured, frame, server.base_url + "/")
                    props["subtitleCues"] = []
                    target = work / f"background-{frame:06d}.png"
                    _compose_still(work, bundle.path, props, target, frame, 1)
                    result[frame] = target
    return result


def _compose_still(work: Path, bundle: Path, props: dict, target: Path, frame: int, scale: int) -> None:
    props_file = work / f"props-{frame:06d}.json"
    props_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    remotion.render_still(web_dir=remotion.web_dir(), bundle_dir=bundle, props=props_file,
                          out=target, frame=frame, scale=scale, composition_id="SceneFilm")


def render_stills(root: Path, project: dict, frames: list[int], destination: Path, *,
                  scale: int = STILL_SCALE) -> dict:
    from film_runtime.types.scene_film import explainer_render
    from film_runtime.engine.browser import configure
    configure()
    if scale not in (1, 2):
        raise VideoError("静帧采样尺度只能为1或2")
    prepared = explainer_render.current(root, project)
    if any(not isinstance(frame, int) or not 0 <= frame < prepared["durationInFrames"] for frame in frames):
        raise VideoError("lookdev 帧号必须位于作品时长内")
    destination = (root / destination).resolve() if not destination.is_absolute() else destination.resolve()
    if not destination.is_relative_to(root) or not destination.is_relative_to(root / "outputs"):
        raise VideoError("lookdev 目标必须位于作品 outputs 内")
    destination.mkdir(parents=True, exist_ok=True)
    entry = root / project["materials"]["storyboard"]
    produced = []
    with tempfile.TemporaryDirectory(prefix="m2v-lookdev-", dir=destination) as temporary, \
            LocalServer(root, cors=True) as server:
        work = Path(temporary)
        native = work / "native"
        native.mkdir()
        captured = native_stills(root, prepared, frames, native, scale=scale)
        with remotion.bundle(
            web_dir=remotion.web_dir(), out_dir=work / "bundle", storyboard_path=entry,
            content_root=root.parent, workspace_root=root.parent, cache=True,
        ) as bundle:
            for frame in frames:
                target = destination / f"still-{frame:06d}.png"
                props = still_props(root, prepared, captured, frame, server.base_url + "/")
                _compose_still(work, bundle.path, props, target, frame, scale)
                produced.append(target)
    manifest = {"schemaVersion": 1, "preparedFingerprint": prepared["preparedFingerprint"],
                "frames": frames, "stillScale": scale,
                "stills": {str(frame): path.relative_to(root).as_posix()
                           for frame, path in zip(frames, produced)},
                "stillSize": [prepared["width"] * scale, prepared["height"] * scale]}
    _write_json(destination / "lookdev.json", manifest)
    return manifest




@using_scene_cache
def materialize_all(root: Path, project: dict) -> dict:
    """物化全片片段并返回带本地媒体路径的准备 props，供制作工具读取。"""
    from film_runtime.types.scene_film import code_scenes, explainer_render
    prepared = explainer_render.current(root, project)
    materialized = code_scenes.materialize(root, prepared, 0, prepared["durationInFrames"])
    audio = prepared.get("audio", {}).get("segments", [])
    value = {"schemaVersion": 1, "preparedFingerprint": prepared["preparedFingerprint"],
             "fps": prepared["fps"], "width": prepared["width"], "height": prepared["height"],
             "durationInFrames": prepared["durationInFrames"],
             "props": materialized["props"],
             "audio": audio[0]["path"] if audio else None}
    _write_json(root / "outputs/materialized.json", value)
    return value
