"""自驾路线共享几何：GCJ-02 Web Mercator 投影、路线 bbox、投影长度与瓦片范围。"""
from __future__ import annotations

import math
from typing import Any

MERCATOR_RADIUS = 6378137.0
WORLD = 2 * math.pi * MERCATOR_RADIUS


def project(lng: float, lat: float) -> tuple[float, float]:
    return (MERCATOR_RADIUS * math.radians(lng),
            MERCATOR_RADIUS * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def unproject(x: float, y: float) -> tuple[float, float]:
    lng = math.degrees(x / MERCATOR_RADIUS)
    lat = math.degrees(2 * math.atan(math.exp(y / MERCATOR_RADIUS)) - math.pi / 2)
    return lng, lat


def route_points(route: dict[str, Any]) -> list[list[float]]:
    return [point for step in route["route"]["steps"] for point in step["points"]]


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
    return float(route["route"]["distanceMeters"]) / projected


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
