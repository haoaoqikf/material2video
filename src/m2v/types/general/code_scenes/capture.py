"""通用 v8 代码场景的逐帧采集、片段缓存与编码验收。

这里只负责「把作品代码录成片段并留证」；入口校验、录制配置与静态模块构建在
`config.py`，本模块单向依赖它。
"""
from __future__ import annotations

import base64
import json
import logging
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from m2v.core.video_config import FPS
from m2v.core import security
from m2v.engine import audio
from m2v.engine.http_server import LocalServer
from .config import WEB, build_scene, digest, implementation_inputs, media_files, require_cinematic_dependencies, scene_config, validate_entry


READY_TIMEOUT_MS = 30000


logger = logging.getLogger(__name__)


def materialize(root: Path, prepared: dict, start: int, end: int) -> dict:
    """只录制与半开全片窗口相交的场景，保留原始时间轴和转场。"""
    import copy
    from .. import media_assets
    from m2v.engine import frames
    result = copy.deepcopy(prepared)
    frame = frames.spec(prepared["width"], prepared["height"])
    media = media_assets.resolve(root)
    selected = []
    for scene in result["props"]["compiledScenes"]:
        first = max(start, scene["startFrame"]) - scene["startFrame"]
        last = min(end, scene["endFrame"]) - scene["startFrame"]
        if first >= last:
            continue
        scene["mediaPath"] = record(root, scene, {}, frame=frame, media=media["media"],
            media_digest=media["digest"],
            capture_range=(first, last))
        scene["mediaStartFrame"] = first
        scene["mediaDurationFrames"] = last - first
        selected.append(scene)
    result["props"]["compiledScenes"] = selected
    return result


def record(root: Path, scene: dict, inputs: dict[str, str], *, frame: dict, media: dict, media_digest: str,
           capture_range: tuple[int, int] | None = None) -> str:
    """构建可达源码，缓存有效时不启动浏览器；画幅、媒体映射与统一契约都进缓存键。"""
    from playwright.sync_api import sync_playwright
    content = scene["content"]
    require_cinematic_dependencies()
    validate_entry(root, content.get("entry"), content.get("props", {}))
    width, height = frame["width"], frame["height"]
    cache = root / "outputs/code-cache"
    cache.mkdir(parents=True, exist_ok=True)
    config = scene_config(scene, frame, media)
    first, last = capture_range or (0, config["durationInFrames"])
    if not 0 <= first < last <= config["durationInFrames"]:
        raise M2VError("场景采集范围越界")
    with tempfile.TemporaryDirectory(prefix="code-", dir=cache) as temporary:
        work = Path(temporary)
        source_inputs = build_scene(root, scene, work)
        inputs.update(source_inputs)
        inputs["codeMedia"] = media_digest
        with sync_playwright() as pw:
            browser_version = pw.chromium.executable_path
            executable = Path(browser_version)
            key = fingerprint({"config": config, "media": media_digest, "sources": source_inputs,
                               "implementation": implementation_inputs(),
                               "browser": digest(executable), "size": [width, height], "capture": "fixed-clock-png-444-v5"})
            output = cache / f"{key}-{first}-{last}.mp4"
            receipt = output.with_suffix(".json")
            if _valid_clip(output, receipt):
                logger.info("代码场景 %s 复用录制缓存", scene["id"])
            else:
                # 已检查的区间原样复用，只采集缺口；不能为补齐整幕再截图一次已有帧。
                accepted = _cached_ranges(cache, key, first, last)
                pieces = []
                cursor = first
                for begin, finish, clip in [*accepted, (last, last, None)]:
                    if begin > cursor:
                        gap = work / f"gap-{cursor}"
                        gap.mkdir()
                        shutil.copyfile(work / "scene.js", gap / "scene.js")
                        target = cache / f"{key}-{cursor}-{begin}.mp4"
                        logger.info("代码场景 %s 采集缺口 %d～%d", scene["id"], cursor, begin)
                        _capture(pw, root, gap, config, selected_frames=list(range(cursor, begin)))
                        _encode(gap, target, begin-cursor, width, height, start_frame=cursor,
                                supersample=int((config.get("motion") or {}).get("supersample", 1)))
                        _clip_receipt(target, cursor, begin)
                        pieces.append(target)
                    if clip is not None:
                        pieces.append(clip)
                    cursor = finish
                if len(pieces) == 1 and pieces[0] == output:
                    pass
                else:
                    listing = work / "concat.txt"
                    listing.write_text("".join("file '" + str(p.resolve()).replace("\\", "/").replace("'", "'\\''") + "'\n" for p in pieces), encoding="utf-8")
                    combined = work / "combined.mp4"
                    audio.ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(combined)])
                    _verify_clip(combined, last-first)
                    security.deliver(combined, output)
                _clip_receipt(output, first, last)
        relative = output.relative_to(root).as_posix()
        inputs["file:" + relative] = digest(output)
        return relative


