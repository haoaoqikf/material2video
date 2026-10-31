"""多日地图游记适配器：材料门禁 + 有声类型生命周期。"""
from __future__ import annotations

from pathlib import Path

from m2v.core.errors import M2VError
from m2v.types.registry import VideoType
from m2v.types.road_trip import materials, prepare as prepare_module, render as render_module


def _load(root: Path, project: dict) -> dict:
    if project.get("materials") != materials.MATERIALS:
        raise M2VError("多日地图游记材料入口固定为 trip.json")
    output = project.get("output") or {}
    if (output.get("width"), output.get("height")) != (materials.WIDTH, materials.HEIGHT):
        raise M2VError(f"多日地图游记画幅固定为 {materials.WIDTH}×{materials.HEIGHT}，"
                       f"当前为 {output.get('width')}×{output.get('height')}；请更新 project.json")
    return materials.load_project(root)


def validate(root: Path, project: dict) -> None:
    _load(root, project)


def prepare(root: Path, project: dict, *, voice: str | None = None, rate: str | None = None,
            rhythm: dict | None = None) -> dict:
    return prepare_module.prepare(root, project, voice=voice, rate=rate, rhythm=rhythm)


def preview(root: Path, project: dict, *, limit_frames: int | None = None,
            start_seconds: float = 0, end_seconds: float | None = None) -> Path:
    return render_module.render(root, project, preview=True, limit_frames=limit_frames,
                                start_seconds=start_seconds, end_seconds=end_seconds)


def render(root: Path, project: dict) -> Path:
    return render_module.render(root, project)


def review_gate(root: Path, project: dict) -> None:
    _load(root, project)
    render_module.current(root, project)


TYPE = VideoType("road-trip", validate, prepare, preview, render,
                 review_gate=review_gate, prepared_check=render_module.current)
