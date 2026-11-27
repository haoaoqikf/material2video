"""随附独立示例的唯一测试清单。"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"
TYPE_EXAMPLES: dict[str, tuple[str, ...]] = {
    "text-motion": (),
    "data-evolution": ("compound-after-20", "global-market-cap-race-portrait"),
    "spatial-3d": ("solar-system-journey",),
}
EXAMPLE_PATHS: dict[str, Path] = {
    slug: EXAMPLES / kind / slug
    for kind, slugs in TYPE_EXAMPLES.items() for slug in slugs
}
STORYBOARD_PATHS = [
    f"examples/{kind}/{slug}/storyboard.json"
    for kind, slugs in sorted(TYPE_EXAMPLES.items()) for slug in slugs
]
