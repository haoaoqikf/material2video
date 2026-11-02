"""building-construction 材料的结构模型。

只描述文档形状；开口是否落在墙面内、阶段是否首尾相接等业务规则仍在
`materials.py` 的语义校验里。
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from m2v.core.schema import NonEmptyText, StrictModel

WallSide = Literal["front", "back", "left", "right"]


class Canvas(StrictModel):
    width: int
    height: int


class Opening(StrictModel):
    id: NonEmptyText
    floor: int
    side: WallSide
    offset: float
    width: float
    height: float


class House(StrictModel):
    width: float
    depth: float
    floors: int
    floorHeight: float
    bayCount: int
    roofHeight: float
    wallThickness: float
    foundationDepth: float
    sitePadding: float
    openings: list[Opening] = Field(max_length=60)


class Building(StrictModel):
    schemaVersion: int
    canvas: Canvas
    house: House


class Stage(StrictModel):
    id: NonEmptyText
    label: NonEmptyText
    startSeconds: float
    endSeconds: float


class Camera(StrictModel):
    startAzimuth: float
    endAzimuth: float
    elevation: float


class Construction(StrictModel):
    schemaVersion: int
    durationSeconds: int
    fps: int
    stages: list[Stage] = Field(min_length=1, max_length=20)
    camera: Camera


class Asset(StrictModel):
    path: NonEmptyText
    sha256: NonEmptyText
    source: NonEmptyText
    license: NonEmptyText


class Manifest(StrictModel):
    schemaVersion: int
    assets: list[Asset] = Field(max_length=50)
