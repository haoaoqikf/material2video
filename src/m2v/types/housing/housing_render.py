"""住宅年度均价视频导出：共用无声渲染管线，只声明本类型的差异。"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from m2v.core.assets import REPOSITORY_ROOT
from m2v.engine import render_pipeline, remotion
from m2v.types.housing import housing

logger = logging.getLogger(__name__)
COMPOSITION_ID = "HousingTimeSeries"


def _inputs_digest(project_dir: Path) -> str:
    """绑定系列材料与共享渲染源码；改动任一实现都要让旧候选失效。"""
    web = REPOSITORY_ROOT / "web"
    script_dir = REPOSITORY_ROOT / "src"
    scripts = (Path(__file__), Path(__file__).with_name("housing.py"), Path(__file__).with_name("adapter.py"),
               Path(render_pipeline.__file__))
    inputs = [(project_dir, project_dir / housing.MATERIAL)]
    inputs.extend((web, path) for path in remotion.build_inputs() if path.is_relative_to(web))
    inputs.extend((REPOSITORY_ROOT, path) for path in remotion.build_inputs() if not path.is_relative_to(web))
    inputs.extend((script_dir, path) for path in scripts)
    digest = hashlib.sha256()
    for base, path in inputs:
        digest.update(path.resolve().relative_to(base.resolve()).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


SPEC = render_pipeline.SilentRenderSpec(
    composition_id=COMPOSITION_ID,
    fps=housing.FPS,
    width=housing.WIDTH,
    height=housing.HEIGHT,
    material_file=housing.MATERIAL,
    destination_name="housing-timeseries.mp4",
    preview_name="housing-timeseries-review.mp4",
    total_frames=lambda series: series.get("durationSeconds", housing.DEFAULT_DURATION_SECONDS) * housing.FPS,
    inputs_digest=lambda root: _inputs_digest(root),
    build_props=lambda series: housing.build_render_props(series),
    provenance_type="housing-timeseries",
    log_message="住宅均价视频已生成：%s（%d 帧，%d fps，无音轨）",
    report_extra=lambda session: {"compositionId": COMPOSITION_ID},
    log_progress=True,
)


def render(project_dir: Path, series: dict, *, output: Path | None = None,
           limit_frames: int | None = None, preview: bool = False, crf: int = 18,
           preset: str = "medium", start_seconds: float = 0, end_seconds: float | None = None) -> Path:
    """预演与正式导出都走共享管线；住宅成片要求无音轨。"""
    return render_pipeline.render(project_dir, series, SPEC, output=output, limit_frames=limit_frames,
                                  preview=preview, crf=crf, preset=preset,
                                  start_seconds=start_seconds, end_seconds=end_seconds)
