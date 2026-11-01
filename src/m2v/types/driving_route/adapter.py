"""自驾路线适配器：材料门禁 + 无声类型生命周期。"""
from __future__ import annotations

from pathlib import Path

from m2v.core.errors import M2VError
from m2v.types.driving_route import materials, render as driving_render
from m2v.type_system.silent_type import SilentTypeSpec, build_silent_type


def _load(root: Path, project: dict) -> dict:
    if project.get("materials") != materials.MATERIALS:
        raise M2VError("自驾路线材料入口固定为 request.json、route.json")
    output = project.get("output") or {}
    width, height = output.get("width"), output.get("height")
    if (width, height) != (materials.WIDTH, materials.HEIGHT):
        raise M2VError(f"自驾路线画幅固定为 {materials.WIDTH}×{materials.HEIGHT}，"
                       f"当前为 {width}×{height}；请更新 project.json")
    return materials.load_project(root)


TYPE = build_silent_type(SilentTypeSpec(
    name="driving-route",
    composition_id=driving_render.COMPOSITION_ID,
    width=materials.WIDTH,
    height=materials.HEIGHT,
    fps=materials.FPS,
    load=_load,
    build_props=materials.build_render_props,
    duration_frames=lambda docs, _props: docs["request"]["durationSeconds"] * materials.FPS,
    render=driving_render.render,
    review_gate=lambda root, project: materials.build_render_props(_load(root, project)),
))

#: 生命周期入口同时以模块级名字暴露：测试与手工排查直接调用它们。
validate, prepare, preview, render = TYPE.validate, TYPE.prepare, TYPE.preview, TYPE.render
review_gate = TYPE.review_gate
