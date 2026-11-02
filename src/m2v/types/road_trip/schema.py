"""road-trip 顶层材料结构模型。"""
from __future__ import annotations

from typing import Any, Literal

from m2v.core.schema import NonEmptyText, StrictModel
from m2v.types.route_schema import Place, SourceUsage


class Day(StrictModel):
    id: str
    title: NonEmptyText
    subtitle: str | None = None
    destination: Place
    via: list[Any]
    route: str
    basemapStyle: Literal["road", "satellite"] | None = None
    narration: list[Any]
    cards: list[Any]
    landmarks: list[Any]


class Trip(StrictModel):
    schemaVersion: int
    title: NonEmptyText
    start: Place
    end: Place
    routePreference: str
    targetSeconds: Any
    sourceUsage: SourceUsage
    sources: list[Any]
    days: list[Day]
    effects: list[Any]


class DayRoute(StrictModel):
    schemaVersion: int
    dayId: str
    start: Any
    destination: Any
    via: list[Any]
    routePreference: str
    requestDigest: str
    coordinateSystem: str
    origin: Any
    endPlace: Any
    viaPoints: Any
    route: Any
    cost: Any
    cities: list[Any]
    administrativePlaces: list[Any]
    acquisition: Any
