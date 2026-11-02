"""自驾路线共享几何：GCJ-02 Web Mercator 投影、路线 bbox、投影长度与瓦片范围。

投影与瓦片索引交给 mercantile，球面距离交给共享的 geographiclib 零扁率球体；
路线起点裁剪与连续大路判定仍是本类型的业务规则。
"""
from __future__ import annotations

import math
import re
from typing import Any

import mercantile

from m2v.core.errors import M2VError
from m2v.core.geodesy import distance_meters

MERCATOR_RADIUS = 6378137.0
WORLD = 2 * math.pi * MERCATOR_RADIUS
MIN_MAJOR_ROAD_STEP_METERS = 1000.0
MAX_ORIGIN_ACCESS_METERS = 5000.0
_MAJOR_ROAD_NAME = re.compile(r"高速|快速|国道|省道|大道|高架|环路|环线|[GS]\d{1,4}", re.IGNORECASE)


def project(lng: float, lat: float) -> tuple[float, float]:
    """经纬度 → Web Mercator 米（y 向北为正）。"""
    return tuple(mercantile.xy(lng, lat))


def unproject(x: float, y: float) -> tuple[float, float]:
    """Web Mercator 米 → 经纬度。"""
    result = mercantile.lnglat(x, y)
    return result.lng, result.lat


def _haversine_meters(a: list[float], b: list[float]) -> float:
    return distance_meters((a[0], a[1]), (b[0], b[1]))


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


def route_steps_for_render(route: dict[str, Any], *, trim_origin: bool = True) -> list[dict[str, Any]]:
    """跳过起点到首条大路之间的短接驳路，原始 API 路线材料保持完整。

    多日行程只有第 1 天需要裁剪：后续每天必须与前一天终点严格相接，裁掉
    起点接驳路会让两天之间出现缺口。
    """
    return route_start_selection(route)[0] if trim_origin else route["route"]["steps"]


def visual_distance_meters(route: dict[str, Any], *, trim_origin: bool = True) -> float:
    """城市间画面的里程不计入被省略的起点接驳路。"""
    if not trim_origin:
        return max(1.0, float(route["route"]["distanceMeters"]))
    return max(1.0, float(route["route"]["distanceMeters"])
               - route_start_selection(route)[1])


def route_points(route: dict[str, Any]) -> list[list[float]]:
    return [point for step in route_steps_for_render(route) for point in step["points"]]


def _haversine_meters(a: list[float], b: list[float]) -> float:
    return distance_meters((a[0], a[1]), (b[0], b[1]))


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


def _tile_axis_bounds(z: int) -> mercantile.Bbox:
    return mercantile.xy_bounds(mercantile.Tile(0, 0, z))


def tile_x(lng: float, z: int) -> float:
    """经度 → 小数瓦片列号；用 mercantile 的同一套投影与瓦片边界换算。"""
    x, _ = mercantile.xy(lng, 0.0)
    bounds = _tile_axis_bounds(z)
    return (x - bounds.left) / (bounds.right - bounds.left)


def tile_y(lat: float, z: int) -> float:
    """纬度 → 小数瓦片行号（向南递增）。"""
    _, y = mercantile.xy(0.0, lat)
    bounds = _tile_axis_bounds(z)
    return (bounds.top - y) / (bounds.top - bounds.bottom)


def tile_range(bbox: tuple[float, float, float, float], z: int) -> tuple[int, int, int, int]:
    limit = (1 << z) - 1
    min_lng, min_lat, max_lng, max_lat = bbox
    x0 = max(0, min(limit, int(math.floor(tile_x(min_lng, z)))))
    x1 = max(0, min(limit, int(math.ceil(tile_x(max_lng, z))) - 1))
    y0 = max(0, min(limit, int(math.floor(tile_y(max_lat, z)))))
    y1 = max(0, min(limit, int(math.ceil(tile_y(min_lat, z))) - 1))
    return x0, y0, x1, y1
