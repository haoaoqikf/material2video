"""运动模糊与 SSAA：子帧计划、子帧平均、降采样编码与宿主子帧协议。"""
from __future__ import annotations

import subprocess

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError
from m2v.engine import media_probe
from m2v.types.general import code_scenes
from test_code_scenes import requires_node

HERO = [{"id": "earth", "tier": "hero", "startFrame": 10, "endFrame": 20},
        {"id": "sun", "tier": "minor", "startFrame": 0, "endFrame": 10}]


def solid(path, color: str, size: str = "64x32") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"color=c={color}:s={size}", "-frames:v", "1", str(path)], check=True)


def mean_gray(path) -> int:
    raw = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(path), "-vf", "format=gray",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return round(sum(raw) / len(raw))


def test_subframes_apply_only_inside_hero_windows():
    assert code_scenes._subframes_for(5, HERO, 4) == 1, "非 hero 镜头保持单帧"
    assert code_scenes._subframes_for(15, HERO, 4) == 4
    assert code_scenes._subframes_for(15, HERO, 1) == 1, "关闭时不取子帧"
    assert code_scenes._subframes_for(20, HERO, 4) == 1, "endFrame 为开区间"


def test_average_blends_subframes_into_one_frame(tmp_path):
    """三个子帧平均后应落在中间值附近——这正是运动模糊的算法。"""
    frames = []
    for index, color in enumerate(("0x000000", "0x808080", "0xffffff")):
        path = tmp_path / f"sub-{index}.png"
        solid(path, color)
        frames.append(path)
    target = tmp_path / "frame-000000.png"
    code_scenes._average(frames, target)
    assert target.is_file()
    assert 120 <= mean_gray(target) <= 136, mean_gray(target)


def test_average_of_one_subframe_copies(tmp_path):
    source = tmp_path / "sub-0.png"
    solid(source, "0x204060")
    target = tmp_path / "frame-000000.png"
    code_scenes._average([source], target)
    assert mean_gray(target) == mean_gray(source)


def test_average_rejects_empty_input(tmp_path):
    with pytest.raises(M2VError, match="没有可平均的子帧"):
        code_scenes._average([], tmp_path / "frame-000000.png")


def test_encode_downscales_supersampled_frames(tmp_path):
    """SSAA：按 2 倍设备像素采集，编码时降采样回目标画幅。"""
    for index in range(2):
        solid(tmp_path / f"frame-{index:06d}.png", "0x335577", size="640x480")
    output = tmp_path / "clip.mp4"
    code_scenes._encode(tmp_path, output, 2, 320, 240, supersample=2)
    assert media_probe.probe_dimensions(output) == (320, 240)


def test_encode_without_supersample_keeps_frame_size(tmp_path):
    for index in range(2):
        solid(tmp_path / f"frame-{index:06d}.png", "0x335577", size="320x240")
    output = tmp_path / "clip.mp4"
    code_scenes._encode(tmp_path, output, 2, 320, 240)
    assert media_probe.probe_dimensions(output) == (320, 240)


def scene(identity="a", *, look=None, shots=None):
    props: dict = {}
    if look is not None:
        props["look"] = look
    if shots is not None:
        props["shots"] = shots
    return {"id": identity, "startFrame": 0, "durationInFrames": 60,
            "content": {"props": props}, "segmentWindows": {},
            "narrationSegments": [{"id": f"{identity}-line", "text": "文本"}]}


FRAME = {"width": 1920, "height": 1080, "subtitle": {"safeArea": {"x": 1, "y": 2, "width": 3, "height": 4}}}


def test_motion_enters_the_cache_config_only_when_declared():
    plain = code_scenes.scene_config(scene(), FRAME, {})
    assert "motion" not in plain, "未声明时缓存键必须与既有一致"
    declared = code_scenes.scene_config(scene(look={"profile": "deep-space", "motion": {"subframes": 3, "supersample": 2}}),
                                        FRAME, {})
    assert declared["motion"] == {"subframes": 3, "supersample": 2}


SUBFAME_SOURCE = """
import {useSceneContext} from 'm2v/code-scene';
import {useEffect, useRef} from 'react';

export default function Demo() {
  const {ready, elapsedSeconds} = useSceneContext();
  const box = useRef(null);
  useEffect(() => {ready();}, []);
  return <div>
    <div id="clock">{String(elapsedSeconds)}</div>
    <div id="mover" ref={box} style={{transform: `translateX(${elapsedSeconds * 600}px)`}}/>
  </div>;
}
"""

MOVING_BOX = """
import {useSceneContext} from 'm2v/code-scene';
import {useEffect} from 'react';

export default function Demo() {
  const {ready, elapsedSeconds} = useSceneContext();
  useEffect(() => {ready();}, []);
  return <div style={{width: 320, height: 240, background: '#000', position: 'relative'}}>
    <div style={{position: 'absolute', top: 100, left: 0, width: 40, height: 40, background: '#fff',
      transform: `translateX(${elapsedSeconds * 2000}px)`}}/>
  </div>;
}
"""


