"""无声类型的渲染管线：打包、逐帧渲染、媒体验收与交付的唯一实现。

金融无声导出在此统一执行 crf 与限帧校验、previews 守卫、临时目录、打包、
composition 元数据核对、渲染、媒体验收、输入摘要复核、交付、溯源与性能报告。

类型参数由 :class:`SilentRenderSpec` 声明，剩下的流程只有这一份。有音轨的通用类型
（`explainer_render`）也复用这里的元数据核对、溯源与报告写法，只是把音频 mux 与
字幕量测留在自己的编排里。
"""
from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from imageio_ffmpeg import get_ffmpeg_exe

from film_runtime.core import security
from film_runtime.core.errors import VideoError
from film_runtime.engine import output_validation, perf, remotion

logger = logging.getLogger(__name__)

#: 溯源旁车固定的写入版本。
PROVENANCE_VERSION = 1


def assert_no_audio(video: Path) -> None:
    """无声成片验收：确认文件里没有音频流，且这个判定本身可被验证。"""
    command = [get_ffmpeg_exe(), "-hide_banner", "-i", str(video), "-map", "0:a", "-f", "null", "-"]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if result.returncode == 0:
        raise VideoError("无声视频验收失败：成片包含音频流")
    if "matches no streams" not in result.stderr and "matches no streams" not in result.stdout:
        raise VideoError(f"无法验证成片音轨：{(result.stderr + result.stdout)[-1200:]}")


def metadata_confirm(
    expected: tuple[int, int, int, int],
    out: Path,
    *,
    crf: int,
    preset: str,
    frames: int,
    start_frame: int,
    label: str = "composition",
) -> Callable[[remotion.CompositionMetadata], dict]:
    """渲染前的元数据核对：画面声明的 fps/宽/高/帧数必须与材料一致。

    返回渲染脚本要求的确认载荷。金融、通用与 look-dev 入口过去各写
    一份同样的闭包，这里只留一份，措辞也统一为「期望 …，实际 …」。
    """

    def confirm(metadata: remotion.CompositionMetadata) -> dict:
        actual = (metadata.fps, metadata.width, metadata.height, metadata.duration_in_frames)
        if actual != expected:
            raise VideoError(f"{label} 元数据不匹配：期望 {expected}，实际 {actual}")
        return {"out": str(out), "crf": crf, "preset": preset,
                "frames": f"{start_frame}-{start_frame + frames - 1}", "scale": 1,
                "concurrency": 1, "progressTotal": frames}

    return confirm


def write_provenance(destination: Path, payload: dict) -> Path:
    """把溯源写到成片旁车 `<同名>.provenance.json`，返回旁车路径。"""
    target = destination.with_suffix(".provenance.json")
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def write_report(
    destination: Path,
    *,
    entry: str,
    storyboard: Path,
    frames: int,
    fps: int,
    width: int,
    height: int,
    timings: perf.StageTimings,
    total_seconds: float,
    outcome: remotion.BundleOutcome,
    extra: dict | None = None,
) -> dict:
    """写性能报告：缓存状态与 `extra` 由调用方给出，其余字段口径一致。"""
    report = perf.build_report(
        entry=entry, output=destination, storyboard=storyboard, frames=frames, fps=fps,
        width=width, height=height, concurrency=1, timings=timings, total_seconds=total_seconds,
        cache={"status": outcome.cache_status, "key": outcome.cache_key, "detail": outcome.cache_detail},
        extra=extra)
    perf.write_report(perf.report_path_for(destination), report)
    return report


@dataclass(frozen=True)
class SilentRenderSpec:
    """无声类型的渲染差异声明；流程本身由 :func:`generate` 与 :func:`render` 提供。"""

    composition_id: str
    fps: int
    width: int
    height: int
    #: 作品材料名（`animation-plan.json`），既用于打包也用于报告。
    material_file: str
    #: 正式成片与预演片段在作品 `outputs/` 下的文件名。
    destination_name: str
    preview_name: str
    #: 材料 → 全片帧数。
    total_frames: Callable[[dict], int]
    #: 作品目录 → 材料与资产摘要。
    inputs_digest: Callable[[Path], str]
    #: 材料 → composition props。
    build_props: Callable[[dict], dict]
    #: 溯源里的类型名与日志措辞。
    provenance_type: str
    log_message: str
    #: 渲染会话 → 性能报告的 `extra` 字段。
    report_extra: Callable[[dict], dict]


def _previews_dir(project_dir: Path) -> Path:
    return (project_dir / "outputs" / "previews").resolve()


def _destination(project_dir: Path, spec: SilentRenderSpec, *, output: Path | None, preview: bool) -> Path:
    if output is not None:
        destination = output
    elif preview:
        destination = project_dir / "outputs" / "previews" / spec.preview_name
    else:
        destination = project_dir / "outputs" / spec.destination_name
    previews = _previews_dir(project_dir)
    if preview and not destination.resolve().is_relative_to(previews):
        raise VideoError("预演只能写入作品 outputs/previews，不能覆盖正式成片")
    if not preview and destination.resolve().is_relative_to(previews):
        raise VideoError("正式成片不能写入 previews")
    return destination


