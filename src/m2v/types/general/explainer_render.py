"""v7 的浏览器布局验收及可靠 Remotion 导出。"""
from __future__ import annotations

import json
import logging
import tempfile
import time
from pathlib import Path
from m2v.core.errors import M2VError
from m2v.core.project import _write_json, load_current_prepared
from m2v.core import security
from m2v.engine import audio, contract_page, output_validation, perf, remotion
from m2v.engine.http_server import LocalServer
from .explainer_prepare import implementation_digest

logger = logging.getLogger(__name__)

# 按真实浏览器字体与文本包围盒验收；不可用字符数估算代替布局检查。
MEASURE = r"""() => {
  const problems = [];
  const visible = el => {
    for (let p = el; p; p = p.parentElement) if (Number(getComputedStyle(p).opacity) < .01) return false;
    return true;
  };
  for (const el of document.querySelectorAll('[data-m2v-copy]')) {
    if (!visible(el)) continue;
    const range = document.createRange(); range.selectNodeContents(el);
    const r = range.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const subtitle = el.closest('[data-m2v-subtitle]');
    if (subtitle) {
      for (const rect of range.getClientRects()) {
        if (!rect.width || !rect.height) continue;
        const top = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
        if (!top || !subtitle.contains(top)) problems.push('字幕被遮挡：' + el.textContent);
      }
    }
    const box = (subtitle || el.closest('[data-m2v-box]'))?.getBoundingClientRect();
    if (r.left < 106 || r.right > 974 || r.top < 158 || r.bottom > (subtitle ? 1782 : 1502))
      problems.push('画布分区溢出：' + el.textContent);
    if (box && (r.left < box.left-2 || r.right > box.right+2 || r.top < box.top-2 || r.bottom > box.bottom+2))
      problems.push('文字超出容器：' + el.textContent);
  }
  for (const el of document.querySelectorAll('[data-m2v-content]')) {
    if (!visible(el)) continue;
    for (const box of el.querySelectorAll('[data-m2v-box]')) {
      if (visible(box) && box.getBoundingClientRect().bottom > 1502) problems.push('内容侵入字幕区');
    }
  }
  return problems;
}"""


def current(root: Path, project: dict) -> dict:
    prepared = load_current_prepared(root, project)
    if "codeAssets" in prepared["inputs"]:
        from .code_scenes import asset_inputs
        from m2v.core.fingerprints import fingerprint
        if prepared["inputs"]["codeAssets"] != fingerprint(asset_inputs(root)):
            raise M2VError("代码场景资源集合已变化；请重新 prepare 并完整预演")
    if (prepared.get("compositionId") != "ArticleExplainer" or prepared["props"].get("version") != 7
            or not 1 <= prepared["durationInFrames"] <= 18000):
        raise M2VError("旧文章准备记录不能用于 v7；请重新编排并 prepare")
    actual = remotion.build_input_fingerprint(workspace_root=root.parent)["digest"]
    if prepared["inputs"].get("renderer") != actual:
        raise M2VError("讲解渲染代码、字体或资源已变化；请重新 prepare 并评审")
    if prepared["inputs"].get("implementation") != implementation_digest():
        raise M2VError("讲解准备、混音或量测实现已变化；请重新 prepare 并评审")
    return prepared


def layout_check(root: Path, prepared: dict, *, snapshots: Path | None = None) -> dict:
    from playwright.sync_api import sync_playwright
    from m2v.core.fonts import audit_fonts
    missing = audit_fonts(contract_page.font_files(), prepared["props"])
    if missing:
        raise M2VError(f"讲解字体缺字：{missing[:5]}")
    outputs = root / "outputs"
    outputs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="layout-", dir=outputs) as temporary, LocalServer(root, cors=True) as server:
        material = Path(temporary) / "props.json"
        material.write_text(json.dumps({**prepared["props"], "mediaBase": server.base_url + "/"}, ensure_ascii=False), encoding="utf-8")
        frames = {0, prepared["durationInFrames"] - 1}
        for scene in prepared["props"]["compiledScenes"]:
            frames.update({scene["startFrame"], scene["endFrame"] - 1})
            for window in scene["segmentWindows"].values():
                frames.update({window["startFrame"], min(window["startFrame"] + 8, scene["endFrame"] - 1), window["endFrame"] - 1})
                frames.update(range(window["startFrame"], min(window["startFrame"] + 9, scene["endFrame"])))
        for cue in prepared["props"]["subtitleCues"]:
            frames.update({cue["startFrame"], cue["endFrame"] - 1})
        problems = []
        with contract_page.serve_contract_page(material, root) as url, sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
                page.goto(url + "&m2v-explainer=1")
                page.wait_for_function("window.__M2V__?.version === 6", timeout=30000)
                page.evaluate("async () => await window.__M2V__.ready()")
                for frame in sorted(frames):
                    page.evaluate("async f => await window.__M2V__.seekToFrame(f)", frame)
                    errors = page.evaluate(MEASURE)
                    problems.extend({"frame": frame, "message": error} for error in errors)
                    if snapshots and any(frame == scene["endFrame"] - 1 for scene in prepared["props"]["compiledScenes"]):
                        snapshots.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(snapshots / f"frame-{frame}.png"))
            finally:
                browser.close()
    result = {"schemaVersion": 6, "preparedFingerprint": prepared["preparedFingerprint"],
              "checkedFrames": len(frames), "problems": problems, "status": "fail" if problems else "pass"}
    _write_json(outputs / "layout-check.json", result)
    if problems:
        raise M2VError(f"讲解排版量测失败：{problems[:5]}；请减少文字或调整分幕")
    return result


