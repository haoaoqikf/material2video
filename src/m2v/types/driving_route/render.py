"""自驾路线视频导出：复用共享无声渲染管线，只声明本类型的差异。"""
from __future__ import annotations

import logging
from pathlib import Path

from m2v.engine import render_pipeline
from m2v.types.driving_route import materials

logger = logging.getLogger(__name__)
COMPOSITION_ID = "DrivingRoute"

SPEC = render_pipeline.SilentRenderSpec(
    composition_id=COMPOSITION_ID,
    fps=materials.FPS,
    width=materials.WIDTH,
    height=materials.HEIGHT,
    material_file=materials.MATERIALS["request"],
    destination_name="driving-route.mp4",
    preview_name="driving-route-review.mp4",
    total_frames=lambda docs: docs["request"]["durationSeconds"] * materials.FPS,
    inputs_digest=materials.render_inputs_digest,
    build_props=materials.build_render_props,
    provenance_type="driving-route",
    log_message="自驾路线视频已生成：%s（%d 帧，%d fps，无音轨）",
    report_extra=lambda session: {"session": {
        "browsersOpened": session.get("browsersOpened"),
        "handshakeSeconds": session.get("readySeconds"),
        "observedPeakMemoryBytes": session.get("peakMemoryBytes"),
        "memorySamples": session.get("memorySamples")}},
)


def render(project_dir: Path, docs: dict, *, output: Path | None = None,
           limit_frames: int | None = None, preview: bool = False, crf: int = 18,
           preset: str = "medium", start_seconds: float = 0,
           end_seconds: float | None = None) -> Path:
    """预演与正式导出都走共享管线；自驾路线成片要求无音轨。"""
    return render_pipeline.render(project_dir, docs, SPEC, output=output, limit_frames=limit_frames,
                                  preview=preview, crf=crf, preset=preset,
                                  start_seconds=start_seconds, end_seconds=end_seconds)
