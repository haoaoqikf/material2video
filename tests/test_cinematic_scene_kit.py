"""真实浏览器验证电影级套件：能渲染、可复现、后期生效且不引入随机源。

跨次运行的判定用 PSNR（同帧两张截图 ≥ 60dB）；「画面确实在动」用同一镜头内
首末帧必须不同来判定。两者都不依赖帧率元数据。
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe
from playwright.sync_api import sync_playwright

from m2v.engine.http_server import LocalServer
from test_code_scenes import WEB, prepare_build, requires_node

LOOK = {"profile": "deep-space", "lut": "deep-space", "bloom": 0.7, "grain": 0.35,
        "vignette": 0.45, "dof": 0.35, "exposure": {"ev": -0.3}}
SHOTS = [{"id": "sun-open", "target": "sun", "tier": "hero", "startFrame": 0, "endFrame": 480,
          "camera": {"path": [[0, 1.5, 14], [2, 0.5, 7], [0, 0, 5]], "fov": 34, "roll": -2,
                     "easing": "quintInOut"},
          "focus": {"target": "sun", "distance": 5, "aperture": 2.8},
          "exposure": {"ev": -0.3, "mode": "shot"},
          "post": {"bloom": 0.9, "grain": 0.4, "vignette": 0.5, "chromaticAberration": 0.25}}]


def scene_source(*, post: bool = True) -> str:
    body = """
import {Canvas, useSceneContext, LookProvider, PostFX, CameraRig, Starfield, ParticleBelt,
  SunSurface, Corona, Atmosphere, Prominence, Rings, OortCloud, Comet} from 'm2v/code-scene';
import {useEffect, useRef} from 'react';

const LOOK = __LOOK__;
const SHOTS = __SHOTS__;

function Ready() {
  const {ready} = useSceneContext();
  useEffect(() => {ready();}, []);
  return null;
}

function World() {
  const sun = useRef(null);
  return (
    <LookProvider look={LOOK} shots={SHOTS}>
      <object3D ref={sun}/>
      <CameraRig targets={{sun: sun.current ?? undefined}} target={[0, 0, 0]}/>
      <Starfield count={300} radius={120} seed="kit"/>
      <SunSurface radius={2}/>
      <Corona radius={2}/>
      <Atmosphere radius={2}/>
      <Prominence radius={2} count={3}/>
      <ParticleBelt count={300} innerRadius={6} outerRadius={9}/>
      <Rings innerRadius={3} outerRadius={5}/>
      <OortCloud count={300} radius={70} bubble={90}/>
      <Comet position={[7, 1, 0]} tailLength={6}/>
      __POST__
      <Ready/>
    </LookProvider>
  );
}

