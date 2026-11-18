"""正式合成取证、短片分界与完整候选复核。"""
import copy
import json

import pytest
from PIL import Image

from m2v.core.delivery import binding, digest, outputs
from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from m2v.production import film_review, issues, ledger, reuse, reviews
from m2v.production.model import ffmpeg
from m2v.production.storage import read, receipt, write
from common.test_media_reviews import report, request, work  # noqa: F401


def _preview(root, project, prepared, path, start, frames):
    write(path.with_suffix(".provenance.json"), {
        "schemaVersion": 1, "projectId": project["id"], "type": project["type"],
        "compositionId": "SceneFilm", "preparedFingerprint": prepared["preparedFingerprint"],
        "startFrame": start, "durationInFrames": frames,
        **{key: prepared[key] for key in ("width", "height", "fps")},
        "delivery": {"sha256": digest(path)},
    })


def _candidate(root, prepared, label):
    base = outputs(root)
    path = base / "candidates" / f"{label}.mp4"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(label.encode())
    record = binding(root, prepared, {"crf": 18})
    write(base / "delivery.json", {
        **record, "key": fingerprint(record), "status": "ready",
        "path": path.relative_to(root).as_posix(), "sha256": digest(path),
    })
    write(base / "qa.json", {
        "status": "pass", "scope": "technical-only", "videoSha256": digest(path),
        "preparedFingerprint": prepared["preparedFingerprint"],
        "fps": prepared["fps"], "durationInFrames": prepared["durationInFrames"],
    })
    return path


def _evidence_request(candidate, start, end, observations):
    return {"candidateSha256": digest(candidate), "observations": "核对各场代表帧与准备时间轴",
            "windows": [{"window": [start, end], "observations": observations}]}


@pytest.fixture
def film(work, monkeypatch):
    root, project = work
    scene = {"id": "core", "startFrame": 0, "endFrame": 470, "content": {"entry": "core.tsx"}}
    other = {"id": "end", "startFrame": 470, "endFrame": 901, "content": {"entry": "unrelated.tsx"}}
    prepared = {
        "preparedFingerprint": "source-v1", "durationInFrames": 901,
        "width": 640, "height": 360, "fps": 30, "type": project["type"],
        "inputs": {"implementation": "runtime-a", "renderer": "render-a"},
        "props": {"compiledScenes": [scene, other], "subtitleCues": [], "subtitle": {}},
    }
    monkeypatch.setattr("m2v.commands._prepared", lambda *_: copy.deepcopy(prepared))
    return root, project, prepared


def _formal_still(work, video, frame, *, name="window-1"):
    root, project = work
    req = request()
    req.update(film=True, sources=[], references=["trial.png"], conditions=["整体形象"],
               items=[{"id": name, "path": video.relative_to(outputs(root)).as_posix(),
                       "window": [frame, frame + 1], "dynamic": False}])
    blind = reviews.import_report(root, project, report(work, reviews.package(root, project, req)))
    assert ledger.status(root, project)["keyframes"]["status"] == "missing"
    contrast = reviews.compare(root, project, blind["id"])
    reviews.import_report(root, project, report(work, contrast))
    return contrast


