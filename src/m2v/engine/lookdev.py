"""通用关键画面与风险样片；采样尺寸和长度按内容选择。"""
from __future__ import annotations

import argparse
import base64
import copy
import json
import math
import re
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


#: 拼图默认列数与单次最多取帧数：列数按张数选，避免竖向堆成一条。
SHEET_COLUMNS = 4
MAX_SHEET_FRAMES = 24
#: 同帧一致性阈值。与 remotion-renderer 规格的既定口径一致，不另立标准。
DETERMINISM_PSNR = 60.0
DEFAULT_MOTION_FRAMES = 12


def seconds_to_frame(seconds: float, fps: int, duration: int) -> int:
    """秒换算为全片帧号；只做换算，越界由 `check_frames` 判定。

    采点用四舍五入而不是向下取整：作者按秒指定时刻，期望的是最近的那一帧。
    """
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or not math.isfinite(seconds):
        raise M2VError(f"时刻必须是有限数值：{seconds!r}")
    frame = round(seconds * fps)
    return max(0, min(duration - 1, frame))


def scene_windows(prepared: dict) -> list[tuple[int, int]]:
    """各幕的全片帧窗口，左闭右开。"""
    return [(scene["startFrame"], scene["endFrame"])
            for scene in prepared["props"].get("compiledScenes", [])]


def _all_pure(prepared: dict, frames: list[int]) -> bool:
    """选中的帧全部落在声明的 pure-time 场景内时才允许倒序验证。"""
    scenes = [scene for scene in prepared["props"].get("compiledScenes", [])
              if any(scene["startFrame"] <= frame < scene["endFrame"] for frame in frames)]
    if not scenes:
        return False
    return all(((scene.get("content", {}).get("props") or {}).get("capture") or {}).get("mode") == "pure-time"
               for scene in scenes)


def check_frames(prepared: dict, frames: list[int]) -> None:
    """在启动浏览器前判定帧号合法且归属于某一幕。

    `native_stills()` 的归属校验在全部采集完成之后才做，非法帧会先白跑一遍
    浏览器；图省事复用那条校验等于把几分钟浪费在注定失败的采集上。
    """
    if not frames:
        raise M2VError("没有可采集的时刻")
    duration = prepared["durationInFrames"]
    windows = scene_windows(prepared)
    for frame in frames:
        if not isinstance(frame, int) or frame < 0 or frame >= duration:
            raise M2VError(f"帧 {frame} 超出全片范围 0～{duration - 1}")
        if not any(start <= frame < end for start, end in windows):
            raise M2VError(f"帧 {frame} 不属于任何已准备场景")


def uniform_frames(start: int, end: int, count: int) -> list[int]:
    """区间内均匀取帧，两端都包含。单帧区间返回该帧本身。"""
    if count < 1:
        raise M2VError("帧数至少为 1")
    if end < start:
        raise M2VError(f"区间终点 {end} 早于起点 {start}")
    if start == end or count == 1:
        return [start]
    span = end - start
    return sorted({start + round(span * index / (count - 1)) for index in range(count)})


def sheet_frames(spec: list[str], prepared: dict) -> list[int]:
    """`--sheet` 参数解析：单个整数按全片均匀取帧，否则按秒逐个换算。"""
    if not spec:
        raise M2VError("--sheet 需要至少一个时刻或帧数")
    fps, duration = prepared["fps"], prepared["durationInFrames"]
    if len(spec) == 1 and re.fullmatch(r"\d+", spec[0]):
        count = int(spec[0])
        if not 1 <= count <= MAX_SHEET_FRAMES:
            raise M2VError(f"均匀取帧数必须是 1～{MAX_SHEET_FRAMES}")
        # 用 count+1 个等分点的间隔中值，末尾保留一帧余量，避免落在最后一帧之外。
        step = duration / count
        return sorted({min(duration - 1, int(step * (index + .5))) for index in range(count)})
    frames = []
    for item in spec:
        try:
            value = float(item)
        except ValueError as exc:
            raise M2VError(f"时刻必须是秒数：{item}") from exc
        # 负时刻静默夹到 0 会让作者以为自己看到的是别的时刻；宁可报错。
        if not math.isfinite(value) or value < 0 or value * fps > duration - 1:
            raise M2VError(f"时刻 {item} 超出成片时长 0～{(duration - 1) / fps:.3f} 秒")
        frames.append(seconds_to_frame(value, fps, duration))
    # 重复时刻只采一次，但保留顺序无关的去重结果。
    return sorted(set(frames))


