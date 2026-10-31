"""多日地图游记导出：画面渲染、本地资源注入、音频混入与有声验收。

底图以本地路径进入 props，渲染时由本地静态服务提供 `assetBase`；前端只挂载
当前视口可见瓦片，全程不发生外部网络请求。正式成片必须带母版音轨，并量测
集成响度与真峰值。
"""
from __future__ import annotations

import hashlib
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

from m2v.core import delivery, security
from m2v.core.errors import M2VError
from m2v.core.preview import window
from m2v.core.project import _write_json, load_current_prepared, load_project
from m2v.engine import audio, contract_page, output_validation, perf, remotion, render_pipeline
from m2v.engine.http_server import LocalServer
from m2v.types.road_trip import materials
from m2v.types.road_trip.prepare import implementation_digest

logger = logging.getLogger(__name__)
COMPOSITION_ID = "RoadTrip"
PREPARED_VERSION = 1

MEASURE_BODY = r"""  const problems = [];
  const box = document.querySelector('[data-m2v-subtitle]');
  if (!box) problems.push('画面缺少共享字幕层');
  else {
    const outer = box.getBoundingClientRect();
    if (Math.round(outer.left) !== B.x || Math.round(outer.top) !== B.y
        || Math.round(outer.width) !== B.width || Math.round(outer.height) !== B.height)
      problems.push('字幕安全区不符：' + [outer.left, outer.top, outer.width, outer.height].join(','));
    const copy = box.querySelector('[data-m2v-copy]');
    if (copy) {
      const range = document.createRange(); range.selectNodeContents(copy);
      for (const rect of range.getClientRects()) {
        if (!rect.width || !rect.height) continue;
        if (rect.left < B.x - 1 || rect.right > B.x + B.width + 1
            || rect.top < B.y - 1 || rect.bottom > B.y + B.height + 1)
          problems.push('字幕溢出安全区：' + copy.textContent);
      }
    }
    for (const card of document.querySelectorAll('[data-m2v-card]')) {
      const rect = card.getBoundingClientRect();
      if (rect.left < B.x + B.width && rect.right > B.x
          && rect.top < B.y + B.height && rect.bottom > B.y)
        problems.push('数据卡遮挡字幕安全区：' + card.getAttribute('data-m2v-card'));
      if (rect.left < -1 || rect.top < -1 || rect.right > W + 1 || rect.bottom > H + 1)
        problems.push('数据卡越出画布：' + card.getAttribute('data-m2v-card'));
    }
  }
  return problems;
}"""


def measure_script(width: int, height: int) -> str:
    from m2v.core import frames
    safe = frames.spec(width, height)["subtitle"]["safeArea"]
    return ("() => {\n  const B = " + json.dumps(safe)
            + f";\n  const W = {width}, H = {height};\n" + MEASURE_BODY)


def has_audio(prepared: dict) -> bool:
    segments = (prepared.get("audio") or {}).get("segments") or []
    return bool(segments)


def current(root: Path, project: dict) -> dict:
    prepared = load_current_prepared(root, project)
    if prepared.get("compositionId") != COMPOSITION_ID:
        raise M2VError("准备记录不是多日地图游记；请重新 prepare")
    if prepared.get("inputs", {}).get("productionContract") != "road-trip-v1":
        raise M2VError("旧制作契约准备记录已失效；请重新 prepare")
    if not has_audio(prepared):
        raise M2VError("准备记录没有母版音轨；请重新 prepare，正式成片不得无声冒充有声")
    master = root / prepared["audio"]["segments"][0]["path"]
    if not master.is_file():
        raise M2VError("准备记录的母版音轨不存在；请重新 prepare")
    actual = remotion.build_input_fingerprint(workspace_root=root.parent)["digest"]
    if prepared["inputs"].get("renderer") != actual:
        raise M2VError("渲染代码、字体或资源已变化；请重新 prepare")
    if prepared["inputs"].get("implementation") != implementation_digest():
        raise M2VError("游记准备、混音或量测实现已变化；请重新 prepare")
    if not 1 <= prepared["durationInFrames"] <= 600 * prepared["fps"]:
        raise M2VError("准备记录时长超出 600 秒；请重新 prepare")
    return prepared


def _frames_to_check(prepared: dict) -> set[int]:
    total = prepared["durationInFrames"]
    frames = {0, total - 1}
    for cue in prepared["props"].get("subtitleCues", []):
        frames.update({cue["startFrame"], cue["endFrame"] - 1})
    for day in prepared["props"]["days"]:
        start = day["startFrame"]
        frames.update({start, start + day.get("arrivalLocalFrame", 0),
                       start + day["durationInFrames"] - 1})
    return {frame for frame in frames if 0 <= frame < total}


