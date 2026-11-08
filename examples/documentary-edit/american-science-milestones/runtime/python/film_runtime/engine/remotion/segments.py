"""按帧区间分进程渲染，再无损拼接。

这是 `--jobs > 1` 的实现：每个区间独立起 Node/浏览器，编码参数与单进程完全一致；
每段先解码核对帧数、尺寸与帧率，拼接后再核对总帧数，最后才交给调用方混音与交付。
任一段失败都不发布半成品。
"""
from __future__ import annotations

import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from film_runtime.core import security
from film_runtime.engine import audio, output_validation
from .process import RemotionError, check_concurrency
from .session import metadata, render_frames


def frame_ranges(total_frames: int, jobs: int) -> list[tuple[int, int]]:
    """把 [0,total) 切成 jobs 个近似等长的半开区间；jobs 不超过总帧数。"""
    jobs = check_concurrency(jobs)
    if total_frames < 1:
        raise RemotionError(f"总帧数必须大于 0，收到 {total_frames}")
    jobs = min(jobs, total_frames)
    cuts = [round(total_frames * index / jobs) for index in range(jobs + 1)]
    return [(cuts[index], cuts[index + 1]) for index in range(jobs)]


def render_parallel(
    *,
    web_dir: Path,
    bundle_dir: Path,
    props: Path,
    composition_id: str,
    out: Path,
    total_frames: int,
    fps: int,
    width: int,
    height: int,
    crf: int,
    preset: str,
    jobs: int,
    timeout_s: float = 3600,
) -> Path:
    if jobs < 2:
        raise RemotionError("分段渲染至少需要 2 个进程")
    expected = (fps, width, height, total_frames)
    actual = metadata(web_dir=web_dir, bundle_dir=bundle_dir, props=props,
                      composition_id=composition_id)
    if (actual.fps, actual.width, actual.height, actual.duration_in_frames) != expected:
        raise RemotionError(
            f"分段渲染元数据不匹配：期望 {expected}，实际 "
            f"{(actual.fps, actual.width, actual.height, actual.duration_in_frames)}")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m2v-parts-", dir=out.parent) as temporary:
        work = Path(temporary)
        ranges = frame_ranges(total_frames, jobs)

        def render(index: int, start: int, end: int) -> Path:
            part = work / f"part-{index:02d}.mp4"
            render_frames(
                web_dir=web_dir, bundle_dir=bundle_dir, props=props, out=part,
                total_frames=end - start, crf=crf, preset=preset, timeout_s=timeout_s,
                frame_start=start, scale=1, composition_id=composition_id, concurrency=1)
            output_validation.verify_output(part, end - start, width, height, fps)
            return part

        with ThreadPoolExecutor(max_workers=len(ranges)) as pool:
            parts = list(pool.map(lambda item: render(item[0], *item[1]), enumerate(ranges)))
        listing = work / "parts.txt"
        listing.write_text("".join(f"file '{part.as_posix()}'\n" for part in parts),
                           encoding="utf-8")
        combined = work / "combined.mp4"
        try:
            audio.ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing),
                          "-c", "copy", str(combined)])
        except Exception as exc:
            raise RemotionError(f"分段片段拼接失败：{exc}") from exc
        output_validation.verify_output(combined, total_frames, width, height, fps)
        security.deliver(combined, out)
    return out
