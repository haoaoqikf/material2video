"""逐帧渲染编排：驱动网页 seek → 截图 → 送入编码器。

这里集中处理三件事：
1. 契约一致性检查（网页声明的 fps/尺寸必须与渲染请求一致）；
2. 帧循环与进度日志；
3. 编码完成后的成片验收（帧数、分辨率、可解码性）。
"""

from __future__ import annotations

import contextlib
import logging
import re
import subprocess
import time
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from imageio_ffmpeg import get_ffmpeg_exe

from . import paths, security
from .audio import mux
from .browser import AnimatedPage, open_animated_page
from .encoder import VideoEncoder
from .errors import A2VError
from .media import Media, media_url
from .static_server import LocalServer
from .storyboard import Storyboard
from .subtitles import srt

logger = logging.getLogger(__name__)


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
    capture_seconds: float
    total_seconds: float
    size_bytes: int

    def summary(self) -> str:
        rate = self.frames / self.capture_seconds if self.capture_seconds else 0
        return (
            f"输出 {self.output}：{self.frames} 帧 / {self.duration_seconds:.1f}s，"
            f"{self.width}x{self.height} @{self.fps}fps，"
            f"截图 {self.capture_seconds:.1f}s（约 {rate:.1f} 帧/秒），"
            f"总耗时 {self.total_seconds:.1f}s，"
            f"文件 {self.size_bytes / 1024 / 1024:.1f} MiB"
        )


def render(
    page_path: str | Path,
    output: str | Path,
    storyboard: Storyboard | None = None,
    fps: int | None = None,
    crf: int = 18,
    preset: str = "medium",
    limit_frames: int | None = None,
    timeout_ms: int = 30000,
    probe: bool = True,
    serve_root: str | Path | None = None,
    capture_format: str = "jpeg",
    media: Media | None = None,
) -> RenderResult:
    """把动画网页逐帧渲染为 MP4。

    storyboard 提供时，以其 fps/尺寸为准并与网页契约交叉校验，用于尽早
    发现「改了脚本没改网页」这类不一致。
    """
    started = time.monotonic()
    output_path = Path(output)

    if media:
        from . import storyboard as sb
        source_model = sb._build(media.data["source"], sb.Report())
        if storyboard != source_model:
            raise RenderError("媒体与分镜不匹配，请重新 prepare")
        storyboard = media.storyboard
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack:
        temp = Path(stack.enter_context(tempfile.TemporaryDirectory(dir=output_path.parent)))
        video_path = temp / "video.mp4"
        url = stack.enter_context(_resolve_page_url(page_path, serve_root))
        if media:
            media_server = stack.enter_context(LocalServer(media.path.parent, cors=True))
            url = media_url(url, media_server.base_url, media)
        with open_animated_page(
            url,
            timeout_ms=timeout_ms,
            width=storyboard.width if storyboard else None,
            height=storyboard.height if storyboard else None,
        ) as page:
            if media and page.evaluate("() => window.__A2V__.mediaFingerprint") != media.data["sourceFingerprint"]:
                raise RenderError("网页未加载媒体清单，请使用 A2V.fetchStoryboard")
            effective_fps = _resolve_fps(page, storyboard, fps)
            if storyboard and (page.contract.width, page.contract.height) != (storyboard.width, storyboard.height):
                raise RenderError("网页与分镜的画面尺寸不一致")
            total_frames = _resolve_total_frames(page, storyboard)
            width, height = page.contract.width, page.contract.height

            if limit_frames is not None:
                total_frames = min(total_frames, max(limit_frames, 1))
                logger.warning("调试模式：仅渲染前 %d 帧", total_frames)

            # 进入渲染模式：隐藏预览控件并取消预览缩放，保证画面严格等于设计尺寸
            page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
            _precheck_dimensions(page)
            _warn_on_time_driven_motion(page_path)

            capture_started = time.monotonic()
            _encode(page, video_path, total_frames, effective_fps, crf, preset, capture_format)
            capture_seconds = time.monotonic() - capture_started

        final_path = video_path
        if media:
            final_path = temp / "final.mp4"
            mux(video_path, media.audio, final_path, total_frames / effective_fps)
            (temp / "subtitles.srt").write_text(srt(media.data["cues"], total_frames / effective_fps), encoding="utf-8")
        if probe:
            _verify_output(final_path, total_frames, width, height, effective_fps, expect_audio=media is not None)
        final_path.replace(output_path)
        if media:
            (temp / "subtitles.srt").replace(output_path.with_suffix(".srt"))
        # 成片经由临时目录中转，Windows 下会把临时目录那份「关闭继承」的 ACL 带过来；
        # 不修的话标准权限的播放器（Windows 11 新版媒体播放器）会报 0x80070005。
        _grant_access(output_path)
        if media:
            _grant_access(output_path.with_suffix(".srt"))

    return RenderResult(
        output=output_path,
        frames=total_frames,
        fps=effective_fps,
        width=width,
        height=height,
        duration_seconds=total_frames / effective_fps,
        capture_seconds=capture_seconds,
        total_seconds=time.monotonic() - started,
        size_bytes=output_path.stat().st_size,
    )


