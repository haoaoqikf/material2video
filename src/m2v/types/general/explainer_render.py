"""v8 的字幕量测与可靠 Remotion 导出。

画面由作品代码绘制并在准备阶段录成片段，合成层只回放片段与共享字幕。因此浏览器
量测能负责的只剩**字幕**：安全区矩形、换行范围与可见性。作品正文在栅格片段里，
系统不声称能自动识别其中的全部正文或主体遮挡——那部分由制作助手实际观看补足。
"""
from __future__ import annotations

from m2v.core.video_config import FPS

import json
import logging
import tempfile
import time
from pathlib import Path
from m2v.core.errors import M2VError
from m2v.core.project import _write_json, load_current_prepared
from m2v.core import security
from m2v.engine import audio, contract_page, frames, output_validation, perf, remotion
from m2v.engine.http_server import LocalServer
from .explainer_prepare import implementation_digest

logger = logging.getLogger(__name__)

# 字幕判据不写死在这里：安全区来自共享画幅配置，由 `measure_script` 注入为 `B`。
# 过去字幕盒写在设计令牌里、量测边界又各写一份常量，改一处不会让另一处报错，
# 只会静默漂移。
#
# 脚本体与外壳分开，是为了用 JSON 注入边界：脚本里全是 JS 的大括号，走 f-string
# 就得把每个 `{` 都写成 `{{`，改一次脚本就错一次。
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
        const top = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
        if (!top || !box.contains(top)) problems.push('字幕被遮挡：' + copy.textContent);
      }
    }
  }
  return problems;
}"""


def measure_script(repo_root: Path | None = None, size: tuple[int, int] | None = None) -> str:
    """把画幅配置里的字幕安全区注入量测脚本。"""
    width, height = size or frames.default(repo_root)
    safe = frames.spec(width, height, repo_root)["subtitle"]["safeArea"]
    return "() => {\n  const B = " + json.dumps(safe) + ";\n" + MEASURE_BODY


def _size(prepared: dict) -> tuple[int, int]:
    return prepared["width"], prepared["height"]


def current(root: Path, project: dict) -> dict:
    prepared = load_current_prepared(root, project)
    if (prepared.get("compositionId") != "ArticleExplainer" or prepared["props"].get("version") != 8
            or not 1 <= prepared["durationInFrames"] <= 600 * FPS):
        raise M2VError("旧文章准备记录不能用于 v8；请重新设计并 prepare")
    actual = remotion.build_input_fingerprint(workspace_root=root.parent)["digest"]
    if prepared["inputs"].get("renderer") != actual:
        raise M2VError("讲解渲染代码、字体或资源已变化；请重新 prepare 并评审")
    if prepared["inputs"].get("implementation") != implementation_digest():
        raise M2VError("讲解准备、混音或量测实现已变化；请重新 prepare 并评审")
    return prepared


def layout_check(root: Path, prepared: dict, *, snapshots: Path | None = None) -> dict:
    from playwright.sync_api import sync_playwright
    from m2v.core.fonts import audit_fonts
    from . import code_scenes
    # 字幕与分镜文字之外，作品源码里的字面量也要查：v8 的可见文字基本都在代码里，
    # 缺字会静默回退到系统字体，字宽字重全变却没有任何报错。
    missing = audit_fonts(contract_page.font_files(), prepared["props"], code_scenes.source_texts(root))
    if missing:
        raise M2VError(f"讲解字体缺字：{missing[:5]}")
    width, height = _size(prepared)
    outputs = root / "outputs"
    outputs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="layout-", dir=outputs) as temporary, LocalServer(root, cors=True) as server:
        material = Path(temporary) / "props.json"
        material.write_text(json.dumps({**prepared["props"], "mediaBase": server.base_url + "/"}, ensure_ascii=False), encoding="utf-8")
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
                script = measure_script(size=(width, height))
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
        raise M2VError(f"讲解字幕量测失败：{problems[:5]}；请调整字幕文本或画幅配置")
    return result


def render(root: Path, project: dict, *, preview=False, limit_frames=None) -> Path:
    prepared = current(root, project)
    if limit_frames is not None and (type(limit_frames) is not int or limit_frames < 1):
        raise M2VError("limit_frames 必须为正整数")
    if not preview and limit_frames is not None:
        raise M2VError("正式导出不能限帧")
    width, height = _size(prepared)
    # 预演和正式输出共用字幕量测；失败不能覆盖之前的有效成片。
    started = time.monotonic()
    layout_check(root, prepared)
    layout_seconds = time.monotonic() - started
    frames_to_render = min(prepared["durationInFrames"], limit_frames or prepared["durationInFrames"])
    # 固定示例的媒体仍归属 videos/examples，避免改变既有作品路径约定。
    output_root = root.parent.parent / "videos/examples" / root.name if root.parent.name == "examples" else root
    destination = output_root / ("outputs/previews/video.mp4" if preview else "outputs/video.mp4")
    destination.parent.mkdir(parents=True, exist_ok=True)
    entry = root / project["materials"]["storyboard"]
    timings = perf.StageTimings()
    with tempfile.TemporaryDirectory(prefix="m2v-explainer-", dir=destination.parent) as temporary, LocalServer(root, cors=True) as server:
        work = Path(temporary)
        props_file = work / "props.json"
        props_file.write_text(json.dumps({**prepared["props"], "mediaBase": server.base_url + "/"}, ensure_ascii=False), encoding="utf-8")
        outcome = remotion.bundle(web_dir=remotion.web_dir(), out_dir=work / "bundle", storyboard_path=entry,
            content_root=root.parent, workspace_root=root.parent, cache=True)
        timings.record("bundle", outcome.build_seconds)
        timings.record("cache", outcome.cache_seconds)
        silent = work / "silent.mp4"
        def confirm(metadata):
            expected = (FPS, width, height, prepared["durationInFrames"])
            actual = (metadata.fps, metadata.width, metadata.height, metadata.duration_in_frames)
            if expected != actual:
                raise M2VError(f"讲解 composition 元数据不匹配：{actual}，期望 {expected}")
            return {"out": str(silent), "crf": 18, "preset": "medium", "frames": f"0-{frames_to_render-1}",
                    "scale": 1, "concurrency": 1, "progressTotal": frames_to_render}
        render_start = time.monotonic()
        session = remotion.render_session(web_dir=remotion.web_dir(), bundle_dir=outcome.path, props=props_file,
            composition_id="ArticleExplainer", on_metadata=confirm, timeout_s=3600,
            on_line=remotion.progress_handler(frames_to_render))
        timings.record("metadata", float(session.get("readySeconds") or 0))
        timings.record("render", max(0, time.monotonic() - render_start - float(session.get("readySeconds") or 0)))
        master = root / prepared["audio"]["segments"][0]["path"]
        final = work / "final.mp4"
        with perf.measure(timings, "mux"):
            audio.mux(silent, master, final, frames_to_render / FPS)
        with perf.measure(timings, "probe"):
            output_validation.verify_output(final, frames_to_render, width, height, FPS, expect_audio=True)
        if current(root, project)["preparedFingerprint"] != prepared["preparedFingerprint"]:
            raise M2VError("渲染期间材料或准备记录变化；丢弃本次输出")
        provenance = {"schemaVersion": 1, "type": "general", "projectId": project["id"],
            "preparedFingerprint": prepared["preparedFingerprint"], "compositionId": "ArticleExplainer",
            "productionProfile": prepared["props"].get("productionProfile", "standard"),
            "productionProfileSource": prepared["props"].get("productionProfileSource", "default"),
            "inputs": prepared["inputs"], "durationInFrames": frames_to_render, "fps": FPS, "width": width, "height": height}
        if not preview:
            _write_json(work / "final.provenance.json", provenance)
        # 临时目录带收紧 ACL，交付必须走 security.deliver：搬运与权限修复不可分开。
        security.deliver(final, destination)
        if not preview:
            security.deliver(work / "final.provenance.json", destination.with_suffix(".provenance.json"))
    perf.write_report(perf.report_path_for(destination), perf.build_report(entry="preview" if preview else "render",
        output=destination, storyboard=entry, frames=frames_to_render, fps=FPS, width=width, height=height, concurrency=1,
        timings=timings, total_seconds=time.monotonic()-started,
        cache={"status": outcome.cache_status, "key": outcome.cache_key, "detail": outcome.cache_detail},
        extra={"layoutCheckSeconds": layout_seconds, "compositionId": "ArticleExplainer"}))
    logger.info("讲解视频导出通过：%s，%d 帧", destination, frames_to_render)
    return destination