def render(root: Path, project: dict, *, preview=False, limit_frames=None) -> Path:
    prepared = current(root, project)
    if limit_frames is not None and (type(limit_frames) is not int or limit_frames < 1):
        raise M2VError("limit_frames 必须为正整数")
    if not preview and limit_frames is not None:
        raise M2VError("正式导出不能限帧")
    # 预演和正式输出共用量测；失败不能覆盖之前的有效成片。
    started = time.monotonic()
    layout_check(root, prepared)
    layout_seconds = time.monotonic() - started
    frames = min(prepared["durationInFrames"], limit_frames or prepared["durationInFrames"])
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
            expected = (30, 1080, 1920, prepared["durationInFrames"])
            actual = (metadata.fps, metadata.width, metadata.height, metadata.duration_in_frames)
            if expected != actual:
                raise M2VError(f"讲解 composition 元数据不匹配：{actual}，期望 {expected}")
            return {"out": str(silent), "crf": 18, "preset": "medium", "frames": f"0-{frames-1}",
                    "scale": 1, "concurrency": 1, "progressTotal": frames}
        render_start = time.monotonic()
        session = remotion.render_session(web_dir=remotion.web_dir(), bundle_dir=outcome.path, props=props_file,
            composition_id="ArticleExplainer", on_metadata=confirm, timeout_s=3600,
            on_line=remotion.progress_handler(frames))
        timings.record("metadata", float(session.get("readySeconds") or 0))
        timings.record("render", max(0, time.monotonic() - render_start - float(session.get("readySeconds") or 0)))
        master = root / prepared["audio"]["segments"][0]["path"]
        final = work / "final.mp4"
        with perf.measure(timings, "mux"):
            audio.mux(silent, master, final, frames / 30)
        with perf.measure(timings, "probe"):
            output_validation.verify_output(final, frames, 1080, 1920, 30, expect_audio=True)
        if current(root, project)["preparedFingerprint"] != prepared["preparedFingerprint"]:
            raise M2VError("渲染期间材料或准备记录变化；丢弃本次输出")
        provenance = {"schemaVersion": 1, "type": "general", "projectId": project["id"],
            "preparedFingerprint": prepared["preparedFingerprint"], "compositionId": "ArticleExplainer",
            "inputs": prepared["inputs"], "durationInFrames": frames, "fps": 30, "width": 1080, "height": 1920}
        if not preview:
            _write_json(work / "final.provenance.json", provenance)
        # 临时目录带收紧 ACL，交付必须走 security.deliver：搬运与权限修复不可分开。
        security.deliver(final, destination)
        if not preview:
            security.deliver(work / "final.provenance.json", destination.with_suffix(".provenance.json"))
    perf.write_report(perf.report_path_for(destination), perf.build_report(entry="preview" if preview else "render",
        output=destination, storyboard=entry, frames=frames, fps=30, width=1080, height=1920, concurrency=1,
        timings=timings, total_seconds=time.monotonic()-started,
        cache={"status": outcome.cache_status, "key": outcome.cache_key, "detail": outcome.cache_detail},
        extra={"layoutCheckSeconds": layout_seconds, "compositionId": "ArticleExplainer"}))
    logger.info("讲解视频导出通过：%s，%d 帧", destination, frames)
    return destination
