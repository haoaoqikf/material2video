"""按字幕所在画面采样自适应柔光参数。

只从登记的原始视频素材取一帧计算平均色与亮度；不读最终成片，也不在浏览器
逐帧取色。结果写入准备记录，参与准备指纹，渲染只消费确定的数值。
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError

#: 字幕安全区大致落在画面的这个纵向区间；采样只取文字背后的条带。
_BAND_TOP = 0.74
_BAND_BOTTOM = 0.93
_BAND_X = (0.08, 0.92)
_SAMPLE_SIZE = (108, 192)
_DEFAULT = (7, 10, 14)


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02x}" for channel in rgb)


def _sample(path: Path, seconds: float) -> tuple[int, int, int]:
    if seconds < 0:
        raise M2VError("字幕背景采样时间不能为负")
    with tempfile.TemporaryDirectory(prefix="subtitle-backing-") as temporary:
        target = Path(temporary) / "frame.png"
        try:
            subprocess.run(
                [get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
                 "-ss", f"{seconds:.3f}", "-i", str(path), "-frames:v", "1",
                 "-vf", f"scale={_SAMPLE_SIZE[0]}:{_SAMPLE_SIZE[1]}", "-y", str(target)],
                check=True, capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            raise M2VError(f"字幕背景采样失败：{path} @ {seconds:.3f}s：{exc}") from exc
        if not target.is_file():
            raise M2VError(f"字幕背景采样没有生成帧：{path} @ {seconds:.3f}s")
        image = Image.open(target).convert("RGB")
        width, height = image.size
        box = (int(width * _BAND_X[0]), int(height * _BAND_TOP),
               int(width * _BAND_X[1]), int(height * _BAND_BOTTOM))
        crop = image.crop(box).resize((54, 18))
        pixels = list(crop.getdata())
    count = len(pixels)
    return tuple(sum(pixel[index] for pixel in pixels) // count for index in range(3))


def sample(path: Path, seconds: float, max_opacity: float) -> dict:
    """返回一条字幕的柔光颜色、透明度与背景参考色。"""
    r, g, b = _sample(path, seconds)
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    opacity = min(max_opacity, 0.10 + 0.55 * max(0.0, luminance - 0.28))
    # 柔光色相来自画面，但压暗并混入中性深色，避免在亮画面上出现彩色块。
    tint = tuple(round(channel * 0.30 + base * 0.70) for channel, base in zip((r, g, b), _DEFAULT))
    return {"color": _hex(tint), "opacity": round(opacity, 3),
            "background": _hex((r, g, b))}


def fallback(max_opacity: float) -> dict:
    """非视频场景没有可采样画面时使用中性柔光。"""
    return {"color": _hex(_DEFAULT), "opacity": round(min(max_opacity, 0.18), 3),
            "background": _hex(_DEFAULT)}
