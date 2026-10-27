"""过程证据的最低媒体容量；不判断画面内容或时间窗对应。"""
from __future__ import annotations

import logging
import math
import subprocess
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError
from .storage import local

logger = logging.getLogger(__name__)
_cache = ContextVar('production_media_probe', default=None)
#: 解码只为读出视频流真实长度；损坏文件可能卡住，超时即判无效证据。
TIMEOUT = 120


@contextmanager
def snapshot():
    """成功和失败均在一次操作内复用；下一次查询必须重验。"""
    if _cache.get() is not None:
        yield
        return
    token = _cache.set({})
    try:
        yield
    finally:
        _cache.reset(token)


def _seconds(progress: str) -> float | None:
    values = [line.partition('=')[2] for line in progress.splitlines() if line.startswith('out_time_us=')]
    if not values:
        return None
    try:
        number = float(values[-1]) / 1_000_000
    except ValueError:
        return None
    return number if math.isfinite(number) and number > 0 else None


def probe(path: Path) -> float:
    """只解码视频流读出长度；容器中的长音轨不能补足短视频。

    使用依赖内自带的 ffmpeg，不要求系统另装 ffprobe；``-map 0:v:0`` 让纯音频
    文件直接失败，而不是用容器时长冒充视频长度。
    """
    try:
        result = subprocess.run(
            [get_ffmpeg_exe(), '-v', 'error', '-nostdin', '-i', str(path), '-map', '0:v:0',
             '-f', 'null', '-', '-progress', 'pipe:1', '-nostats'],
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M2VError(f'无法探测视频：{exc}') from exc
    detail = result.stderr.strip().splitlines()[-1][:300] if result.stderr.strip() else ''
    if result.returncode:
        if 'matches no streams' in result.stderr or 'does not contain any stream' in result.stderr:
            raise M2VError('缺少有效视频流')
        raise M2VError('视频无法解码' + (f'：{detail}' if detail else ''))
    length = _seconds(result.stdout)
    if length is None:
        raise M2VError('视频流没有可核验的正时长' + (f'：{detail}' if detail else ''))
    logger.debug('过程证据探测 %s：%.6fs', path, length)
    return length


def duration(path: Path) -> float:
    cache = _cache.get()
    key = path.resolve()
    if cache is None:
        return probe(path)
    if key not in cache:
        try:
            cache[key] = probe(path)
        except M2VError as exc:
            cache[key] = exc
    value = cache[key]
    if isinstance(value, M2VError):
        raise value
    return value


def validate(items: list, c: dict, base: Path, checkpoint_ids: set[str]) -> None:
    """每项至少一段够长；禁止将多个短片段求和。"""
    fps = c['fps']
    with snapshot():
        for item in items:
            try:
                cid = item['checkpointId']
            except (KeyError, TypeError) as exc:
                raise M2VError(f'过程证据记录无效：{exc}') from exc
            if cid not in checkpoint_ids:
                continue
            try:
                required = (item['window'][1] - item['window'][0]) / fps
                videos = [e['path'] for e in item['evidence'] if Path(e['path']).suffix.lower() in ('.mp4', '.webm')]
            except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
                raise M2VError(f'{cid}：过程证据记录无效：{exc}') from exc
            if not videos:
                raise M2VError(f'{cid}：动态核心需要完整过程片段，端点静帧不足')
            lengths = []
            for reference in videos:
                try:
                    lengths.append(duration(local(base, reference)))
                except M2VError as exc:
                    raise M2VError(f'{cid}：{reference}：{exc}') from exc
            if max(lengths) + 1 / fps + 1e-9 < required:
                raise M2VError(f'{cid}：{", ".join(videos)}：过程片段最长 {max(lengths):.6f}s，'
                               f'检查窗需要 {required:.6f}s（容差一帧）')