export default function Demo() {
  return (
    <Canvas style={{width: 320, height: 240}} gl={{antialias: false}}>
      <color attach="background" args={['#000000']}/>
      <ambientLight intensity={0.2}/>
      <World/>
    </Canvas>
  );
}
"""
    return (body.replace("__LOOK__", json.dumps(LOOK))
                .replace("__SHOTS__", json.dumps(SHOTS))
                .replace("__POST__", "<PostFX/>" if post else ""))


@contextmanager
def kit_page(work: Path, *, frames: int = 62):
    config = dict(props={}, fps=60, durationInFrames=frames, width=320, height=240,
                  segmentWindows={}, subtitleSafeArea=dict(x=0, y=200, width=320, height=40))
    (work / "index.html").write_text(
        '<div id="root"></div><script>window.__M2V_CODE_CONFIG__=' + json.dumps(config)
        + '</script><script src="scene.js"></script>', encoding="utf-8")
    with LocalServer(work, mounts={"/fonts": WEB / "public/fonts"}, cors=True) as server, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 320, "height": 240})
            page.add_init_script(path=str(WEB / "src/code-scene/capture-clock.js"))
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(server.base_url)
            deadline = time.monotonic() + 60
            while not page.evaluate("Boolean(window.__M2V_CODE__?.ready)"):
                assert not errors, errors
                assert time.monotonic() < deadline, "场景未就绪"
                page.evaluate("window.__M2V_CAPTURE_CLOCK__.bootstrap()")
            page.evaluate("window.__M2V_CODE__.start()")
            yield page, errors
            assert not errors, errors
        finally:
            browser.close()


def psnr(first: bytes, second: bytes, tmp_path: Path) -> float:
    """用 ffmpeg 的 psnr 统计比较两张截图；完全相同时为 inf。"""
    left, right = tmp_path / "left.png", tmp_path / "right.png"
    left.write_bytes(first)
    right.write_bytes(second)
    result = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(left), "-i", str(right),
                             "-lavfi", "psnr=stats_file=-", "-f", "null", "-"],
                            capture_output=True, text=True, timeout=120)
    match = re.search(r"psnr_avg:([\d.]+|inf)", result.stdout)
    assert match, f"无法读取 PSNR：{result.stdout[-400:]} {result.stderr[-400:]}"
    return float("inf") if match.group(1) == "inf" else float(match.group(1))


def advance(page, frame: int) -> None:
    page.evaluate("n => window.__M2V_CODE__.advanceToFrame(n)", frame)


def capture_at(work: Path, frame: int) -> bytes:
    with kit_page(work) as (page, _):
        for index in range(frame + 1):
            advance(page, index)
        return page.screenshot()


@requires_node
def test_kit_renders_the_same_frame_identically_across_runs(tmp_path):
    """同一帧在两次独立录制里必须给出同一张画面（PSNR ≥ 60dB）。"""
    _, work, result = prepare_build(tmp_path, scene_source())
    assert result.returncode == 0, result.stderr
    first = capture_at(work, 40)
    second = capture_at(work, 40)
    assert psnr(first, second, tmp_path) >= 60


@requires_node
def test_camera_rig_actually_moves_within_a_shot(tmp_path):
    """镜头必须随帧推进：同一镜头首末帧不能是同一张画面。"""
    _, work, result = prepare_build(tmp_path, scene_source())
    assert result.returncode == 0, result.stderr
    start = capture_at(work, 0)
    end = capture_at(work, 59)
    assert psnr(start, end, tmp_path) < 40


@requires_node
def test_post_processing_changes_the_picture(tmp_path):
    """后期确实作用于 canvas：开与关的画面必须不同。"""
    _, plain, plain_result = prepare_build(tmp_path / "plain", scene_source(post=False))
    _, graded, graded_result = prepare_build(tmp_path / "graded", scene_source(post=True))
    assert plain_result.returncode == 0, plain_result.stderr
    assert graded_result.returncode == 0, graded_result.stderr
    assert psnr(capture_at(plain, 30), capture_at(graded, 30), tmp_path) < 45


@requires_node
def test_approved_cinematic_packages_build(tmp_path):
    """批准清单包含后期依赖：作品可以直接引用它们。"""
    source = """