def test_boundary_and_binding_to_actual_candidate(work, film):
    from m2v.cli import main

    root, project, prepared = film
    prepared["durationInFrames"] = 900
    source = outputs(root) / "preview.mp4"
    source.write_bytes((outputs(root) / "trial.png").read_bytes())
    _preview(root, project, prepared, source, 0, 20)
    contrast = _formal_still(work, source, 8)
    questions = (contrast / "questions.md").read_text(encoding="utf-8")
    assert "世界级成片完成度" in questions and "足以指导后续制作" not in questions
    assert "试制对照逐项" not in questions
    assert "试制通过须在实际观看条件下" not in questions
    assert "小屏减弱的非必要抽象细节" in questions
    assert "以各尺寸的完整画面作证" in questions
    assert "可直接观察的复查问题" in questions
    candidate = _candidate(root, prepared, "first")
    before = ledger.status(root, project)
    assert before["keySamples"]["status"] == "exempt"
    assert before["technicalQA"]["status"] == "pass"
    assert not before["complete"]
    binding = film_review.qa_binding(root, project)
    ledger.append(root, project, "playback-confirmed", data={**binding, "observations": "历史复核"})
    assert ledger.status(root, project)["wholeFilmReview"]["status"] == "missing"
    ledger.append(root, project, "film-evidence-confirmed", data={**binding, "observations": "缺少帧窗"})
    assert ledger.status(root, project)["wholeFilmReview"]["status"] == "invalid"
    request = _evidence_request(candidate, 898, 900, "末两帧的结论读数一致")
    with pytest.raises(M2VError, match="摘要"):
        film_review.confirm_evidence(root, project, {**request, "candidateSha256": "wrong"})
    with pytest.raises(M2VError, match="已核查帧窗"):
        film_review.confirm_evidence(root, project, {**request, "windows": []})
    with pytest.raises(M2VError, match="超出当前候选"):
        film_review.confirm_evidence(root, project, _evidence_request(candidate, 899, 901, "越界"))
    assert not ledger.status(root, project)["complete"]
    confirmation = outputs(root) / "review-input.json"
    write(confirmation, request)
    assert main(["review", "confirm-evidence", "--project", str(root), "--file", str(confirmation)]) == 0
    confirmed = ledger.status(root, project)
    assert confirmed["complete"] and confirmed["wholeFilmReview"]["windows"] == request["windows"]

    _candidate(root, prepared, "revised")
    changed = ledger.status(root, project)
    assert changed["wholeFilmReview"]["status"] == "stale" and not changed["complete"]
    assert changed["keyframes"]["status"] == "pass"
    prepared.update(durationInFrames=901, preparedFingerprint="source-v2")
    assert ledger.status(root, project)["keySamples"]["status"] == "required"


def test_pin_delivery_after_qa_without_ignoring_timeline_change(film):
    root, project, prepared = film
    candidate = _candidate(root, prepared, "first")
    _preview(root, project, prepared, candidate, 0, prepared["durationInFrames"])
    delivery = outputs(root) / "video.mp4"
    delivery.write_bytes(candidate.read_bytes())
    sidecar = delivery.with_suffix(".provenance.json")
    value = read(candidate.with_suffix(".provenance.json"))
    value["qa"] = {"status": "pass", "report": "outputs/qa.json"}
    write(sidecar, value)
    req = {"items": [{"path": "video.mp4", "window": [10, 11]}]}

    pinned = film_review.pin_sources(root, project, req)
    assert pinned["items"][0]["path"] == candidate.relative_to(outputs(root)).as_posix()

    write(sidecar, {**value, "startFrame": 1})
    with pytest.raises(M2VError, match="时间映射不一致"):
        film_review.pin_sources(root, project, req)


