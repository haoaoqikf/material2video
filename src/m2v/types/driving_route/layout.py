"""自驾路线画面布局的唯一常量源（与前端 layout.json 同源）。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from m2v.core.assets import REPOSITORY_ROOT

LAYOUT_PATH = REPOSITORY_ROOT / "web/src/compositions/driving/layout.json"


@lru_cache(maxsize=1)
def layout() -> dict[str, Any]:
    return json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))


def layout_version() -> int:
    return int(layout()["version"])


def content_rect(width: int | None = None, height: int | None = None) -> dict[str, float]:
    spec = layout()
    width = int(width or spec["width"])
    height = int(height or spec["height"])
    top = spec["title"]["height"] + spec["content"]["topGap"]
    bottom = height - spec["content"]["bottomMargin"]
    left = spec["content"]["sideMargin"]
    right = width - spec["content"]["sideMargin"]
    padding = spec["content"]["padding"]
    return {
        "top": top, "bottom": bottom, "left": left, "right": right,
        "inner_top": top + padding, "inner_bottom": bottom - padding,
        "inner_left": left + padding, "inner_right": right - padding,
        "cx": (left + right) / 2, "cy": (top + bottom) / 2,
    }


def camera_envelope(route_bbox: tuple[float, float, float, float],
                    projected_length: float,
                    route_length_meters: float) -> dict[str, float]:
    """计算全程/跟随底图需要覆盖的投影半宽/半高与相机比例。

    route_bbox 与 projected_length 使用与前端一致的 Web Mercator 米；底层只服务
    本类型的底图取图与校验，不替代前端相机。
    """
    spec = layout()
    content = content_rect()
    span_x = max(route_bbox[2] - route_bbox[0], 1.0)
    span_y = max(route_bbox[3] - route_bbox[1], 1.0)
    inner_w = content["inner_right"] - content["inner_left"]
    inner_h = content["inner_bottom"] - content["inner_top"]
    full_scale = min(inner_w / span_x, inner_h / span_y)
    camera = spec["camera"]
    follow_scale = full_scale * camera["followZoom"]
    opening_scale = full_scale * camera["openingStartZoom"]
    meters_per_projected = (route_length_meters / projected_length) if projected_length > 0 else 1.0
    visible_meters = min(spec["width"], spec["height"]) / follow_scale * meters_per_projected
    lookahead_meters = min(route_length_meters * camera["lookaheadRouteFraction"],
                           visible_meters * camera["lookaheadViewFraction"])
    lookahead_projected = lookahead_meters / meters_per_projected if meters_per_projected > 0 else 0.0
    # 相机中心在内容区中心（略低于画幅中心），上下覆盖必须取到画幅边缘的最大距离。
    vertical_half = max(content["cy"], spec["height"] - content["cy"]) / full_scale
    overview_half_x = spec["width"] / (2 * full_scale) + lookahead_projected / 2
    overview_half_y = vertical_half + lookahead_projected / 2
    follow_half_x = max(spec["width"] / (2 * follow_scale),
                        spec["width"] / (2 * opening_scale)) + lookahead_projected / 2
    follow_half_y = max(vertical_half * full_scale / follow_scale,
                        vertical_half * full_scale / opening_scale) + lookahead_projected / 2
    return {
        "full_scale": full_scale,
        "follow_scale": follow_scale,
        "opening_scale": opening_scale,
        "lookahead_meters": lookahead_meters,
        "lookahead_projected": lookahead_projected,
        "overview_half_x": overview_half_x,
        "overview_half_y": overview_half_y,
        "follow_half_x": follow_half_x,
        "follow_half_y": follow_half_y,
    }