@contextlib.contextmanager
def _resolve_page_url(
    page_path: str | Path, serve_root: str | Path | None
) -> Iterator[str]:
    """把本地网页路径转成可用的 URL。

    远程 URL 原样透传；本地文件通过临时静态服务器暴露，因为网页需要
    fetch 同目录的分镜 JSON，而 file:// 下会被同源策略拒绝。
    """
    text = str(page_path)
    if text.startswith(("http://", "https://")):
        yield text
        return

    page_file = Path(text).resolve()
    if not page_file.is_file():
        raise RenderError(f"动画网页不存在: {page_file}")

    root = Path(serve_root).resolve() if serve_root else _default_serve_root(page_file)
    with LocalServer(root) as server:
        try:
            relative = page_file.relative_to(server.root)
        except ValueError as exc:
            raise RenderError(f"网页 {page_file} 不在静态根目录 {server.root} 之内") from exc
        yield f"{server.base_url}/{relative.as_posix()}"


def _default_serve_root(page_file: Path) -> Path:
    """选择静态根目录。

    网页通常既引用同目录的 storyboard.json，也引用仓库内共享的 skill 资产
    （base.css / timeline.js），因此默认取项目根目录（含
    `.agents/skills/article2video/SKILL.md` 的那一层），让两者都能通过相对
    路径访问；不在 article2video 项目内时退回网页所在目录。
    """
    try:
        return paths.project_root(page_file)
    except A2VError:
        return page_file.parent


def _resolve_fps(page: AnimatedPage, storyboard: Storyboard | None, fps: int | None) -> int:
    contract_fps = page.contract.fps
    if storyboard and contract_fps != storyboard.fps:
        raise RenderError(
            f"帧率不一致：网页声明 {contract_fps}fps，分镜脚本声明 {storyboard.fps}fps"
        )
    if fps and contract_fps != fps:
        raise RenderError(f"帧率不一致：网页声明 {contract_fps}fps，命令行指定 {fps}fps")
    return contract_fps


def _resolve_total_frames(page: AnimatedPage, storyboard: Storyboard | None) -> int:
    contract_frames = page.contract.duration_in_frames
    if storyboard and contract_frames != storyboard.total_frames:
        raise RenderError(
            f"总帧数不一致：网页声明 {contract_frames} 帧，"
            f"分镜脚本累计 {storyboard.total_frames} 帧"
        )
    if contract_frames <= 0:
        raise RenderError("网页声明的 durationInFrames 必须为正整数")
    return contract_frames


def _precheck_dimensions(page: AnimatedPage) -> None:
    """在开渲前确认网页画面恰好填满视口，失败信息直接指向具体 CSS 问题。"""
    actual = page.evaluate(
        "() => ({w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight,"
        "vw: window.innerWidth, vh: window.innerHeight,"
        "root: (() => {const el=document.querySelector('[data-a2v-stage]')||document.body;"
        "const r=el.getBoundingClientRect();return {w:Math.round(r.width),h:Math.round(r.height)};})()})"
    )
    if actual["w"] > actual["vw"] or actual["h"] > actual["vh"]:
        logger.warning(
            "文档尺寸 %sx%s 超出视口 %sx%s，可能存在溢出内容被裁切",
            actual["w"],
            actual["h"],
            actual["vw"],
            actual["vh"],
        )
    if actual["root"]["w"] != page.contract.width or actual["root"]["h"] != page.contract.height:
        logger.warning(
            "舞台元素实际尺寸 %sx%s 与契约 %dx%d 不一致，请检查缩放设置",
            actual["root"]["w"],
            actual["root"]["h"],
            page.contract.width,
            page.contract.height,
        )


# 由浏览器时钟驱动、与帧号脱钩的动效声明。命中时画面在逐帧截图下可能闪烁。
_TIME_DRIVEN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"@keyframes\b"), "@keyframes"),
    (re.compile(r"(?<![\w-])animation(?:-[\w-]+)?\s*:"), "animation"),
    (re.compile(r"(?<![\w-])transition(?:-[\w-]+)?\s*:"), "transition"),
)

