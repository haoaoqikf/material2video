"""共享动效原语：实现指纹、确定性闸门与 SDK 导出。"""
from __future__ import annotations

from pathlib import Path

from m2v.core import source_policy
from m2v.types.general import code_scenes

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
PRIMITIVES = WEB / "src/code-scene/primitives.ts"
SDK = WEB / "src/code-scene/sdk.tsx"


def test_primitives_are_part_of_the_implementation_fingerprint():
    """改原语必须让引用作品重新准备，不能静默复用旧片段。"""
    inputs = {name.replace("\\", "/"): value for name, value in code_scenes.implementation_inputs().items()}
    assert "web/src/code-scene/primitives.ts" in inputs
    assert inputs["web/src/code-scene/primitives.ts"] == code_scenes.digest(PRIMITIVES)


def test_primitives_pass_the_determinism_source_gate():
    """原语不得引入挂钟、隐式随机源、计时器或未适配的 CSS 动画。"""
    violations = source_policy.scan([PRIMITIVES])
    assert not violations, [item.render(WEB) for item in violations]


def test_sdk_exports_the_shared_primitives():
    assert "export * from './primitives';" in SDK.read_text(encoding="utf-8")
