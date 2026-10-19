"""金融时间序列视频导出：使用共享打包、浏览器会话与媒体验收底座。"""
from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

import m2v.types.financial.financial as financial
from m2v.core import security
from m2v.core.errors import M2VError
from m2v.engine import output_validation, perf, remotion

logger = logging.getLogger(__name__)
COMPOSITION_ID = "FinancialTimeSeries"


def _assert_no_audio(video: Path) -> None:
    command = [get_ffmpeg_exe(), "-hide_banner", "-i", str(video), "-map", "0:a", "-f", "null", "-"]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if result.returncode == 0:
        raise M2VError("无声视频验收失败：成片包含音频流")
    if "matches no streams" not in result.stderr and "matches no streams" not in result.stdout:
        raise M2VError(f"无法验证成片音轨：{(result.stderr + result.stdout)[-1200:]}")


def _generate(
    project_dir: Path,
    docs: dict,
    *,
    output: Path | None = None,
    limit_frames: int | None = None,
    preview: bool = False,
    crf: int = 18,
    preset: str = "medium",
    start_frame: int = 0,
    defer_validation: bool = False,
) -> Path:
    """Validate, render into a temporary file, then atomically publish the video."""
    if crf < 0 or crf > 51:
        raise M2VError("CRF 必须处于 0 至 51")
    total_frames = docs["plan"]["durationSeconds"] * financial.FPS
    if limit_frames is not None and limit_frames < 1:
        raise M2VError("--limit-frames 必须大于 0")
    frames = min(total_frames, limit_frames) if limit_frames is not None else total_frames
    if limit_frames is not None and not preview:
        raise M2VError("短预演须使用 preview 命令，正式导出不能限制帧数")
    destination = output or project_dir / "outputs" / "financial-line-no-events.mp4"
    if preview and output is None:
        destination = project_dir / "outputs" / "previews" / "financial-line-no-events-review.mp4"
    if preview and not destination.resolve().is_relative_to((project_dir / "outputs" / "previews").resolve()):
        raise M2VError("预演只能写入作品 outputs/previews，不能覆盖正式成片")
    if not preview and destination.resolve().is_relative_to((project_dir / "outputs" / "previews").resolve()):
        raise M2VError("正式成片不能写入 previews")
    destination.parent.mkdir(parents=True, exist_ok=True)
    web = remotion.web_dir()
    started = time.monotonic()
    timings = perf.StageTimings()
    inputs_digest = financial.render_inputs_digest(project_dir)
    props = financial.build_render_props(docs)
    storyboard_path = project_dir / "animation-plan.json"
    with tempfile.TemporaryDirectory(prefix="m2v-financial-", dir=destination.parent) as temporary:
        temp = Path(temporary)
        props_path = temp / "props.json"
        props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        temp_video = temp / "video.mp4"
        outcome = remotion.bundle(web_dir=web, out_dir=temp / "bundle", storyboard_path=storyboard_path,
                                  content_root=project_dir.parent, workspace_root=project_dir.parent, cache=True)
        timings.record("bundle", outcome.build_seconds)
        timings.record("cache", outcome.cache_seconds)

        def confirm(metadata: remotion.CompositionMetadata) -> dict:
            expected = (financial.FPS, financial.WIDTH, financial.HEIGHT, total_frames)
            actual = (metadata.fps, metadata.width, metadata.height, metadata.duration_in_frames)
            if actual != expected:
                raise M2VError(f"composition 元数据不匹配：期望 {expected}，实际 {actual}")
            return {"out": str(temp_video), "crf": crf, "preset": preset,
                    "frames": f"{start_frame}-{start_frame + frames - 1}", "scale": 1, "concurrency": 1,
                    "progressTotal": frames}

        render_started = time.monotonic()
        session = remotion.render_session(web_dir=web, bundle_dir=outcome.path, props=props_path,
            composition_id=COMPOSITION_ID, on_metadata=confirm, timeout_s=3600)
        timings.record("metadata", float(session.get("readySeconds") or 0))
        timings.record("render", max(time.monotonic() - render_started - timings.as_dict()["metadata"], 0))
        with perf.measure(timings, "probe"):
            if not defer_validation:
                output_validation.verify_output(temp_video, frames, financial.WIDTH, financial.HEIGHT, financial.FPS)
                _assert_no_audio(temp_video)
        if inputs_digest != financial.render_inputs_digest(project_dir):
            raise M2VError("渲染期间材料或资产变化；丢弃本次输出并重新预演")
        security.deliver(temp_video, destination)

    if not preview:
        provenance = {"schemaVersion": 1, "type": "financial-timeseries",
                      "frames": frames, "fps": financial.FPS, "width": financial.WIDTH,
                      "height": financial.HEIGHT, "renderer": "remotion",
                      "compositionId": COMPOSITION_ID, "materialsAndAssetsSha256": inputs_digest,
                      "bundleKey": outcome.cache_key}
        destination.with_suffix(".provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = perf.build_report(entry="preview" if preview else "render", output=destination,
        storyboard=storyboard_path, frames=frames, fps=financial.FPS, width=financial.WIDTH,
        height=financial.HEIGHT, concurrency=1, timings=timings, total_seconds=time.monotonic() - started,
        cache={"status": outcome.cache_status, "key": outcome.cache_key, "detail": outcome.cache_detail},
        extra={"session": {"browsersOpened": session.get("browsersOpened"),
                           "handshakeSeconds": session.get("readySeconds"),
                           "observedPeakMemoryBytes": session.get("peakMemoryBytes"),
                           "memorySamples": session.get("memorySamples")}})
    perf.write_report(perf.report_path_for(destination), report)
    logger.info("金融视频已生成：%s（%d 帧，%d fps，无音轨）", destination, frames, financial.FPS)
    return destination


def render(project_dir: Path, docs: dict, *, output: Path | None = None,
           limit_frames: int | None = None, preview: bool = False, crf: int = 18,
           preset: str = "medium", start_seconds: float = 0, end_seconds: float | None = None) -> Path:
    from m2v.core import delivery
    from m2v.core.preview import window
    from m2v.core.project import load_project, load_current_prepared
    material = docs
    total = docs["plan"]["durationSeconds"] * financial.FPS
    if preview:
        start, end = window(total, financial.FPS, start_seconds=start_seconds, end_seconds=end_seconds, limit_frames=limit_frames)
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
            "inputs": financial.render_inputs_digest(root)})
    def verify(video):
        output_validation.verify_output(video, total, financial.WIDTH, financial.HEIGHT, financial.FPS)
        _assert_no_audio(video)
    destination = output or root / "outputs/financial-line-no-events.mp4"
    return delivery.export_once(destination, current(),
        lambda target: _generate(root, material, output=target, crf=crf, preset=preset, defer_validation=True),
        verify, current, directory=delivery.outputs(root))
