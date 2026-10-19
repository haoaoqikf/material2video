"""Silent Remotion export for annual housing-price projects."""
from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core import security
from m2v.core.assets import REPOSITORY_ROOT
from m2v.core.errors import M2VError
from m2v.engine import output_validation, perf, remotion
from m2v.types.housing import housing

logger = logging.getLogger(__name__)
COMPOSITION_ID = "HousingTimeSeries"


def _assert_no_audio(video: Path) -> None:
    result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(video), "-map", "0:a", "-f", "null", "-"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    output = result.stderr + result.stdout
    if result.returncode == 0 or "matches no streams" not in output:
        raise M2VError(f"无声视频验收失败：无法确认音轨为空（{output[-1200:]}）")


def _inputs_digest(project_dir: Path) -> str:
    web = REPOSITORY_ROOT / "web"
    script_dir = REPOSITORY_ROOT / "src"
    scripts = (Path(__file__), Path(__file__).with_name("housing.py"), Path(__file__).with_name("adapter.py"))
    inputs = [(project_dir, project_dir / housing.MATERIAL)]
    inputs.extend((web, path) for path in remotion.build_inputs())
    inputs.extend((script_dir, path) for path in scripts)
    digest = hashlib.sha256()
    for base, path in inputs:
        digest.update(path.resolve().relative_to(base.resolve()).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _generate(project_dir: Path, series: dict, *, output: Path | None = None,
           limit_frames: int | None = None, preview: bool = False,
           crf: int = 18, preset: str = "medium", start_frame: int = 0, defer_validation: bool = False) -> Path:
    if not 0 <= crf <= 51:
        raise M2VError("CRF 必须处于 0 至 51")
    total_frames = series.get("durationSeconds", housing.DEFAULT_DURATION_SECONDS) * housing.FPS
    if limit_frames is not None and limit_frames < 1:
        raise M2VError("--limit-frames 必须大于 0")
    frames = min(total_frames, limit_frames) if limit_frames is not None else total_frames
    if limit_frames is not None and not preview:
        raise M2VError("短预演须使用 preview 命令，正式导出不能限制帧数")
    destination = output or project_dir / "outputs" / "housing-timeseries.mp4"
    if preview and output is None:
        destination = project_dir / "outputs" / "previews" / "housing-timeseries-review.mp4"
    preview_dir = (project_dir / "outputs" / "previews").resolve()
    if preview and not destination.resolve().is_relative_to(preview_dir):
        raise M2VError("预演只能写入作品 outputs/previews，不能覆盖正式成片")
    if not preview and destination.resolve().is_relative_to(preview_dir):
        raise M2VError("正式成片不能写入 previews")
    destination.parent.mkdir(parents=True, exist_ok=True)
    web = remotion.web_dir()
    started = time.monotonic()
    timings = perf.StageTimings()
    inputs_digest = _inputs_digest(project_dir)
    props = housing.build_render_props(series)
    source_path = project_dir / housing.MATERIAL
    with tempfile.TemporaryDirectory(prefix="m2v-housing-", dir=destination.parent) as temporary:
        temp = Path(temporary)
        props_path = temp / "props.json"
        props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        temp_video = temp / "video.mp4"
        outcome = remotion.bundle(web_dir=web, out_dir=temp / "bundle", storyboard_path=source_path,
                                  content_root=project_dir.parent, workspace_root=project_dir.parent, cache=True)
        timings.record("bundle", outcome.build_seconds)
        timings.record("cache", outcome.cache_seconds)

        def confirm(metadata: remotion.CompositionMetadata) -> dict:
            expected = (housing.FPS, housing.WIDTH, housing.HEIGHT, total_frames)
            actual = (metadata.fps, metadata.width, metadata.height, metadata.duration_in_frames)
            if actual != expected:
                raise M2VError(f"composition 元数据不匹配：期望 {expected}，实际 {actual}")
            return {"out": str(temp_video), "crf": crf, "preset": preset,
                    "frames": f"{start_frame}-{start_frame + frames - 1}", "scale": 1, "concurrency": 1,
                    "progressTotal": frames}

        render_started = time.monotonic()
        session = remotion.render_session(web_dir=web, bundle_dir=outcome.path, props=props_path,
            composition_id=COMPOSITION_ID, on_metadata=confirm, timeout_s=3600,
            on_line=lambda line: logger.info("%s", line) if "__M2V_PROGRESS__" in line else None)
        timings.record("metadata", float(session.get("readySeconds") or 0))
        timings.record("render", max(time.monotonic() - render_started - timings.as_dict()["metadata"], 0))
        with perf.measure(timings, "probe"):
            if not defer_validation:
                output_validation.verify_output(temp_video, frames, housing.WIDTH, housing.HEIGHT, housing.FPS)
                _assert_no_audio(temp_video)
        if inputs_digest != _inputs_digest(project_dir):
            raise M2VError("渲染期间材料或资产变化；丢弃本次输出并重新预演")
        security.deliver(temp_video, destination)

    if not preview:
        provenance = {"schemaVersion": 1, "type": "housing-timeseries", "frames": frames,
                      "fps": housing.FPS, "width": housing.WIDTH, "height": housing.HEIGHT,
                      "renderer": "remotion", "compositionId": COMPOSITION_ID,
                      "materialsAndAssetsSha256": inputs_digest, "bundleKey": outcome.cache_key}
        destination.with_suffix(".provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    perf.write_report(perf.report_path_for(destination), perf.build_report(
        entry="preview" if preview else "render", output=destination, storyboard=source_path,
        frames=frames, fps=housing.FPS, width=housing.WIDTH, height=housing.HEIGHT,
        concurrency=1, timings=timings, total_seconds=time.monotonic() - started,
        cache={"status": outcome.cache_status, "key": outcome.cache_key, "detail": outcome.cache_detail},
        extra={"compositionId": COMPOSITION_ID}))
    logger.info("住宅均价视频已生成：%s（%d 帧，%d fps，无音轨）", destination, frames, housing.FPS)
    return destination


