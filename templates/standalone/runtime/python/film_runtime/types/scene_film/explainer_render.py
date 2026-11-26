"""v9 的字幕量测与可靠 Remotion 导出。

画面由作品代码绘制并在检查或正式生成时按需录成片段，合成层只回放片段与共享字幕。因此浏览器
量测能负责的只剩**字幕**：安全区矩形、换行范围与可见性。作品正文在栅格片段里，
系统不声称能自动识别其中的全部正文或主体遮挡——那部分由制作助手核查关键帧或代表性抽帧补足。
"""
from __future__ import annotations


import hashlib
import json
import logging
import tempfile
import time
import wave
from pathlib import Path
from film_runtime.core.audio_policy import declared_audio
from film_runtime.core.errors import VideoError
from film_runtime.core.project import _write_json, load_current_prepared
from film_runtime.core import security
from film_runtime.core import frames
from film_runtime.engine import audio, contract_page, output_validation, perf, remotion, render_pipeline
from film_runtime.engine.http_server import LocalServer
from .explainer_prepare import implementation_digest
from .code_scenes.cache import using_scene_cache

logger = logging.getLogger(__name__)


def _has_audio(prepared: dict) -> bool:
    """按声音声明判定交付轨道；内部静音母版不代表作品需要音轨。"""
    return declared_audio(prepared)


def _master_audio_metadata(path: Path) -> dict:
    """记录实际母版头信息；音床混音可为双声道，不能沿用旁白的单声道常量。"""
    with wave.open(str(path), "rb") as stream:
        return {"masterSampleRate": stream.getframerate(), "masterChannels": stream.getnchannels()}

# 字幕判据不写死在这里：完整样式来自准备记录，由 `measure_script` 注入。
# 过去字幕盒写在设计令牌里、量测边界又各写一份常量，改一处不会让另一处报错，
# 只会静默漂移。
#
# 脚本体与外壳分开，是为了用 JSON 注入边界：脚本里全是 JS 的大括号，走 f-string
# 就得把每个 `{` 都写成 `{{`，改一次脚本就错一次。
MEASURE_BODY = r"""  const problems = [];
  const box = document.querySelector('[data-m2v-subtitle]');
  if (!box) problems.push('画面缺少共享字幕层');
  else {
    const actualFontSize = Number.parseFloat(getComputedStyle(box).fontSize);
    if (actualFontSize !== S.fontSize)
      problems.push('字幕字号不符：' + actualFontSize + '，准备字号：' + S.fontSize);
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
        const top = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
        if (!top || !box.contains(top)) problems.push('字幕被遮挡：' + copy.textContent);
      }
    }
  }
  return problems;
}"""


def measure_script(repo_root: Path | None = None, size: tuple[int, int] | None = None, *,
                   subtitle: dict | None = None) -> str:
    """注入准备样式；未传入时供直接调用者量测画幅默认样式。"""
    if subtitle is None:
        width, height = size or frames.default(repo_root)
        subtitle = frames.spec(width, height, repo_root)["subtitle"]
    return ("() => {\n  const S = " + json.dumps(subtitle)
            + ";\n  const B = S.safeArea;\n" + MEASURE_BODY)


def _size(prepared: dict) -> tuple[int, int]:
    return prepared["width"], prepared["height"]


def current(root: Path, project: dict) -> dict:
    prepared = load_current_prepared(root, project)
    if (prepared.get("compositionId") != "SceneFilm" or prepared["props"].get("version") != 9
            or not 1 <= prepared["durationInFrames"] <= 600 * prepared["fps"]):
        raise VideoError("旧准备记录不能用于 v9 五类视频；请重新设计并 prepare")
    if prepared["inputs"].get("productionContract") != "standalone-v3":
        raise VideoError("旧制作契约准备记录已失效；请重新 prepare")
    actual = remotion.build_input_fingerprint(workspace_root=root.parent)["digest"]
    if prepared["inputs"].get("renderer") != actual:
        raise VideoError("讲解渲染代码、字体或资源已变化；请重新 prepare 并评审")
    if prepared["inputs"].get("implementation") != implementation_digest():
        raise VideoError("讲解准备、混音或量测实现已变化；请重新 prepare 并评审")
    return prepared


