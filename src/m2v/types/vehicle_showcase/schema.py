"""vehicle-model 来源材料的结构模型。"""
from __future__ import annotations

from pydantic import Field

from m2v.core.schema import NonEmptyText, StrictModel


class Canvas(StrictModel):
    width: int
    height: int


class Camera(StrictModel):
    distance: float
    height: float
    orbitStartDegrees: float
    orbitEndDegrees: float


class Effects(StrictModel):
    speedStartSeconds: float
    speedEndSeconds: float
    fadeOutSeconds: float


class Studio(StrictModel):
    environment: NonEmptyText
    bodyAo: NonEmptyText
    floorNormal: NonEmptyText
    floorRoughness: NonEmptyText


class Showcase(StrictModel):
    schemaVersion: int
    canvas: Canvas
    durationSeconds: int
    fps: int
    model: NonEmptyText
    wheelNodes: list[NonEmptyText] = Field(min_length=1, max_length=12)
    camera: Camera
    effects: Effects
    studio: Studio


class Asset(StrictModel):
    path: NonEmptyText
    sha256: NonEmptyText
    source: NonEmptyText
    license: NonEmptyText


class Manifest(StrictModel):
    schemaVersion: int
    assets: list[Asset] = Field(min_length=1, max_length=80)