def motion_frames(start_seconds: float, end_seconds: float, count: int, prepared: dict) -> list[int]:
    """`--motion` 参数解析：把起止秒换算成帧后均匀取帧。"""
    fps, duration = prepared["fps"], prepared["durationInFrames"]
    if not 1 <= count <= MAX_SHEET_FRAMES:
        raise M2VError(f"区间帧数必须是 1～{MAX_SHEET_FRAMES}")
    raw_start = start_seconds * fps
    raw_end = end_seconds * fps
    if not (math.isfinite(raw_start) and math.isfinite(raw_end)):
        raise M2VError("区间时刻必须是有限数值")
    if raw_end < raw_start:
        raise M2VError(f"区间终点 {end_seconds} 秒早于起点 {start_seconds} 秒")
    if not 0 <= raw_start <= duration - 1 or not 0 <= raw_end <= duration - 1:
        raise M2VError(f"区间 {start_seconds}～{end_seconds} 秒超出成片时长 0～{(duration - 1) / fps:.3f} 秒")
    return uniform_frames(round(raw_start), round(raw_end), count)


def resolve_event_selectors(prepared: dict, selectors: list[str], *, before: int, after: int,
                            hold: int = 0) -> dict:
    """把幕内事件解析成作者声明的取证窗口。

    事件在 prepare 阶段已解析为幕内帧和全片帧；这里不重新计算时间，只按
    `before/at/after/hold` 四点取帧。作者必须显式声明前后窗口，不套用全片统一间隔。
    """
    for name, value in (("before", before), ("after", after), ("hold", hold)):
        if type(value) is not int or value < 0:
            raise M2VError(f"事件取点的 {name} 必须是非负整数帧")
    if not selectors:
        raise M2VError("事件取点至少需要一个 --event")
    scenes = {scene["id"]: scene for scene in prepared["props"].get("compiledScenes", [])}
    events = prepared["props"].get("resolvedEvents") or []
    if not events:
        raise M2VError("当前准备记录没有幕内事件；请确认作品已声明 events 并重新 prepare")

    selected, seen = [], set()
    for selector in selectors:
        if not isinstance(selector, str) or not selector.strip():
            raise M2VError("事件选择器必须是非空文字")
        if ":" in selector:
            scene_id, event_id = selector.split(":", 1)
            if not scene_id or not event_id:
                raise M2VError(f"事件选择器必须为 sceneId:eventId：{selector!r}")
            matches = [event for event in events
                       if event["sceneId"] == scene_id and event["id"] == event_id]
        else:
            matches = [event for event in events if event["id"] == selector]
            if len(matches) > 1:
                scenes_with = "、".join(sorted({event["sceneId"] for event in matches}))
                raise M2VError(f"事件 ID {selector!r} 在多个幕中出现（{scenes_with}）；"
                               "请用 sceneId:eventId 指定")
        if not matches:
            raise M2VError(f"未找到幕内事件：{selector!r}")
        event = matches[0]
        key = (event["sceneId"], event["id"])
        if key not in seen:
            seen.add(key)
            selected.append(event)

    frames: dict[int, list[str]] = {}
    resolved = []
    for event in selected:
        scene = scenes.get(event["sceneId"])
        if scene is None:
            raise M2VError(f"事件 {event['sceneId']}:{event['id']} 所属的幕不在已准备场景中")
        duration = scene["durationInFrames"]
        phases = []
        for name, offset, suffix in (("before", -before, f"b{before}"),
                                     ("at", 0, "at"),
                                     ("after", after, f"a{after}"),
                                     ("hold", after + hold, f"h{hold}")):
            if name == "hold" and hold <= 0:
                continue
            local = event["frame"] + offset
            if not 0 <= local < duration:
                raise M2VError(
                    f"事件 {event['sceneId']}:{event['id']} 的 {name} 帧 {local} "
                    f"超出本幕范围 0～{duration - 1}；请缩小 --before/--after/--hold")
            global_frame = scene["startFrame"] + local
            label = f"{event['sceneId']}.{event['id']}.{suffix}"
            phases.append({"phase": name, "offsetFrames": offset, "localFrame": local,
                           "globalFrame": global_frame, "label": label})
            frames.setdefault(global_frame, []).append(label)
        resolved.append({**event, "phases": phases})

    warnings = []
    by_scene: dict[str, list[dict]] = {}
    for event in selected:
        by_scene.setdefault(event["sceneId"], []).append(event)
    if before + after > 0:
        for scene_id, group in by_scene.items():
            group = sorted(group, key=lambda item: item["frame"])
            for left, right in zip(group, group[1:]):
                gap = right["frame"] - left["frame"]
                if gap < before + after:
                    warnings.append(
                        f"事件簇：{scene_id}:{left['id']} 与 {right['id']} 相隔 {gap} 帧，"
                        f"小于 before+after={before + after}；单事件窗口会覆盖相邻事件，"
                        "建议一次查看整个簇")
    ordered = sorted(frames)
    labels = [".".join(dict.fromkeys(frames[frame])) for frame in ordered]
    return {"frames": ordered, "labels": labels, "events": resolved, "warnings": warnings}


