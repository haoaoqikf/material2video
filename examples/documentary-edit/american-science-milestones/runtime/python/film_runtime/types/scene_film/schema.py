"""五类统一 v9 分镜的顶层结构模型。

幕内内容、镜头与事件的语义校验仍在 `explainer.py` 与 `code_scenes` 中；
这里只固定顶层与每一幕的字段集合，保持「未知字段拒绝」的现有行为。
字段类型留给现有中文校验器，避免通用英文错误抢先出现。
"""
from __future__ import annotations

from typing import Any

from film_runtime.core.schema import StrictModel


class Scene(StrictModel):
    id: Any
    template: Any
    content: Any
    narrationSegments: Any = None
    keywords: Any = None
    durationFrames: Any = None
    transition: Any = None
    transitionFrames: Any = None
    speech: Any = None
    leadInFrames: Any = None
    tailFrames: Any = None
    readingHoldFrames: Any = None
    events: Any = None


class Storyboard(StrictModel):
    version: Any
    schemaVersion: Any
    fps: Any = None
    width: Any = None
    height: Any = None
    title: Any
    input: Any = None
    targetSeconds: Any = None
    soundtrack: Any = None
    sources: Any = None
    scenes: list[Scene]