def render(project_dir: Path, series: dict, *, output: Path | None = None,
           limit_frames: int | None = None, preview: bool = False, crf: int = 18,
           preset: str = "medium", start_seconds: float = 0, end_seconds: float | None = None) -> Path:
    from m2v.core import delivery
    from m2v.core.preview import window
    from m2v.core.project import load_project, load_current_prepared
    material = series
    total = series.get("durationSeconds", housing.DEFAULT_DURATION_SECONDS) * housing.FPS
    if preview:
        start, end = window(total, housing.FPS, start_seconds=start_seconds, end_seconds=end_seconds, limit_frames=limit_frames)
        return _generate(project_dir, material, output=output, preview=True, limit_frames=end-start,
                         start_frame=start, crf=crf, preset=preset)
    if limit_frames is not None or start_seconds or end_seconds is not None:
        raise M2VError("正式导出不能限制时间范围")
    if output is not None and output.resolve().is_relative_to((project_dir / "outputs/previews").resolve()):
        raise M2VError("正式成片不能写入 previews")
    root, project = load_project(project_dir)
    def current():
        _, latest = load_project(root)
        prepared = load_current_prepared(root, latest)
        return delivery.binding(root, prepared, {"crf": crf, "preset": preset,
            "inputs": _inputs_digest(root)})
    def verify(video):
        output_validation.verify_output(video, total, housing.WIDTH, housing.HEIGHT, housing.FPS)
        _assert_no_audio(video)
    destination = output or root / "outputs/housing-timeseries.mp4"
    return delivery.export_once(destination, current(),
        lambda target: _generate(root, material, output=target, crf=crf, preset=preset, defer_validation=True),
        verify, current, directory=delivery.outputs(root))