@pytest.mark.media
def test_long_film_checks_each_composed_window_and_keeps_unaffected_evidence(work, film, monkeypatch):
    root, project, prepared = film
    prepared["props"]["subtitleCues"] = [{"startFrame": 101, "endFrame": 105, "text": "第一句", "secondary": "Opening"}]
    req = request()
    req.update(film=True, purpose="process", reviewType="process", sources=[], references=["trial.png"])
    source = outputs(root) / "previews" / "video.mp4"
    source.parent.mkdir()
    monkeypatch.setattr(reviews, "ffmpeg", ffmpeg)
    ffmpeg(["-f", "lavfi", "-i", "color=s=640x360:r=30:c=white:d=0.5",
            "-frames:v", "15", str(source)])
    _preview(root, project, prepared, source, 100, 15)
    contrast = _formal_still(work, source, 2)
    frame = read(contrast / "manifest.json")["items"][0]
    assert frame["filmWindow"] == [102, 103] and frame["path"].endswith(".png")
    windows = [{"id": "start", "window": [100, 108], "goal": "换句与揭示配合"},
               {"id": "end", "window": [700, 708], "goal": "结尾完整停留"}]
    film_review.register_windows(root, project, {"windows": windows})
    candidate = _candidate(root, prepared, "long-film")
    film_review.confirm_evidence(root, project, _evidence_request(candidate, 700, 708, "末镜读数连续"))

    def approve(index):
        item = windows[index]
        req.update(conditions=[item["goal"]], items=[
            {"id": item["id"], "path": "previews/video.mp4", "window": [0, 8], "dynamic": True}])
        pack = reviews.package(root, project, req)
        return reviews.import_report(root, project, report(work, pack))

    opening = approve(0)
    state = ledger.status(root, project)
    assert [item["status"] for item in state["keySamples"]["windows"]] == ["pass", "missing"] and not state["complete"]
    # 预演固定名称第二次使用。第一版被封存，不随局部预演覆盖。
    _preview(root, project, prepared, source, 700, 15)
    _, _, private, _ = reuse.evidence(root, project, opening["id"])
    first = private["request"]["items"][0]
    req.update(conditions=[item["goal"] for item in windows], items=[
        first, {"id": "end", "path": "previews/video.mp4", "window": [0, 8], "dynamic": True}])
    pack = reviews.package(root, project, req)
    reviews.import_report(root, project, report(work, pack))
    assert ledger.status(root, project)["complete"]

    section_report = report(work, pack)
    value = read(section_report)
    value.update(verdict="fail", adoption="reject")
    failed = value["coverage"][1]
    failed.update(status="fail", adoption="reject")
    failed["assessment"]["presentation"]["status"] = "fail"
    write(section_report, value)
    reviews.import_report(root, project, section_report)
    problem, = issues.load(root, required=True)
    assert [item["id"] for item in problem["scope"]["items"]] == ["end"]

    # 开头改动使旧单窗报告和批量报告的一个窗口过期，结尾仍可独立采用。
    (root / "core.tsx").write_text("export default 4;", encoding="utf-8")
    prepared["preparedFingerprint"] = "source-v2"
    state = ledger.status(root, project)
    assert [item["status"] for item in state["keySamples"]["windows"]] == ["missing", "pass"]
    assert state["keyframes"]["status"] == "missing" and not state["complete"]


@pytest.mark.media
@pytest.mark.slow
def test_actual_bilingual_composition_in_both_independent_review_packages(work, film, monkeypatch, chromium_ready):
    from pathlib import Path
    from film_runtime.engine import remotion, render_pipeline
    from film_runtime.engine.http_server import LocalServer
    from playwright.sync_api import sync_playwright

    root, project, prepared = film
    width, height, fps = prepared["width"], prepared["height"], prepared["fps"]
    template = Path(__file__).resolve().parents[2] / "templates/standalone"
    base = outputs(root)
    props = prepared["props"]
    props.update(width=width, height=height, fps=fps, durationInFrames=901, version=9, schemaVersion=9)
    props["subtitle"] = {"safeArea": {"x": 20, "y": 245, "width": 600, "height": 100},
                         "fontSize": 30, "lineHeight": 1.15, "textColor": "#fff",
                         "plateColor": "#000", "secondary": {"fontSize": 18}}
    props["compiledScenes"][0].update(durationInFrames=470, transition="cut", transitionFrames=0)
    props["compiledScenes"][1].update(durationInFrames=431, transition="cut", transitionFrames=0)
    for scene, colour in zip(props["compiledScenes"], ("#111111", "#eeeeee"), strict=True):
        image = base / f"{scene['id']}.png"
        Image.new("RGB", (width, height), colour).save(image)
    props["subtitleCues"] = [
        {"startFrame": 467, "endFrame": 470, "text": "第一句", "secondary": "First English line",
         "backing": {"color": "#000000", "opacity": 0.6, "textColor": "#ffffff"}},
        {"startFrame": 470, "endFrame": 473, "text": "第二句", "secondary": "Second English line",
         "backing": {"color": "#ffffff", "opacity": 0.6, "textColor": "#111111"}},
    ]
    config = root / "fixture-props.json"
    source = base / "preview.mp4"
    with sync_playwright() as playwright:
        monkeypatch.setenv("VIDEO_BROWSER_EXECUTABLE", playwright.chromium.executable_path)
    with LocalServer(base) as server:
        render_props = {**props, "compiledScenes": [
            {**scene, "stillPath": f"{server.base_url}/{scene['id']}.png"} for scene in props["compiledScenes"]
        ]}
        write(config, render_props)
        bundle = remotion.bundle(web_dir=template, out_dir=root / "bundle", storyboard_path=config,
                                 content_root=root.parent, workspace_root=root.parent, cache=True)
        confirm = render_pipeline.metadata_confirm(
            (fps, width, height, 901), source, crf=18, preset="medium", frames=6, start_frame=467)
        remotion.render_session(web_dir=template, bundle_dir=bundle.path, props=config,
                                composition_id="SceneFilm", on_metadata=confirm, timeout_s=90)

    _preview(root, project, prepared, source, 467, 6)
    monkeypatch.setattr(reviews, "ffmpeg", ffmpeg)
    contrast = _formal_still(work, source, 1, name="dark-cue")
    request_data = request()
    goal = "切镜前后的中英字幕层级及换句"
    request_data.update(film=True, purpose="process", reviewType="process", sources=[],
                        references=["trial.png"], conditions=[goal],
                        items=[{"id": "sub-cue", "path": "preview.mp4", "window": [0, 6], "dynamic": True}])
    pack = reviews.package(root, project, request_data)
    static_item = read(contrast / "manifest.json")["items"][0]
    dynamic_item = read(pack / "manifest.json")["items"][0]
    assert static_item["filmWindow"] == [468, 469] and dynamic_item["filmWindow"] == [467, 473]
    assert len(dynamic_item["sequence"]) == 6
    for directory, image_name, is_dark in (
        (contrast, static_item["path"], True),
        (pack, dynamic_item["sequence"][4]["path"], False),
    ):
        with Image.open(directory / image_name) as image:
            gray = image.convert("L")
            assert (gray.getpixel((100, 100)) < 80) is is_dark
            main = gray.crop((260, 255, 380, 296)).tobytes()
            secondary = gray.crop((235, 302, 405, 334)).tobytes()
            # 两行都必须在切镜前后烧录进证据，且适应实际背景明暗。
            for pixels in (main, secondary):
                assert sum((value > 200) if is_dark else (value < 60) for value in pixels) > 40
    assert "字号" in (contrast / "questions.md").read_text(encoding="utf-8")
    assert "换句" in (pack / "questions.md").read_text(encoding="utf-8")


