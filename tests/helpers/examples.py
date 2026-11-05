"""固定风格示例清单的唯一测试口径。

示例统一位于 `styles/<style-id>/examples/<slug>/`。增删示例时只改这里，而不是让多个
测试文件各自维护一份名单。运行时不会导入本模块。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STYLES = ROOT / "styles"

#: 风格 ID → 随附作品 slug。dark-proof 展示两种不同的论证组织。
STYLE_EXAMPLES: dict[str, tuple[str, ...]] = {
    "vibe-night": ("fold",),
    "vibe-fable": ("pigeon",),
    "doc-archive": ("american-science-milestones",),
    "count-ledger": ("compound-interest",),
    "deep-journey": ("solar-system-journey",),
    "dark-proof": ("compound-connect", "luck-on-stage"),
}

#: 示例作品 slug → 绝对路径。
EXAMPLE_PATHS: dict[str, Path] = {
    slug: STYLES / style / "examples" / slug
    for style, slugs in STYLE_EXAMPLES.items() for slug in slugs
}

STORYBOARDS = sorted(STYLES.glob("*/examples/*/storyboard.json"))
STORYBOARD_PATHS = [
    f"styles/{style}/examples/{slug}/storyboard.json"
    for style, slugs in sorted(STYLE_EXAMPLES.items()) for slug in slugs
]
