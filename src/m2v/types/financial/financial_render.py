"""金融时间序列视频导出：使用共享打包、浏览器会话与媒体验收底座。"""
from __future__ import annotations

import hashlib
import json
import logging
import os
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


def render(
    project_dir: Path,
    docs: dict,
    *,
    output: Path | None = None,
    limit_frames: int | None = None,
    preview: bool = False,
    crf: int = 18,
    preset: str = "medium",
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
    if not preview:
        financial.load_preview_record(project_dir, docs)
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
                    "frames": f"0-{frames - 1}", "scale": 1, "concurrency": 1,
                    "progressTotal": frames}

        render_started = time.monotonic()
        session = remotion.render_session(web_dir=web, bundle_dir=outcome.path, props=props_path,
            composition_id=COMPOSITION_ID, on_metadata=confirm, timeout_s=3600)
        timings.record("metadata", float(session.get("readySeconds") or 0))
        timings.record("render", max(time.monotonic() - render_started - timings.as_dict()["metadata"], 0))
        with perf.measure(timings, "probe"):
            output_validation.verify_output(temp_video, frames, financial.WIDTH, financial.HEIGHT, financial.FPS)
            _assert_no_audio(temp_video)
        if inputs_digest != financial.render_inputs_digest(project_dir):
            raise M2VError("渲染期间材料或资产变化；丢弃本次输出并重新预演")
        temp_video.replace(destination)

    security.grant_inherited_access(destination)
    if preview and output is None:
        record_path = project_dir / "outputs" / "previews" / "preview-record.json"
        record_path.write_text(json.dumps({
            "path": destination.resolve().relative_to(project_dir.resolve()).as_posix(),
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "frames": frames, "materialsAndAssetsSha256": inputs_digest,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
    logger.info("金融视频导出通过：%s（%d 帧，%d fps，无音轨）", destination, frames, financial.FPS)
    return destination
