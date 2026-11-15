"""共享动效原语：实现指纹、确定性闸门与 SDK 导出。"""
from __future__ import annotations

import re
from pathlib import Path

from film_runtime.core import source_policy
from m2v.types.scene_film import cinematic, code_scenes

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
PRIMITIVES = WEB / "src/code-scene/primitives.ts"
DYNAMICS = WEB / "src/code-scene/dynamics.ts"
SUBTITLES = WEB / "src/code-scene/subtitles.ts"
RHYTHM = WEB / "src/code-scene/rhythm.ts"
EFFECTS = WEB / "src/code-scene/effects/screen-burst.tsx"
MOTION = WEB / "src/code-scene/motion.ts"
SDK = Path(__file__).resolve().parents[1] / "support/code-scene-reference.tsx"




def test_primitives_pass_the_determinism_source_gate():
    """原语不得引入挂钟、隐式随机源、计时器或未适配的 CSS 动画。"""
    violations = source_policy.scan([PRIMITIVES, DYNAMICS, SUBTITLES, RHYTHM, EFFECTS])
    assert not violations, [item.render(WEB) for item in violations]


def test_sdk_exports_the_shared_primitives():
    text = SDK.read_text(encoding="utf-8")
    assert "export * from '../../web/src/code-scene/primitives';" in text
    assert "export * from '../../web/src/code-scene/dynamics';" in text
    assert "export * from '../../web/src/code-scene/subtitles';" in text
    assert "export * from '../../web/src/code-scene/rhythm';" in text
    assert "export * from '../../web/src/code-scene/effects/screen-burst';" in text
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
