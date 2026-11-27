"""三类统一 v9 代码场景的逐帧采集、片段缓存与编码验收。

这里只负责「把作品代码录成片段并留证」；入口校验、录制配置与静态模块构建在
`config.py`，本模块单向依赖它。
"""
from __future__ import annotations

import base64
import json
import logging
import math
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from film_runtime.core.errors import VideoError
from film_runtime.core.fingerprints import fingerprint
from film_runtime.core.video_config import DEFAULT_FPS, validate_fps
from film_runtime.core import security, source_policy
from film_runtime.engine import audio, images
from film_runtime.engine.http_server import LocalServer
from .config import (WEB, build_scene, capture_settings, digest, implementation_inputs, media_files,
                     scene_config, validate_entry, copy_build_outputs)


READY_TIMEOUT_MS = 30000
# v1 可能把尚未通过整组边界验证的分块发布到缓存；旧收据不能继续授权复用。
PURE_CONTRACT = "pure-seek-png-444-v2"
SEQUENTIAL_CONTRACT = "fixed-clock-png-444-v5"

from .workspace import recording_workspace

logger = logging.getLogger(__name__)


def materialize(root: Path, prepared: dict, start: int, end: int, *, jobs: int | None = None) -> dict:
    """只录制与半开全片窗口相交的场景，保留原始时间轴和转场。

    pure 场景把请求窗口向外扩到 `blockFrames` 边界，使预演与全片渲染能复用同一批块；
    合成层按 `mediaStartFrame` 回放扩展窗口，请求窗口的画面不偏移。
    """
    import copy
    from .. import media_assets
    result = copy.deepcopy(prepared)
    frame = {"width": result["width"], "height": result["height"],
             "subtitle": result["props"]["subtitle"]}
    media = media_assets.resolve(root)
    selected = []
    for scene in result["props"]["compiledScenes"]:
        first = max(start, scene["startFrame"]) - scene["startFrame"]
        last = min(end, scene["endFrame"]) - scene["startFrame"]
        if first >= last:
            continue
        settings = capture_settings((scene.get("content") or {}).get("props", {}))
        if settings["mode"] == "pure-time":
            block = settings["blockFrames"] or prepared["fps"]
            first = (first // block) * block
            last = min(scene["durationInFrames"], ((last + block - 1) // block) * block)
        scene["mediaPath"] = record(root, scene, {}, frame=frame, media=media["media"],
            media_digest=media["digest"], capture_range=(first, last), fps=prepared["fps"],
            jobs=settings["jobs"] if jobs is None else jobs)
        scene["mediaStartFrame"] = first
        scene["mediaDurationFrames"] = last - first
        selected.append(scene)
    result["props"]["compiledScenes"] = selected
    return result


def record(root: Path, scene: dict, inputs: dict[str, str], *, frame: dict, media: dict, media_digest: str,
           capture_range: tuple[int, int] | None = None, fps: int = DEFAULT_FPS,
           jobs: int = 1) -> str:
    """构建可达源码，缓存有效时不启动浏览器；画幅、媒体映射与统一契约都进缓存键。"""
    from playwright.sync_api import sync_playwright
    content = scene["content"]
    props = content.get("props", {})
    validate_entry(root, content.get("entry"), props)
    settings = capture_settings(props)
    pure = settings["mode"] == "pure-time"
    verify_frames = settings["verifyFrames"]
    jobs = min(4, max(jobs, settings["jobs"]))
    contract = PURE_CONTRACT if pure else None
    width, height = frame["width"], frame["height"]
    cache = root / "outputs/code-cache"
    cache.mkdir(parents=True, exist_ok=True)
    config = scene_config(scene, frame, media, fps=fps)
    first, last = capture_range or (0, config["durationInFrames"])
    if not 0 <= first < last <= config["durationInFrames"]:
        raise VideoError("场景采集范围越界")
    with recording_workspace(cache) as work:
        source_inputs = build_scene(root, scene, work)
        inputs.update(source_inputs)
        inputs["codeMedia"] = media_digest
        if pure:
            _assert_pure_sources(root, work)
        with sync_playwright() as pw:
            browser_version = pw.chromium.executable_path
            executable = Path(browser_version)
            key = fingerprint({"config": config, "media": media_digest, "sources": source_inputs,
                               "implementation": implementation_inputs(),
                               "browser": digest(executable), "size": [width, height],
                               "capture": contract or SEQUENTIAL_CONTRACT})
            output = cache / f"{key}-{first}-{last}.mp4"
            receipt = output.with_suffix(".json")
            if _valid_clip(output, receipt, contract=contract):
                logger.info("代码场景 %s 复用录制缓存", scene["id"])
            else:
                # 已检查的区间原样复用，只采集缺口；不能为补齐整幕再截图一次已有帧。
                accepted = _cached_ranges(cache, key, first, last, contract=contract)
                pieces = []
                probe_reports = []
                if pure and jobs > 1:
                    cached, gaps = _gap_pieces(first, last, accepted)
                    pieces = [*cached, *_parallel_chunks(
                        root, work, config, gaps, cache, key, fps=fps, jobs=jobs,
                        verify_frames=verify_frames, block=settings["blockFrames"] or fps)]
                    pieces.sort(key=lambda item: item[0])
                    probes, minimum = _receipt_probes(pieces)
                    if probes:
                        probe_reports.append({"probes": probes, "minPsnr": minimum})
                else:
                    cursor = first
                    for begin, finish, clip in [*(accepted or []), (last, last, None)]:
                        if begin > cursor:
                            gap = work / f"gap-{cursor}"
                            gap.mkdir()
                            copy_build_outputs(work, gap)
                            target = cache / f"{key}-{cursor}-{begin}.mp4"
                            logger.info("代码场景 %s 采集缺口 %d～%d", scene["id"], cursor, begin)
                            runtime = dict(config)
                            probe = _capture(pw, root, gap, runtime, selected_frames=list(range(cursor, begin)),
                                             pure=pure, verify_frames=verify_frames, capture_start=cursor)
                            if pure and probe:
                                probe_reports.append(probe)
                            _encode(gap, target, begin-cursor, width, height, start_frame=cursor, fps=fps,
                                    supersample=int((config.get("motion") or {}).get("supersample", 1)))
                            extra = {"contract": PURE_CONTRACT, "verified": True, **(probe or {})} if pure else None
                            _clip_receipt(target, cursor, begin, extra=extra)
                            pieces.append((cursor, begin, target))
                        if clip is not None:
                            pieces.append((begin, finish, clip))
                        cursor = finish
                pieces = [item[2] for item in sorted(pieces, key=lambda item: item[0])]
                if len(pieces) == 1 and pieces[0] == output:
                    pass
                else:
                    listing = work / "concat.txt"
                    listing.write_text("".join("file '" + str(p.resolve()).replace("\\", "/").replace("'", "'\\''") + "'\n" for p in pieces), encoding="utf-8")
                    combined = work / "combined.mp4"
                    audio.ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(combined)])
                    _verify_clip(combined, last-first)
                    security.deliver(combined, output)
                final_extra = {"contract": PURE_CONTRACT, "verified": True} if pure else None
                if pure and probe_reports:
                    final_extra["probes"] = [item for report in probe_reports for item in report["probes"]]
                    final_extra["minPsnr"] = min(
                        (report["minPsnr"] for report in probe_reports if report["minPsnr"] is not None),
                        default=None)
                _clip_receipt(output, first, last, extra=final_extra)
        relative = output.relative_to(root).as_posix()
        inputs["file:" + relative] = digest(output)
        output.touch()
        return relative


def _valid_clip(video: Path, receipt: Path, *, contract: str | None = None) -> bool:
    try:
        data = json.loads(receipt.read_text(encoding="utf-8"))
        if video.is_file() is False or data.get("sha256") != digest(video):
            return False
        if contract is not None:
            return data.get("contract") == contract and data.get("verified") is True
        return True
    except (OSError, ValueError, AttributeError):
        return False


def _clip_receipt(video: Path, first: int, last: int, *, extra: dict | None = None) -> None:
    from film_runtime.core.delivery import _save
    payload = {"sha256": digest(video), "first": first, "last": last}
    if extra:
        payload.update(extra)
    # Windows 索引器可能短暂占用前一份收据；复用交付层已有的有界重试。
    _save(video.with_suffix(".json"), payload)


def _cached_ranges(cache: Path, key: str, first: int, last: int, *, contract: str | None = None) -> list:
    candidates = []
    for receipt in cache.glob(f"{key}-*.json"):
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
            begin, finish = data["first"], data["last"]
            video = receipt.with_suffix(".mp4")
            if first <= begin < finish <= last and _valid_clip(video, receipt, contract=contract):
                candidates.append((begin, finish, video))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    accepted, cursor = [], first
    for begin, finish, video in sorted(candidates, key=lambda item: (item[0], -item[1])):
        if begin >= cursor:
            accepted.append((begin, finish, video))
            cursor = finish
    return accepted


def _gap_pieces(first: int, last: int, accepted: list) -> tuple[list, list[tuple[int, int]]]:
    """把已缓存区间与待采集缺口拆开，返回 (已缓存 pieces, 缺口列表)。"""
    pieces, gaps = [], []
    cursor = first
    for begin, finish, clip in accepted:
        if begin > cursor:
            gaps.append((cursor, begin))
        pieces.append((begin, finish, clip))
        cursor = finish
    if cursor < last:
        gaps.append((cursor, last))
    return pieces, gaps


def _parallel_chunks(root: Path, work: Path, config: dict, gaps: list[tuple[int, int]],
                     cache: Path, key: str, *, fps: int, jobs: int, verify_frames: int,
                     block: int) -> list[tuple[int, int, Path]]:
    """把缺口按块切成子进程任务；返回块区间与片段路径（按起点排序）。"""
    chunks = []
    for first, last in gaps:
        for start in range(first, last, block):
            end = min(last, start + block)
            # worker 只写本次临时目录。整组边界通过前，任何分块都不可成为可复用缓存。
            chunks.append((start, end, work / f"chunk-{start}-{end}" / "clip.mp4"))
    chunks.sort(key=lambda item: item[0])
    tasks = []
    for index, (start, end, target) in enumerate(chunks):
        witnesses = []
        if index + 1 < len(chunks):
            witnesses.append(chunks[index + 1][0])
        if index > 0:
            witnesses.append(chunks[index][0])
        directory = work / f"chunk-{start}-{end}"
        directory.mkdir(parents=True, exist_ok=True)
        job = {"root": str(root), "work": str(directory), "sceneJs": str(work / "scene.js"),
               "config": config, "first": start, "last": end, "output": str(target),
               "fps": fps, "verifyFrames": verify_frames, "witnessFrames": witnesses}
        job_file = directory / "job.json"
        job_file.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        tasks.append((start, end, job_file))

    if tasks:
        def run(task):
            start, end, job_file = task
            result = subprocess.run(
                [sys.executable, "-m", "film_runtime.types.scene_film.code_scenes.worker", str(job_file)],
                cwd=str(root), capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=3600)
            if result.returncode:
                raise VideoError(f"pure-time 块 {start}–{end} 采集失败：{(result.stderr or result.stdout)[-1200:]}")

        with ThreadPoolExecutor(max_workers=jobs) as pool:
            list(pool.map(run, tasks))

    for start, end, target in chunks:
        _verify_clip(target, end - start)
        if not _valid_clip(target, target.with_suffix(".json"), contract=PURE_CONTRACT):
            raise VideoError(f"pure-time 块 {start}–{end} 未通过验收")

    # 相邻块边界见证帧：同一帧在两个独立进程里采集，检验块首状态没有跨进程漂移。
    for left, right in zip(chunks, chunks[1:]):
        left_start, left_end, _ = left
        right_start, right_end, _ = right
        left_witness = work / f"chunk-{left_start}-{left_end}" / f"witness-{right_start:06d}.png"
        right_witness = work / f"chunk-{right_start}-{right_end}" / f"witness-{right_start:06d}.png"
        if not left_witness.is_file() or not right_witness.is_file():
            raise VideoError(f"pure-time 块边界 {right_start} 帧缺少跨进程见证帧")
        value = images.psnr(left_witness, right_witness)
        if value < 60:
            # 保存实际失败帧，避免临时目录清理后只能凭数字猜测原因；不把诊断当通过证据。
            diagnostic = cache / "diagnostics" / f"{key}-{right_start}"
            diagnostic.mkdir(parents=True, exist_ok=True)
            for name, source in (("left.png", left_witness), ("right.png", right_witness)):
                copied = work / ("diagnostic-" + name)
                shutil.copyfile(source, copied)
                security.deliver(copied, diagnostic / name)
            logger.error("pure-time 边界检查失败 frame=%s psnr=%.2f evidence=%s",
                         right_start, value, diagnostic)
            raise VideoError(f"pure-time 块边界 {right_start} 帧跨进程 PSNR {value:.2f} dB < 60 dB；诊断：{diagnostic}")
    published = []
    for start, end, source in chunks:
        target = cache / f"{key}-{start}-{end}.mp4"
        security.deliver(source, target)
        security.deliver(source.with_suffix(".json"), target.with_suffix(".json"))
        published.append((start, end, target))
    return published


def _receipt_probes(pieces: list[tuple[int, int, Path]]) -> tuple[list, float | None]:
    probes, minimum = [], None
    for _first, _last, clip in pieces:
        try:
            data = json.loads(clip.with_suffix(".json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        probes.extend(data.get("probes") or [])
        value = data.get("minPsnr")
        if isinstance(value, (int, float)):
            minimum = value if minimum is None else min(minimum, value)
    return probes, minimum


def _pure_source_paths(root: Path, work: Path) -> list[Path]:
    """作品根内的实际构建输入；不扫 node_modules 与共享运行时。"""
    try:
        names = json.loads((work / "inputs.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    paths = []
    # 这些模块实现受控采集本身，不是作品自走代码；其字节仍进入运行时指纹。
    infrastructure = {'src/code-scene/host.tsx', 'src/code-scene/context.ts',
                      'src/code-scene/frame-tasks.ts', 'src/fonts.ts'}
    for name in names:
        path = Path(name).resolve()
        if path.is_relative_to(root.resolve()):
            relative = path.relative_to(root.resolve())
            if 'node_modules' in relative.parts or relative.as_posix() in infrastructure:
                continue
            paths.append(path)
    return paths


def _assert_pure_sources(root: Path, work: Path) -> None:
    violations = source_policy.scan_pure(_pure_source_paths(root, work))
    if violations:
        detail = "；".join(item.render(root) for item in violations[:5])
        raise VideoError(f"pure-time 场景含自走动画或真实时钟：{detail}")


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
        raise VideoError("没有可平均的子帧")
    if len(files) == 1:
        target.write_bytes(files[0].read_bytes())
        return
    args: list[str] = []
    for file in files:
        args += ["-i", str(file)]
    labels = "".join(f"[{index}]" for index in range(len(files)))
    audio.ffmpeg([*args, "-filter_complex", f"{labels}mix=inputs={len(files)}[out]",
                  "-map", "[out]", "-frames:v", "1", "-y", str(target)])


def _capture(pw, root: Path, work: Path, config: dict, *, selected_frames: list[int] | None = None,
             observe=None, pure: bool = False, verify_frames: int = 4,
             capture_start: int | None = None,
             witness_frames: list[int] | None = None) -> dict | None:
    """固定时间推进、绘制后截图；逐帧落盘且宿主超时不使用作品时钟。

    顺序模式按连续帧推进；pure 模式只遍历目标帧并绝对 seek，允许倒序。声明 look.motion
    的重点镜头在同一帧内再取若干子帧（`(frame + k/N) / fps`），把子帧平均成一个输出帧；
    `supersample` 为 2 时按 2 倍设备像素采集，编码时降采样回目标画幅（SSAA）。
    """
    errors: list[str] = []
    width, height = config["width"], config["height"]
    motion = config.get("motion") or {}
    hero_subframes = int(motion.get("subframes", 1))
    supersample = int(motion.get("supersample", 1))
    capture_scale = config.get("captureScale", 1)
    pure = pure or config.get("captureMode") == "pure-time"
    order = None if selected_frames is None else list(selected_frames)
    if pure:
        if order is None:
            order = list(range(config["durationInFrames"]))
        if not order or any(type(n) is not int or n < 0 or n >= config["durationInFrames"] for n in order):
            raise VideoError("关键帧索引必须位于场景时长内")
        selected = None
    else:
        selected = None if order is None else set(order)
        if selected is not None and (not selected or any(type(n) is not int or n < 0
                                                        or n >= config["durationInFrames"] for n in selected)):
            raise VideoError("关键帧索引必须位于场景时长内")
    if capture_scale not in (1, 2):
        raise VideoError("原生采集像素密度必须为 1 或 2")
    shots = (config.get("props") or {}).get("shots") or []
    runtime = dict(config)
    if pure:
        runtime["captureMode"] = "pure-time"
        runtime["captureStartFrame"] = capture_start if capture_start is not None else order[0]
        runtime["verifyFrames"] = verify_frames
    # 使用 JSON.parse 保留 __proto__ 等合法字典键；对象字面量会将其当成原型设置。
    # 外层字符串继续转义 <，避免作品字符串中的 </script> 提前终止脚本。
    config_text = json.dumps(json.dumps(runtime, ensure_ascii=True)).replace("<", "\\u003c")
    stylesheet = '<link rel="stylesheet" href="scene.css">' if (work / "scene.css").is_file() else ''
    (work / "index.html").write_text('<!doctype html><html><head><meta charset="utf-8">' + stylesheet + '</head>'
        # 页面底色是编码兜底而不是作品主题：作品必须在 ready 之前自己画满不透明背景。
        '<body style="margin:0;overflow:hidden;background:#000">'
        f'<div id="root" style="width:{width}px;height:{height}px;overflow:hidden"></div>'
        f'<script>window.__M2V_CODE_CONFIG__=JSON.parse({config_text})</script><script src="scene.js"></script></body></html>',
        encoding="utf-8")
    # 只开放已登记媒体与批准字体，不暴露作品配置、源文、导入记录或 assets 下的其他文件。
    mounts = {"/fonts": WEB / "public/fonts"}
    files = media_files(root, config["media"])
    with LocalServer(work, mounts=mounts, files=files, cors=True) as server:
        # 默认无头 Chromium 走 SwiftShader 软件光栅化，实测整片只有约 1 帧/秒；
        # 显式打开 ANGLE/D3D11 后走真实 GPU。没有可用 GPU 的环境会自动回退到软件
        # 光栅化，因此这是提速而不是新的硬依赖。
        # 完整Chromium的无头模式包含Windows WebGPU所需的DXC；headless shell不包含它。
        browser = pw.chromium.launch(channel="chromium", headless=True, args=[
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
                    raise VideoError("代码场景就绪失败：" + "; ".join(errors or ["30 秒内未调用 ready() / 字体或素材未就绪"]))
                page.evaluate("window.__M2V_CAPTURE_CLOCK__.bootstrap()")
            session = context.new_cdp_session(page)
            started = time.monotonic()
            page.evaluate("window.__M2V_CODE__.start()")
            frames = order if pure else list(range(config["durationInFrames"] if selected is None else max(selected) + 1))
            subframe_total = 0
            for position, frame_index in enumerate(frames):
                count = _subframes_for(frame_index, shots, hero_subframes)
                # SSAA 只作用于 hero 帧：总览保持 1×，避免整片按 2 倍像素采集。
                frame_scale = capture_scale if capture_scale > 1 else (
                    supersample if _is_hero_frame(frame_index, shots) else 1)
                subframe_total += count
                pieces: list[Path] = []
                for subframe in range(count):
                    # 截图期间时钟冻结，超时使用注入前保留的原生真实定时器。
                    method = "seekToSubframe" if pure else "advanceToSubframe"
                    try:
                        page.evaluate("""([method, frame, subframe, count, timeout]) => window.__M2V_CAPTURE_CLOCK__.deadline(
                            window.__M2V_CODE__[method](frame, subframe, count), timeout)""",
                            [method, frame_index, subframe, count, READY_TIMEOUT_MS])
                    except Exception as exc:
                        raise VideoError(f"代码场景第 {frame_index} 帧绘制失败：{exc}") from exc
                    if errors:
                        raise VideoError(f"代码场景第 {frame_index} 帧运行失败：" + "; ".join(errors))
                    # 状态型动画仍逐帧推进，但只在选定位置读回 GPU，避免生成整片图像。
                    if not pure and selected is not None and frame_index not in selected:
                        continue
                    if observe is not None and subframe == 0:
                        # 开发侧观察器只读取已推进的页面，不向运行时配置或成片注入探针。
                        observe(page, frame_index)
                    if capture_scale > 1:
                        insufficient = page.evaluate("""scale => [...document.querySelectorAll('canvas')]
                            .filter(c => {const r = c.getBoundingClientRect(); return r.width > 0 && r.height > 0
                              && (c.width < Math.round(r.width * scale) || c.height < Math.round(r.height * scale));})
                            .map(c => ({width:c.width,height:c.height,cssWidth:c.clientWidth,cssHeight:c.clientHeight}))""",
                            capture_scale)
                        if insufficient:
                            raise VideoError(f"原生采集画布像素不足：{insufficient}；请按 captureScale 绘制")
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
                    if position % 300 == 0:
                        logger.info("关键帧采集时钟推进 %d/%d，耗时 %.1f 秒",
                                    position + 1, len(frames), time.monotonic() - started)
                    continue
                target = work / f"frame-{frame_index:06d}.png"
                _average(pieces, target)
                for piece in pieces:
                    piece.unlink()
                if position % 300 == 0 or position + 1 == len(frames):
                    logger.info("代码场景逐帧采集 %d/%d（子帧 %d），耗时 %.1f 秒",
                                position + 1, len(frames), subframe_total, time.monotonic() - started)
            if not pure:
                return None
            witnesses = []
            for frame in witness_frames or []:
                if not 0 <= frame < config["durationInFrames"]:
                    continue
                page.evaluate("""([frame, timeout]) => window.__M2V_CAPTURE_CLOCK__.deadline(
                    window.__M2V_CODE__.seekToSubframe(frame, 0, 1), timeout)""",
                    [frame, READY_TIMEOUT_MS])
                if errors:
                    raise VideoError(f"pure-time 边界见证帧 {frame} 运行失败：" + "; ".join(errors))
                image = session.send("Page.captureScreenshot",
                                     {"format": "png", "captureBeyondViewport": False,
                                      "optimizeForSpeed": True})
                target = work / f"witness-{frame:06d}.png"
                target.write_bytes(base64.b64decode(image["data"]))
                witnesses.append(str(target))
            result = _probe_pure(page, session, work, order, verify_frames, errors) or {}
            result["witness"] = witnesses
            return result
        except VideoError:
            raise
        except Exception as exc:
            raise VideoError(f"代码场景浏览器录制失败：{exc}") from exc
        finally:
            browser.close()


def _probe_pure(page, session, work: Path, order: list[int], verify_frames: int,
                errors: list[str]) -> dict | None:
    """正序/倒序探针：证明同一帧与到达顺序无关。"""
    if len(order) < 2 or verify_frames < 2:
        return None
    count = min(verify_frames, len(order))
    picks = sorted({round(index * (len(order) - 1) / (count - 1)) for index in range(count)})
    if len(picks) < 2:
        return None
    shots: dict[int, tuple[Path, Path]] = {}

    def screenshot(pick: int, suffix: str) -> Path:
        frame = order[pick]
        page.evaluate("""([frame, timeout]) => window.__M2V_CAPTURE_CLOCK__.deadline(
            window.__M2V_CODE__.seekToSubframe(frame, 0, 1), timeout)""",
            [frame, READY_TIMEOUT_MS])
        if errors:
            raise VideoError(f"pure-time 探针第 {frame} 帧运行失败：" + "; ".join(errors))
        image = session.send("Page.captureScreenshot",
                             {"format": "png", "captureBeyondViewport": False, "optimizeForSpeed": True})
        target = work / f"probe-{suffix}-{pick:04d}.png"
        target.write_bytes(base64.b64decode(image["data"]))
        return target

    for pick in picks:
        shots.setdefault(pick, (None, None))
        shots[pick] = (screenshot(pick, "f"), shots[pick][1])
    for pick in reversed(picks):
        shots[pick] = (shots[pick][0], screenshot(pick, "r"))
    results, minimum = [], math.inf
    for pick in picks:
        value = images.psnr(*shots[pick])
        minimum = min(minimum, value)
        results.append({"frame": order[pick], "psnr": None if math.isinf(value) else round(value, 2)})
        if value < 60:
            raise VideoError(f"pure-time 自检失败：帧 {order[pick]} 正序/倒序 PSNR {value:.2f} dB < 60 dB；"
                           "场景可能依赖跨帧状态、计时器或随机源")
    return {"probes": results, "minPsnr": None if math.isinf(minimum) else round(minimum, 2)}


def _encode(work: Path, output: Path, frames: int, width: int, height: int, *, supersample: int = 1, start_frame: int = 0, fps: int = DEFAULT_FPS) -> None:
    temporary = work / "encoded.mp4"
    # yuv444p 而不是 yuv420p：片段会与作品画布直接拼接，4:2:0 的色度抽样会让底色偏
    # 一两个色阶，在深色画面上显出方块边缘；4:4:4 的往返对纯色是精确的。
    captured = sorted(work.glob("frame-*.png"))
    if len(captured) != frames or any(path.name != f"frame-{i + start_frame:06d}.png" for i, path in enumerate(captured)):
        raise VideoError("代码场景采集帧缺失，拒绝补帧编码")
    scale: list[str] = []
    if supersample > 1:
        # SSAA：采集时按 2 倍设备像素渲染，编码时降采样回目标画幅。
        scale = ["-vf", f"scale={width}:{height}:flags=lanczos"]
    audio.ffmpeg(["-framerate", str(validate_fps(fps)), "-start_number", str(start_frame), "-i", str(work / "frame-%06d.png"),
                  *scale, "-an", "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv444p",
                  "-crf", "18", str(temporary)])
    _verify_clip(temporary, frames)
    security.deliver(temporary, output)
    for frame_path in captured:
        frame_path.unlink()


def _verify_clip(video: Path, frames: int) -> None:
    # 缓存拼接也必须解码核验帧数，不能相信容器时长。
    from imageio_ffmpeg import get_ffmpeg_exe
    result = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(video), "-map", "0:v:0",
                             "-f", "framehash", "-"], capture_output=True, text=True, timeout=300)
    decoded = sum(bool(line.strip()) and not line.startswith("#") for line in result.stdout.splitlines())
    if result.returncode or decoded != frames:
        raise VideoError(f"代码场景编码帧数不符：期望 {frames}，实际 {decoded}")
