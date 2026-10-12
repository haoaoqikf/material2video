"""视频类型的行为注册表。

一个视频类型由两处构成，且只有这两处：

1. **行为**——本模块注册的 ``VideoType``（校验、准备、预演、渲染与可选钩子）；
2. **身份与材料**——``catalog.json`` 里的一份登记项（名称、说明、材料入口、
   初始化模板与文档文案）。

新增类型因此不需要改动统一入口的命令分发，也不需要改作品契约；注册表与目录
按名称对应，任一侧缺失都会在渲染前以可照做的报错失败，而不是静默降级。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from m2v.core.errors import M2VError
from m2v.types import catalog

#: 已注册但未在类型目录登记时的说明文案。不使用空串，避免把缺失伪装成正常。
UNREGISTERED_DESCRIPTION = "未在类型目录登记"


@dataclass(frozen=True)
class VideoType:
    """一个视频类型的**行为**实现。

    名称必须与类型目录中的登记项一致；说明文案由目录提供，不在这里重复一次。
    """

    name: str
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
    """取行为实现；未注册或未在类型目录登记都在渲染前失败。"""
    try:
        video_type = _registry[name]
    except KeyError as exc:
        raise M2VError(f"未知视频类型：{name}；运行 m2v types 查看可用类型") from exc
    entry = catalog.catalog()
    if not entry.has(name):
        raise M2VError(
            f"视频类型未在类型目录登记：{name}；请在 {catalog.CATALOG_PATH.name} 中登记该类型的"
            f"说明与材料入口后重试（运行 m2v types 查看可用类型）"
        )
    return video_type


def all_types() -> tuple[VideoType, ...]:
    return tuple(_registry[name] for name in sorted(_registry))


def describe(name: str) -> str:
    """类型的一句话说明；未登记时显式标注，而不是回落到空串。"""
    entry = catalog.catalog()
    return entry.get(name).description if entry.has(name) else UNREGISTERED_DESCRIPTION
