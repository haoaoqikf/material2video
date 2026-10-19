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


def prepare(root: Path, project: dict, *, voice: str | None = None, rate: str | None = None,
            rhythm: dict | None = None, profile: str | None = None) -> dict:
    # 金融成片契约要求无音轨，因此不接受音色、语速与韵律；参数只为统一类型接口。
    # 制作档位目前只由通用类型提供：显式拒绝，而不是静默按 standard 处理。
    if profile is not None:
        raise M2VError("金融成片不支持制作档位；--profile 仅适用于 general 作品")
    docs = _load(root, project)
    props = financial.build_render_props(docs)
    frames = docs["plan"]["durationSeconds"] * financial.FPS
    return save_prepared(root, project=project, composition_id="FinancialTimeSeries", props=props,
        width=financial.WIDTH, height=financial.HEIGHT, fps=financial.FPS,
        duration_in_frames=frames, inputs=file_inputs(root, project))


def preview(root: Path, project: dict, *, limit_frames: int | None = None, start_seconds=0, end_seconds=None) -> Path:
    docs = _load(root, project)
    return financial_render.render(root, docs, preview=True, limit_frames=limit_frames, start_seconds=start_seconds, end_seconds=end_seconds)


def render(root: Path, project: dict) -> Path:
    docs = _load(root, project)
    return financial_render.render(root, docs)


def review_gate(root: Path, project: dict) -> None:
    docs = _load(root, project)
    financial.build_render_props(docs)


TYPE = VideoType("financial-timeseries", validate, prepare, preview, render,
                 review_gate=review_gate, manual_review_available=False)