def layout_check(root: Path, prepared: dict, *, snapshots: Path | None = None) -> dict:
    from playwright.sync_api import sync_playwright
    from film_runtime.core.fonts import audit_fonts
    from . import code_scenes
    # 字幕与分镜文字之外，作品源码里的字面量也要查：v9 的可见文字基本都在代码里，
    # 缺字会静默回退到系统字体，字宽字重全变却没有任何报错。
    missing = audit_fonts(contract_page.font_files(), prepared["props"], code_scenes.source_texts(root))
    if missing:
        raise VideoError(f"讲解字体缺字：{missing[:5]}")
    width, height = _size(prepared)
    outputs = root / "outputs"
    outputs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="layout-", dir=outputs) as temporary, LocalServer(root, cors=True) as server:
        material = Path(temporary) / "props.json"
        material.write_text(json.dumps({**prepared["props"], "compiledScenes": [], "mediaBase": server.base_url + "/"}, ensure_ascii=False), encoding="utf-8")
        frames_to_check = {0, prepared["durationInFrames"] - 1}
        for cue in prepared["props"]["subtitleCues"]:
            frames_to_check.update({cue["startFrame"], cue["endFrame"] - 1})
        problems = []
        with contract_page.serve_contract_page(material, root) as url, sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
                page.goto(url + "&m2v-explainer=1")
                page.wait_for_function("window.__M2V__?.version === 6", timeout=30000)
                page.evaluate("async () => await window.__M2V__.ready()")
                script = measure_script(subtitle=prepared["props"]["subtitle"])
                for frame_number in sorted(frames_to_check):
                    page.evaluate("async f => await window.__M2V__.seekToFrame(f)", frame_number)
                    errors = page.evaluate(script)
                    problems.extend({"frame": frame_number, "message": error} for error in errors)
                    if snapshots and frame_number in frames_to_check:
                        snapshots.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(snapshots / f"frame-{frame_number}.png"))
            finally:
                browser.close()
    result = {"schemaVersion": 6, "preparedFingerprint": prepared["preparedFingerprint"],
              "checkedFrames": len(frames_to_check), "problems": problems, "status": "fail" if problems else "pass"}
    _write_json(outputs / "layout-check.json", result)
    if problems:
        raise VideoError(f"讲解字幕量测失败：{problems[:5]}；请调整字幕文本或画幅配置")
    return result


def visual_provenance(prepared: dict) -> dict:
    """逐幕汇总视觉溯源；镜头帧号换算成全片帧号，避免只记录第一幕。

    单幕作品保留原来的 `look` 对象形状；多幕作品给出 `幕ID → look` 映射，因为各幕
    可以使用不同的 look 与后期参数。
    """
    scenes = prepared["props"].get("compiledScenes") or []
    looks = {(scene.get("id") or f"scene-{index}"):
             ((scene.get("content", {}).get("props") or {}).get("look"))
             for index, scene in enumerate(scenes)}
    shots = []
    for scene in scenes:
        scene_props = scene.get("content", {}).get("props") or {}
        for shot in scene_props.get("shots") or []:
            shots.append({
                **{name: shot.get(name) for name in
                   ("id", "tier", "target", "startFrame", "endFrame", "post")},
                "sceneId": scene.get("id"),
                "startFrame": scene.get("startFrame", 0) + shot["startFrame"],
                "endFrame": scene.get("startFrame", 0) + shot["endFrame"],
            })
    look = looks.get(scenes[0].get("id")) if len(scenes) == 1 else looks
    return {"look": look, "shots": shots,
            "postFx": {"look": look,
                       "shots": {shot["id"]: shot.get("post") for shot in shots}}}


