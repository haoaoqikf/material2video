"""固定风格示例清单的唯一测试口径。

示例统一位于 `styles/<style-id>/examples/<slug>/`。替换示例时只改这里，而不是让多个
测试文件各自维护一份名单。运行时不会导入本模块。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STYLES = ROOT / "styles"

#: 每个正式风格一个规范示例：风格 ID → 作品 slug。
STYLE_EXAMPLES: dict[str, str] = {
    "vibe-night": "fold",
    "vibe-fable": "pigeon",
    "doc-archive": "american-science-milestones",
    "count-ledger": "compound-interest",
    "deep-journey": "solar-system-journey",
    "dark-proof": "compound-connect",
}

#: 示例作品 slug → 绝对路径。
EXAMPLE_PATHS: dict[str, Path] = {
    slug: STYLES / style / "examples" / slug for style, slug in STYLE_EXAMPLES.items()
}

STORYBOARDS = sorted(STYLES.glob("*/examples/*/storyboard.json"))
STORYBOARD_PATHS = [
    f"styles/{style}/examples/{slug}/storyboard.json"
    for style, slug in sorted(STYLE_EXAMPLES.items())
]
