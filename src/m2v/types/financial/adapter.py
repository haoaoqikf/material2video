"""金融时间序列适配器：材料门禁 + 无声类型生命周期。"""
from __future__ import annotations

from pathlib import Path

from m2v.core.errors import M2VError
from m2v.types.financial import financial, financial_render
from m2v.types.silent_type import SilentTypeSpec, build_silent_type

#: 材料入口固定为这三份；名字写在契约里，不由作品清单自选。
MATERIALS = {"request": "request.json", "prices": "prices.json", "plan": "animation-plan.json"}


def _load(root: Path, project: dict) -> dict:
    if project.get("materials") != MATERIALS:
        raise M2VError("金融类型材料入口固定为 request.json、prices.json、animation-plan.json")
    return financial.load_project(root)


TYPE = build_silent_type(SilentTypeSpec(
    name="financial-timeseries",
    composition_id="FinancialTimeSeries",
    width=financial.WIDTH,
    height=financial.HEIGHT,
    fps=financial.FPS,
    load=_load,
    build_props=financial.build_render_props,
    duration_frames=lambda docs, _props: docs["plan"]["durationSeconds"] * financial.FPS,
    render=financial_render.render,
    review_gate=lambda root, project: financial.build_render_props(_load(root, project)),
))

#: 生命周期入口同时以模块级名字暴露：测试与手工排查直接调用它们。
validate, prepare, preview, render = TYPE.validate, TYPE.prepare, TYPE.preview, TYPE.render
review_gate = TYPE.review_gate