def generate(
    project_dir: Path,
    material: dict,
    spec: SilentRenderSpec,
    *,
    output: Path | None = None,
    limit_frames: int | None = None,
    preview: bool = False,
    crf: int = 18,
    preset: str = "medium",
    start_frame: int = 0,
    defer_validation: bool = False,
) -> Path:
    """校验、渲染到临时文件，再原子发布成片。"""
    if crf < 0 or crf > 51:
        raise VideoError("CRF 必须处于 0 至 51")
    total_frames = spec.total_frames(material)
    if limit_frames is not None and limit_frames < 1:
        raise VideoError("--limit-frames 必须大于 0")
    frames = min(total_frames, limit_frames) if limit_frames is not None else total_frames
    if limit_frames is not None and not preview:
        raise VideoError("短预演须使用 preview 命令，正式导出不能限制帧数")
    destination = _destination(project_dir, spec, output=output, preview=preview)
    destination.parent.mkdir(parents=True, exist_ok=True)
    web = remotion.web_dir()
    started = time.monotonic()
    timings = perf.StageTimings()
    inputs_digest = spec.inputs_digest(project_dir)
    props = spec.build_props(material)
    material_path = project_dir / spec.material_file
    with tempfile.TemporaryDirectory(prefix="m2v-render-", dir=destination.parent) as temporary:
        temp = Path(temporary)
        props_path = temp / "props.json"
        props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        temp_video = temp / "video.mp4"
        outcome = remotion.bundle(web_dir=web, out_dir=temp / "bundle", storyboard_path=material_path,
                                  content_root=project_dir.parent, workspace_root=project_dir.parent, cache=True)
        timings.record("bundle", outcome.build_seconds)
        timings.record("cache", outcome.cache_seconds)
        confirm = metadata_confirm((spec.fps, spec.width, spec.height, total_frames), temp_video,
                                   crf=crf, preset=preset, frames=frames, start_frame=start_frame)
        render_started = time.monotonic()
        session = remotion.render_session(
            web_dir=web, bundle_dir=outcome.path, props=props_path, composition_id=spec.composition_id,
            on_metadata=confirm, timeout_s=3600,
            on_line=None)
        timings.record("metadata", float(session.get("readySeconds") or 0))
        timings.record("render", max(time.monotonic() - render_started - timings.as_dict()["metadata"], 0))
        with perf.measure(timings, "probe"):
            if not defer_validation:
                output_validation.verify_output(temp_video, frames, spec.width, spec.height, spec.fps)
                assert_no_audio(temp_video)
        if inputs_digest != spec.inputs_digest(project_dir):
            raise VideoError("渲染期间材料或资产变化；丢弃本次输出并重新预演")
        security.deliver(temp_video, destination)
    if not preview:
        write_provenance(destination, {
            "schemaVersion": PROVENANCE_VERSION, "type": spec.provenance_type, "frames": frames,
            "fps": spec.fps, "width": spec.width, "height": spec.height, "renderer": "remotion",
            "compositionId": spec.composition_id, "materialsAndAssetsSha256": inputs_digest,
            "bundleKey": outcome.cache_key})
    write_report(destination, entry="preview" if preview else "render", storyboard=material_path,
                 frames=frames, fps=spec.fps, width=spec.width, height=spec.height, timings=timings,
                 total_seconds=time.monotonic() - started, outcome=outcome,
                 extra=spec.report_extra(session))
    logger.info(spec.log_message, destination, frames, spec.fps)
    return destination


def render(
    project_dir: Path,
    material: dict,
    spec: SilentRenderSpec,
    *,
    output: Path | None = None,
    limit_frames: int | None = None,
    preview: bool = False,
    crf: int = 18,
    preset: str = "medium",
    start_seconds: float = 0,
    end_seconds: float | None = None,
) -> Path:
    """预演走片段窗口，正式导出走一次全片生成 + 验收 + 交付。"""
    from film_runtime.core import delivery
    from film_runtime.core.preview import window
    from film_runtime.core.project import load_current_prepared, load_project
    total = spec.total_frames(material)
    if preview:
        start, end = window(total, spec.fps, start_seconds=start_seconds,
                            end_seconds=end_seconds, limit_frames=limit_frames)
        return generate(project_dir, material, spec, output=output, preview=True, limit_frames=end - start,
                        start_frame=start, crf=crf, preset=preset)
    if limit_frames is not None or start_seconds or end_seconds is not None:
        raise VideoError("正式导出不能限制时间范围")
    if output is not None and output.resolve().is_relative_to(_previews_dir(project_dir)):
        raise VideoError("正式成片不能写入 previews")
    root, _project = load_project(project_dir)

    def current() -> dict:
        _, latest = load_project(root)
        prepared = load_current_prepared(root, latest)
        return delivery.binding(root, prepared, {"crf": crf, "preset": preset,
                                                 "inputs": spec.inputs_digest(root)})

    def verify(video: Path) -> None:
        output_validation.verify_output(video, total, spec.width, spec.height, spec.fps)
        assert_no_audio(video)

    destination = output or root / "outputs" / spec.destination_name
    return delivery.export_once(
        destination, current(),
        lambda target: generate(root, material, spec, output=target, crf=crf, preset=preset,
                                defer_validation=True),
        verify, current, directory=delivery.outputs(root))
