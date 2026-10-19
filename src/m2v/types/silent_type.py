"""无声类型（金融、住宅）的统一适配器。

两种无声类型过去各写一份同样的生命周期：材料门禁 `_load`、`prepare`（拒绝
`--profile`、构造 props、写准备记录）、`preview`/`render` 转发与评审钩子。差异只有
类型名、材料门禁文案、props 构造、composition 参数、时长推导与评审钩子——全部由
:class:`SilentTypeSpec` 声明，生命周期只有这一份。

有音轨的通用类型不走这里：它的准备要合成配音、编译时间轴，形状不同。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from m2v.core.errors import M2VError
from m2v.core.project import file_inputs, save_prepared
from m2v.types.registry import VideoType


@dataclass(frozen=True)
class SilentTypeSpec:
    """无声类型的差异声明。"""

    name: str
    composition_id: str
    width: int
    height: int
    fps: int
    #: 显式传入 `--profile` 时的拒绝文案：档位目前只由通用类型提供。
    profile_error: str
    #: （作品根，作品清单）→ 已加载的材料；门禁不通过时抛出 M2VError。
    load: Callable[[Path, dict], dict]
    #: 材料 → composition props。
    build_props: Callable[[dict], dict]
    #: （材料，props）→ 全片帧数。
    duration_frames: Callable[[dict, dict], int]
    #: 类型自己的导出入口（`render(project_dir, material, ...)`）。
    render: Callable[..., Path]
    review_gate: Callable[[Path, dict], None] | None = None
    review_criteria: Callable[[Path, dict, dict], dict[str, str]] | None = None
    manual_review_available: bool = False


def build_silent_type(spec: SilentTypeSpec) -> VideoType:
    """按差异声明装配一个无声类型的 :class:`VideoType`。"""

    def validate(root: Path, project: dict) -> None:
        spec.load(root, project)

    def prepare(root: Path, project: dict, *, voice: str | None = None, rate: str | None = None,
                rhythm: dict | None = None, profile: str | None = None) -> dict:
        # 无声成片契约要求无音轨，因此不接受音色、语速与韵律；参数只为统一类型接口。
        if profile is not None:
            raise M2VError(spec.profile_error)
        docs = spec.load(root, project)
        props = spec.build_props(docs)
        return save_prepared(root, project=project, composition_id=spec.composition_id, props=props,
                             width=spec.width, height=spec.height, fps=spec.fps,
                             duration_in_frames=spec.duration_frames(docs, props),
                             inputs=file_inputs(root, project))

    def preview(root: Path, project: dict, *, limit_frames: int | None = None,
                start_seconds: float = 0, end_seconds: float | None = None) -> Path:
        return spec.render(root, spec.load(root, project), preview=True, limit_frames=limit_frames,
                           start_seconds=start_seconds, end_seconds=end_seconds)

    def render(root: Path, project: dict) -> Path:
        return spec.render(root, spec.load(root, project))

    return VideoType(spec.name, validate, prepare, preview, render,
                     review_gate=spec.review_gate, review_criteria=spec.review_criteria,
                     manual_review_available=spec.manual_review_available)
