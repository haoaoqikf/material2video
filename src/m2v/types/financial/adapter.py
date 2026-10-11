"""Financial time-series adapter for the common project lifecycle."""
from __future__ import annotations

from pathlib import Path

from m2v.core.errors import M2VError
from m2v.core.project import file_inputs, save_prepared
from m2v.types.financial import financial, financial_render
from m2v.types.registry import VideoType


def _load(root: Path, project: dict) -> dict:
    expected = {"request": "request.json", "prices": "prices.json", "plan": "animation-plan.json"}
    if project.get("materials") != expected:
        raise M2VError("金融类型材料入口固定为 request.json、prices.json、animation-plan.json")
    return financial.load_project(root)


def validate(root: Path, project: dict) -> None:
    _load(root, project)


def prepare(root: Path, project: dict) -> dict:
    docs = _load(root, project)
    props = financial.build_render_props(docs)
    frames = docs["plan"]["durationSeconds"] * financial.FPS
    return save_prepared(root, project=project, composition_id="FinancialTimeSeries", props=props,
        width=financial.WIDTH, height=financial.HEIGHT, fps=financial.FPS,
        duration_in_frames=frames, inputs=file_inputs(root, project))


def preview(root: Path, project: dict, *, limit_frames: int | None = None) -> Path:
    docs = _load(root, project)
    return financial_render.render(root, docs, preview=True, limit_frames=limit_frames)


def render(root: Path, project: dict) -> Path:
    docs = _load(root, project)
    return financial_render.render(root, docs)


def review_gate(root: Path, project: dict) -> None:
    docs = _load(root, project)
    financial.validate_legibility_review(root, docs)


def review_template(root: Path, _project: dict) -> None:
    """Create the existing full-video and mobile-legibility review template."""
    from m2v.types.financial import commands

    if commands.main(["review-template", "--project-dir", str(root)]):
        raise M2VError("金融类型手机可读性评审模板生成失败")


def review_criteria(_root: Path, _project: dict, _prepared: dict) -> dict[str, str]:
    return {"priceBasis": "价格来源、口径、覆盖范围与交易日一致",
            "investmentCalculation": "本金、日期区间和假设投资价值计算",
            "mobileLegibility": "手机竖屏下坐标、标注和收益颜色可读"}


TYPE = VideoType("financial-timeseries", "金融时间序列与假设投资价值演变", validate, prepare, preview, render,
                 review_gate=review_gate, review_criteria=review_criteria, review_template=review_template)