def sheet_columns(count: int) -> int:
    """按张数选列数：短拼图少列，长拼图多列，避免单列堆成一条。"""
    if count <= 2:
        return count or 1
    if count <= 6:
        return 3
    return SHEET_COLUMNS


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
            config = code_scenes.scene_config(scene, frame_config, media, fps=prepared["fps"])
            config["captureScale"] = scale
            try:
                code_scenes._capture(pw, root, directory, config, selected_frames=selected, verify_frames=0)
            except M2VError as exc:
                # 多场景采样共用一个命令；保留原始原因，同时指出需要修改的场景入口。
                raise M2VError(f"lookdev 场景 {scene['id']}（{scene['content']['entry']}）：{exc}") from exc
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


def contact_sheet(stills: list[Path], target: Path, columns: int = 2,
                  labels: list[str] | None = None) -> Path:
    """把静帧拼成一张接触表；张数不足时按实际数量拼一行。

    给了 `labels` 就在每格左上角标注。标注只用数字、字母与点：冒号、逗号和
    空格都要在 ffmpeg 的 filter 里转义，服务器也未必有中文字体，一旦解析失败
    整条拼图命令都会失败，而失败原因与拼图本身无关。

    标注必须**逐张先打完再拼**：tile 之前的滤镜链对每一帧都执行，三组 drawtext
    叠在同一位置时只有最后一组可见，拼出来会变成每一格都标着同一个时刻。
    """
    if not stills:
        raise M2VError("没有静帧可拼接触表")
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = max(1, (len(stills) + columns - 1) // columns)
    with tempfile.TemporaryDirectory(prefix="lookdev-", dir=target.parent) as temporary:
        work = Path(temporary)
        tiles = list(stills)
        if labels:
            if len(labels) < len(stills):
                raise M2VError("接触表标注少于静帧张数")
            labelled = []
            for index, path in enumerate(stills):
                text = re.sub(r"[^0-9A-Za-z.]", "-", labels[index]).strip("-") or str(index)
                out = work / f"labelled-{index:03d}.png"
                result = subprocess.run(
                    [get_ffmpeg_exe(), "-y", "-v", "error", "-i", str(path), "-vf",
                     f"drawtext=text='{text}':x=8:y=8:fontsize=28:fontcolor=white:"
                     "box=1:boxcolor=black@0.55:boxborderw=6", "-frames:v", "1", str(out)],
                    capture_output=True, timeout=300)
                if result.returncode or not out.is_file():
                    raise M2VError(f"接触表标注失败：{result.stderr.decode('utf-8', 'replace')[-800:]}")
                labelled.append(out)
            tiles = labelled
        listing = work / "stills.txt"
        listing.write_text("".join(f"file '{path.as_posix()}'\n" for path in tiles), encoding="utf-8")
        result = subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "concat", "-safe", "0",
                                 "-i", str(listing), "-vf", f"scale=960:-2,tile={columns}x{rows}",
                                 "-frames:v", "1", str(target)], capture_output=True, timeout=300)
    if result.returncode or not target.is_file():
        raise M2VError(f"接触表生成失败：{result.stderr.decode('utf-8', 'replace')[-800:]}")
    return target


