"""汽车展示类型适配器：材料门禁 + 无声类型生命周期。"""
from __future__ import annotations

from pathlib import Path

from m2v.core.errors import M2VError
from m2v.type_system.silent_type import SilentTypeSpec, build_silent_type
from m2v.types.vehicle_showcase import materials, render as vehicle_render


def _load(root: Path, project: dict) -> dict:
    if project.get("materials") != materials.MATERIALS:
        raise M2VError("汽车展示材料入口固定为 showcase.json、manifest.json")
    output = project.get("output") or {}
    if (output.get("width"), output.get("height")) != (materials.WIDTH, materials.HEIGHT):
        raise M2VError(f"汽车展示画幅固定为 {materials.WIDTH}×{materials.HEIGHT}；请更新 project.json")
    return materials.load_project(root)


TYPE = build_silent_type(SilentTypeSpec(
    name="vehicle-showcase",
    composition_id=vehicle_render.COMPOSITION_ID,
    width=materials.WIDTH,
    height=materials.HEIGHT,
    fps=materials.FPS,
    load=_load,
    build_props=materials.build_render_props,
    duration_frames=lambda docs, _props: docs["showcase"]["durationSeconds"] * materials.FPS,
    render=vehicle_render.render,
    review_gate=lambda root, project: materials.build_render_props(_load(root, project)),
))

validate, prepare, preview, render = TYPE.validate, TYPE.prepare, TYPE.preview, TYPE.render
review_gate = TYPE.review_gate
