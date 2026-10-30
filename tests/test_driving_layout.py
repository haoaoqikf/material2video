"""共享布局与底图覆盖公式的跨语言常量检查。"""
from __future__ import annotations

from m2v.types.driving_route import geometry, layout


def test_layout_matches_the_portrait_contract():
    spec = layout.layout()
    assert (spec["width"], spec["height"]) == (1080, 1920)
    assert spec["title"]["height"] == 300
    content = layout.content_rect()
    assert content["top"] == 340
    assert content["bottom"] == 1830
    assert content["inner_left"] < content["inner_right"]
    assert content["inner_top"] < content["inner_bottom"]


def test_camera_envelope_covers_follow_and_overview_viewports():
    route_box = (12_600_000.0, 3_600_000.0, 13_500_000.0, 4_050_000.0)
    route_length = 937_000.0
    projected = 870_000.0
    envelope = layout.camera_envelope(route_box, projected, route_length)
    content = layout.content_rect()
    vertical_half = max(content["cy"], 1920 - content["cy"]) / envelope["full_scale"]
    assert envelope["full_scale"] > 0
    assert envelope["follow_scale"] == envelope["full_scale"] * layout.layout()["camera"]["followZoom"]
    assert envelope["follow_half_x"] >= 1080 / (2 * envelope["opening_scale"])
    assert envelope["follow_half_y"] >= max(content["cy"], 1920 - content["cy"]) / envelope["opening_scale"]
    assert envelope["overview_half_x"] >= 1080 / (2 * envelope["full_scale"])
    assert envelope["overview_half_y"] >= vertical_half
    assert envelope["lookahead_meters"] <= route_length


def test_flat_route_overview_covers_the_whole_screen_height():
    # 宽度远大于高度的东西向路线：概览仍须覆盖画幅上下边缘，而不是只覆盖内容区。
    route_box = (12_000_000.0, 3_900_000.0, 13_500_000.0, 3_960_000.0)
    envelope = layout.camera_envelope(route_box, 1_500_000.0, 1_200_000.0)
    content = layout.content_rect()
    assert envelope["overview_half_y"] >= max(content["cy"], 1920 - content["cy"]) / envelope["full_scale"]


def test_geometry_projection_and_length_are_consistent():
    route = {
        "route": {
            "distanceMeters": 5000,
            "steps": [{"points": [[121.47, 31.23], [121.48, 31.24], [121.49, 31.25]]}],
        }
    }
    assert geometry.projected_length(route) > 0
    assert geometry.meters_per_projected(route) > 0
    bbox = geometry.route_projected_bbox(route)
    assert bbox[0] < bbox[2] and bbox[1] < bbox[3]
    x0, y0, x1, y1 = geometry.tile_range((121.44, 31.2, 121.53, 31.29), 10)
    assert x0 <= x1 and y0 <= y1


def test_layout_json_is_a_build_input():
    from m2v.engine import remotion

    names = {path.name for path in remotion.build_inputs()}
    assert "layout.json" in names
