"""素材剪辑成片的渲染接线：本地媒体服务、Remotion 会话、音轨合成与验收。

画面里的视频素材不能像图片那样内嵌成 ``data:`` URL，也不能复制进共享前端工程
的 ``public/``（那会污染共享工程并让打包缓存键随作品变化）。因此这里在渲染期间
用既有的 :class:`LocalServer` 把**作品目录**暴露在回环地址上，并把地址注入 props；
服务器只绑 127.0.0.1，浏览器侧的离线守卫照旧放行本机地址，Range 支持由既有的
媒体处理器提供，渲染结束后服务器随进程销毁。
"""
from __future__ import annotations

import hashlib
import json
import logging
import tempfile
import time
from pathlib import Path

from m2v.core import security
from m2v.core.errors import M2VError
from m2v.engine import audio as audio_engine
from m2v.engine import output_validation, perf, remotion
from m2v.engine.http_server import LocalServer

logger = logging.getLogger(__name__)
COMPOSITION_ID = "StockMontage"


def _audio_segment(root: Path, prepared: dict) -> dict | None:
    segments = prepared.get("audio", {}).get("segments", [])
    if not segments:
        return None
    if len(segments) != 1:
        raise M2VError("素材剪辑成片只接受单条母版音轨；请重新 prepare")
    segment = segments[0]
    path = (root / segment["path"]).resolve()
    if not path.is_file():
        raise M2VError(f"准备音轨缺失：{segment['path']}；请重新 prepare")
    if hashlib.sha256(path.read_bytes()).hexdigest() != segment.get("sha256"):
        raise M2VError(f"准备音轨已变化：{segment['path']}；请重新 prepare")
    return segment


def render(root: Path, project: dict, prepared: dict, *, preview: bool,
           limit_frames: int | None = None) -> Path:
    if limit_frames is not None and limit_frames < 1:
        raise M2VError("limit_frames 必须为正整数")
    if not preview and limit_frames is not None:
        raise M2VError("正式导出不支持限帧渲染")
    entry = root / project["materials"]["brief"]
    current = remotion.build_input_fingerprint(
        storyboard_path=entry, content_root=root.parent, workspace_root=root.parent)["digest"]
    if prepared.get("inputs", {}).get("renderer") != current:
        raise M2VError("画面代码、字体或资源已变化；请重新 prepare 并生成完整预演")
    destination = root / ("outputs/previews/video.mp4" if preview else "outputs/video.mp4")
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected_frames = min(prepared["durationInFrames"], limit_frames or prepared["durationInFrames"])
    segment = _audio_segment(root, prepared)
    web = remotion.web_dir()
    started = time.monotonic()
    timings = perf.StageTimings()
    with tempfile.TemporaryDirectory(prefix="m2v-stock-", dir=destination.parent) as temporary:
        temp = Path(temporary)
        raw_video = temp / "video.mp4"
        # 媒体地址只在渲染前注入：准备记录里存的是作品内相对路径，因此准备指纹
        # 不随「这次渲染用了哪个端口」变化。
        with LocalServer(root, cors=True) as server:
            props = {**prepared["props"], "mediaBase": server.base_url + "/"}
            props_file = temp / "prepared-props.json"
            props_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
            outcome = remotion.bundle(web_dir=web, out_dir=temp / "bundle", storyboard_path=entry,
                                      content_root=root.parent, workspace_root=root.parent, cache=True,
                                      cache_identity=entry)
            timings.record("bundle", outcome.build_seconds)
            timings.record("cache", outcome.cache_seconds)

            def confirm(metadata: remotion.CompositionMetadata) -> dict:
                wanted = (prepared["fps"], prepared["width"], prepared["height"], prepared["durationInFrames"])
                actual = (metadata.fps, metadata.width, metadata.height, metadata.duration_in_frames)
                if actual != wanted:
                    raise M2VError(f"StockMontage 元数据与准备记录不匹配：期望 {wanted}，实际 {actual}；请重新 prepare")
                return {"out": str(raw_video), "crf": 18, "preset": "medium",
                        "frames": f"0-{expected_frames - 1}", "scale": 1, "concurrency": 1,
                        "progressTotal": expected_frames}

            render_started = time.monotonic()
            session = remotion.render_session(web_dir=web, bundle_dir=outcome.path, props=props_file,
                composition_id=COMPOSITION_ID, on_metadata=confirm, timeout_s=3600,
                on_line=lambda line: logger.info("%s", line) if "__M2V_PROGRESS__" in line else None)
            timings.record("metadata", float(session.get("readySeconds") or 0))
            timings.record("render", max(time.monotonic() - render_started - timings.as_dict()["metadata"], 0))
        final_video = raw_video
        if segment is not None:
            final_video = temp / "final.mp4"
            audio_engine.mux(raw_video, (root / segment["path"]).resolve(), final_video,
                             expected_frames / prepared["fps"])
            timings.record("mux", time.monotonic() - render_started - (timings.as_dict()["render"] or 0))
        else:
            timings.skip("mux")
        with perf.measure(timings, "probe"):
            output_validation.verify_output(final_video, expected_frames, prepared["width"],
                                            prepared["height"], prepared["fps"], expect_audio=segment is not None)
        staged = temp / destination.name
        try:
            staged.write_bytes(final_video.read_bytes())
            staged.replace(destination)
        except OSError:
            staged.unlink(missing_ok=True)
            raise
        security.grant_inherited_access(destination)
    if not preview:
        provenance = {"schemaVersion": 1, "type": "stock-montage", "projectId": project["id"],
                      "preparedFingerprint": prepared["preparedFingerprint"],
                      "inputs": prepared.get("inputs", {}), "durationInFrames": expected_frames,
                      "fps": prepared["fps"], "width": prepared["width"], "height": prepared["height"],
                      "renderer": "remotion", "compositionId": COMPOSITION_ID,
                      "bundleKey": outcome.cache_key}
        destination.with_suffix(".provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    perf.write_report(perf.report_path_for(destination), perf.build_report(
        entry="preview" if preview else "render", output=destination, storyboard=entry,
        frames=expected_frames, fps=prepared["fps"], width=prepared["width"], height=prepared["height"],
        concurrency=1, timings=timings, total_seconds=time.monotonic() - started,
        cache={"status": outcome.cache_status, "key": outcome.cache_key, "detail": outcome.cache_detail},
        extra={"compositionId": COMPOSITION_ID}))
    return destination
