"""固定示例清单的唯一测试口径。

替换示例时只改这里，而不是让四个测试文件各自维护一份名单——分散的名单会在
替换时漏改，表现为某个测试还在读已删除的目录。运行时不会导入本模块。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

#: 三个固定示例及其画幅；数量上限为三，替换须用户明确授权。
EXPECTED_FRAMES: dict[str, tuple[int, int]] = {
    "american-science-milestones": (1920, 1080),
    "compound-interest": (1920, 1080),
    "solar-system-journey": (1920, 1080),
}
EXPECTED_EXAMPLES = set(EXPECTED_FRAMES)
STORYBOARDS = sorted(EXAMPLES.glob("*/storyboard.json"))
STORYBOARD_PATHS = [f"examples/{name}/storyboard.json" for name in sorted(EXPECTED_EXAMPLES)]

#: 当前三支示例实际覆盖的共享组件族；GSAP 随拥堵波示例退役，不再要求为覆盖而引入。
COVERED_COMPONENTS = {
    "Motion": ("motion", "motion/react"),
    "ECharts": ("Chart", "echarts"),
    "Three.js": ("THREE", "three"),
    "React Three Fiber": ("Canvas", "@react-three/fiber"),
    "Drei": ("Float", "Stars", "PerspectiveCamera", "@react-three/drei"),
}