def _valid_clip(video: Path, receipt: Path) -> bool:
    try:
        data = json.loads(receipt.read_text(encoding="utf-8"))
        return video.is_file() and data.get("sha256") == digest(video)
    except (OSError, ValueError, AttributeError):
        return False


def _clip_receipt(video: Path, first: int, last: int) -> None:
    from m2v.core.project import _write_json
    _write_json(video.with_suffix(".json"), {"sha256": digest(video), "first": first, "last": last})


def _cached_ranges(cache: Path, key: str, first: int, last: int) -> list:
    candidates = []
    for receipt in cache.glob(f"{key}-*.json"):
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
            begin, finish = data["first"], data["last"]
            video = receipt.with_suffix(".mp4")
            if first <= begin < finish <= last and _valid_clip(video, receipt):
                candidates.append((begin, finish, video))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    accepted, cursor = [], first
    for begin, finish, video in sorted(candidates, key=lambda item: (item[0], -item[1])):
        if begin >= cursor:
            accepted.append((begin, finish, video))
            cursor = finish
    return accepted


def _is_hero_frame(frame: int, shots: list[dict]) -> bool:
    return any(shot.get("tier") == "hero" and shot.get("startFrame", 0) <= frame < shot.get("endFrame", 0)
               for shot in shots)


def _subframes_for(frame: int, shots: list[dict], hero_subframes: int) -> int:
    """hero 镜头内的帧取多个子帧做运动模糊；其余镜头保持单帧。"""
    if hero_subframes <= 1:
        return 1
    return hero_subframes if _is_hero_frame(frame, shots) else 1


def _average(files: list[Path], target: Path) -> None:
    """把同一帧的多个子帧平均成一张图；输入同尺寸同格式，平均即运动模糊。

    用 `mix`（等权、归一化）而不是 `blend=all_mode=average`：后者对同一组
    0/128/255 的子帧给出 159 而不是 128，不能当作平均。
    """
    if not files:
        raise M2VError("没有可平均的子帧")
    if len(files) == 1:
        target.write_bytes(files[0].read_bytes())
        return
    args: list[str] = []
    for file in files:
        args += ["-i", str(file)]
    labels = "".join(f"[{index}]" for index in range(len(files)))
    audio.ffmpeg([*args, "-filter_complex", f"{labels}mix=inputs={len(files)}[out]",
                  "-map", "[out]", "-frames:v", "1", "-y", str(target)])


