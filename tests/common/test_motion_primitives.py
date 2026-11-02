"""共享动效原语：实现指纹、确定性闸门与 SDK 导出。"""
from __future__ import annotations

import re
from pathlib import Path

from m2v.core import source_policy
from m2v.types.general import cinematic, code_scenes

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
PRIMITIVES = WEB / "src/code-scene/primitives.ts"
DYNAMICS = WEB / "src/code-scene/dynamics.ts"
SUBTITLES = WEB / "src/code-scene/subtitles.ts"
RHYTHM = WEB / "src/code-scene/rhythm.ts"
EFFECTS = WEB / "src/code-scene/effects/screen-burst.tsx"
MOTION = WEB / "src/code-scene/motion.ts"
SDK = WEB / "src/code-scene/sdk.tsx"


def test_primitives_are_part_of_the_implementation_fingerprint():
    """改原语必须让引用作品重新准备，不能静默复用旧片段。"""
    inputs = {name.replace("\\", "/"): value for name, value in code_scenes.implementation_inputs().items()}
    assert "web/src/code-scene/primitives.ts" in inputs
    assert inputs["web/src/code-scene/primitives.ts"] == code_scenes.digest(PRIMITIVES)
    assert "web/src/code-scene/dynamics.ts" in inputs
    assert inputs["web/src/code-scene/dynamics.ts"] == code_scenes.digest(DYNAMICS)
    assert "web/src/code-scene/subtitles.ts" in inputs
    assert inputs["web/src/code-scene/subtitles.ts"] == code_scenes.digest(SUBTITLES)
    assert "web/src/code-scene/rhythm.ts" in inputs
    assert inputs["web/src/code-scene/rhythm.ts"] == code_scenes.digest(RHYTHM)
    assert "web/src/code-scene/effects/screen-burst.tsx" in inputs
    assert inputs["web/src/code-scene/effects/screen-burst.tsx"] == code_scenes.digest(EFFECTS)


def test_primitives_pass_the_determinism_source_gate():
    """原语不得引入挂钟、隐式随机源、计时器或未适配的 CSS 动画。"""
    violations = source_policy.scan([PRIMITIVES, DYNAMICS, SUBTITLES, RHYTHM, EFFECTS])
    assert not violations, [item.render(WEB) for item in violations]


def test_sdk_exports_the_shared_primitives():
    text = SDK.read_text(encoding="utf-8")
    assert "export * from './primitives';" in text
    assert "export * from './dynamics';" in text
    assert "export * from './subtitles';" in text
    assert "export * from './rhythm';" in text
    assert "export * from './effects/screen-burst';" in text
    assert "svg-path-properties" in text
    assert "perfect-freehand" in text


def test_named_curves_match_the_python_validator():
    """分镜声明的缓动名必须与 TS 曲线表同集合，否则校验通过却取不到曲线。"""
    text = MOTION.read_text(encoding="utf-8")
    union = text.split("export type MotionCurveName", 1)[1].split(";", 1)[0]
    names = set(re.findall(r"'([A-Za-z]+)'", union))
    assert names == set(cinematic.EASINGS)
    table = text.split("export const MOTION_CURVES", 1)[1].split("\n};", 1)[0]
    assert set(re.findall(r"^\s{2}([A-Za-z]+):", table, re.M)) == names