# 让画面脱离帧号的时间源与随机源。命中时同一帧会渲染出不同结果。
_NON_DETERMINISTIC_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bDate\.now\s*\("), "Date.now()"),
    (re.compile(r"\bperformance\.now\s*\("), "performance.now()"),
    (re.compile(r"\bMath\.random\s*\("), "Math.random()"),
)

_PROJECT_MARKERS = (".git", "pyproject.toml")


def _project_root(start: Path) -> Path | None:
    """从网页所在目录向上找项目根，用来界定「可以扫描的本地资源」。

    共享资产（如 skill 的 assets/）通常不在网页目录内，只按网页目录判断会漏扫；
    但也不能顺着相对路径读到仓库外的任意文件，因此以项目标记为界。
    """
    current = start.resolve()
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in _PROJECT_MARKERS):
            return candidate
    return None


def _local_assets(page: Path, html: str) -> list[tuple[str, Path]]:
    """收集网页引用到的本地样式表与脚本，跳过远程与范围外的路径。"""
    root = _project_root(page.parent)
    found: list[tuple[str, Path]] = []
    pattern = re.compile(
        r"""<(?:link[^>]+href|script[^>]+src)=["']([^"']+\.(?:css|js))["']""",
        re.IGNORECASE,
    )
    for reference in pattern.findall(html):
        if reference.startswith(("http://", "https://", "//")):
            continue
        candidate = (page.parent / reference.split("?")[0].split("#")[0]).resolve()
        if not candidate.is_file():
            continue
        inside_page_dir = page.parent.resolve() in candidate.parents
        inside_project = root is not None and root in candidate.parents
        if not (inside_page_dir or inside_project):
            continue
        found.append((reference, candidate))
    return found


def _warn_on_time_driven_motion(page_path: str | Path) -> None:
    """渲染前静态扫描样式与脚本，提示与帧号脱钩的写法。

    网页契约由「同一帧重复渲染一致」的运行时测试保证，这里只做一次廉价的
    静态提示：CSS animation/transition 由浏览器时钟驱动，Date.now/Math.random
    让同一帧在不同时刻得到不同结果，典型表现是视频里出现随机闪烁。
    只提示不阻断——是否闪烁最终由确定性验收决定。

    扫描范围包含网页引用的本地样式表与脚本（含 skill 的共享资产），
    否则把动效写进共享组件库就能绕过这道检查。
    """
    page = Path(str(page_path))
    if not page.is_file():
        return
    try:
        html = page.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    targets: list[tuple[str, str]] = [(page.name, html)]
    for reference, candidate in _local_assets(page, html):
        try:
            targets.append((reference, candidate.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue

    for name, text in targets:
        # 脚本只查时间与随机源：rAF 与 CSS transform 的静态写法本身是允许的
        patterns = (
            _NON_DETERMINISTIC_PATTERNS if name.endswith(".js") else _TIME_DRIVEN_PATTERNS
        )
        for pattern, label in patterns:
            match = pattern.search(text)
            if not match:
                continue
            line = text.count("\n", 0, match.start()) + 1
            if label in ("Date.now()", "performance.now()", "Math.random()"):
                hint = f"它让同一帧在不同时刻渲染出不同结果，请改为从 state.frame 推导"
            else:
                hint = "它由浏览器时钟驱动，逐帧截图可能闪烁"
            logger.warning(
                "%s:%d 使用了 %s：%s（见 references/render-contract.md）",
                name,
                line,
                label,
                hint,
            )


def _encode(
    page: AnimatedPage,
    output: Path,
    total_frames: int,
    fps: int,
    crf: int,
    preset: str,
    capture_format: str,
) -> None:
    """帧循环：seek 到第 n 帧后立刻截图，图片通过管道交给 ffmpeg。"""
    progress_every = max(fps, 1)
    input_codec = "png" if capture_format == "png" else "mjpeg"
    with VideoEncoder(
        output, fps=fps, crf=crf, preset=preset, input_codec=input_codec
    ) as encoder:
        for frame in range(total_frames):
            page.seek(frame)
            encoder.write(page.capture(capture_format))
            if frame % progress_every == 0 or frame == total_frames - 1:
                logger.info(
                    "已渲染 %d/%d 帧（%.1fs / %.1fs）",
                    frame + 1,
                    total_frames,
                    (frame + 1) / fps,
                    total_frames / fps,
                )


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