def _capture(pw, root: Path, work: Path, config: dict, *, selected_frames: list[int] | None = None) -> None:
    """固定时间推进、绘制后截图；逐帧落盘且宿主超时不使用作品时钟。

    声明 look.motion 的重点镜头在同一帧内再取若干子帧（`(frame + k/N) / fps`），把子帧平均成
    一个输出帧，等效快门时间内的运动模糊；`supersample` 为 2 时按 2 倍设备像素采集，
    编码时降采样回目标画幅（SSAA）。两者都只由配置决定，因此同一帧仍然可复现。
    """
    errors: list[str] = []
    width, height = config["width"], config["height"]
    motion = config.get("motion") or {}
    hero_subframes = int(motion.get("subframes", 1))
    supersample = int(motion.get("supersample", 1))
    capture_scale = config.get("captureScale", 1)
    selected = None if selected_frames is None else set(selected_frames)
    if selected is not None and (not selected or any(type(n) is not int or n < 0
                                                    or n >= config["durationInFrames"] for n in selected)):
        raise M2VError("关键帧索引必须位于场景时长内")
    if capture_scale not in (1, 2):
        raise M2VError("原生采集像素密度必须为 1 或 2")
    shots = (config.get("props") or {}).get("shots") or []
    config_text = json.dumps(config, ensure_ascii=True).replace("<", "\\u003c")
    (work / "index.html").write_text('<!doctype html><html><head><meta charset="utf-8"></head>'
        # 页面底色是编码兜底而不是作品主题：作品必须在 ready 之前自己画满不透明背景。
        '<body style="margin:0;overflow:hidden;background:#000">'
        f'<div id="root" style="width:{width}px;height:{height}px;overflow:hidden"></div>'
        f'<script>window.__M2V_CODE_CONFIG__={config_text}</script><script src="scene.js"></script></body></html>',
        encoding="utf-8")
    # 只开放已登记媒体与批准字体，不暴露作品配置、源文、导入记录或 assets 下的其他文件。
    mounts = {"/fonts": WEB / "public/fonts"}
    files = media_files(root, config["media"])
    with LocalServer(work, mounts=mounts, files=files, cors=True) as server:
        # 默认无头 Chromium 走 SwiftShader 软件光栅化，实测整片只有约 1 帧/秒；
        # 显式打开 ANGLE/D3D11 后走真实 GPU。没有可用 GPU 的环境会自动回退到软件
        # 光栅化，因此这是提速而不是新的硬依赖。
        browser = pw.chromium.launch(headless=True, args=[
            "--autoplay-policy=no-user-gesture-required",
            "--use-gl=angle", "--use-angle=d3d11", "--ignore-gpu-blocklist",
        ])
        try:
            context = browser.new_context(viewport={"width": width, "height": height},
                                          device_scale_factor=1,
                                          service_workers="block")
            def route_request(route):
                url = route.request.url
                if url.startswith(server.base_url + "/") or url.startswith(("data:", "blob:")):
                    route.continue_()
                else:
                    errors.append("代码场景禁止外网请求：" + url)
                    route.abort()
            context.add_init_script(path=str(WEB / "src/code-scene/capture-clock.js"))
            context.route("**/*", route_request)
            context.route_web_socket("**/*", lambda route: (errors.append("代码场景禁止 WebSocket"), route.close()))
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda response: errors.append(f"资源加载失败：{response.url}") if response.status >= 400 else None)
            page.goto(server.base_url + "/index.html")
            deadline = time.monotonic() + READY_TIMEOUT_MS / 1000
            while not page.evaluate("Boolean(window.__M2V_CODE__?.ready)"):
                if errors or time.monotonic() >= deadline:
                    raise M2VError("代码场景就绪失败：" + "; ".join(errors or ["30 秒内未调用 ready() / 字体或素材未就绪"]))
                page.evaluate("window.__M2V_CAPTURE_CLOCK__.bootstrap()")
            session = context.new_cdp_session(page)
            started = time.monotonic()
            page.evaluate("window.__M2V_CODE__.start()")
            total = config["durationInFrames"] if selected is None else max(selected) + 1
            subframe_total = 0
            for frame_index in range(total):
                count = _subframes_for(frame_index, shots, hero_subframes)
                # SSAA 只作用于 hero 帧：总览保持 1×，避免整片按 2 倍像素采集。
                frame_scale = capture_scale if capture_scale > 1 else (
                    supersample if _is_hero_frame(frame_index, shots) else 1)
                subframe_total += count
                pieces: list[Path] = []
                for subframe in range(count):
                    # 截图期间时钟冻结，超时使用注入前保留的原生真实定时器。
                    try:
                        page.evaluate("""([frame, subframe, count, timeout]) => window.__M2V_CAPTURE_CLOCK__.deadline(
                            window.__M2V_CODE__.advanceToSubframe(frame, subframe, count), timeout)""",
                            [frame_index, subframe, count, READY_TIMEOUT_MS])
                    except Exception as exc:
                        raise M2VError(f"代码场景第 {frame_index} 帧绘制失败：{exc}") from exc
                    if errors:
                        raise M2VError(f"代码场景第 {frame_index} 帧运行失败：" + "; ".join(errors))
                    # 状态型动画仍逐帧推进，但只在选定位置读回 GPU，避免生成整片图像。
                    if selected is not None and frame_index not in selected:
                        continue
                    if capture_scale > 1:
                        insufficient = page.evaluate("""scale => [...document.querySelectorAll('canvas')]
                            .filter(c => {const r = c.getBoundingClientRect(); return r.width > 0 && r.height > 0
                              && (c.width < Math.round(r.width * scale) || c.height < Math.round(r.height * scale));})
                            .map(c => ({width:c.width,height:c.height,cssWidth:c.clientWidth,cssHeight:c.clientHeight}))""",
                            capture_scale)
                        if insufficient:
                            raise M2VError(f"原生采集画布像素不足：{insufficient}；请按 captureScale 绘制")
                    # CDP 截取已完成绘制的画面；不依赖 screencast 的实时投递频率。
                    # SSAA 用 clip 的 scale 显式放大：裸的 captureScreenshot 只按 CSS 像素
                    # 出图，device_scale_factor 不会体现在结果里。编码时统一降采样，
                    # 因此同一段片段里 1× 与 2× 的帧可以混用。
                    params = {"format": "png", "captureBeyondViewport": False, "optimizeForSpeed": True}
                    if frame_scale > 1:
                        params["clip"] = {"x": 0, "y": 0, "width": width, "height": height,
                                          "scale": frame_scale}
                    shot = session.send("Page.captureScreenshot", params)
                    piece = work / f"sub-{frame_index:06d}-{subframe}.png"
                    piece.write_bytes(base64.b64decode(shot["data"]))
                    pieces.append(piece)
                if not pieces:
                    if frame_index % 300 == 0:
                        logger.info("关键帧采集时钟推进 %d/%d，耗时 %.1f 秒",
                                    frame_index + 1, total, time.monotonic() - started)
                    continue
                target = work / f"frame-{frame_index:06d}.png"
                _average(pieces, target)
                for piece in pieces:
                    piece.unlink()
                if frame_index % 300 == 0 or frame_index + 1 == total:
                    logger.info("代码场景逐帧采集 %d/%d（子帧 %d），耗时 %.1f 秒",
                                frame_index + 1, total, subframe_total, time.monotonic() - started)
        except M2VError:
            raise
        except Exception as exc:
            raise M2VError(f"代码场景浏览器录制失败：{exc}") from exc
        finally:
            browser.close()