def psnr(first: Path, second: Path) -> float:
    """两张同尺寸图的 PSNR；完全相同时为无穷大。"""
    from m2v.engine import images
    return images.psnr(first, second)


def _render_stills(root: Path, project: dict, prepared: dict, frames: list[int],
                   scale: int, *, into: Path | None = None) -> list[Path]:
    """采集并合成指定帧的静帧，返回按帧顺序的 PNG 路径。

    复用 `keyframes()` 的骨架：重建场景 → 只截选定帧 → 交给共享 composition
    合成字幕与转场。不调 `materialize`，不录样片，因此比 `run()` 轻。
    `into` 用于把两次独立采集分开落盘，避免后者覆盖前者。
    """
    outputs = into or (root / "outputs/lookdev")
    outputs.mkdir(parents=True, exist_ok=True)
    produced: dict[int, Path] = {}
    with LocalServer(root, cors=True) as server, \
            tempfile.TemporaryDirectory(prefix="m2v-sheet-", dir=root / "outputs/lookdev") as temporary:
        work = Path(temporary)
        native = work / "native"
        native.mkdir()
        captured = native_stills(root, prepared, frames, native, scale=scale)
        bundle = remotion.bundle(web_dir=remotion.web_dir(), out_dir=work / "bundle",
                                 storyboard_path=root / project["materials"]["storyboard"],
                                 content_root=root.parent, workspace_root=root.parent, cache=True)
        for frame in frames:
            props_file = work / f"props-{frame:06d}.json"
            props_file.write_text(json.dumps(still_props(prepared, captured, frame, server.base_url + "/"),
                                             ensure_ascii=False), encoding="utf-8")
            target = outputs / f"still-{frame:06d}.png"
            remotion.render_still(web_dir=remotion.web_dir(), bundle_dir=bundle.path,
                                  props=props_file, out=target, frame=frame, scale=scale,
                                  composition_id="ArticleExplainer")
            produced[frame] = target
    return [produced[frame] for frame in frames]


def _building_frames(args, prepared: dict) -> list[int]:
    """建筑类型的代表帧：秒数与帧号都按准备记录换算。"""
    fps = prepared["fps"]
    duration = prepared["durationInFrames"]
    if args.sheet:
        seconds: list[float] = []
        for item in args.sheet:
            try:
                seconds.append(float(item))
            except (TypeError, ValueError):
                raise M2VError(f"--sheet 需要秒数或单个张数，收到：{item}") from None
        if len(args.sheet) == 1 and float(args.sheet[0]).is_integer() and float(args.sheet[0]) <= 24:
            count = int(float(args.sheet[0]))
            return [round(index * (duration - 1) / max(1, count - 1)) for index in range(count)]
        return [seconds_to_frame(value, fps, duration) for value in seconds]
    if args.det:
        return [round(index * (duration - 1) / 7) for index in range(8)]
    return [round(duration * ratio) for ratio in (0.25, 0.5, 0.75, 0.99)]