import {EffectComposer} from '@react-three/postprocessing';
import {BlendFunction} from 'postprocessing';
export default function Demo() {
  return <div>{String(Boolean(EffectComposer) && Boolean(BlendFunction))}</div>;
}
"""
    _, _, result = prepare_build(tmp_path, source)
    assert result.returncode == 0, result.stderr


def test_unapproved_package_is_still_rejected(tmp_path):
    """新增批准项不能放宽边界：未批准的包仍然拒绝。"""
    _, _, result = prepare_build(tmp_path, "import _ from 'lodash';\nexport default () => _;\n")
    assert result.returncode != 0
    assert "未批准的作品依赖" in result.stderr


def test_cinematic_sdk_has_no_wall_clock_random_or_css_animation():
    """电影套件自己也要过确定性闸门：不许挂钟、随机数与 CSS 动画。"""
    from m2v.core import source_policy

    # 套件拆成包后要扫全部模块：`scan` 会静默跳过缺失文件，写死单个路径会让闸门空跑。
    sdk = sorted((WEB / "src/code-scene/cinematic").glob("*.tsx"))
    assert sdk, "电影套件的源码文件不见了"
    violations = source_policy.scan(sdk)
    assert not violations, [item.render(WEB) for item in violations]


def test_missing_cinematic_dependency_fails_before_building(monkeypatch):
    """缺后期依赖时在打包前明确失败，而不是渲染成没有后期的画面。"""
    from m2v.core.errors import M2VError
    from m2v.types.general import code_scenes

    monkeypatch.setattr(code_scenes.config, "CINEMATIC_DEPS", ("definitely-missing-package",))
    with pytest.raises(M2VError, match="缺少电影级后期依赖"):
        code_scenes.require_cinematic_dependencies()
    monkeypatch.setattr(code_scenes.config, "CINEMATIC_DEPS", ())
    code_scenes.require_cinematic_dependencies()


STANDARD_SOURCE = """
import {Canvas, useSceneContext} from 'm2v/code-scene';
import {useEffect} from 'react';
function Ready() {
  const {ready} = useSceneContext();
  useEffect(() => {ready();}, []);
  return null;
}
export default function Demo() {
  return <Canvas style={{width: 320, height: 240}} gl={{antialias: false}}>
    <color attach="background" args={['#000000']}/>
    <ambientLight intensity={0.5}/>
    <mesh rotation={[0.4, 0.8, 0]}>
      <boxGeometry args={[2, 2, 2]}/>
      <meshStandardMaterial color="#4b9dff"/>
    </mesh>
    <Ready/>
  </Canvas>;
}
"""


@requires_node
def test_standard_picture_ignores_the_new_dependencies(tmp_path):
    """标准画面不因新依赖改变：把电影套件从 SDK 导出里摘掉后必须逐像素一致。"""
    sdk = WEB / "src/code-scene/sdk.tsx"
    original = sdk.read_text(encoding="utf-8")
    assert "export * from './cinematic';" in original
    _, work, result = prepare_build(tmp_path / "with", STANDARD_SOURCE)
    assert result.returncode == 0, result.stderr
    with_kit = capture_at(work, 30)
    try:
        sdk.write_text(original.replace("export * from './cinematic';\n", ""), encoding="utf-8")
        _, work, result = prepare_build(tmp_path / "without", STANDARD_SOURCE)
        assert result.returncode == 0, result.stderr
        without_kit = capture_at(work, 30)
    finally:
        sdk.write_text(original, encoding="utf-8")
    assert psnr(with_kit, without_kit, tmp_path) == float("inf")


RISK_SOURCE = """
import {cameraPathRisk, pathIntersectsSphere, backgroundRisk, activeShot, ease} from 'm2v/code-scene';
import {useSceneContext} from 'm2v/code-scene';
import {useEffect} from 'react';

export default function Demo() {
  const {ready} = useSceneContext();
  useEffect(() => {
    window.__risk = {
      hit: pathIntersectsSphere([[0, 0, 10], [0, 0, -10]], [0, 0, 0], 2),
      miss: pathIntersectsSphere([[0, 6, 10], [0, 6, -10]], [0, 0, 0], 2),
      clearance: pathIntersectsSphere([[0, 3, 10], [0, 3, -10]], [0, 0, 0], 2, 1.5),
      risk: cameraPathRisk([[0, 1, 10], [0, 1, -10]], [{name: 'sun', center: [0, 0, 0], radius: 2},
        {name: 'earth', center: [40, 0, 0], radius: 1}]),
      background: backgroundRisk([[0, 0, 90], [0, 0, 130]], 120, 100),
      shot: activeShot([{id: 'a', startFrame: 0, endFrame: 10}, {id: 'b', startFrame: 10, endFrame: 20}], 10)?.id,
      easing: [ease('linear', 0.25), ease('quintInOut', 0), ease('quintInOut', 1)],
    };
    ready();
  }, []);
  return null;
}
"""


@requires_node
def test_camera_path_and_background_checks(tmp_path):
    """穿球与背景裁切检查是纯函数，结果直接可断言。"""
    from test_capture_clock import scene_page

    with scene_page(tmp_path, RISK_SOURCE) as (page, _):
        risk = page.evaluate("window.__risk")
    assert risk["hit"] is True and risk["miss"] is False
    assert risk["clearance"] is True, "余量不足也算穿球风险"
    assert [item["name"] for item in risk["risk"]] == ["sun"]
    assert risk["risk"][0]["distance"] < 0
    assert any("星空壳" in item for item in risk["background"])
    assert any("远裁剪面" in item for item in risk["background"])
    assert risk["shot"] == "b", "帧号落在 endFrame 时属于下一个镜头"
    assert risk["easing"] == [0.25, 0, 1]
