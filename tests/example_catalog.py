"""固定风格示例清单的唯一测试口径。

示例统一位于 `styles/examples/<style-id>/<slug>/`。替换示例时只改这里，而不是让多个
测试文件各自维护一份名单。运行时不会导入本模块。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "styles" / "examples"

#: 每个正式风格一个规范示例：风格 ID → 作品 slug。
STYLE_EXAMPLES: dict[str, str] = {
    "vibe-night": "fold",
    "vibe-fable": "pigeon",
    "doc-archive": "american-science-milestones",
    "count-ledger": "compound-interest",
    "deep-journey": "solar-system-journey",
}

#: 示例作品 slug → 绝对路径。
EXAMPLE_PATHS: dict[str, Path] = {
    slug: EXAMPLES / style / slug for style, slug in STYLE_EXAMPLES.items()
}

EXPECTED_EXAMPLES = set(EXAMPLE_PATHS)
CONTENT_CONTRACTS = {
    "american-science-milestones",
    "compound-interest",
    "solar-system-journey",
}

EXPECTED_FRAMES: dict[str, tuple[int, int]] = {
    "fold": (1920, 1080),
    "pigeon": (1920, 1080),
    "american-science-milestones": (1920, 1080),
    "compound-interest": (1920, 1080),
    "solar-system-journey": (1920, 1080),
}
EXPECTED_FPS: dict[str, int] = {
    "fold": 30,
    "pigeon": 30,
    "american-science-milestones": 60,
    "compound-interest": 30,
    "solar-system-journey": 60,
}
STORYBOARDS = sorted(EXAMPLES.glob("*/*/storyboard.json"))
STORYBOARD_PATHS = [
    f"styles/examples/{style}/{slug}/storyboard.json"
    for style, slug in sorted(STYLE_EXAMPLES.items())
]

#: 当前五个示例实际覆盖的共享组件族；Motion 与 GSAP 已随旧场景退役，
#: 不再为了覆盖清单引入无关效果。
COVERED_COMPONENTS = {
    "ECharts": ("Chart", "echarts"),
    "Three.js": ("THREE", "three"),
    "React Three Fiber": ("Canvas", "@react-three/fiber"),
    "Drei": ("Float", "Stars", "PerspectiveCamera", "@react-three/drei"),
}