def _building_preview(root: Path, prepared: dict, *, mode: str, frames: list[int],
                      still_scale: int, labels: list[str] | None = None) -> dict:
    """建筑类型没有 code scene 采集链：直接按准备 props 渲染原生静帧。"""
    outputs = root / "outputs/lookdev"
    outputs.mkdir(parents=True, exist_ok=True)
    props = prepared["props"]
    composition = prepared["compositionId"]
    web = remotion.web_dir()
    fps = prepared["fps"]
    if labels is None:
        labels = [f"{index + 1}-{frame / fps:.2f}s-f{frame}" for index, frame in enumerate(frames)]
    first_dir = outputs / "determinism-first"
    second_dir = outputs / "determinism-second"

    def capture(order: list[int], target: Path) -> dict[int, Path]:
        target.mkdir(parents=True, exist_ok=True)
        produced: dict[int, Path] = {}
        with tempfile.TemporaryDirectory(prefix="building-lookdev-", dir=outputs) as temporary:
            work = Path(temporary)
            props_file = work / "props.json"
            props_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
            bundle = remotion.bundle(
                web_dir=web, out_dir=work / "bundle",
                storyboard_path=root / "construction.json",
                content_root=root.parent, workspace_root=root.parent, cache=True)
            for frame in order:
                out = target / f"still-{frame:06d}.png"
                remotion.render_still(web_dir=web, bundle_dir=bundle.path, props=props_file,
                                      out=out, frame=frame, scale=still_scale,
                                      composition_id=composition)
                produced[frame] = out
        return produced

    if mode == "det":
        first_dir.mkdir(parents=True, exist_ok=True)
        second_dir.mkdir(parents=True, exist_ok=True)
        first = capture(frames, first_dir)
        second = capture(list(reversed(frames)), second_dir)
        rows, failed = [], []
        for frame in frames:
            path, twin = first[frame], second[frame]
            if _image_size(path) != _image_size(twin):
                raise M2VError(f"帧 {frame} 两次采集尺寸不一致；无法比较")
            value = psnr(path, twin)
            ok = value >= DETERMINISM_PSNR
            rows.append({"frame": frame, "time": round(frame / fps, 3),
                         "psnr": None if math.isinf(value) else round(value, 2), "pass": ok})
            if not ok:
                failed.append({"frame": frame, "time": round(frame / fps, 3),
                               "psnr": round(value, 2)})
        manifest = {"schemaVersion": 1, "preparedFingerprint": prepared["preparedFingerprint"],
                    "mode": "det", "stillScale": still_scale, "threshold": DETERMINISM_PSNR,
                    "frames": frames, "results": rows, "failed": failed,
                    "first": first_dir.relative_to(root).as_posix(),
                    "second": second_dir.relative_to(root).as_posix(),
                    "secondOrder": "reverse", "stillCapture": "native-code-png-v1"}
        _write_json(root / "outputs/lookdev.json", manifest)
        return manifest

    produced = capture(frames, outputs)
    stills = [produced[frame] for frame in frames]
    columns = sheet_columns(len(stills))
    sheet = contact_sheet(stills, outputs / f"{mode}.png", columns=columns, labels=labels)
    manifest = {"schemaVersion": 1, "preparedFingerprint": prepared["preparedFingerprint"],
                "mode": mode, "stillScale": still_scale, "frames": frames,
                "times": [round(frame / fps, 3) for frame in frames], "labels": labels,
                "stills": [path.relative_to(root).as_posix() for path in stills],
                "sheet": sheet.relative_to(root).as_posix(), "columns": columns,
                "stillCapture": "native-code-png-v1"}
    _write_json(root / "outputs/lookdev.json", manifest)
    return manifest


def preview(root: Path, project: dict, prepared: dict, *, mode: str, frames: list[int],
            still_scale: int = STILL_SCALE, labels: list[str] | None = None,
            extra: dict | None = None) -> dict:
    """取点预览：拼图、区间拼图、同帧一致性与事件取证。产物落 `outputs/lookdev/`。"""
    if still_scale not in (1, 2):
        raise M2VError("静帧采样尺度只能为1或2")
    check_frames(prepared, frames)
    fps = prepared["fps"]
    if labels is None:
        labels = [f"{index + 1}-{frame / fps:.2f}s-f{frame}" for index, frame in enumerate(frames)]
    if len(labels) != len(frames):
        raise M2VError("接触表标注数量与取帧数量不一致")
    outputs = root / "outputs/lookdev"
    outputs.mkdir(parents=True, exist_ok=True)
    if mode == "det":
        return _determinism(root, project, prepared, frames, still_scale, outputs)
    produced = _render_stills(root, project, prepared, frames, still_scale)
    columns = sheet_columns(len(produced))
    sheet = contact_sheet(produced, outputs / f"{mode}.png", columns=columns, labels=labels)
    manifest = {"schemaVersion": 1, "preparedFingerprint": prepared["preparedFingerprint"],
                "mode": mode, "stillScale": still_scale, "frames": frames,
                "times": [round(frame / fps, 3) for frame in frames],
                "labels": labels,
                "stills": [path.relative_to(root).as_posix() for path in produced],
                "sheet": sheet.relative_to(root).as_posix(), "columns": columns,
                "stillCapture": "native-code-png-v1"}
    if extra:
        manifest.update(extra)
    _write_json(root / "outputs/lookdev.json", manifest)
    return manifest