def _encode(work: Path, output: Path, frames: int, width: int, height: int, *, supersample: int = 1, start_frame: int = 0) -> None:
    temporary = work / "encoded.mp4"
    # yuv444p 而不是 yuv420p：片段会与作品画布直接拼接，4:2:0 的色度抽样会让底色偏
    # 一两个色阶，在深色画面上显出方块边缘；4:4:4 的往返对纯色是精确的。
    captured = sorted(work.glob("frame-*.png"))
    if len(captured) != frames or any(path.name != f"frame-{i + start_frame:06d}.png" for i, path in enumerate(captured)):
        raise M2VError("代码场景采集帧缺失，拒绝补帧编码")
    scale: list[str] = []
    if supersample > 1:
        # SSAA：采集时按 2 倍设备像素渲染，编码时降采样回目标画幅。
        scale = ["-vf", f"scale={width}:{height}:flags=lanczos"]
    audio.ffmpeg(["-framerate", str(FPS), "-start_number", str(start_frame), "-i", str(work / "frame-%06d.png"),
                  *scale, "-an", "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv444p",
                  "-crf", "18", str(temporary)])
    _verify_clip(temporary, frames)
    security.deliver(temporary, output)


def _verify_clip(video: Path, frames: int) -> None:
    # 缓存拼接也必须解码核验帧数，不能相信容器时长。
    from imageio_ffmpeg import get_ffmpeg_exe
    result = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(video), "-map", "0:v:0",
                             "-f", "framehash", "-"], capture_output=True, text=True, timeout=300)
    decoded = sum(bool(line.strip()) and not line.startswith("#") for line in result.stdout.splitlines())
    if result.returncode or decoded != frames:
        raise M2VError(f"代码场景编码帧数不符：期望 {frames}，实际 {decoded}")