def layout_check(root: Path, prepared: dict, *, snapshots: Path | None = None) -> dict:
    from playwright.sync_api import sync_playwright
    from m2v.core.fonts import audit_fonts
    missing = audit_fonts(contract_page.font_files(), prepared["props"])
    if missing:
        raise M2VError(f"游记字体缺字：{missing[:5]}")
    width, height = prepared["width"], prepared["height"]
    outputs = root / "outputs"
    outputs.mkdir(exist_ok=True)
    problems: list[dict[str, Any]] = []
    checked = _frames_to_check(prepared)
    with tempfile.TemporaryDirectory(prefix="roadtrip-layout-", dir=outputs) as temporary, \
            LocalServer(root, cors=True) as server:
        material = Path(temporary) / "props.json"
        material.write_text(json.dumps({**prepared["props"], "assetBase": server.base_url + "/"},
                                       ensure_ascii=False), encoding="utf-8")
        script = measure_script(width, height)
        with contract_page.serve_roadtrip_page(material, root) as url, sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": width, "height": height},
                                        device_scale_factor=1)
                page.goto(url + "&m2v-roadtrip=1")
                page.wait_for_function("window.__M2V__?.version === 6", timeout=30000)
                page.evaluate("async () => await window.__M2V__.ready()")
                for frame_number in sorted(checked):
                    page.evaluate("async f => await window.__M2V__.seekToFrame(f)", frame_number)
                    errors = page.evaluate(script)
                    problems.extend({"frame": frame_number, "message": error}
                                    for error in errors)
                    if snapshots:
                        snapshots.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(snapshots / f"frame-{frame_number}.png"))
            finally:
                browser.close()
    result = {"schemaVersion": 1, "preparedFingerprint": prepared["preparedFingerprint"],
              "checkedFrames": len(checked), "problems": problems,
              "status": "fail" if problems else "pass"}
    _write_json(outputs / "layout-check.json", result)
    if problems:
        raise M2VError(f"游记画面量测失败：{problems[:5]}；请调整卡片位置或字幕文本")
    return result


def _binding(root: Path, prepared: dict) -> dict:
    return delivery.binding(root, prepared, {"crf": 18, "preset": "medium",
                                             "inputs-digest": materials.render_inputs_digest(root)})


def _mux_audio(root: Path, prepared: dict, silent: Path, target: Path, *,
               start_frame: int, frames: int) -> None:
    fps = prepared["fps"]
    master = root / prepared["audio"]["segments"][0]["path"]
    audio.mux(silent, master, target, frames / fps, start=start_frame / fps)


