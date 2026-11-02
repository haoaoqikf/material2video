"""financial-timeseries 顶层材料结构模型。

金融材料有大量跨字段语义（日期覆盖、来源区间、投资计算），这里只校验文档形状；
为保证已有材料里的补充字段不被误判，prices 与 plan 允许额外键。
"""
from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from m2v.core.schema import NonEmptyText, StrictModel


class Instrument(StrictModel):
    model_config = ConfigDict(extra="allow", strict=True)

    kind: str
    name: NonEmptyText
    code: NonEmptyText
    market: NonEmptyText
    unit: NonEmptyText
    displayName: NonEmptyText | None = None
    listingDate: str | None = None
    indexStartDate: str | None = None


class Design(StrictModel):
    profile: str | None = None
    accent: str | None = None
    titleMode: str | None = None
    personality: str | None = None


class Request(StrictModel):
    model_config = ConfigDict(extra="allow", strict=True)

    schemaVersion: Any
    originalRequest: NonEmptyText
    instrument: Instrument
    requestedRange: list[str]
    displayRange: list[str]
    investment: Any = None
    confirmations: list[Any] | None = None
    design: Design | None = None


class Prices(StrictModel):
    model_config = ConfigDict(extra="allow", strict=True)

    schemaVersion: Any
    unit: str
    priceBasis: str
    points: list[Any]
    sources: list[Any]
    rawSnapshots: list[Any]
    expectedTradingDates: list[str]
    expectedTradingDatesSource: list[str]
    adjustmentBaseDate: str | None = None
    adjustmentDefinition: str | None = None
    splitAdjustments: list[Any] | None = None
    indexType: str | None = None
    fx: Any = None


class Canvas(StrictModel):
    width: int
    height: int


class Axis(StrictModel):
    model_config = ConfigDict(extra="allow", strict=True)

    dateRange: list[str]
    dateScale: str
    valueScale: str


class Segment(StrictModel):
    model_config = ConfigDict(extra="allow", strict=True)

    frames: list[Any]
    dates: list[Any]
    kind: str


class Plan(StrictModel):
    model_config = ConfigDict(extra="allow", strict=True)

    schemaVersion: Any
    chartType: str
    durationSeconds: Any
    fps: Any
    canvas: Canvas
    axis: Axis
    segments: list[Segment]
    pacing: Any = None
    rationale: Any = None
