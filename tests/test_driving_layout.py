"""共享布局与底图覆盖公式的跨语言常量检查。"""
from __future__ import annotations

import pytest

from m2v.core.errors import M2VError
from m2v.types.driving_route import geometry, layout


def test_layout_matches_the_portrait_contract():
    spec = layout.layout()
    assert spec["version"] == 6
    assert (spec["width"], spec["height"]) == (1080, 1920)
    assert spec["title"]["height"] == 300
    assert spec["camera"]["openingSeconds"] == 2
    assert spec["camera"]["openingStartZoom"] == 9
    assert spec["camera"]["openingEndZoom"] == 16
    assert spec["camera"]["openingTransitionSeconds"] == 0
    assert spec["camera"]["followZoom"] == 16
    assert spec["camera"]["cameraSmoothingSeconds"] == 0.6
    assert spec["camera"]["endingSeconds"] == 2
    assert spec["camera"]["endingHoldSeconds"] == 1
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


def test_opening_uses_faster_ease_out():
    route = {"route": {"steps": [{"points": [[121.47, 31.23], [121.48, 31.24]]}]}}
    geom = layout.route_geometry(route)
    start = layout._opening_camera(geom, 0.0, 1080, 1920)["scale"]
    middle = layout._opening_camera(geom, 0.5, 1080, 1920)["scale"]
    end = layout._opening_camera(geom, 1.0, 1080, 1920)["scale"]
    assert middle == pytest.approx(start + (end - start) * 0.75)


def test_follow_camera_smoothing_reduces_frame_acceleration():
    points = []
    for index in range(120):
        points.append([121.47 + index * 0.02, 31.23 + (0.004 if index % 2 else -0.004)])
    geom = layout.route_geometry({"route": {"steps": [{"points": points}]}})
    content = layout.content_rect()
    spans = layout._timeline(1800, 30)
    step = geom["length_meters"] / spans["drive_frames"]
    screen_scale = layout._full_scale(geom, 1080, 1920) * 16

    def acceleration(half_frames: int) -> list[float]:
        centers = []
        for frame in range(75, 1740):
            distance = layout.distance_for_frame(geom, frame, 1800, 30)
            camera = layout._follow_camera(geom, distance, 1080, 1920, step, half_frames)
            centers.append(((content["cx"] - camera["tx"]) / camera["scale"],
                            (content["cy"] - camera["ty"]) / camera["scale"]))
        values = []
        for index in range(1, len(centers) - 1):
            dx = centers[index + 1][0] - 2 * centers[index][0] + centers[index - 1][0]
            dy = centers[index + 1][1] - 2 * centers[index][1] + centers[index - 1][1]
            values.append((dx * dx + dy * dy) ** 0.5 * screen_scale)
        values.sort()
        return values

    raw = acceleration(0)
    smoothed = acceleration(18)
    assert smoothed[int(len(smoothed) * 0.95)] < raw[int(len(raw) * 0.95)] * 0.2
    assert smoothed[int(len(smoothed) * 0.95)] < 0.8


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


def test_city_route_starts_at_first_major_road_and_omits_local_access_mileage():
    access = [
        {"road": "厦门路", "distanceMeters": 88,
         "points": [[121.477422, 31.240031], [121.478329, 31.240224]]},
        {"road": "南苏州路", "distanceMeters": 48,
         "points": [[121.478329, 31.240224], [121.478742, 31.239961]]},
        {"road": "福建中路", "distanceMeters": 94,
         "points": [[121.478742, 31.239961], [121.479091, 31.239162]]},
    ]
    arterial = {"road": "北京东路", "distanceMeters": 3789,
                "points": [[121.479091, 31.239162], [121.442838, 31.224775]]}
    route = {"route": {"distanceMeters": 937281, "steps": [*access, arterial]}}

    render_steps, omitted_meters = geometry.route_start_selection(route)

    assert render_steps == [arterial]
    assert omitted_meters == pytest.approx(230)
    assert geometry.route_points(route)[0] == arterial["points"][0]
    assert geometry.visual_distance_meters(route) == pytest.approx(937051)


def test_city_route_requires_a_major_road_within_five_kilometers():
    points = [[121.47 + index * 0.001, 31.23] for index in range(7)]
    route = {"route": {"distanceMeters": 6000, "steps": [
        {"road": "街道", "distanceMeters": 900, "points": [points[index], points[index + 1]]}
        for index in range(6)
    ]}}

    with pytest.raises(M2VError, match="起点前 5 公里内未找到"):
        geometry.route_steps_for_render(route)


def test_layout_json_is_a_build_input():
    from m2v.engine import remotion

    names = {path.name for path in remotion.build_inputs()}
    assert "layout.json" in names
