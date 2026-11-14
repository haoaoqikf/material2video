"""受控本地媒体探测与 PTS 换算，不把名义帧率当作源时间。

旧尺寸探针只输出宽高，无法提供本工作层必需的流时间基和起始 PTS；这里使用
标准 ffprobe JSON，并复用项目的 FFmpeg 可执行文件。所有输入禁网络和清单格式。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, UnidentifiedImageError

from .contracts import Probe, SourceMapping, TimeBase, Timeline
from .errors import MaterialError
from .paths import no_links

# 不允许 concat/hls/dash/image2 等可由媒体内容引用任意其它文件的 demuxer。
LOCAL_FORMATS = ('mov,matroska,webm,avi,mpegts,mpeg,mpegvideo,ogg,mp3,wav,flac,aac,aiff,asf,flv,'
                 'png_pipe,jpeg_pipe,webp_pipe,bmp_pipe,tiff_pipe,gif,apng,ico')
LOCAL_INPUT_OPTIONS = ['-protocol_whitelist', 'file', '-format_whitelist', LOCAL_FORMATS]


def seconds_us(value) -> int:
    """以十进制文本换算，避免二进制浮点乘法令微秒在边界上漂移。"""
    if isinstance(value, bool):
        raise MaterialError('invalid-request', '时间不能使用布尔值', stage='probe')
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError
        return round(number * 1_000_000)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise MaterialError('invalid-request', '无效时间数值', stage='probe') from exc


def pts_us(pts: int, time_base: TimeBase) -> int:
    if type(pts) is not int:
        raise MaterialError('invalid-request', 'PTS 必须为整数', stage='probe')
    return round(Fraction(pts * time_base.num * 1_000_000, time_base.den))


@lru_cache(maxsize=1)
def ffprobe_exe() -> str:
    executable = os.environ.get('M2V_FFPROBE') or shutil.which('ffprobe')
    if not executable or not Path(executable).is_file():
        raise MaterialError('dependency-missing', '需要 ffprobe；请安装 FFmpeg 工具或显式配置 M2V_FFPROBE', stage='probe')
    return executable


def _probe_json(path: Path, entries: list[str], *, timeout_s: float = 120) -> dict:
    try:
        # ffprobe 不接受 FFmpeg 的 -nostdin；只使用固定探测参数，不接收用户额外命令。
        result = subprocess.run([ffprobe_exe(), '-v', 'error', '-max_alloc', '67108864',
                                 '-max_streams', '64', *LOCAL_INPUT_OPTIONS,
                                 *entries, '-of', 'json', '-i', str(path)],
                                capture_output=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        raise MaterialError('resource-limit', '素材探测超时', stage='probe') from exc
    if result.returncode:
        raise MaterialError('media-invalid', '无法探测本地媒体或格式被安全策略拒绝', stage='probe')
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise MaterialError('media-invalid', '媒体探测未返回有效结构', stage='probe') from exc


def _rational(value: str | None) -> TimeBase | None:
    try:
        rational = Fraction(value or '0')
        return TimeBase(num=rational.numerator, den=rational.denominator) if rational > 0 else None
    except (ValueError, ZeroDivisionError):
        return None


def first_video_pts(path: Path) -> tuple[int | None, TimeBase | None]:
    info = _probe_json(path, ['-select_streams', 'v:0', '-read_intervals', '%+#64', '-show_frames',
                             '-show_entries', 'frame=best_effort_timestamp,pts:stream=time_base'])
    frames = info.get('frames', [])
    values = [int(frame.get('best_effort_timestamp', frame.get('pts'))) for frame in frames
              if frame.get('best_effort_timestamp', frame.get('pts')) is not None]
    streams = info.get('streams') or []
    return (min(values) if values else None, _rational(streams[0].get('time_base')) if streams else None)


def probe(path: Path, *, full_source: bool = False, timeout_s: float = 120, max_pixels: int = 64_000_000) -> Probe:
    if type(max_pixels) is not int or max_pixels < 1:
        raise MaterialError('invalid-request', '图像像素预算必须为正整数', stage='probe')
    path = no_links(path, stage='probe')
    if not path.is_file() or not path.stat().st_size:
        raise MaterialError('not-found', '缺少非空本地媒体文件', stage='probe')
    try:
        with Image.open(path) as image:
            width, height = image.size
            if width * height > max_pixels:
                raise MaterialError('resource-limit', '图像超过本次像素预算，请提供较小规格', stage='probe')
            container = image.format or 'image'
            image.verify()
        return Probe(kind='image', container=container.lower(), width=width, height=height)
    except (UnidentifiedImageError, OSError, SyntaxError):
        pass
    except Image.DecompressionBombError as exc:
        raise MaterialError('resource-limit', '图像尺寸超过安全解码范围', stage='probe') from exc
    # 只请求制作所需字段，不把任意大标签/附件内容展开成 JSON 后全部载入内存。
    info = _probe_json(path, ['-show_entries',
        'format=format_name,start_time,duration:stream=codec_type,width,height,time_base,start_pts,start_time,'
        'duration,avg_frame_rate,r_frame_rate,sample_rate,channels:stream_disposition=attached_pic'], timeout_s=timeout_s)
    streams = info.get('streams') or []
    video = next((stream for stream in streams if stream.get('codec_type') == 'video'
                  and not (stream.get('disposition') or {}).get('attached_pic')), None)
    audio = next((stream for stream in streams if stream.get('codec_type') == 'audio'), None)
    if not video and not audio:
        raise MaterialError('media-invalid', '文件没有可使用的图像或声音流', stage='probe')
    principal = video or audio
    duration = principal.get('duration')
    container_info = info.get('format') or {}
    if duration not in {None, 'N/A'}:
        duration_us = seconds_us(duration)
    else:
        duration_us = seconds_us(container_info.get('duration', 0)) - max(0, seconds_us(container_info.get('start_time', 0)))
    if duration_us <= 0:
        raise MaterialError('media-invalid', '媒体没有有效时长', stage='probe')
    time_base = _rational(principal.get('time_base'))
    first_pts = int(principal['start_pts']) if 'start_pts' in principal else None
    if video:
        measured_pts, measured_base = first_video_pts(path)
        if measured_pts is not None:
            first_pts, time_base = measured_pts, measured_base or time_base
    mapping = SourceMapping(status='verified', method='full-input', sourceOriginUs=0,
                            maxErrorUs=0) if full_source else SourceMapping()
    return Probe(kind='video' if video else 'audio', container=container_info.get('format_name', 'unknown'),
                 width=int(video['width']) if video else None, height=int(video['height']) if video else None,
                 durationUs=duration_us, fps=(_rational(video.get('avg_frame_rate')) or _rational(video.get('r_frame_rate'))) if video else None,
                 hasAudio=audio is not None, sampleRate=int(audio['sample_rate']) if audio and audio.get('sample_rate') else None,
                 audioChannels=int(audio['channels']) if audio and audio.get('channels') else None,
                 videoStartUs=pts_us(first_pts, time_base) if video and first_pts is not None and time_base else None,
                 audioStartUs=seconds_us(audio['start_time']) if audio and audio.get('start_time') else None,
                 timeline=Timeline(localOriginPts=first_pts, timeBase=time_base, sourceMapping=mapping))


@lru_cache(maxsize=1)
def _tool_versions() -> tuple[str, str]:
    versions = []
    for executable in (get_ffmpeg_exe(), ffprobe_exe()):
        try:
            result = subprocess.run([executable, '-version'], capture_output=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MaterialError('dependency-missing', '本地媒体工具无法执行', stage='probe') from exc
        lines = result.stdout.decode('utf-8', 'replace').splitlines()
        if result.returncode or not lines:
            raise MaterialError('dependency-missing', '本地媒体工具未返回版本', stage='probe')
        versions.append(lines[0])
    return versions[0], versions[1]


def toolchain() -> dict:
    ffmpeg, ffprobe = _tool_versions()
    # 缓存不可变版本元组，不让调用者修改返回 dict 后污染后续获取/索引身份。
    return {'ffmpeg': ffmpeg, 'ffprobe': ffprobe, 'timePolicy': 'first-presentation-pts-us-v1'}
