"""building-construction 材料的结构模型（v2）。

只描述文档形状；洞口是否落在墙面内、阶段/镜头/步骤覆盖等业务规则在
`materials.py`，构件 ID 规则在 `components.py`。
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from m2v.core.schema import NonEmptyText, StrictModel

WallSide = Literal["front", "back", "left", "right"]
RoofType = Literal["gable", "flat"]
Action = Literal["excavate", "pour", "grow", "slide", "lift", "rotate", "insert", "spread"]


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
    sill: float


class Roof(StrictModel):
    type: RoofType
    height: float
    overhang: float


class Stairs(StrictModel):
    side: WallSide
    offset: float
    width: float


class House(StrictModel):
    width: float
    depth: float
    floors: int
    floorHeight: float
    bayCount: int
    roof: Roof
    wallThickness: float
    foundationDepth: float
    sitePadding: float
    stairs: Stairs
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


class CameraSpec(StrictModel):
    position: list[float]
    target: list[float]
    fov: float


class Shot(StrictModel):
    id: NonEmptyText
    startSeconds: float
    endSeconds: float
    camera: CameraSpec
    to: CameraSpec | None = None
    hide: list[str] = Field(default_factory=list, max_length=60)


class Step(StrictModel):
    id: NonEmptyText
    stage: NonEmptyText
    select: list[NonEmptyText] = Field(min_length=1, max_length=60)
    action: Action
    label: NonEmptyText | None = None
    startSeconds: float
    endSeconds: float
    after: list[NonEmptyText] = Field(default_factory=list, max_length=30)


class Construction(StrictModel):
    schemaVersion: int
    durationSeconds: int
    fps: int
    stages: list[Stage] = Field(min_length=1, max_length=20)
    shots: list[Shot] = Field(min_length=1, max_length=30)
    initial: list[NonEmptyText] = Field(default_factory=list, max_length=60)
    steps: list[Step] = Field(min_length=1, max_length=200)


class Asset(StrictModel):
    path: NonEmptyText
    sha256: NonEmptyText
    source: NonEmptyText
    license: NonEmptyText


class Manifest(StrictModel):
    schemaVersion: int
    assets: list[Asset] = Field(max_length=50)
