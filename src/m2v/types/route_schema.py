"""路线类型共享的结构模型：地点、来源使用与顶层文档。"""
from __future__ import annotations

from m2v.core.schema import NonEmptyText, StrictModel


class Place(StrictModel):
    city: NonEmptyText
    address: NonEmptyText
    label: NonEmptyText


class SourceDocument(StrictModel):
    title: NonEmptyText
    url: NonEmptyText
    note: NonEmptyText | None = None


class SourceUsage(StrictModel):
    verifiedOn: str
    documents: list[SourceDocument]
    account: NonEmptyText
    purpose: NonEmptyText
    offlineStorage: bool
    derivativeFrames: bool
    videoPublication: bool
    mapTiles: bool
    attribution: NonEmptyText
