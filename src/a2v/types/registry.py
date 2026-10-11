"""Explicit built-in type registry. New types register here without engine edits."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from a2v.core.errors import A2VError


@dataclass(frozen=True)
class VideoType:
    name: str
    description: str
    validate: Callable
    prepare: Callable
    preview: Callable
    render: Callable
    review_gate: Callable | None = None
    review_criteria: Callable | None = None
    review_template: Callable | None = None
    audio_tracks: Callable | None = None
    prepare_narration: Callable | None = None


_registry: dict[str, VideoType] = {}


def register(video_type: VideoType) -> None:
    if video_type.name in _registry:
        raise ValueError(f"视频类型重复注册：{video_type.name}")
    _registry[video_type.name] = video_type


def get(name: str) -> VideoType:
    try:
        return _registry[name]
    except KeyError as exc:
        raise A2VError(f"未知视频类型：{name}；运行 a2v types 查看可用类型") from exc


def all_types() -> tuple[VideoType, ...]:
    return tuple(_registry[name] for name in sorted(_registry))