@using_scene_cache
def _generate(root: Path, project: dict, *, preview=False, start_frame=0, end_frame=None, output=None,
              defer_validation=False, jobs: int = 1) -> Path:
    prepared = current(root, project)
    fps = prepared["fps"]
    width, height = _size(prepared)
    # 预演和正式输出共用字幕量测；失败不能覆盖之前的有效成片。
    started = time.monotonic()
    layout_check(root, prepared)
    layout_seconds = time.monotonic() - started
    end_frame = end_frame or prepared["durationInFrames"]
    frames_to_render = end_frame - start_frame
    from . import code_scenes
    prepared = code_scenes.materialize(root, prepared, start_frame, end_frame, jobs=jobs)
    # 示例与正式作品的预演、成片都落在作品目录下的 outputs/。
    destination = output or root / ("outputs/previews/video.mp4" if preview else "outputs/video.mp4")
    destination.parent.mkdir(parents=True, exist_ok=True)
    entry = root / project["materials"]["storyboard"]
    timings = perf.StageTimings()
    with tempfile.TemporaryDirectory(prefix="m2v-explainer-", dir=destination.parent) as temporary, LocalServer(root, cors=True) as server:
        work = Path(temporary)
        props_file = work / "props.json"
        props_file.write_text(json.dumps({**prepared["props"], "mediaBase": server.base_url + "/"}, ensure_ascii=False), encoding="utf-8")
        with remotion.bundle(
            web_dir=remotion.web_dir(), out_dir=work / "bundle", storyboard_path=entry,
            content_root=root.parent, workspace_root=root.parent, cache=True,
        ) as outcome:
            timings.record("bundle", outcome.build_seconds)
            timings.record("cache", outcome.cache_seconds)
            silent = work / "silent.mp4"
            if jobs < 1:
                raise VideoError("--jobs 必须为正整数")
            render_start = time.monotonic()
            if jobs > 1 and not preview:
                remotion.render_parallel(
                    web_dir=remotion.web_dir(), bundle_dir=outcome.path, props=props_file,
                    composition_id="SceneFilm", out=silent,
                    total_frames=prepared["durationInFrames"], fps=fps, width=width, height=height,
                    crf=18, preset="medium", jobs=jobs)
                timings.skip("metadata")
                session = {"renderJobs": jobs, "readySeconds": 0}
            else:
                confirm = render_pipeline.metadata_confirm(
                    (fps, width, height, prepared["durationInFrames"]), silent, crf=18, preset="medium",
                    frames=frames_to_render, start_frame=start_frame, label="讲解 composition")
                session = remotion.render_session(web_dir=remotion.web_dir(), bundle_dir=outcome.path, props=props_file,
                    composition_id="SceneFilm", on_metadata=confirm, timeout_s=3600,
                    on_line=remotion.progress_handler(frames_to_render))
                timings.record("metadata", float(session.get("readySeconds") or 0))
        timings.record("render", max(0, time.monotonic() - render_start - float(session.get("readySeconds") or 0)))
        has_audio = _has_audio(prepared)
        final = work / "final.mp4" if has_audio else silent
        if has_audio:
            master = root / prepared["audio"]["segments"][0]["path"]
            with perf.measure(timings, "mux"):
                audio.mux(silent, master, final, frames_to_render / fps, start=start_frame / fps)
        else:
            timings.record("mux", 0)
            logger.info("作品无声音声明，直接交付无音轨候选")
        with perf.measure(timings, "probe"):
            if not defer_validation:
                output_validation.verify_output(final, frames_to_render, width, height, fps, expect_audio=has_audio)
        if current(root, project)["preparedFingerprint"] != prepared["preparedFingerprint"]:
            raise VideoError("渲染期间材料或准备记录变化；丢弃本次输出")
        provenance = {"schemaVersion": 1, "type": project["type"], "projectId": project["id"],
            "preparedFingerprint": prepared["preparedFingerprint"], "compositionId": "SceneFilm",
            "inputs": prepared["inputs"], "startFrame": start_frame,
            "durationInFrames": frames_to_render, "fps": fps, "width": width, "height": height}
        provenance.update(visual_provenance(prepared))
        provenance.update({
            "audio": {"master": prepared["audio"]["segments"][0]["path"],
                      "masterSha256": prepared["audio"]["segments"][0].get("sha256"),
                      "masterCodec": "pcm_s16le", **_master_audio_metadata(master),
                      "delivery": {"codec": "aac", "sampleRate": 44100, "channels": 2,
                                   "bitrate": "128k"}} if has_audio else {"mode": "none"},
            "delivery": {"sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
                         "codec": "h264", "pixelFormat": "yuv420p(tv, bt709)",
                         "frames": frames_to_render, "fps": fps, "width": width, "height": height},
        })
        _write_json(work / "final.provenance.json", provenance)
        # 临时目录带收紧 ACL，交付必须走 security.deliver：搬运与权限修复不可分开。
        security.deliver(final, destination)
        security.deliver(work / "final.provenance.json", destination.with_suffix(".provenance.json"))
    render_pipeline.write_report(destination, entry="preview" if preview else "render", storyboard=entry,
        frames=frames_to_render, fps=fps, width=width, height=height, timings=timings,
        total_seconds=time.monotonic()-started, outcome=outcome,
        extra={"layoutCheckSeconds": layout_seconds, "compositionId": "SceneFilm",
               "renderJobs": jobs})
    logger.info("讲解视频导出通过：%s，%d 帧", destination, frames_to_render)
    return destination


def render(root: Path, project: dict, *, preview=False, limit_frames=None,
           start_seconds=0, end_seconds=None, jobs: int = 1) -> Path:
    from film_runtime.core import delivery
    from film_runtime.core.preview import window
    from film_runtime.core.project import load_project
    prepared = current(root, project)
    fps = prepared["fps"]
    if preview:
        start, end = window(prepared["durationInFrames"], fps, start_seconds=start_seconds,
                            end_seconds=end_seconds, limit_frames=limit_frames)
        return _generate(root, project, preview=True, start_frame=start, end_frame=end, jobs=jobs)
    if limit_frames is not None or start_seconds or end_seconds is not None:
        raise VideoError("正式导出不能限制时间范围")
    def binding():
        _, latest = load_project(root)
        return delivery.binding(root, current(root, latest), {"crf": 18, "preset": "medium"})
    def verify(video):
        layout_check(root, current(root, project))
        output_validation.verify_output(video, prepared["durationInFrames"], prepared["width"],
                                        prepared["height"], fps, expect_audio=_has_audio(prepared))
    def generate(target):
        return _generate(root, project, output=target, defer_validation=True, jobs=jobs)
    return delivery.export_once(delivery.outputs(root) / "video.mp4", binding(),
        generate, verify, binding)