def test_open_legacy_final_issue_survives_protocol_upgrade(work, film):
    root, project, prepared = film
    base = outputs(root)
    old = {**ledger.cycle(root), "version": 3, "finalFocuses": ["comprehensive"], "basis": "旧流程"}
    write(ledger.directory(root) / "cycle.json", old)
    write(base / "production/workflow.json", old)
    old_dir = base / "production" / old["cycleId"]
    write(old_dir / "reports/failure.json", {"id": "failure", "round": "final", "verdict": "fail"})
    report_ref = receipt(base, old_dir / "reports/failure.json")
    event = {"version": 3, "id": "old-event", "cycleId": old["cycleId"], "projectId": old["projectId"],
             "type": "review", "time": old["createdAt"],
             "data": {"reportId": "failure", "reportPath": report_ref["path"], "receipts": [report_ref]}}
    (old_dir / "history.jsonl").write_text(json.dumps(event), encoding="utf-8")
    original = {"id": "REVIEW-failure", "cycleId": old["cycleId"], "status": "open",
                "required": True, "round": "final", "scope": {}, "reportId": "failure",
                "versionRefs": ["current"], "cause": "implementation", "observations": "转场有白闪"}
    fence = chr(96) * 3
    body = f"{fence}m2v-issues-v3\n" + json.dumps({"version": 3, "cycleId": old["cycleId"], "items": [original]}) + f"\n{fence}\n"
    (base / "visual-notes.md").write_text(body, encoding="utf-8")

    ledger.start(root, project)
    state = ledger.status(root, project)
    item, = state["issues"]
    assert item["required"] and not state["complete"]
    legacy = item["scope"]["legacy"]
    assert legacy["reportId"] == "failure"
    assert (base / legacy["notes"]["path"]).read_text(encoding="utf-8") == body
    assert read(old_dir / "reports/failure.json")["verdict"] == "fail"
    with pytest.raises(M2VError, match="未关闭"):
        ledger.start(root, project)
    closure = {**item, "status": "closed", "evidence": [receipt(base, base / "trial.png")]}
    path = _candidate(root, prepared, "fixed")
    with pytest.raises(M2VError, match="整片证据复核"):
        issues.update(root, closure)
    film_review.confirm_evidence(root, project, _evidence_request(path, 469, 472, "切镜相邻帧未出现白闪"))
    issues.update(root, closure)
    assert not ledger.status(root, project)["issues"]
