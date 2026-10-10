"""逐帧渲染编排：把 React composition 确定性地渲染并编码为 MP4。

这里集中处理三件事：
1. 契约一致性检查（composition 声明的 fps/尺寸必须与分镜一致，渲染前交叉校验）；
2. 逐帧渲染（Remotion 引擎按帧号求值）与进度日志；
3. 编码完成后的成片验收（帧数、分辨率、可解码性、播放器兼容性）。
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import subprocess
import time
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from imageio_ffmpeg import get_ffmpeg_exe

from . import assets, paths, perf, remotion, security
from .audio import mux
from .browser import PageContract
from .errors import A2VError
from .media import Media, asset_fingerprint, file_digest, write_effective_storyboard
from .http_server import LocalServer
from .storyboard import Storyboard
from .subtitles import srt

logger = logging.getLogger(__name__)

#: 画面来源：网页（旧路径）与 React composition（Remotion 路径）。
#: 写进溯源，让复核知道该用哪一套指纹口径——两者的「资产」根本不是一回事。
RENDERER_PAGE = "page"
RENDERER_REMOTION = "remotion"


class RenderError(A2VError):
    """渲染前置条件不满足或成片验收失败。"""


@dataclass(frozen=True)
class RenderResult:
    """一次成功渲染的统计信息，用于 CLI 汇报。"""

    output: Path
    frames: int
    fps: int
    width: int
    height: int
    duration_seconds: float
    #: 画面产出耗时。网页路径是逐帧截图；Remotion 路径是**同一个 Node 会话**的
    #: 元数据握手 + 逐帧渲染编码（浏览器只冷启动一次），两条路径都会把这一段
    #: 耗时报出来，好比较换渲染器到底快了多少。
    capture_seconds: float
    total_seconds: float
    size_bytes: int
    #: `hit` / `miss` / `disabled`：本次是否复用了打包缓存
    cache_status: str = ""
    #: 实际使用的渲染并发
    concurrency: int = remotion.DEFAULT_CONCURRENCY
    #: 分阶段耗时（`None` 表示该阶段本次未执行）
    stages: dict[str, float | None] | None = None
    #: 结构化性能报告落点；写失败时为 None
    performance_path: Path | None = None

    def summary(self) -> str:
        rate = self.frames / self.capture_seconds if self.capture_seconds else 0
        extra = []
        if self.cache_status:
            extra.append(
                {"hit": "打包缓存命中", "miss": "打包缓存未命中", "disabled": "本次禁用打包缓存"}[
                    self.cache_status
                ]
            )
            extra.append(f"并发 {self.concurrency}")
        return (
            f"输出 {self.output}：{self.frames} 帧 / {self.duration_seconds:.1f}s，"
            f"{self.width}x{self.height} @{self.fps}fps，"
            f"画面产出 {self.capture_seconds:.1f}s（约 {rate:.1f} 帧/秒），"
            f"总耗时 {self.total_seconds:.1f}s，"
            + ("，".join(extra) + "，" if extra else "")
            + f"文件 {self.size_bytes / 1024 / 1024:.1f} MiB"
            + (f"，性能报告 {self.performance_path.name}" if self.performance_path else "")
        )


def _storyboard_beside(
    page_file: Path, storyboard_url: str | None, origin: str | Path | None = None
) -> Path | None:
    """成片溯源里要记的分镜文件。

    `origin` 是渲染入口拿到的分镜路径（共享页面的分镜由命令行传入，
    网页旁边并没有 storyboard.json）；没有时才退回按地址猜。
    """
    if origin is not None and Path(origin).is_file():
        return Path(origin)
    candidate = page_file.parent / "storyboard.json"
    if not candidate.is_file() and storyboard_url:
        probe = Path(storyboard_url.split("?")[0].split("#")[0])
        candidate = probe if probe.is_absolute() else page_file.parent / probe
    return candidate if candidate.is_file() else None


def _write_provenance(
    output_path: Path,
    *,
    page_file: Path,
    storyboard_url: str | None,
    storyboard_origin: str | Path | None = None,
    workspace_root: str | Path | None = None,
    frames: int,
    fps: int,
    width: int,
    height: int,
    capture_format: str,
    media_fingerprint: str | None,
    renderer: str = RENDERER_PAGE,
    assets_override: dict | None = None,
) -> Path:
    """落一份成片溯源，让验收能回答「这个成片是不是旧资产渲的」。

    没有它的时候，改了动效资产而没重渲的成片只能靠人比对文件时间戳发现——
    实测发生过：两支实际作品的成片比动效重写早了几个小时，仍然带着被修掉的
    3 帧弹跳，而它们看上去仍然是「上次验收通过」的样子。
    写失败不回滚成片：成片已经通过验收，溯源是附加信息。

    定位一律用**相对引用**（`workspace` 指回工作区根，资产键相对它或走别名），
    因此文章与产物落在仓库之外时，这份溯源仍然读得懂。

    `assets_override` 由画面来自 React composition 的路径给出：那时画面不由
    某个 HTML 决定，而是由整个 `web/src` 的源码决定，因此指纹换成构建输入
    （见 `remotion.build_input_fingerprint`）。两条路径都走同一个复核函数。
    """
    workspace = (
        Path(workspace_root).resolve()
        if workspace_root is not None
        else (assets.project_root(page_file.parent) or page_file.parent)
    )

    def relative(path: Path | None) -> str:
        if path is None:
            return ""
        try:
            return path.resolve().relative_to(workspace).as_posix()
        except ValueError:  # 工作区根之外：只记文件名，溯源里不写绝对路径
            return path.name

    storyboard_path = _storyboard_beside(page_file, storyboard_url, storyboard_origin)
    extra: dict[str, str] = {}
    if storyboard_path is not None:
        extra[relative(storyboard_path)] = file_digest(storyboard_path)
    if media_fingerprint:
        extra["media.sourceFingerprint"] = media_fingerprint
    if assets_override is not None:
        asset_record = assets_override
    else:
        html = page_file.read_text(encoding="utf-8", errors="replace")
        asset_record = asset_fingerprint(page_file, html, extra, workspace_root=workspace)
    payload = {
        #: 4：画面来源区分为「网页」与「React composition」，后者指纹整个构建输入
        "version": 4,
        "renderer": renderer,
        "workspace": _workspace_reference(output_path, workspace),
        "renderedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # 共享页面在 bundle 里、工作区根之外：按同一套规则记成别名键
        "page": assets.asset_key(page_file, workspace),
        "storyboard": relative(storyboard_path),
        "frames": frames,
        "fps": fps,
        "width": width,
        "height": height,
        "captureFormat": capture_format,
        "assets": asset_record,
    }
    target = output_path.with_suffix(".provenance.json")
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _workspace_reference(output_path: Path, workspace: Path) -> str:
    """产物目录 → 工作区根的相对路径（如 `../..`）。

    存相对引用而不是绝对路径：溯源文件跟着成片走，换机器或换目录之后仍能读。
    """
    return os.path.relpath(workspace, output_path.parent).replace(os.sep, "/")


def provenance_status(video: str | Path) -> dict:
    """这个成片是不是旧资产渲的。

    三种结论，缺一不可：

    * `current`：溯源里的资产指纹与现在逐个对得上；
    * `stale`：有文件变了、少了，或网页新引用了当时没有的东西；
    * `unknown`：没有溯源、读不出来，或溯源里的网页已经不在了——
      **如实说「无法判断」，不默认放行**。一个安静返回「通过」的检查
      和一个真的通过的检查在报告里长得一模一样，正是要避免的失败模式。

    判定只回答「产物是不是旧的」，不回答「画面是不是废的」，
    因此调用方不得据此改变错误数与退出码。
    """
    video_path = Path(video)
    sidecar = video_path.with_suffix(".provenance.json")
    empty: dict[str, list[str]] = {"changed": [], "missing": [], "unverifiable": []}
    if not sidecar.is_file():
        return {"status": "unknown", "detail": f"没有溯源文件 {sidecar.name}，无法判断该成片是否落后", **empty}
    try:
        recorded = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status": "unknown", "detail": f"溯源文件读不出来（{exc}），无法判断", **empty}

    version = recorded.get("version")
    if version not in (3, 4):
        return {
            "status": "unknown",
            "detail": f"溯源是旧格式（version={version!r}），"
                      "定位口径已改为相对引用，请重渲一次再看",
            **empty,
        }

    # version 3 一律是网页路径渲的；version 4 起由 renderer 字段区分画面来源
    renderer = str(recorded.get("renderer") or RENDERER_PAGE)
    # 键可能记的是别名（构建输入在 `web/` 别名下、共享页面在 bundle 别名下）：
    # 按挂载表解析，与写入时同一套
    # 工作区根由溯源里的相对引用反解，不再依赖产物上级是否有仓库标记：
    # 文章落在仓库之外时，那条路走不通。
    workspace_ref = str(recorded.get("workspace") or "")
    if not workspace_ref:
        return {"status": "unknown", "detail": "溯源里没有工作区引用，无法判断页面在哪里", **empty}
    workspace = (video_path.parent / workspace_ref).resolve()
    mounts = _fingerprint_mounts(workspace)

    if renderer == RENDERER_REMOTION:
        storyboard_rel = str(recorded.get("storyboard") or "")
        storyboard_path = (workspace / storyboard_rel).resolve() if storyboard_rel else None
        current = remotion.build_input_fingerprint(
            storyboard_path=storyboard_path if storyboard_path and storyboard_path.is_file() else None,
            content_root=workspace,
            workspace_root=workspace,
        )["files"]
        old = (recorded.get("assets") or {}).get("files") or {}
        return _compare_fingerprint(old, current, workspace, mounts, label="构建输入")

    page_rel = str(recorded.get("page") or "")
    page_file = assets.key_path(page_rel, workspace, mounts) if page_rel else None
    if page_file is None or not page_file.is_file():
        return {"status": "unknown", "detail": f"溯源里的网页 {page_rel or '(未记录)'} 找不到了，无法判断", **empty}

    html = page_file.read_text(encoding="utf-8", errors="replace")
    current = asset_fingerprint(page_file, html, workspace_root=workspace)["files"]
    old = (recorded.get("assets") or {}).get("files") or {}
    return _compare_fingerprint(old, current, workspace, mounts, label="资产")


def _compare_fingerprint(
    old: dict, current: dict, workspace: Path, mounts: dict[str, Path], *, label: str
) -> dict:
    """逐项复核指纹，并把差异说成人能照着修的一句话。"""
    changed: list[str] = []
    missing: list[str] = []
    unverifiable: list[str] = []
    asset_suffixes = (".css", ".js", ".json", ".html", ".htm", ".ts", ".tsx")
    for key, digest in old.items():
        path = assets.key_path(str(key), workspace, mounts)
        if path is None or not path.is_file():
            (missing if key.endswith(asset_suffixes) else unverifiable).append(key)
        elif file_digest(path) != digest:
            changed.append(key)
    added = [key for key in current if key not in old]

    status = "stale" if (changed or missing or added) else "current"
    if status == "stale":
        parts = []
        if changed:
            parts.append("改了：" + "、".join(sorted(changed)))
        if added:
            parts.append("新引用：" + "、".join(sorted(added)))
        if missing:
            parts.append("不见了：" + "、".join(sorted(missing)))
        detail = "；".join(parts)
    else:
        detail = f"溯源里的{label}指纹逐个对得上" + (
            f"（{len(unverifiable)} 项无法复核：{'、'.join(sorted(unverifiable))}）" if unverifiable else ""
        )
    return {"status": status, "detail": detail, "changed": sorted(changed), "missing": sorted(missing), "unverifiable": sorted(unverifiable)}


def _fingerprint_mounts(workspace_root: str | Path | None = None) -> dict[str, Path]:
    """复核指纹时用的挂载表。

    与写入时保持同一套别名，否则别名键会因为解析不到而被判成「不见了」——
    那是最糟的一种错报：它让「资产真的改了」淹没在噪音里。
    """
    try:
        return remotion.fingerprint_mounts(workspace_root=workspace_root)
    except A2VError:  # `web/` 不存在（只留了旧页面的裁剪副本）：退回共享资产别名
        return assets.default_mounts()


def _finalize_output(
    *,
    video_path: Path,
    temp: Path,
    output_path: Path,
    total_frames: int,
    fps: int,
    width: int,
    height: int,
    media: Media | None,
    probe: bool,
    frame_start: int = 0,
    subtitle_offset: float | None = None,
    timings: perf.StageTimings | None = None,
) -> Path:
    """两条渲染路径共用的收口：合音轨、验成片、搬到最终位置、修权限。

    共用是刻意的：帧数、分辨率、帧率、音轨参数都是验收项，
    两条路径各写一遍迟早会出现「一条路径的成片能过、另一条过不了」，
    而那种差异只会在交付之后被人发现。

    `timings` 给出时，合音轨与验收分别计时；没执行的那一段记「跳过」而不是 0。
    """
    final_path = video_path
    if media:
        final_path = temp / "final.mp4"
        offset = frame_start / fps if subtitle_offset is None else subtitle_offset
        with perf.measure(timings, "mux"):
            mux(video_path, media.audio, final_path, total_frames / fps, start=offset)
        cues = [
            {**cue, "start": max(cue["start"] - offset, 0), "end": cue["end"] - offset}
            for cue in media.data["cues"]
            if cue["end"] > offset and cue["start"] < offset + total_frames / fps
        ]
        (temp / "subtitles.srt").write_text(
            srt(cues, total_frames / fps), encoding="utf-8"
        )
    elif timings is not None:
        timings.skip("mux")
    if probe:
        with perf.measure(timings, "probe"):
            _verify_output(final_path, total_frames, width, height, fps, expect_audio=media is not None)
    elif timings is not None:
        timings.skip("probe")
    final_path.replace(output_path)
    if media:
        (temp / "subtitles.srt").replace(output_path.with_suffix(".srt"))
    # 成片经由临时目录中转，Windows 下会把临时目录那份「关闭继承」的 ACL 带过来；
    # 不修的话标准权限的播放器（Windows 11 新版媒体播放器）会报 0x80070005。
    _grant_access(output_path)
    if media:
        _grant_access(output_path.with_suffix(".srt"))
    return final_path


def render_with_remotion(
    output: str | Path,
    storyboard: Storyboard,
    storyboard_path: str | Path | None = None,
    crf: int = 18,
    preset: str = "medium",
    limit_frames: int | None = None,
    timeout_ms: int = 30000,
    probe: bool = True,
    media: Media | None = None,
    storyboard_url: str | None = None,
    storyboard_origin: str | Path | None = None,
    workspace_root: str | Path | None = None,
    content_root: str | Path | None = None,
    frame_range: tuple[int, int] | None = None,
    scale: float = 1,
    concurrency: int = remotion.DEFAULT_CONCURRENCY,
    bundle_cache: bool = True,
) -> RenderResult:
    """用 React composition（Remotion）逐帧渲染并编码成片。

    与网页路径的区别只有「画面从哪来」：这里画面由 composition 的源码决定，
    因此不再有网页可查——取而代之的是渲染前先向 composition 要一份真实元数据
    （fps / 尺寸 / 总帧数），并用**同一组判定函数**与分镜交叉校验。
    合音轨、成片验收、交付权限与溯源与网页路径共用同一段代码。

    打包走本地缓存（键覆盖全部构建输入，命中前逐文件复核完整性）；渲染走
    **同一个 Node 会话**：只开一个浏览器，元数据交叉校验通过后才下发渲染参数。
    两条都与画质无关——分辨率、CRF、JPEG 质量、编码参数与验收标准都不变。
    本次的分阶段耗时、缓存状态与实际并发写进同级的 `<名字>.performance.json`。
    """
    started = time.monotonic()
    concurrency = remotion.check_concurrency(concurrency)
    output_path = Path(output)
    if not 0 < scale <= 1:
        raise RenderError("输出缩放比例必须大于 0 且不超过 1")
    if storyboard_path is None:
        raise RenderError("Remotion 路径需要分镜文件：它是 composition 的 props")

    if media:
        if media.data.get("version") != 4:
            raise RenderError("媒体清单版本过旧（v4 之前的幕级时间轴），请按 v4 契约重新 prepare")
        from .media import fingerprint
        try:
            source_data = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RenderError(f"读取 v4 源分镜失败：{exc}") from exc
        if fingerprint(source_data) != media.data.get("sourceFingerprint"):
            raise RenderError("媒体与分镜不匹配，请重新 prepare")
        storyboard = media.storyboard
    output_path.parent.mkdir(parents=True, exist_ok=True)

    props = Path(storyboard_path).resolve()
    if not props.is_file():
        raise RenderError(f"分镜文件不存在: {props}")

    directory = remotion.require_environment()
    timings = perf.StageTimings()
    #: 会话回调里算出来的画面参数；渲染失败时不会用到
    resolved: dict[str, int] = {}
    with contextlib.ExitStack() as stack:
        temp = Path(stack.enter_context(tempfile.TemporaryDirectory(dir=output_path.parent)))
        video_path = temp / "video.mp4"

        if media is not None:
            # composition 的时长由 props 推导：--media 时 props 必须换成
            # 媒体派生的有效分镜，否则画面按声明时长走、音轨按派生时长合成，
            # 总帧数交叉校验直接失败。打包仍用原始路径：代码场景清单与
            # 作品归属按原分镜与文章目录解析。
            props = write_effective_storyboard(media, temp)

        outcome = remotion.bundle(
            web_dir=directory,
            out_dir=temp / "bundle",
            storyboard_path=storyboard_path,
            content_root=content_root,
            workspace_root=workspace_root,
            cache=bundle_cache,
        )
        if outcome.cache_status == "hit":
            timings.skip("bundle")
        else:
            timings.record("bundle", outcome.build_seconds)
        if outcome.cache_status == "disabled":
            timings.skip("cache")
        else:
            timings.record("cache", outcome.cache_seconds)

        def confirm(declared: remotion.CompositionMetadata) -> dict:
            """元数据交叉校验通过后才向 Node 下发渲染参数。

            这里用的判定函数与网页路径完全一致：`_resolve_fps` /
            `_resolve_dimensions` / `_resolve_total_frames`。校验不通过时抛错，
            会话随即收到 ABORT 并收掉进程树——**一帧都不会渲**。
            """
            contract = declared.contract
            effective_fps = _resolve_fps(contract, storyboard, None)
            width, height = _resolve_dimensions(contract, storyboard)
            output_width, output_height = round(width * scale), round(height * scale)
            if output_width % 2 or output_height % 2:
                raise RenderError(f"缩放后尺寸必须为偶数，当前为 {output_width}×{output_height}")
            total_frames = _resolve_total_frames(contract, storyboard)
            logger.info(
                "composition 契约: %d fps, %d 帧, %dx%d（并发 %d）",
                effective_fps, total_frames, width, height, concurrency,
            )
            if frame_range is not None:
                start_frame, end_frame = frame_range
                if start_frame < 0 or end_frame < start_frame or end_frame >= total_frames:
                    raise RenderError(
                        f"全局帧范围无效：{start_frame}-{end_frame}，总帧数 {total_frames}"
                    )
                rendered_frames = end_frame - start_frame + 1
            else:
                start_frame = 0
                rendered_frames = total_frames
            if limit_frames is not None:
                rendered_frames = min(rendered_frames, max(limit_frames, 1))
                logger.warning("调试模式：仅渲染 %d 帧", rendered_frames)
            resolved.update(
                fps=effective_fps,
                width=width,
                height=height,
                output_width=output_width,
                output_height=output_height,
                start_frame=start_frame,
                rendered_frames=rendered_frames,
            )
            return {
                "out": str(video_path),
                "crf": crf,
                "preset": preset,
                # 显式给出帧区间：composition 自己也有时长，但**渲染的帧数**是验收项，
                # 让它由 Python 算出来并写死，比隐含在画面里可核对
                "frames": f"{start_frame}-{start_frame + rendered_frames - 1}",
                "scale": scale,
                "concurrency": concurrency,
                # 仅供 Python 侧的进度日志使用；Node 不读这个字段
                "progressTotal": rendered_frames,
            }

        session_started = time.monotonic()
        session_info = remotion.render_session(
            web_dir=directory,
            bundle_dir=outcome.path,
            props=props,
            on_metadata=confirm,
            # 逐帧渲染按分钟计，命令行给的 timeout 是**页面**超时，
            # 拿它当渲染超时会让正常的大项目渲染被误杀
            timeout_s=max(timeout_ms / 1000 * 60, 3600.0),
        )
        session_seconds = time.monotonic() - session_started
        handshake_seconds = float(session_info.get("readySeconds") or 0.0)
        timings.record("metadata", handshake_seconds)
        # 渲染与编码在 Remotion 内部重叠，只记一段合并耗时
        timings.record("render", max(session_seconds - handshake_seconds, 0.0))
        capture_seconds = session_seconds

        _finalize_output(
            video_path=video_path,
            temp=temp,
            output_path=output_path,
            total_frames=resolved["rendered_frames"],
            fps=resolved["fps"],
            width=resolved["output_width"],
            height=resolved["output_height"],
            media=media,
            probe=probe,
            frame_start=resolved["start_frame"],
            subtitle_offset=resolved["start_frame"] / resolved["fps"],
            timings=timings,
        )

    entry = directory / remotion.ENTRY_POINT
    # 打包时已经算过构建输入指纹：直接复用，不再对同一批文件哈希第二遍
    # （禁用缓存的路径没有这份指纹，那时才算）
    assets = outcome.input_fingerprint or remotion.build_input_fingerprint(
        storyboard_path=storyboard_path,
        content_root=content_root or workspace_root,
        workspace_root=workspace_root,
    )
    _write_provenance(
        output_path,
        page_file=entry,
        storyboard_url=storyboard_url,
        storyboard_origin=storyboard_origin,
        workspace_root=workspace_root,
        frames=resolved["rendered_frames"],
        fps=resolved["fps"],
        width=resolved["output_width"],
        height=resolved["output_height"],
        capture_format="remotion",
        media_fingerprint=(media.data.get("sourceFingerprint") if media else None),
        renderer=RENDERER_REMOTION,
        assets_override=assets,
    )

    total_seconds = time.monotonic() - started
    report_path = _write_performance_report(
        output=output_path,
        storyboard_path=storyboard_path,
        resolved=resolved,
        concurrency=concurrency,
        timings=timings,
        total_seconds=total_seconds,
        outcome=outcome,
        session_info=session_info,
    )

    return RenderResult(
        output=output_path,
        frames=resolved["rendered_frames"],
        fps=resolved["fps"],
        width=resolved["output_width"],
        height=resolved["output_height"],
        duration_seconds=resolved["rendered_frames"] / resolved["fps"],
        capture_seconds=capture_seconds,
        total_seconds=total_seconds,
        size_bytes=output_path.stat().st_size,
        cache_status=outcome.cache_status,
        concurrency=concurrency,
        stages=timings.as_dict(),
        performance_path=report_path,
    )


def _write_performance_report(
    *,
    output: Path,
    storyboard_path: str | Path | None,
    resolved: dict[str, int],
    concurrency: int,
    timings: perf.StageTimings,
    total_seconds: float,
    outcome: remotion.BundleOutcome,
    session_info: dict,
) -> Path | None:
    """写结构化性能报告；失败只记警告，不牵动已经验收通过的成片。"""
    payload = perf.build_report(
        entry="render",
        output=output,
        storyboard=storyboard_path,
        frames=resolved["rendered_frames"],
        fps=resolved["fps"],
        width=resolved["output_width"],
        height=resolved["output_height"],
        concurrency=concurrency,
        timings=timings,
        total_seconds=total_seconds,
        cache={
            "status": outcome.cache_status,
            "key": outcome.cache_key,
            "detail": outcome.cache_detail,
            "prepareSeconds": round(outcome.cache_seconds, 3),
            "buildSeconds": round(outcome.build_seconds, 3),
        },
        extra={
            "session": {
                "browsersOpened": session_info.get("browsersOpened"),
                "handshakeSeconds": round(float(session_info.get("readySeconds") or 0.0), 3),
            }
        },
    )
    try:
        target = perf.write_report(perf.report_path_for(output), payload)
    except OSError as exc:  # 报告是附加信息，写不出来不改变成片结论
        logger.warning("性能报告写入失败（不影响成片）：%s", exc)
        return None
    logger.info(
        "性能报告 %s：总耗时 %.1fs，缓存%s，并发 %d",
        target.name,
        total_seconds,
        {"hit": "命中", "miss": "未命中", "disabled": "已禁用"}[outcome.cache_status],
        concurrency,
    )
    return target


@contextlib.contextmanager
def _resolve_page_url(
    page_path: str | Path,
    serve_root: str | Path | None,
    mounts: dict[str, Path] | None = None,
) -> Iterator[str]:
    """把本地网页路径转成可用的 URL。

    远程 URL 原样透传；本地文件通过临时静态服务器暴露，因为契约页需要
    读到分镜 JSON，而 file:// 下会被同源策略拒绝。

    mounts 由调用方给出：契约页在仓库的 `web/` 下、分镜在工作区根下，
    两者不在同一棵树里，靠 `/__a2v_web__/` 别名而不是相对路径接起来。
    """
    text = str(page_path)
    if text.startswith(("http://", "https://")):
        yield text
        return

    page_file = Path(text).resolve()
    if not page_file.is_file():
        raise RenderError(f"页面文件不存在: {page_file}")

    root = Path(serve_root).resolve() if serve_root else _default_serve_root(page_file)
    with LocalServer(root, mounts=assets.default_mounts() if mounts is None else mounts) as server:
        try:
            url = server.url_for(page_file)
        except A2VError as exc:  # 网页既不在静态根、也不在别名目录里
            raise RenderError(str(exc)) from exc
        yield url


def _default_serve_root(page_file: Path, content_root: str | Path | None = None) -> Path:
    """选择静态根目录。

    取文章所属的**工作区根**：仓库内的页面（示例、仓库内文章）拿到仓库根，
    内容根里的页面拿到内容根，于是同目录的 storyboard.json 与页面内资产
    都能通过相对路径访问；契约页与前端工程资产走 `/__a2v_web__/` 别名，
    与静态根在哪无关。
    推导不出来时（任意位置的页面、远程页面）退回网页所在目录。
    """
    try:
        return paths.for_page(page_file, content_root).workspace_root
    except A2VError:
        return page_file.parent


def _resolve_dimensions(contract: PageContract, storyboard: Storyboard | None) -> tuple[int, int]:
    """画面尺寸：以画面声明的契约为准，与分镜不一致时报错并**列出两边的值**。

    只写「尺寸不一致」是不够的：这句话既没说哪一边对，也没说差多少，
    而两种可能（改错了分镜、改错了画面）需要完全相反的修法。
    """
    width, height = contract.width, contract.height
    if storyboard and (width, height) != (storyboard.width, storyboard.height):
        raise RenderError(
            f"画面尺寸不一致：画面声明 {width}×{height}，"
            f"分镜脚本声明 {storyboard.width}×{storyboard.height}"
        )
    return width, height


def _resolve_fps(contract: PageContract, storyboard: Storyboard | None, fps: int | None) -> int:
    contract_fps = contract.fps
    if storyboard and contract_fps != storyboard.fps:
        raise RenderError(
            f"帧率不一致：画面声明 {contract_fps}fps，分镜脚本声明 {storyboard.fps}fps"
        )
    if fps and contract_fps != fps:
        raise RenderError(f"帧率不一致：画面声明 {contract_fps}fps，命令行指定 {fps}fps")
    return contract_fps


def _resolve_total_frames(contract: PageContract, storyboard: Storyboard | None) -> int:
    contract_frames = contract.duration_in_frames
    if storyboard and contract_frames != storyboard.total_frames:
        raise RenderError(
            f"总帧数不一致：画面声明 {contract_frames} 帧，"
            f"分镜脚本累计 {storyboard.total_frames} 帧"
        )
    if contract_frames <= 0:
        raise RenderError("画面声明的 durationInFrames 必须为正整数")
    return contract_frames


def _verify_output(output: Path, expected_frames: int, width: int, height: int, fps: int, expect_audio: bool = False) -> None:
    """完整解码一遍成片，核对帧数、分辨率与帧率，避免「文件存在但不可播」。"""
    if not output.exists():
        raise RenderError("ffmpeg 没有生成输出文件")
    command = [
        get_ffmpeg_exe(),
        "-v",
        "error",
        "-i",
        str(output),
        "-map",
        "0:v:0",
        "-f",
        "null",
        "-",
        "-stats",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise RenderError(f"成片解码失败:\n{completed.stderr[-1500:]}")

    # image2pipe 的取整策略可能导致 ±1 帧，帧率用同一份取整逻辑比较
    reported = _last_int(completed.stderr, "frame=")
    if reported is not None and abs(reported - expected_frames) > 1:
        raise RenderError(f"成片帧数校验失败：期望 {expected_frames}，实际解码 {reported}")

    from imageio_ffmpeg import read_frames
    reader = read_frames(str(output))
    try:
        metadata = next(reader)
    finally:
        reader.close()
    if tuple(metadata["size"]) != (width, height) or abs(metadata["fps"] - fps) > 0.01:
        raise RenderError("成片尺寸或帧率不匹配")
    if abs(metadata["duration"] - expected_frames / fps) > max(0.1, 1 / fps):
        raise RenderError("成片时长不匹配")
    _verify_playback_compatibility(output)
    if expect_audio:
        # 解码到临时文件，长视频的 PCM 不常驻内存。
        with tempfile.TemporaryFile() as pcm:
            try:
                decoded = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(output),
                    "-map", "0:a:0", "-ac", "1", "-ar", "24000", "-f", "s16le", "-"],
                    stdout=pcm, stderr=subprocess.PIPE, timeout=300)
            except subprocess.TimeoutExpired as exc:
                raise RenderError("成片音轨验收超时") from exc
            if decoded.returncode or abs(pcm.tell() / 48000 - expected_frames / fps) > 0.1:
                raise RenderError("成片音轨缺失、不可解码或音画时长不一致")
    logger.info(
        "成片验收通过: %dx%d @ %dfps, 解码 %s 帧",
        width,
        height,
        fps,
        reported if reported is not None else "?",
    )


def _grant_access(path: Path) -> None:
    """把交付文件交回父目录的继承权限。

    成片、字幕都经临时目录中转，Windows 下会带上临时目录那份「关闭继承」的 ACL，
    标准权限的播放器（Windows 11 新版媒体播放器）因此报 0x80070005。修复失败只记
    日志，不影响已经渲染好的成片。
    """
    if not security.grant_inherited_access(path):
        logger.warning("未能修复 %s 的访问权限，打包应用可能无法打开该文件", path)


def _verify_playback_compatibility(output: Path) -> None:
    """核对码流参数是否落在「各播放器都认」的范围内。

    背景：JPEG 中间帧是全范围色彩，直接交给 libx264 会产出 yuvj420p(pc) 的流，
    Windows 的 Media Foundation 会以 0xc00d36c4 拒绝打开整个文件；而 ffmpeg
    自己解码一切正常，所以只做解码验收根本发现不了。这里从 ffmpeg 的输入信息里
    读回像素格式，把这类「能解码但播不了」的问题挡在交付之前。
    """
    completed = subprocess.run(
        [get_ffmpeg_exe(), "-hide_banner", "-i", str(output)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stream_line = next(
        (
            line
            for line in completed.stderr.splitlines()
            if "Video:" in line and "Stream #" in line
        ),
        None,
    )
    if stream_line is None:
        logger.warning("无法读取成片码流信息，跳过播放兼容性检查")
        return
    # 先判全范围：yuvj420p 也包含 "yuv420p" 子串，顺序反过来会报错报错原因
    if "yuvj420p" in stream_line or "(pc," in stream_line:
        raise RenderError(
            "成片使用了全范围像素格式（yuvj420p/pc），Windows 播放器会报 0xc00d36c4：\n"
            + stream_line.strip()
        )
    if "yuv420p(" not in stream_line:
        raise RenderError(
            "成片像素格式不是标准 4:2:0，部分播放器会拒绝打开：\n" + stream_line.strip()
        )
    logger.info("码流兼容性检查通过: %s", stream_line.split("Video:")[-1].split(",")[0].strip())


def _last_int(text: str, key: str) -> int | None:
    """从 ffmpeg 统计文本中提取 `key=<整数>` 的最后一个匹配。

    ffmpeg 的行内统计形如 `frame=  120 fps=...`，等号与数字之间可能有空格，
    因此不能按空白切分后直接取等号后的片段。
    """
    matches = re.findall(rf"{re.escape(key)}\s*(\d+)", text)
    return int(matches[-1]) if matches else None
