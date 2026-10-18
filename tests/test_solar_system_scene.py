"""真实浏览器验证太阳系示例场景：能构建、能逐帧渲染、画面不是全黑。

不跑全片（3824 帧太慢），只把示例自己的 `scenes/` 按小画幅录几帧；相机、后期、
look 与旁白时间窗都走与正式制作相同的代码路径。
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe
from playwright.sync_api import sync_playwright

from m2v.engine.http_server import LocalServer
from m2v.types.general import code_scenes
from test_code_scenes import WEB, requires_node

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/solar-system-journey"
FRAMES = 6

LOOK = {"profile": "deep-space-cinematic", "lut": "deep-space", "bloom": 0.7, "dof": 0.45,
        "grain": 0.35, "vignette": 0.45, "motion": {"subframes": 1, "supersample": 1}}
SHOTS = [
    {"id": "cold-open", "target": "sun", "tier": "minor", "startFrame": 0, "endFrame": 3,
     "camera": {"path": [[3.4, 0.35, 1.0], [4.2, 0.5, 1.4]], "fov": 40, "easing": "linear"},
     "focus": {"target": "sun", "distance": 3.4}},
    {"id": "earth-hero", "target": "earth", "tier": "hero", "startFrame": 3, "endFrame": 6,
     "camera": {"path": [[13.0, 0.95, -0.5], [18.0, 1.2, -6.0], [20.6, 1.4, -9.4], [17.0, 1.2, -12.0]],
                "fov": 36, "easing": "quintInOut"},
     "focus": {"target": "earth", "from": 6, "to": 3.4, "aperture": 2.8},
     "post": {"bloom": 0.7, "dof": 0.6}},
]


def build_example(tmp_path: Path):
    """用与制作完全相同的构建入口打包示例自己的场景与已登记素材。"""
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE / "scenes", project / "scenes")
    shutil.copytree(EXAMPLE / "assets/media", project / "assets/media")
    output = tmp_path / "out"
    output.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([shutil.which("node"), str(WEB / "scripts/build-code-scene.mjs"),
                             str(project), "scenes/journey.tsx", str(output)], cwd=WEB,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    return project, output, result


def media_mapping() -> dict:
    """按来源记录构造「素材 ID → 只读解析信息」，与准备阶段注入的形状一致。"""
    record = json.loads((EXAMPLE / "assets/media-sources.json").read_text(encoding="utf-8"))
    return {entry["id"]: {"src": f"/media/{Path(entry['path']).name}", "kind": entry["kind"],
                          "width": entry["width"], "height": entry["height"],
                          "durationSeconds": entry["durationSeconds"], "colorSpace": "srgb",
                          "alpha": False, "license": entry["license"]}
            for entry in record["assets"]}


def capture_config() -> dict:
    return {"props": {"shots": SHOTS, "look": LOOK}, "fps": 60, "durationInFrames": FRAMES,
            "width": 1920, "height": 1080, "subtitleSafeArea": {"x": 192, "y": 888, "width": 1536, "height": 113},
            "segmentWindows": {"sun-0": {"startFrame": 0, "endFrame": 3},
                               "home-0": {"startFrame": 3, "endFrame": 6}},
            "media": media_mapping()}


#: 避开左侧信息栏、顶部进度轨与底部读数的中央区域（1920×1080 画布）。
CENTRE = (700, 300, 1220, 800)


def centre_pixels(path: Path, box: tuple[int, int, int, int] = CENTRE) -> bytes:
    """把中央区域解成 rgb24 原始字节；用于不依赖 UI 的画面统计。"""
    left, top, right, bottom = box
    return subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(path),
                           "-vf", f"crop={right - left}:{bottom - top}:{left}:{top}",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                          capture_output=True, check=True).stdout


#: 地球圆面所在的中央方块（1920×1080 画布）；比圆面小，因此不会被太阳辉光与 UI 污染。
DISC = (810, 390, 1110, 690)


def box_stats(path: Path, box: tuple[int, int, int, int] = DISC) -> tuple[float, int]:
    """地球圆面的中位亮度与「暖而亮」的像素数。

    用中位数而不是均值：夜面机位背后有太阳，辉光会把均值抬起来。
    城市灯光是圆面上少数的暖色亮点，因此单看「暖而亮」的绝对数量即可判定。
    """
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    raw = centre_pixels(path, box)
    values = []
    warm = 0
    for index in range(0, len(raw), 3):
        red, green, blue = raw[index], raw[index + 1], raw[index + 2]
        values.append((red + green + blue) / 3)
        if red > 150 and red - blue > 40:
            warm += 1
    values.sort()
    return values[len(values) // 2], warm


@requires_node
def test_example_scene_builds_and_records(tmp_path):
    project, output, result = build_example(tmp_path)
    assert result.returncode == 0, result.stderr
    assert (output / "scene.js").is_file()
    with sync_playwright() as pw:
        code_scenes._capture(pw, project, output, capture_config())
    frames = sorted(output.glob("frame-*.png"))
    assert [path.name for path in frames] == [f"frame-{index:06d}.png" for index in range(FRAMES)]
    # 画面不能是全黑：只看避开 UI 的中央区域，确认相机确实拍到了东西。
    raw = centre_pixels(frames[3])
    assert sum(raw) / len(raw) > 1.5, "中央画面几乎全黑，相机或光照没有生效"


@requires_node
def test_example_scene_moves_between_shots(tmp_path):
    """两个镜头的画面必须不同：镜头路径与后期确实在改变画面。"""
    project, output, result = build_example(tmp_path)
    assert result.returncode == 0, result.stderr
    with sync_playwright() as pw:
        code_scenes._capture(pw, project, output, capture_config())
    frames = sorted(output.glob("frame-*.png"))
    assert frames[0].read_bytes() != frames[5].read_bytes()


#: 地球在压缩坐标里的位置：轨道 17、角度 1.55（一镜到底螺旋布局）。
EARTH = (17 * math.cos(1.55), 0.0, 17 * math.sin(1.55))


def side_camera(distance: float) -> list[float]:
    """沿地球的径向偏移：distance > 0 在地球外侧（夜面），< 0 在内侧（日面）。"""
    scale = (17 + distance) / 17
    return [round(EARTH[0] * scale, 3), 1.0, round(EARTH[2] * scale, 3)]


def side_config(shots: list[dict]) -> dict:
    config = capture_config()
    config["props"] = {"shots": shots, "look": LOOK}
    config["durationInFrames"] = 3
    config["segmentWindows"] = {"home-0": {"startFrame": 0, "endFrame": 3}}
    return config


@requires_node
def test_earth_night_side_shows_warm_city_lights(tmp_path):
    """地球 hero：外侧机位看夜面（更暗、暗背景上有暖色灯光），内侧机位看日面（更亮）。"""
    shots = [
        {"id": "night", "target": "earth", "tier": "hero", "startFrame": 0, "endFrame": 1,
         "camera": {"path": [side_camera(3.6), side_camera(3.6)], "fov": 40, "easing": "linear"},
         "focus": {"target": "earth", "distance": 3.6}},
        {"id": "day", "target": "earth", "tier": "hero", "startFrame": 1, "endFrame": 3,
         "camera": {"path": [side_camera(-3.6), side_camera(-3.6)], "fov": 40, "easing": "linear"},
         "focus": {"target": "earth", "distance": 3.6}},
    ]
    project, output, result = build_example(tmp_path)
    assert result.returncode == 0, result.stderr
    with sync_playwright() as pw:
        code_scenes._capture(pw, project, output, side_config(shots))
    frames = sorted(output.glob("frame-*.png"))
    night_median, night_lights = box_stats(frames[0])
    day_median, _day_lights = box_stats(frames[1])
    # 只断言「夜面圆面更暗」与「夜面上存在足够多的暖色亮点」：日面被照亮的陆地同样是
    # 暖色，拿两边的暖色数量作比较并不成立（实测日面更多）。
    assert night_median < day_median * 0.6, f"夜面圆面没有明显更暗：夜 {night_median:.1f} / 日 {day_median:.1f}"
    assert night_lights > 150, f"夜面几乎没有城市灯光：{night_lights} 个暖色亮点"
