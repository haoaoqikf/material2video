"""Offline Remotion export for validated financial time-series materials."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from . import financial, remotion, render as render_engine, source_policy
from .errors import A2VError

logger = logging.getLogger(__name__)
COMPOSITION_ID = "FinancialTimeSeries"
ENTRY_POINT = "src/index.ts"
RENDER_SCRIPT = "scripts/remotion-render.mjs"


def _run_node(command: list[str], web: Path, what: str, timeout: float) -> None:
    try:
        result = subprocess.run(command, cwd=web, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise A2VError(f"{what}失败：{exc}") from exc
    if result.returncode:
        raise A2VError(f"{what}失败：\n{(result.stdout + result.stderr)[-5000:]}")


def _ensure_empty_code_scene_manifest(web: Path) -> None:
    """Financial scenes are shared trusted code and never import user modules."""
    manifest_path = web / ".gen" / "scene-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({
        "webDir": str(web.resolve()), "outFile": ".gen/active-scenes.ts", "modules": [],
    }), encoding="utf-8")
    _run_node([
        remotion.program("node"), "scripts/gen-active-scenes.mjs", "--manifest", str(manifest_path),
    ], web, "清理作品代码场景入口", 120)


def _bundle(web: Path, out: Path) -> Path:
    remotion.require_environment(web)
    _run_node([remotion.program("node"), "scripts/sync-fonts.mjs"], web, "同步渲染字体", 120)
    _run_node([remotion.program("node"), "scripts/ensure-entry.mjs"], web, "准备 Remotion 入口", 120)
    _ensure_empty_code_scene_manifest(web)
    source_violations = source_policy.scan(remotion.build_inputs())
    if source_violations:
        raise A2VError("Remotion 源码未通过确定性检查：" + "；".join(v.render(web) for v in source_violations))
    bundle = out / "bundle"
    _run_node([
        remotion.program("npx"), "remotion", "bundle", ENTRY_POINT, "--out-dir", str(bundle),
    ], web, "打包金融时间序列 composition", 600)
    if not bundle.is_dir():
        raise A2VError(f"Remotion 打包目录不存在：{bundle}")
    return bundle


def _assert_no_audio(video: Path) -> None:
    command = [get_ffmpeg_exe(), "-hide_banner", "-i", str(video), "-map", "0:a", "-f", "null", "-"]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if result.returncode == 0:
        raise A2VError("无声视频验收失败：成片包含音频流")
    if "matches no streams" not in result.stderr and "matches no streams" not in result.stdout:
        raise A2VError(f"无法验证成片音轨：{(result.stderr + result.stdout)[-1200:]}")


def render(
    project_dir: Path,
    docs: dict,
    *,
    output: Path | None = None,
    limit_frames: int | None = None,
    crf: int = 18,
    preset: str = "medium",
) -> Path:
    """Render validated props offline, verify media, then atomically publish it."""
    if crf < 0 or crf > 51:
        raise A2VError("CRF 必须处于 0 至 51")
    total_frames = docs["plan"]["durationSeconds"] * financial.FPS
    if limit_frames is not None and limit_frames < 1:
        raise A2VError("--limit-frames 必须大于 0")
    frames = min(total_frames, limit_frames) if limit_frames is not None else total_frames
    destination = output or project_dir / "outputs" / "financial-timeseries.mp4"
    if limit_frames is not None and output is None:
        destination = project_dir / "outputs" / "previews" / "financial-timeseries-preview.mp4"
    destination.parent.mkdir(parents=True, exist_ok=True)
    web = remotion.web_dir()
    remotion.require_environment(web)
    props = financial.build_render_props(docs)
    with tempfile.TemporaryDirectory(prefix="a2v-financial-", dir=destination.parent) as temporary:
        temp = Path(temporary)
        props_path = temp / "props.json"
        props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        bundle = _bundle(web, temp)
        metadata = remotion.metadata(web_dir=web, bundle_dir=bundle, props=props_path, composition_id=COMPOSITION_ID)
        expected = (financial.FPS, financial.WIDTH, financial.HEIGHT, total_frames)
        actual = (metadata.fps, metadata.width, metadata.height, metadata.duration_in_frames)
        if actual != expected:
            raise A2VError(f"composition 元数据不匹配：期望 {expected}，实际 {actual}")
        temp_video = temp / "video.mp4"
        remotion.render_frames(
            web_dir=web, bundle_dir=bundle, props=props_path, out=temp_video,
            total_frames=frames, crf=crf, preset=preset, timeout_s=3600,
            composition_id=COMPOSITION_ID,
        )
        render_engine._verify_output(temp_video, frames, financial.WIDTH, financial.HEIGHT, financial.FPS)
        _assert_no_audio(temp_video)
        if limit_frames is None:
            render_engine._grant_access(temp_video)
        os.replace(temp_video, destination)
    logger.info("金融视频导出通过：%s（%d 帧，%d fps，无音轨）", destination, frames, financial.FPS)
    return destination
