"""通用关键画面与风险样片；采样尺寸和长度按内容选择。"""
from __future__ import annotations

import argparse
import base64
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError
from m2v.core.project import _write_json, load_project
from m2v.engine import audio, perf, remotion
from m2v.engine.http_server import LocalServer

#: 静帧张数与放大倍数：按片长与风险选择，默认原生像素。
DEFAULT_STILLS = 4
STILL_SCALE = 1
#: 样片长度：够看出节奏与声音，又不必等一次全片渲染。
DEFAULT_SAMPLE_SECONDS = 24
MIN_SAMPLE_SECONDS, MAX_SAMPLE_SECONDS = 1, 600


def still_frames(prepared: dict, count: int) -> list[int]:
    """静帧取点：hero 镜头中点优先，其余用首尾与等距点补足，最终恰好 `count` 张。"""
    duration = prepared["durationInFrames"]
    shots = timeline_shots(prepared)
    heroes = sorted((shot for shot in shots if shot["tier"] == "hero"),
                    key=lambda shot: shot["startFrame"])
    picks: list[int] = []
    # hero 的后段才是回报：土星的环在该段展开、土卫六进入画面，取 75% 处而不是正中。
    for frame in [round(shot["startFrame"] + (shot["endFrame"] - shot["startFrame"]) * 0.75)
                  for shot in heroes]:
        value = max(0, min(duration - 1, int(frame)))
        if value not in picks:
            picks.append(value)
    if len(picks) > count:
        stride = len(picks) / count
        picks = [picks[min(len(picks) - 1, int(index * stride))] for index in range(count)]
    step = duration / count
    extras = [0, duration - 1, *[round(step * (index + .5)) for index in range(count)]]
    for frame in extras:
        if len(picks) >= count:
            break
        value = max(0, min(duration - 1, int(frame)))
        if value not in picks:
            picks.append(value)
    return sorted(picks)


def sample_window(prepared: dict, seconds: int) -> tuple[int, int]:
    """样片窗口：优先覆盖第一个 hero 镜头，否则从片头取。"""
    duration = prepared["durationInFrames"]
    fps = prepared["fps"]
    shots = timeline_shots(prepared)
    heroes = sorted((shot for shot in shots if shot["tier"] == "hero"),
                    key=lambda shot: shot["startFrame"])
    start = heroes[0]["startFrame"] if heroes else 0
    length = min(seconds * fps, duration - start)
    if start == 0 and length == duration:
        length -= 1
    if length <= 0:
        raise M2VError("样片窗口超出成片时长")
    return start, start + length - 1


def timeline_shots(prepared: dict) -> list[dict]:
    """作品镜头使用幕内帧号，取点前换算成全片帧号。"""
    return [{**shot, "startFrame": scene.get("startFrame", 0) + shot["startFrame"],
             "endFrame": scene.get("startFrame", 0) + shot["endFrame"]}
            for scene in prepared["props"].get("compiledScenes", [])
            for shot in ((scene.get("content", {}).get("props") or {}).get("shots") or [])]


def sample_audio(prepared: dict, root: Path) -> tuple[bool, Path | None]:
    """返回是否应带声音及其准备音轨；空旁白/音床的作品保持无音轨。"""
    props = prepared["props"]
    soundtrack = props.get("soundtrack", {})
    has_sound_design = bool(soundtrack.get("music") or soundtrack.get("effects"))
    has_narration = any(scene.get("narrationSegments") for scene in props.get("compiledScenes", []))
    if not (has_sound_design or has_narration):
        return False, None
    segments = prepared.get("audio", {}).get("segments", [])
    if not segments:
        raise M2VError("有声作品缺少准备音轨，无法生成 look-dev 样片")
    return True, root / segments[0]["path"]


def native_stills(root: Path, prepared: dict, frames: list[int], work: Path, *, scale: int = STILL_SCALE) -> dict[tuple[str, int], Path]:
    """只保存选定帧，但从零连续推进每幕时钟；不触碰准备阶段的视频缓存。"""
    from playwright.sync_api import sync_playwright
    from m2v.types.general import code_scenes, media_assets
    props = prepared["props"]
    frame_config = {"width": prepared["width"], "height": prepared["height"], "subtitle": props["subtitle"]}
    media = media_assets.resolve(root)["media"]
    captured: dict[tuple[str, int], Path] = {}
    with sync_playwright() as pw:
        for index, scene in enumerate(props["compiledScenes"]):
            selected = [frame - scene["startFrame"] for frame in frames
                        if scene["startFrame"] <= frame < scene["endFrame"]]
            if not selected:
                continue
            directory = work / f"native-{index}"
            directory.mkdir()
            code_scenes.build_scene(root, scene, directory)
            config = code_scenes.scene_config(scene, frame_config, media)
            config["captureScale"] = scale
            code_scenes._capture(pw, root, directory, config, selected_frames=selected)
            for frame in selected:
                captured[(scene["id"], frame + scene["startFrame"])] = directory / f"frame-{frame:06d}.png"
    for frame in frames:
        if not any(key[1] == frame for key in captured):
            raise M2VError(f"lookdev 第 {frame} 帧不属于任何已准备场景")
    return captured