def _determinism(root: Path, project: dict, prepared: dict, frames: list[int],
                 still_scale: int, outputs: Path) -> dict:
    """两次独立采集同一批帧，逐帧比较 PSNR；尺寸不一致时明确失败。

    两次都是完整会话：各自从第 0 帧连续推进到目标帧，语义等于「同帧重复
    渲染是否一致」。运行时拒绝跳帧与倒序，所以不能靠乱序重截实现。
    """
    first_dir = outputs / "determinism-first"
    second_dir = outputs / "determinism-second"
    for directory in (first_dir, second_dir):
        directory.mkdir(parents=True, exist_ok=True)
    rows, failed = [], []
    # pure 场景可以乱序直达：第二遍按倒序采集，正好验证「同帧与到达顺序无关」。
    # 非 pure 场景的顺序采集不受 id 列表顺序影响（内部仍从 0 推进），不会回归。
    second_frames = list(reversed(frames)) if _all_pure(prepared, frames) else list(frames)
    first = _render_stills(root, project, prepared, frames, still_scale, into=first_dir)
    second = _render_stills(root, project, prepared, second_frames, still_scale, into=second_dir)
    first_by_frame = dict(zip(frames, first))
    second_by_frame = dict(zip(second_frames, second))
    for frame in frames:
        path, twin = first_by_frame[frame], second_by_frame[frame]
        if _image_size(path) != _image_size(twin):
            raise M2VError(f"帧 {frame} 两次采集尺寸不一致：{_image_size(path)} 与 {_image_size(twin)}；"
                           "无法比较，可能是采集密度或后期设置不同")
        value = psnr(path, twin)
        ok = value >= DETERMINISM_PSNR
        rows.append({"frame": frame, "time": round(frame / prepared["fps"], 3),
                     "psnr": None if math.isinf(value) else round(value, 2), "pass": ok})
        if not ok:
            failed.append({"frame": frame, "time": round(frame / prepared["fps"], 3),
                           "psnr": round(value, 2)})
    manifest = {"schemaVersion": 1, "preparedFingerprint": prepared["preparedFingerprint"],
                "mode": "det", "stillScale": still_scale, "threshold": DETERMINISM_PSNR,
                "frames": frames, "results": rows, "failed": failed,
                "first": first_dir.relative_to(root).as_posix(),
                "second": second_dir.relative_to(root).as_posix(),
                "secondOrder": "reverse" if second_frames != frames else "forward",
                "stillCapture": "native-code-png-v1"}
    _write_json(root / "outputs/lookdev.json", manifest)
    return manifest


def _image_size(path: Path) -> tuple[int, int]:
    """读 PNG 的宽高；不是 PNG 时返回空，交给调用方判失败。"""
    head = path.read_bytes()[:24]
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        raise M2VError(f"静帧不是 PNG：{path}")
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


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


def _reject_conflicting_modes(args) -> None:
    """取点模式与代表静帧互斥，同一调用只能声明一种。"""
    event = getattr(args, "event", None)
    declared = [name for name, value in (("--sheet", args.sheet), ("--motion", args.motion),
                                         ("--det", args.det), ("--event", event)) if value]
    if len(declared) > 1:
        raise M2VError(f"{'、'.join(declared)} 互斥，同一调用只能声明一种取点模式")
    if declared and args.stills is not None:
        raise M2VError(f"{declared[0]} 与 --stills 互斥；取点模式不使用代表静帧张数")
    if declared and args.sample_seconds != DEFAULT_SAMPLE_SECONDS:
        raise M2VError(f"{declared[0]} 与 --sample-seconds 互斥；取点模式不生成样片")
    before = getattr(args, "before", None)
    after = getattr(args, "after", None)
    hold = getattr(args, "hold", 0)
    if not event and (before is not None or after is not None or hold):
        raise M2VError("--before/--after/--hold 只能与 --event 一起使用")
    if event and (before is None or after is None):
        raise M2VError("事件取点必须同时声明 --before 与 --after；窗口由作者按事件决定")