def capture_config(motion: dict, *, hero: tuple[int, int] = (0, 4)) -> dict:
    return {"props": {"shots": [{"id": "h", "tier": "hero", "startFrame": hero[0], "endFrame": hero[1]}]},
            "fps": 60, "durationInFrames": 4, "width": 320, "height": 240,
            "subtitleSafeArea": {"x": 0, "y": 200, "width": 320, "height": 40},
            "segmentWindows": {}, "media": {}, "motion": motion}


def capture_with(tmp_path, motion: dict, *, hero: tuple[int, int] = (0, 4)):
    """走真实采集路径（Playwright + CDP 截图 + 子帧平均），只是画幅很小。"""
    from playwright.sync_api import sync_playwright

    from test_code_scenes import prepare_build

    root, work, result = prepare_build(tmp_path, MOVING_BOX)
    assert result.returncode == 0, result.stderr
    with sync_playwright() as pw:
        code_scenes._capture(pw, root, work, capture_config(motion, hero=hero))
    return work


@requires_node
def test_capture_averages_subframes_and_supersamples(tmp_path):
    """真实采集路径：hero 帧取两个子帧、按 2 倍设备像素采集，并清理中间文件。"""
    work = capture_with(tmp_path, {"subframes": 2, "supersample": 2})
    frames = sorted(work.glob("frame-*.png"))
    assert [path.name for path in frames] == [f"frame-{index:06d}.png" for index in range(4)]
    assert media_probe.probe_dimensions(frames[0]) == (640, 480), "SSAA 按 2 倍设备像素采集"
    assert not list(work.glob("sub-*.png")), "子帧中间文件必须清理"


@requires_node
def test_supersample_applies_only_to_hero_frames(tmp_path):
    """总览保持 1×：只有 hero 帧按 2 倍采集，其余帧仍是目标画幅。"""
    work = capture_with(tmp_path, {"subframes": 1, "supersample": 2}, hero=(0, 2))
    frames = sorted(work.glob("frame-*.png"))
    assert media_probe.probe_dimensions(frames[0]) == (640, 480)
    assert media_probe.probe_dimensions(frames[3]) == (320, 240)


def test_encode_normalises_mixed_supersample_frames(tmp_path):
    """同一片段里 1× 与 2× 的帧混用，编码后统一为目标画幅。"""
    solid(tmp_path / "frame-000000.png", "0x335577", size="640x480")
    solid(tmp_path / "frame-000001.png", "0x335577", size="320x240")
    output = tmp_path / "clip.mp4"
    code_scenes._encode(tmp_path, output, 2, 320, 240, supersample=2)
    assert media_probe.probe_dimensions(output) == (320, 240)


@requires_node
def test_motion_blur_changes_the_recorded_frame(tmp_path):
    """同一帧取两个子帧与只取一个子帧必须给出不同画面——否则模糊是假的。"""
    blurred = sorted(capture_with(tmp_path / "blur", {"subframes": 2, "supersample": 1}).glob("frame-*.png"))
    single = sorted(capture_with(tmp_path / "single", {"subframes": 1, "supersample": 1}).glob("frame-*.png"))
    assert blurred[0].read_bytes() != single[0].read_bytes()


@requires_node
def test_subframe_advance_moves_time_within_a_frame(tmp_path):
    """子帧必须真的推进 React 时间与画面，否则运动模糊只是重复同一张图。"""
    from test_capture_clock import scene_page

    with scene_page(tmp_path, SUBFAME_SOURCE) as (page, _):
        page.evaluate("window.__M2V_CODE__.advanceToSubframe(0, 0, 3)")
        first = page.evaluate("Number(document.querySelector('#clock').textContent)")
        page.evaluate("window.__M2V_CODE__.advanceToSubframe(0, 1, 3)")
        second = page.evaluate("Number(document.querySelector('#clock').textContent)")
        page.evaluate("window.__M2V_CODE__.advanceToSubframe(0, 2, 3)")
        third = page.evaluate("Number(document.querySelector('#clock').textContent)")
        page.evaluate("window.__M2V_CODE__.advanceToSubframe(1, 0, 3)")
        fourth = page.evaluate("Number(document.querySelector('#clock').textContent)")
    assert first == pytest.approx(0)
    assert second == pytest.approx(1 / 180)
    assert third == pytest.approx(2 / 180)
    assert fourth == pytest.approx(1 / 60)


@requires_node
def test_subframe_protocol_rejects_disorder(tmp_path):
    from test_capture_clock import scene_page

    with scene_page(tmp_path, SUBFAME_SOURCE) as (page, _):
        page.evaluate("window.__M2V_CODE__.advanceToSubframe(0, 0, 3)")
        for call in ("window.__M2V_CODE__.advanceToSubframe(0, 2, 3)",
                     "window.__M2V_CODE__.advanceToSubframe(0, 0, 3)",
                     "window.__M2V_CODE__.advanceToSubframe(1, 1, 3)",
                     "window.__M2V_CODE__.advanceToSubframe(2, 0, 3)",
                     "window.__M2V_CODE__.advanceToSubframe(0, 3, 3)"):
            with pytest.raises(Exception, match="连续帧号"):
                page.evaluate(call)
        # 单帧推进等价于「下一帧的第 0 个子帧」，因此可以与子帧混用。
        page.evaluate("window.__M2V_CODE__.advanceToFrame(1)")
        assert page.evaluate("Number(document.querySelector('#clock').textContent)") == pytest.approx(1 / 60)
