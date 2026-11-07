"""过程证据的最低媒体容量；不判断画面内容或时间窗对应。"""
from __future__ import annotations

import logging
import math
import re
import subprocess
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError

logger = logging.getLogger(__name__)
_cache = ContextVar('production_media_probe', default=None)
#: 解码只为读出视频流真实长度；损坏文件可能卡住，超时即判无效证据。
TIMEOUT = 120
#: 微秒级量化误差吸收：只覆盖 ffmpeg 进度的时间精度，远小于一帧。
EPSILON = 1e-5
_PROGRESS = re.compile(r'^(frame|out_time_us)=(.+)$', re.M)


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


def _progress(text: str) -> tuple[int | None, float | None]:
    frames, seconds = None, None
    for match in _PROGRESS.finditer(text):
        key, value = match.group(1), match.group(2)
        try:
            if key == 'frame':
                frames = int(value)
            else:
                number = float(value) / 1_000_000
                if math.isfinite(number) and number >= 0:
                    seconds = number
        except ValueError:
            continue
    return frames, seconds


def probe(path: Path) -> float:
    """只解码视频流读出长度；容器中的长音轨不能补足短视频。

    使用依赖内自带的 ffmpeg，不要求系统另装 ffprobe；``-map 0:v:0`` 让纯音频
    文件直接失败。``setpts`` 先把首帧 PTS 归零，避免视频前面的音轨或流把绝对
    时间戳垫长——否则 1 秒画面配长音轨会被读成 5 秒。
    """
    try:
        result = subprocess.run(
            [get_ffmpeg_exe(), '-v', 'error', '-nostdin', '-i', str(path), '-map', '0:v:0',
             '-vf', 'setpts=PTS-STARTPTS', '-f', 'null', '-', '-progress', 'pipe:1', '-nostats'],
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M2VError(f'无法探测视频：{exc}') from exc
    detail = result.stderr.strip().splitlines()[-1][:300] if result.stderr.strip() else ''
    if result.returncode:
        if 'matches no streams' in result.stderr or 'does not contain any stream' in result.stderr:
            raise M2VError('缺少有效视频流')
        raise M2VError('视频无法解码' + (f'：{detail}' if detail else ''))
    frames, last = _progress(result.stdout)
    if not frames or last is None or last < 0:
        raise M2VError('视频流没有可核验的正时长' + (f'：{detail}' if detail else ''))
    # 归零后只剩 N-1 个帧间隔，末帧自身时长按平均帧间隔补回；单帧按零长度处理。
    length = last * frames / (frames - 1) if frames > 1 else 0.0
    logger.debug('过程证据探测 %s：%.6fs（%d 帧）', path, length, frames)
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
            # 只缓存原因，不复用异常实例，避免多次 raise 时 traceback 串到首次调用点。
            cache[key] = str(exc)
    value = cache[key]
    if isinstance(value, str):
        raise M2VError(value)
    return value