def still_props(prepared: dict, captured: dict, frame: int, media_base: str) -> dict:
    """仅为静帧保留当前活跃场景，避免未采样幕回放没有 mediaPath 的片段。

    静帧是单帧画面，其他幕的内容不会出现在这一帧里；把它们留在合成时间线上只会
    读取准备阶段尚未物化的 `mediaPath`。转场与字幕层仍由共享 composition 处理。
    """
    props = copy.deepcopy(prepared["props"])
    active = []
    for scene in props["compiledScenes"]:
        picture = captured.get((scene["id"], frame))
        if picture:
            scene["stillPath"] = "data:image/png;base64," + base64.b64encode(picture.read_bytes()).decode("ascii")
            active.append(scene)
    props["compiledScenes"] = active
    props["mediaBase"] = media_base
    return props


def contact_sheet(stills: list[Path], target: Path, columns: int = 2) -> Path:
    """把静帧拼成一张接触表；张数不足时按实际数量拼一行。"""
    if not stills:
        raise M2VError("没有静帧可拼接触表")
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = max(1, (len(stills) + columns - 1) // columns)
    with tempfile.TemporaryDirectory(prefix="lookdev-", dir=target.parent) as temporary:
        listing = Path(temporary) / "stills.txt"
        listing.write_text("".join(f"file '{path.as_posix()}'\n" for path in stills), encoding="utf-8")
        result = subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "concat", "-safe", "0",
                                 "-i", str(listing), "-vf", f"scale=960:-2,tile={columns}x{rows}",
                                 "-frames:v", "1", str(target)], capture_output=True, timeout=300)
    if result.returncode or not target.is_file():
        raise M2VError(f"接触表生成失败：{result.stderr.decode('utf-8', 'replace')[-800:]}")
    return target


