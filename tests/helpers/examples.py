"""五类视频随附示例的唯一测试清单。"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"
TYPE_EXAMPLES: dict[str, tuple[str, ...]] = {
    "text-motion": ("fold",),
    "data-evolution": ("compound-interest", "compound-connect"),
    "principle-metaphor": ("pigeon", "luck-on-stage"),
    "spatial-3d": ("solar-system-journey",),
    "documentary-edit": ("american-science-milestones",),
}
EXAMPLE_PATHS: dict[str, Path] = {
    slug: EXAMPLES / kind / slug
    for kind, slugs in TYPE_EXAMPLES.items() for slug in slugs
}
STORYBOARDS = sorted(EXAMPLES.glob("*/*/storyboard.json"))
STORYBOARD_PATHS = [
    f"examples/{kind}/{slug}/storyboard.json"
    for kind, slugs in sorted(TYPE_EXAMPLES.items()) for slug in slugs
]
