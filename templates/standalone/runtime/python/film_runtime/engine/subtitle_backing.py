"""从实际幕画面取样，生成与旁白时间轴一起冻结的字幕色彩。"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from PIL import Image

from film_runtime.core.errors import VideoError

logger = logging.getLogger(__name__)

DARK_INK = "#101219"
LIGHT_INK = "#ffffff"
MIN_CONTRAST = 4.5
# 柔光在字行外侧已开始羽化，量测使用比中心更保守的混合强度。
HALO_WEIGHT = 0.55


def rgb(color: str) -> tuple[int, int, int]:
    if len(color) != 7 or not color.startswith("#"):
        raise VideoError(f"颜色必须是 #rrggbb：{color}")
    return tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))


def hex_color(channels) -> str:
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def luminance(color: str) -> float:
    channels = [value / 255 for value in rgb(color)]
    linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4
              for value in channels]
    return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))


def contrast(foreground: str, background: str) -> float:
    low, high = sorted((luminance(foreground), luminance(background)))
    return (high + .05) / (low + .05)


def blend(foreground: str, background: str, alpha: float) -> str:
    return hex_color(round(f * alpha + b * (1 - alpha))
                     for f, b in zip(rgb(foreground), rgb(background)))


def appearance(background: str, subtitle: dict) -> dict:
    backing = subtitle["backing"]
    configured = subtitle["textColor"]
    light_ink, dark_ink = ((configured, DARK_INK) if luminance(configured) >= .5
                           else (LIGHT_INK, configured))
    light_ratio = contrast(light_ink, background)
    dark_ratio = contrast(dark_ink, background)
    light_text = light_ratio >= dark_ratio
    ink = light_ink if light_text else dark_ink
    halo = backing["color"] if light_text else "#fff9f0"
    if (luminance(halo) > luminance(background)) == light_text:
        halo = "#000000" if light_text else LIGHT_INK
    ratio = max(light_ratio, dark_ratio)
    opacity = round(min(backing["maxOpacity"], .14 + .10 * max(0, 6 - ratio)), 3)
    return {"background": background, "textColor": ink, "color": halo, "opacity": opacity}


def region_color(path: Path, safe_area: dict, width: int, height: int) -> str:
    """取安全区中央的代表色，覆盖实际字行而非整幅画面。"""
    x, y = safe_area["x"], safe_area["y"]
    w, h = safe_area["width"], safe_area["height"]
    with Image.open(path) as image:
        sx, sy = image.width / width, image.height / height
        box = (round((x + .12 * w) * sx), round((y + .28 * h) * sy),
               round((x + .88 * w) * sx), round((y + .72 * h) * sy))
        pixel = image.convert("RGB").resize((1, 1), Image.Resampling.BOX, box).getpixel((0, 0))
    return hex_color(pixel)


def apply(root: Path, storyboard: Path, prepared: dict) -> None:
    props = prepared["props"]
    cues = props["subtitleCues"]
    if not cues:
        return
    from film_runtime.engine import browser, lookdev

    subtitle = props["subtitle"]
    browser.configure()
    midpoints = [(cue["startFrame"] + cue["endFrame"]) // 2 for cue in cues]
    logger.info("字幕背景采样：%d 条字幕", len(cues))
    with tempfile.TemporaryDirectory(prefix="subtitle-backing-", dir=root / "outputs") as temporary:
        work = Path(temporary)
        samples = lookdev.background_stills(root, storyboard, prepared, sorted(set(midpoints)), work)
        for frame, cue in zip(midpoints, cues):
            background = region_color(samples[frame], subtitle["safeArea"], prepared["width"], prepared["height"])
            cue["backing"] = appearance(background, subtitle)
