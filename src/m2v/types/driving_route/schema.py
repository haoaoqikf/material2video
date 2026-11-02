"""driving-route 顶层材料结构模型。"""
from __future__ import annotations

from typing import Any

from m2v.core.schema import StrictModel
from m2v.types.route_schema import Place, SourceUsage


class Canvas(StrictModel):
    width: int
    height: int


class DrivingRequest(StrictModel):
    schemaVersion: int
    origin: Place
    destination: Place
    strategy: str
    durationSeconds: Any
    canvas: Canvas
    sourceUsage: SourceUsage


class DrivingRoute(StrictModel):
    schemaVersion: int
    requestDigest: str
    coordinateSystem: str
    origin: Any
    destination: Any
    route: Any
    cost: Any
    cities: list[Any]
    administrativePlaces: list[Any]
    acquisition: Any
    sourceUsage: Any
    basemap: Any | None = None
