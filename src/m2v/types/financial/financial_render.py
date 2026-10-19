"""金融时间序列视频导出：共用无声渲染管线，只声明本类型的差异。"""
from __future__ import annotations

import logging
from pathlib import Path

import m2v.types.financial.financial as financial
from m2v.engine import render_pipeline

logger = logging.getLogger(__name__)
COMPOSITION_ID = "FinancialTimeSeries"

#: 渲染差异全部在这里，流程由 `render_pipeline` 提供。取值经模块属性间接读取，
#: 测试可以照旧替换材料摘要或 props 构造。
SPEC = render_pipeline.SilentRenderSpec(
    composition_id=COMPOSITION_ID,
    fps=financial.FPS,
    width=financial.WIDTH,
    height=financial.HEIGHT,
    material_file="animation-plan.json",
    destination_name="financial-line-no-events.mp4",
    preview_name="financial-line-no-events-review.mp4",
    total_frames=lambda docs: docs["plan"]["durationSeconds"] * financial.FPS,
    inputs_digest=lambda root: financial.render_inputs_digest(root),
    build_props=lambda docs: financial.build_render_props(docs),
    provenance_type="financial-timeseries",
    log_message="金融视频已生成：%s（%d 帧，%d fps，无音轨）",
    report_extra=lambda session: {"session": {
        "browsersOpened": session.get("browsersOpened"),
        "handshakeSeconds": session.get("readySeconds"),
        "observedPeakMemoryBytes": session.get("peakMemoryBytes"),
        "memorySamples": session.get("memorySamples")}},
)


def render(project_dir: Path, docs: dict, *, output: Path | None = None,
           limit_frames: int | None = None, preview: bool = False, crf: int = 18,
           preset: str = "medium", start_seconds: float = 0, end_seconds: float | None = None) -> Path:
    """预演与正式导出都走共享管线；金融成片要求无音轨。"""
    return render_pipeline.render(project_dir, docs, SPEC, output=output, limit_frames=limit_frames,
                                  preview=preview, crf=crf, preset=preset,
                                  start_seconds=start_seconds, end_seconds=end_seconds)
