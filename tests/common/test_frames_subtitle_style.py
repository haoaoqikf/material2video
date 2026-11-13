"""字幕双行与柔光字段的画幅清单校验。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from m2v.core import frames
from m2v.core.errors import M2VError


def _root(tmp_path: Path, subtitle: dict) -> Path:
    root = tmp_path / "repo"
    (root / "web/src").mkdir(parents=True)
    (root / "web/src/frames.json").write_text(json.dumps({
        "schemaVersion": 1, "default": "1080x1920",
        "frames": [{"width": 1080, "height": 1920, "subtitle": subtitle}],
    }), encoding="utf-8")
    return root


def _base() -> dict:
    return {"x": 108, "y": 1518, "width": 864, "height": 240, "fontSize": 40,
            "lineHeight": 1.35, "textColor": "#f7f2e6", "plateColor": "#0b0d12"}


def test_spec_preserves_secondary_and_backing(tmp_path: Path) -> None:
    subtitle = {**_base(), "fontFamily": "M2V Serif SC",
                "secondary": {"fontFamily": "M2V Inter", "fontSize": 30, "lineHeight": 1.38,
                              "textColor": "#f7f2e6", "opacity": 0.8},
                "backing": {"mode": "adaptiveHalo", "color": "#070a0e",
                            "maxOpacity": 0.3, "feather": 240}}
    spec = frames.spec(1080, 1920, _root(tmp_path, subtitle))["subtitle"]
    assert spec["fontFamily"] == "M2V Serif SC"
    assert spec["secondary"]["fontSize"] == 30
    assert spec["backing"]["mode"] == "adaptiveHalo"


@pytest.mark.parametrize("change, message", [
    ({"secondary": {"fontSize": 30}}, "fontFamily"),
    ({"backing": {"mode": "plain", "color": "#070a0e", "maxOpacity": 0.3, "feather": 240}}, "mode"),
    ({"backing": {"mode": "adaptiveHalo", "color": "black", "maxOpacity": 0.3, "feather": 240}}, "颜色"),
])
def test_invalid_subtitle_style_is_rejected(tmp_path: Path, change: dict, message: str) -> None:
    with pytest.raises(M2VError, match=message):
        frames.spec(1080, 1920, _root(tmp_path, {**_base(), **change}))
