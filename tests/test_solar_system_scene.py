"""真实浏览器验证太阳系示例场景：能构建、能逐帧渲染、画面不是全黑。

不跑全片（3824 帧太慢），只把示例自己的 `scenes/` 按小画幅录几帧；相机、后期、
look 与旁白时间窗都走与正式制作相同的代码路径。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
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
            "width": 320, "height": 240, "subtitleSafeArea": {"x": 0, "y": 200, "width": 320, "height": 40},
            "segmentWindows": {"sun-0": {"startFrame": 0, "endFrame": 3},
                               "home-0": {"startFrame": 3, "endFrame": 6}},
            "media": media_mapping()}


@requires_node
def test_example_scene_builds_and_records(tmp_path):
    project, output, result = build_example(tmp_path)
    assert result.returncode == 0, result.stderr
    assert (output / "scene.js").is_file()
    with sync_playwright() as pw:
        code_scenes._capture(pw, project, output, capture_config())
    frames = sorted(output.glob("frame-*.png"))
    assert [path.name for path in frames] == [f"frame-{index:06d}.png" for index in range(FRAMES)]
    # 画面不能是全黑：抽取中间帧的灰度均值，确认相机确实拍到了东西。
    from imageio_ffmpeg import get_ffmpeg_exe
    raw = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(frames[3]), "-vf", "format=gray",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    assert sum(raw) / len(raw) > 1.5, "画面几乎全黑，相机或光照没有生效"


@requires_node
def test_example_scene_moves_between_shots(tmp_path):
    """两个镜头的画面必须不同：镜头路径与后期确实在改变画面。"""
    project, output, result = build_example(tmp_path)
    assert result.returncode == 0, result.stderr
    with sync_playwright() as pw:
        code_scenes._capture(pw, project, output, capture_config())
    frames = sorted(output.glob("frame-*.png"))
    assert frames[0].read_bytes() != frames[5].read_bytes()