def _generate(root: Path, project: dict, *, preview: bool = False, start_frame: int = 0,
              end_frame: int | None = None, output: Path | None = None,
              defer_validation: bool = False) -> Path:
    prepared = current(root, project)
    fps = prepared["fps"]
    width, height = prepared["width"], prepared["height"]
    started = time.monotonic()
    layout_check(root, prepared)
    layout_seconds = time.monotonic() - started
    end_frame = end_frame or prepared["durationInFrames"]
    frames = end_frame - start_frame
    destination = output or root / (
        "outputs/previews/road-trip-review.mp4" if preview else "outputs/road-trip.mp4")
    destination.parent.mkdir(parents=True, exist_ok=True)
    entry = root / materials.MATERIALS["trip"]
    timings = perf.StageTimings()
    with tempfile.TemporaryDirectory(prefix="road-trip-render-", dir=destination.parent) as temporary, \
            LocalServer(root, cors=True) as server:
        work = Path(temporary)
        props_file = work / "props.json"
        props_file.write_text(json.dumps({**prepared["props"], "assetBase": server.base_url + "/"},
                                         ensure_ascii=False), encoding="utf-8")
        outcome = remotion.bundle(web_dir=remotion.web_dir(), out_dir=work / "bundle",
                                  storyboard_path=entry, content_root=root.parent,
                                  workspace_root=root.parent, cache=True)
        timings.record("bundle", outcome.build_seconds)
        timings.record("cache", outcome.cache_seconds)
        silent = work / "silent.mp4"
        confirm = render_pipeline.metadata_confirm(
            (fps, width, height, prepared["durationInFrames"]), silent, crf=18, preset="medium",
            frames=frames, start_frame=start_frame, label="游记 composition")
        render_started = time.monotonic()
        session = remotion.render_session(
            web_dir=remotion.web_dir(), bundle_dir=outcome.path, props=props_file,
            composition_id=COMPOSITION_ID, on_metadata=confirm, timeout_s=7200,
            on_line=remotion.progress_handler(frames))
        timings.record("metadata", float(session.get("readySeconds") or 0))
        timings.record("render", max(0, time.monotonic() - render_started
                                     - float(session.get("readySeconds") or 0)))
        final = work / "final.mp4"
        with perf.measure(timings, "mux"):
            _mux_audio(root, prepared, silent, final, start_frame=start_frame, frames=frames)
        with perf.measure(timings, "probe"):
            if not defer_validation:
                output_validation.verify_output(final, frames, width, height, fps, expect_audio=True)
                _verify_audio_stream(final)
        if current(root, project)["preparedFingerprint"] != prepared["preparedFingerprint"]:
            raise M2VError("渲染期间材料或准备记录变化；丢弃本次输出")
        provenance = {
            "schemaVersion": 1, "type": "road-trip", "projectId": project["id"],
            "preparedFingerprint": prepared["preparedFingerprint"],
            "compositionId": COMPOSITION_ID, "inputs": prepared["inputs"],
            "durationInFrames": frames, "fps": fps, "width": width, "height": height,
            "audio": {
                "master": prepared["audio"]["segments"][0]["path"],
                "masterSha256": prepared["audio"]["segments"][0].get("sha256"),
                "delivery": {"codec": "aac", "sampleRate": 44100, "channels": 2,
                             "bitrate": "128k"},
            },
            "delivery": {"sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                         "codec": "h264", "frames": frames, "fps": fps,
                         "width": width, "height": height},
        }
        if not preview:
            _write_json(work / "final.provenance.json", provenance)
        security.deliver(final, destination)
        if not preview:
            security.deliver(work / "final.provenance.json",
                             destination.with_suffix(".provenance.json"))
    render_pipeline.write_report(
        destination, entry="preview" if preview else "render", storyboard=entry, frames=frames,
        fps=fps, width=width, height=height, timings=timings,
        total_seconds=time.monotonic() - started, outcome=outcome,
        extra={"layoutCheckSeconds": layout_seconds, "compositionId": COMPOSITION_ID})
    logger.info("多日地图游记导出通过：%s，%d 帧（含音轨）", destination, frames)
    return destination


def _verify_audio_stream(video: Path) -> None:
    """交付音频必须是 AAC-LC、44.1 kHz、双声道。"""
    import subprocess
    from imageio_ffmpeg import get_ffmpeg_exe
    result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(video)],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace")
    line = next((item for item in result.stderr.splitlines()
                 if "Audio:" in item and "Stream #" in item), "")
    if not line or "aac" not in line.lower():
        raise M2VError("成片音频流不是 AAC")
    if "44100 Hz" not in line or "stereo" not in line:
        raise M2VError("成片音频必须是 44.1 kHz 双声道")


def _verify_audio(video: Path) -> None:
    _verify_audio_stream(video)
    stats = audio.loudness(video)
    try:
        integrated = float(stats["input_i"])
        peak = float(stats["input_tp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise M2VError("无法读取成片响度量测结果") from exc
    if abs(integrated + 14.0) > 1.0:
        raise M2VError(f"成片集成响度 {integrated:.1f} LUFS，超出 -14±1 LUFS")
    if peak > -1.0:
        raise M2VError(f"成片真峰值 {peak:.1f} dBTP，超过 -1 dBTP")


def render(root: Path, project: dict, *, preview: bool = False, limit_frames: int | None = None,
           start_seconds: float = 0, end_seconds: float | None = None) -> Path:
    prepared = current(root, project)
    fps = prepared["fps"]
    if preview:
        start, end = window(prepared["durationInFrames"], fps, start_seconds=start_seconds,
                            end_seconds=end_seconds, limit_frames=limit_frames)
        return _generate(root, project, preview=True, start_frame=start, end_frame=end)
    if limit_frames is not None or start_seconds or end_seconds is not None:
        raise M2VError("正式导出不能限制时间范围")

    def binding() -> dict:
        _, latest = load_project(root)
        return _binding(root, current(root, latest))

    def verify(video: Path) -> None:
        layout_check(root, current(root, project))
        output_validation.verify_output(video, prepared["durationInFrames"], prepared["width"],
                                        prepared["height"], fps, expect_audio=True)
        _verify_audio(video)

    return delivery.export_once(delivery.outputs(root) / "road-trip.mp4", binding(),
                                lambda target: _generate(root, project, output=target,
                                                         defer_validation=True),
                                verify, binding)
