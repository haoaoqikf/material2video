"""建筑建造类型适配器：材料门禁 + 无声类型生命周期。"""
from __future__ import annotations

from pathlib import Path

from m2v.core.errors import M2VError
from m2v.types.building_construction import materials, render as building_render
from m2v.type_system.silent_type import SilentTypeSpec, build_silent_type


def _load(root: Path, project: dict) -> dict:
    if project.get("materials") != materials.MATERIALS:
        raise M2VError("建筑建造材料入口固定为 building.json、construction.json、assets/manifest.json")
    output = project.get("output") or {}
    if (output.get("width"), output.get("height")) != (materials.WIDTH, materials.HEIGHT):
        raise M2VError(f"建筑建造画幅固定为 {materials.WIDTH}×{materials.HEIGHT}；请更新 project.json")
    return materials.load_project(root)


TYPE = build_silent_type(SilentTypeSpec(
    name="building-construction",
    composition_id=building_render.COMPOSITION_ID,
    width=materials.WIDTH,
    height=materials.HEIGHT,
    fps=materials.FPS,
    load=_load,
    build_props=materials.build_render_props,
    duration_frames=lambda docs, _props: docs["construction"]["durationSeconds"] * materials.FPS,
    render=building_render.render,
    review_gate=lambda root, project: materials.build_render_props(_load(root, project)),
))

validate, prepare, preview, render = TYPE.validate, TYPE.prepare, TYPE.preview, TYPE.render
review_gate = TYPE.review_gate
