"""建筑建造视频导出：复用共享无声渲染管线。"""
from __future__ import annotations

import logging
from pathlib import Path

from m2v.engine import render_pipeline
from m2v.types.building_construction import materials

logger = logging.getLogger(__name__)
COMPOSITION_ID = "BuildingConstruction"

SPEC = render_pipeline.SilentRenderSpec(
    composition_id=COMPOSITION_ID,
    fps=materials.FPS,
    width=materials.WIDTH,
    height=materials.HEIGHT,
    material_file=materials.MATERIALS["building"],
    destination_name="building-construction.mp4",
    preview_name="building-construction-review.mp4",
    total_frames=lambda docs: docs["construction"]["durationSeconds"] * materials.FPS,
    inputs_digest=materials.render_inputs_digest,
    build_props=materials.build_render_props,
    provenance_type="building-construction",
    log_message="建筑建造视频已生成：%s（%d 帧，%d fps，无音轨）",
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
    return render_pipeline.render(project_dir, docs, SPEC, output=output, limit_frames=limit_frames,
                                  preview=preview, crf=crf, preset=preset,
                                  start_seconds=start_seconds, end_seconds=end_seconds)