def _preview_frames(args, prepared: dict) -> list[int]:
    """把三种模式的参数换成全片帧号；`--motion` 允许第三个参数作帧数。"""
    if args.det:
        # 自检不指定时刻时覆盖全片均匀若干帧，让不一致更容易暴露。
        return sheet_frames([str(min(MAX_SHEET_FRAMES, 8))], prepared)
    if args.sheet:
        return sheet_frames([str(item) for item in args.sheet], prepared)
    values = list(args.motion or [])
    if len(values) not in (2, 3):
        raise M2VError("--motion 需要起点、终点秒，可选再给一个帧数")
    count = int(values[2]) if len(values) == 3 else DEFAULT_MOTION_FRAMES
    return motion_frames(values[0], values[1], count, prepared)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="m2v lookdev", description="通用关键画面与风险样片")
    parser.add_argument("--project", required=True)
    parser.add_argument("--stills", type=int, default=None,
                        help=f"代表静帧张数 1～12；省略时为 {DEFAULT_STILLS}，给出任一取点模式时不用")
    parser.add_argument("--sample-seconds", type=int, default=DEFAULT_SAMPLE_SECONDS)
    parser.add_argument("--still-scale", type=int, choices=(1, 2), default=STILL_SCALE)
    parser.add_argument("--sheet", nargs="+", metavar="TIME",
                        help="按时刻（秒）拼一张接触表；给单个整数时按全片均匀取这么多帧")
    parser.add_argument("--motion", nargs="+", metavar="TIME", type=float,
                        help="区间起止秒，可再给一个帧数；均匀取帧拼一张看转场")
    parser.add_argument("--det", action="store_true",
                        help=f"同帧一致性自检：两次独立采集比 PSNR（阈值 {DETERMINISM_PSNR:g} dB）")
    parser.add_argument("--event", action="append", metavar="SCENE:EVENT",
                        help="按幕内事件取点；可重复；需同时声明 --before/--after（帧，非秒）")
    parser.add_argument("--before", type=int, metavar="FRAMES", help="事件发生前取帧数（帧）")
    parser.add_argument("--after", type=int, metavar="FRAMES", help="事件发生后取帧数（帧）")
    parser.add_argument("--hold", type=int, default=0, metavar="FRAMES",
                        help="结果停留结束帧相对事件后段的额外帧数")
    args = parser.parse_args(argv)
    _reject_conflicting_modes(args)
    from m2v.types.general.explainer_render import current
    root, manifest = load_project(args.project)
    if manifest["type"] == "building-construction":
        from m2v.core.project import load_current_prepared
        if args.event or args.motion:
            raise M2VError("建筑类型暂不支持 --event/--motion；请用 --sheet 秒数取代表帧")
        prepared = load_current_prepared(root, manifest)
        frames = _building_frames(args, prepared)
        mode = "det" if args.det else "sheet"
        result = _building_preview(root, prepared, mode=mode, frames=frames,
                                   still_scale=args.still_scale)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.det and result["failed"]:
            return 1
        return 0
    if manifest["type"] != "general":
        raise M2VError("m2v lookdev 仅适用于 general 与 building-construction 作品")
    prepared = current(root, manifest)
    if args.event:
        resolved = resolve_event_selectors(prepared, args.event, before=args.before,
                                           after=args.after, hold=args.hold)
        result = preview(root, manifest, prepared, mode="event", frames=resolved["frames"],
                         still_scale=args.still_scale, labels=resolved["labels"],
                         extra={"events": resolved["events"],
                                "eventWarnings": resolved["warnings"]})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.sheet or args.motion or args.det:
        frames = _preview_frames(args, prepared)
        mode = "det" if args.det else ("motion" if args.motion else "sheet")
        result = preview(root, manifest, prepared, mode=mode, frames=frames, still_scale=args.still_scale)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.det and result["failed"]:
            # 有帧不一致时以非零退出码结束，便于脚本判断；这不是导出门禁。
            return 1
        return 0
    result = run(root, manifest, prepared, stills=args.stills or DEFAULT_STILLS,
                 sample_seconds=args.sample_seconds, still_scale=args.still_scale)
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
