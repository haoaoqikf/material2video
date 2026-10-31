"""自驾路线共享几何：GCJ-02 Web Mercator 投影、路线 bbox、投影长度与瓦片范围。"""
from __future__ import annotations

import math
import re
from typing import Any

from m2v.core.errors import M2VError

MERCATOR_RADIUS = 6378137.0
WORLD = 2 * math.pi * MERCATOR_RADIUS
MIN_MAJOR_ROAD_STEP_METERS = 1000.0
MAX_ORIGIN_ACCESS_METERS = 5000.0
_MAJOR_ROAD_NAME = re.compile(r"高速|快速|国道|省道|大道|高架|环路|环线|[GS]\d{1,4}", re.IGNORECASE)


def project(lng: float, lat: float) -> tuple[float, float]:
    return (MERCATOR_RADIUS * math.radians(lng),
            MERCATOR_RADIUS * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def unproject(x: float, y: float) -> tuple[float, float]:
    lng = math.degrees(x / MERCATOR_RADIUS)
    lat = math.degrees(2 * math.atan(math.exp(y / MERCATOR_RADIUS)) - math.pi / 2)
    return lng, lat


def route_start_selection(route: dict[str, Any]) -> tuple[list[dict[str, Any]], float]:
    """返回首条大路起点后的路线和被省略的起点接驳里程。"""
    steps = route["route"]["steps"]
    skipped_meters = 0.0
    for index, step in enumerate(steps):
        road = str(step.get("road", "")).strip()
        try:
            distance = float(step.get("distanceMeters", 0))
        except (TypeError, ValueError):
            distance = 0.0
        if distance <= 0:
            points = step.get("points", [])
            distance = sum(_haversine_meters(points[point_index - 1], points[point_index])
                           for point_index in range(1, len(points)))
        is_named_major = bool(_MAJOR_ROAD_NAME.search(road))
        if is_named_major or distance >= MIN_MAJOR_ROAD_STEP_METERS:
            return steps[index:], skipped_meters
        skipped_meters += distance
        if skipped_meters > MAX_ORIGIN_ACCESS_METERS:
            break
    raise M2VError("起点前 5 公里内未找到可作为城市间行程起点的大路；"
                   "请将起点调整到主干道后重新取数")


def route_steps_for_render(route: dict[str, Any]) -> list[dict[str, Any]]:
    """跳过起点到首条大路之间的短接驳路，原始 API 路线材料保持完整。"""
    return route_start_selection(route)[0]


def visual_distance_meters(route: dict[str, Any]) -> float:
    """城市间画面的里程不计入被省略的起点接驳路。"""
    return max(1.0, float(route["route"]["distanceMeters"])
               - route_start_selection(route)[1])


def route_points(route: dict[str, Any]) -> list[list[float]]:
    return [point for step in route_steps_for_render(route) for point in step["points"]]


def _haversine_meters(a: list[float], b: list[float]) -> float:
    lng1, lat1 = math.radians(a[0]), math.radians(a[1])
    lng2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(h)))


def route_projected_points(route: dict[str, Any]) -> list[tuple[float, float]]:
    return [project(point[0], point[1]) for point in route_points(route)]


def route_projected_bbox(route: dict[str, Any]) -> tuple[float, float, float, float]:
    points = route_projected_points(route)
    return (min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points))


def projected_length(route: dict[str, Any]) -> float:
    points = route_projected_points(route)
    return sum(math.dist(points[index - 1], points[index]) for index in range(1, len(points)))


def meters_per_projected(route: dict[str, Any]) -> float:
    projected = projected_length(route)
    if projected <= 0:
        return 1.0
    return visual_distance_meters(route) / projected


def tile_x(lng: float, z: int) -> float:
    return (lng + 180.0) / 360.0 * (1 << z)


def tile_y(lat: float, z: int) -> float:
    return (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * (1 << z)


def tile_range(bbox: tuple[float, float, float, float], z: int) -> tuple[int, int, int, int]:
    limit = (1 << z) - 1
    min_lng, min_lat, max_lng, max_lat = bbox
    x0 = max(0, min(limit, int(math.floor(tile_x(min_lng, z)))))
    x1 = max(0, min(limit, int(math.ceil(tile_x(max_lng, z))) - 1))
    y0 = max(0, min(limit, int(math.floor(tile_y(max_lat, z)))))
    y1 = max(0, min(limit, int(math.ceil(tile_y(min_lat, z))) - 1))
    return x0, y0, x1, y1