def run(root: Path, project: dict, prepared: dict, *, stills: int = DEFAULT_STILLS,
        sample_seconds: int = DEFAULT_SAMPLE_SECONDS, still_scale: int = STILL_SCALE) -> dict:
    """渲染静帧、接触表与有声样片，返回清单并写入 `outputs/lookdev.json`。"""
    if still_scale not in (1, 2):
        raise M2VError("静帧采样尺度只能为1或2")
    if not MIN_SAMPLE_SECONDS <= sample_seconds <= MAX_SAMPLE_SECONDS:
        raise M2VError(f"样片长度必须是 {MIN_SAMPLE_SECONDS}～{MAX_SAMPLE_SECONDS} 秒")
    if not 1 <= stills <= 12:
        raise M2VError("静帧张数必须是 1～12")
    fps, width, height = prepared["fps"], prepared["width"], prepared["height"]
    outputs = root / "outputs/lookdev"
    outputs.mkdir(parents=True, exist_ok=True)
    entry = root / project["materials"]["storyboard"]
    has_audio, master = sample_audio(prepared, root)
    frames = still_frames(prepared, stills)
    start, end = sample_window(prepared, sample_seconds)
    from m2v.types.general.code_scenes import materialize
    sample_prepared = materialize(root, prepared, start, end + 1)
    timings = perf.StageTimings()
    # 画面里的代码片段按相对路径引用，必须像正式渲染那样由本地服务器提供作品根：
    # 少了这一步，composition 会去 bundle 的静态目录找片段并报 404。
    with LocalServer(root, cors=True) as server, \
            tempfile.TemporaryDirectory(prefix="m2v-lookdev-", dir=outputs) as temporary:
        work = Path(temporary)
        props_file = work / "props.json"
        props_file.write_text(json.dumps({**sample_prepared["props"], "mediaBase": server.base_url + "/"},
                                         ensure_ascii=False), encoding="utf-8")
        bundle = remotion.bundle(web_dir=remotion.web_dir(), out_dir=work / "bundle",
                                 storyboard_path=entry, content_root=root.parent,
                                 workspace_root=root.parent, cache=True)
        timings.record("bundle", bundle.build_seconds)
        captured = native_stills(root, prepared, frames, work, scale=still_scale)
        rendered: list[Path] = []
        for frame in frames:
            # 原生 PNG 内联到临时 props，避免暴露源码或扩大 HTTP 服务范围。
            still_file = work / "still-props.json"
            still_file.write_text(json.dumps(still_props(prepared, captured, frame, server.base_url + "/"),
                                            ensure_ascii=False), encoding="utf-8")
            target = outputs / f"still-{frame:06d}.png"
            remotion.render_still(web_dir=remotion.web_dir(), bundle_dir=bundle.path, props=still_file,
                                  out=target, frame=frame, scale=still_scale, composition_id="ArticleExplainer")
            rendered.append(target)
        sheet = contact_sheet(rendered, outputs / "contact-sheet.png")
        silent = work / "sample-silent.mp4"
        sample = outputs / "sample.mp4"
        frames_spec = {"value": f"{start}-{end}"}
        def confirm(metadata):
            expected = (fps, width, height, prepared["durationInFrames"])
            actual = (metadata.fps, metadata.width, metadata.height, metadata.duration_in_frames)
            if expected != actual:
                raise M2VError(f"look-dev 元数据不匹配：{actual}，期望 {expected}")
            return {"out": str(silent), "crf": 16, "preset": "medium", "frames": frames_spec["value"],
                    "scale": 1, "concurrency": 1, "progressTotal": end - start + 1}
        remotion.render_session(web_dir=remotion.web_dir(), bundle_dir=bundle.path, props=props_file,
                                composition_id="ArticleExplainer", on_metadata=confirm, timeout_s=3600,
                                on_line=remotion.progress_handler(end - start + 1))
        if master:
            audio.mux(silent, master, sample, (end - start + 1) / fps, start=start / fps)
        else:
            silent.replace(sample)
    manifest = {"schemaVersion": 1, "preparedFingerprint": prepared["preparedFingerprint"],
                "stills": [path.relative_to(root).as_posix() for path in rendered],
                "contactSheet": sheet.relative_to(root).as_posix(),
                "sample": sample.relative_to(root).as_posix(),
                "sampleFrames": [start, end], "sampleSeconds": round((end - start + 1) / fps, 2),
                "sampleAudio": "present" if has_audio else "none",
                "stillScale": still_scale, "stillSize": [width * still_scale, height * still_scale],
                "stillCapture": "native-code-png-v1"}
    _write_json(root / "outputs/lookdev.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="m2v lookdev", description="通用关键画面与风险样片")
    parser.add_argument("--project", required=True)
    parser.add_argument("--stills", type=int, default=DEFAULT_STILLS)
    parser.add_argument("--sample-seconds", type=int, default=DEFAULT_SAMPLE_SECONDS)
    parser.add_argument("--still-scale", type=int, choices=(1, 2), default=STILL_SCALE)
    args = parser.parse_args(argv)
    from m2v.types.general.explainer_render import current
    root, manifest = load_project(args.project)
    if manifest["type"] != "general":
        raise M2VError("m2v lookdev 仅适用于 general 作品")
    prepared = current(root, manifest)
    result = run(root, manifest, prepared, stills=args.stills, sample_seconds=args.sample_seconds, still_scale=args.still_scale)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


def keyframes(root: Path, project: dict, prepared: dict) -> dict:
    """直接采集代表静帧，不录制整幕视频。"""
    frames = still_frames(prepared, 3)
    outputs = root / "outputs/keyframes"
    outputs.mkdir(parents=True, exist_ok=True)
    with LocalServer(root, cors=True) as server, tempfile.TemporaryDirectory(dir=outputs) as temporary:
        work = Path(temporary)
        captured = native_stills(root, prepared, frames, work)
        bundle = remotion.bundle(web_dir=remotion.web_dir(), out_dir=work / "bundle",
            storyboard_path=root / project["materials"]["storyboard"], content_root=root.parent,
            workspace_root=root.parent, cache=True)
        files = []
        for frame in frames:
            props = work / "props.json"
            props.write_text(json.dumps(still_props(prepared, captured, frame, server.base_url + "/"), ensure_ascii=False), encoding="utf-8")
            target = outputs / f"still-{frame:06d}.png"
            remotion.render_still(web_dir=remotion.web_dir(), bundle_dir=bundle.path, props=props,
                out=target, frame=frame, scale=STILL_SCALE, composition_id="ArticleExplainer")
            files.append(target)
        contact_sheet(files, outputs / "contact-sheet.png")
    result = {"preparedFingerprint": prepared["preparedFingerprint"], "frames": frames,
              "files": [str(p.relative_to(root)) for p in files]}
    _write_json(root / "outputs/keyframes.json", result)
    return result
