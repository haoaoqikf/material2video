"""新评审契约的关键边界；普通绑定测试使用静态媒体，动态另做一次真实取证。"""

import copy
import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from m2v.core.delivery import outputs, digest
from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_project
from m2v.production import ledger, reviews, issues, baselines
from m2v.production.storage import read, write, receipt, local, locked


@pytest.fixture
def work(tmp_path, monkeypatch):
    root = tmp_path / "work"
    create_project(root, "text-motion", {"storyboard": "storyboard.json"})
    (root / "storyboard.json").unlink(missing_ok=True)
    (root / "DESIGN.md").unlink(missing_ok=True)
    manifest = load_project(root)[1]
    out = outputs(root)
    out.mkdir()
    (root / "core.tsx").write_text("export default 1;", encoding="utf-8")
    (root / "unrelated.tsx").write_text("export default 2;", encoding="utf-8")
    Image.new("RGB", (640, 360), "blue").save(out / "trial.png")
    ledger.start(root, manifest)

    # 静态绑定测试无需重复启动 ffmpeg；真实净化与动态取证由媒体节点覆盖。
    def image_copy(args):
        source = args[args.index("-i") + 1]
        with Image.open(source) as im:
            im.save(args[-1])

    monkeypatch.setattr(reviews, "ffmpeg", image_copy)
    return root, manifest


def request():
    return dict(
        version=2,
        round="trial",
        fps=30,
        items=[dict(id="window-1", path="trial.png", window=[0, 1], dynamic=False)],
        sources=["core.tsx"],
        sceneIds=[],
        displaySizes=[640, 393],
    )


def test_history_cycle_reads_do_not_grow_with_events_and_all_rows_remain_checked(work, monkeypatch):
    root, _ = work
    event = ledger.history(root)[0][0]
    rows = [dict(event, id=uuid.uuid4().hex, type="observation") for _ in range(128)]
    path = ledger.directory(root) / "history.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    original, calls = ledger._cycle, []

    def counted(directory):
        calls.append(directory)
        return original(directory)

    monkeypatch.setattr(ledger, "_cycle", counted)
    actual, errors = ledger.history(root)
    assert actual == rows and not errors
    assert len(calls) <= 3

    # 最后一行损坏仍必须发现，不能以减少周期读取为由省略任何历史行。
    rows[-1]["projectId"] = "different-project"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    actual, errors = ledger.history(root)
    assert errors and len(actual) == len(rows) - 1


@pytest.mark.parametrize(("frames", "final_pass", "complete"), [
    (1800, True, True),
    (1801, True, False),
    (1800, False, False),
])
def test_status_uses_qa_duration_for_trial_exemption(work, monkeypatch, frames, final_pass, complete):
    root, manifest = work
    final_report = {
        "id": "final-report", "verdict": "pass", "isolation": "independent-subagent",
        "reviewType": "blind", "requiresComparison": False,
    }
    if final_pass:
        report_path = outputs(root) / "final-report.json"
        write(report_path, final_report)
        ledger.append(root, manifest, "review", data={
            "round": "final", "focus": "comprehensive", "reviewerId": "fresh-final",
            "reportId": "final-report", "reportPath": report_path.name,
            "receipts": [receipt(outputs(root), report_path)],
        })
    monkeypatch.setattr(reviews, "current_report", lambda *_: final_report)
    monkeypatch.setattr(ledger, "final_binding", lambda *_: {"durationFrames": frames, "fps": 30})
    result = ledger.status(root, manifest)
    assert result.get("technicalQA", {}).get("status") == "pass", result["diagnostics"]
    assert result["trial"] == []
    assert result["complete"] is complete


@pytest.mark.parametrize("cached_query", [False, True])
def test_history_rejects_cycle_switch_during_scan_even_in_read_query(work, monkeypatch, cached_query):
    from contextlib import nullcontext

    root, _ = work
    current = copy.deepcopy(ledger.cycle(root))
    path = ledger.directory(root) / "history.jsonl"
    original, switched = Path.read_text, []

    def reading(candidate, *args, **kwargs):
        content = original(candidate, *args, **kwargs)
        if candidate == path and not switched:
            changed = dict(current, cycleId=uuid.uuid4().hex)
            write(outputs(root) / f"production/{changed['cycleId']}/cycle.json", changed)
            write(outputs(root) / "production/workflow.json", changed)
            switched.append(changed)
        return content

    monkeypatch.setattr(Path, "read_text", reading)
    with ledger.query() if cached_query else nullcontext():
        _, errors = ledger.history(root)
    assert switched and errors


def test_render_cleanup_preserves_bound_trial_and_reference_media(work):
    from m2v.production.cleanup import cleanup_render_outputs

    root, manifest = work
    base = outputs(root)
    trial = base / "previews/trial.png"
    trial.parent.mkdir()
    (base / "trial.png").rename(trial)
    reference = base / "previews/target.png"
    Image.new("RGB", (640, 360), "red").save(reference)
    unused = base / "previews/unused.mp4"
    unused.write_bytes(b"unused")
    current = base / "video.mp4"
    current.write_bytes(b"current")
    req = request()
    req["items"][0]["path"] = "previews/trial.png"
    req["references"] = ["previews/target.png"]
    req["conditions"] = ["主体保持可辨轮廓，目标用于比较形体"]
    # 未导入的评审包也必须保留源媒体；包内副本并不解除来源摘要绑定。
    pack = reviews.package(root, manifest, req)
    assert cleanup_render_outputs(root, current) == []
    assert trial.is_file() and reference.is_file() and not unused.exists()
    reviews.load_package(root, manifest, (pack / "manifest.json").relative_to(base).as_posix(),
                         digest(pack / "manifest.json"))


def test_render_cleanup_stops_when_review_binding_cannot_be_trusted(work):
    from m2v.production.cleanup import cleanup_render_outputs

    root, manifest = work
    reviews.package(root, manifest, request())
    record = next((ledger.directory(root) / "packages").glob("*.json"))
    record.write_text("{}", encoding="utf-8")
    base = outputs(root)
    current = base / "video.mp4"
    current.write_bytes(b"current")
    old = base / "old.mp4"
    old.write_bytes(b"old")
    failures = cleanup_render_outputs(root, current)
    assert failures and "未执行清理" in failures[0]
    assert old.is_file() and current.is_file()


def report(
    work,
    pack,
    *,
    who="reviewer-1",
    verdict="pass",
    isolation="independent-subagent",
    focus="comprehensive",
):
    root, manifest = work
    data = read(pack / "manifest.json")
    now = datetime.now(timezone.utc) + timedelta(seconds=1)
    call_id = uuid.uuid4().hex
    invocation = ledger.directory(root) / "calls" / f"{call_id}.json"
    write(
        invocation,
        dict(
            id=call_id,
            reviewerId=who,
            freshContext=True,
            startedAt=now.isoformat(),
            completedAt=(now + timedelta(seconds=1)).isoformat(),
            inputPaths=[(pack / "manifest.json").relative_to(outputs(root)).as_posix()],
            readReportIds=[] if data["reviewType"] == "blind" else [data["blindId"]],
        ),
    )
    result = dict(
        version=2,
        round=data["round"],
        reviewType=data["reviewType"],
        packPath=(pack / "manifest.json").relative_to(outputs(root)).as_posix(),
        packSha256=digest(pack / "manifest.json"),
        reviewerId=who,
        isolation=isolation,
        focus=focus,
        verdict=verdict,
        observations="实际观察到主体与变化",
        invocation=receipt(outputs(root), invocation),
        coverage=[],
    )
    for item in data["items"]:
        result["coverage"].append(
            dict(
                id=item["id"],
                window=item["window"],
                status=verdict,
                observations="窗口已完整查看",
                limitations=[],
                assessment={
                    k: dict(status=verdict, observations="具体观察")
                    for k in ("understanding", "presentation", "representativeness")
                },
            )
        )
    if data["blindId"]:
        result["blindId"] = data["blindId"]
    target = outputs(root) / "report.json"
    write(target, result)
    return target


def submit(work, **kwargs):
    root, manifest = work
    pack = reviews.package(root, manifest, request())
    return reviews.import_report(root, manifest, report(work, pack, **kwargs))


def test_local_trial_without_design_or_board_and_readonly_state(work):
    root, manifest = work
    assert not (root / "DESIGN.md").exists() and not (root / "storyboard.json").exists()
    accepted = submit(work)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    result = ledger.status(root, manifest)
    assert (
        result["trial"][0]["id"] == accepted["id"]
        and result["trial"][0]["status"] == "pass"
    )
    assert not result["complete"] and "gates" not in result and "phase" not in result
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_source_scope_reuse_and_private_binding_integrity(work):
    root, manifest = work
    submit(work)
    (root / "unrelated.tsx").write_text("changed", encoding="utf-8")
    assert ledger.status(root, manifest)["trial"][0]["status"] == "pass"
    (root / "core.tsx").write_text("changed", encoding="utf-8")
    assert ledger.status(root, manifest)["trial"][0]["status"] == "stale"
    private = next((ledger.directory(root) / "packages").glob("*.json"))
    data = read(private)
    data["binding"] = ledger.binding(root, manifest, data["request"])
    write(private, data)
    assert "私有来源" in ledger.status(root, manifest)["trial"][0]["detail"]


def test_scene_dependencies_and_global_output_change(work):
    root, manifest = work
    write(
        root / "storyboard.json",
        {
            "scenes": [
                {"id": "one", "content": {"entry": "core.tsx"}},
                {"id": "two", "content": {"entry": "unrelated.tsx"}},
            ]
        },
    )
    r = request()
    r.update(sources=[], sceneIds=["one"])
    pack = reviews.package(root, manifest, r)
    reviews.import_report(root, manifest, report(work, pack))
    (root / "unrelated.tsx").write_text("changed", encoding="utf-8")
    assert ledger.status(root, manifest)["trial"][0]["status"] == "pass"
    value = read(root / "project.json")
    value["output"]["fps"] = 24
    write(root / "project.json", value)
    assert ledger.status(root, manifest)["trial"][0]["status"] == "stale"


@pytest.mark.parametrize(
    "mutation", ["legacy", "outside", "empty", "dynamic-image", "missing-phone"]
)
def test_invalid_requests(work, mutation):
    root, manifest = work
    r = request()
    if mutation == "legacy":
        r.update(gate="G4")
    if mutation == "outside":
        r["items"][0]["path"] = "../trial.png"
    if mutation == "empty":
        r["items"] = []
    if mutation == "dynamic-image":
        r["items"][0]["dynamic"] = True
    if mutation == "missing-phone":
        r["displaySizes"] = [640]
    with pytest.raises(M2VError):
        reviews.package(root, manifest, r)


@pytest.mark.parametrize(
    "mutation",
    ["coverage", "assessment", "call", "isolation", "input", "pack", "old-version"],
)
def test_rejects_incomplete_or_tampered_reports(work, mutation):
    root, manifest = work
    pack = reviews.package(root, manifest, request())
    path = report(work, pack)
    value = read(path)
    if mutation == "coverage":
        value["coverage"][0]["window"] = [0, 2]
    if mutation == "assessment":
        value["coverage"][0]["assessment"]["presentation"]["status"] = "insufficient"
    if mutation == "call":
        value["invocation"]["sha256"] = "0" * 64
    if mutation == "isolation":
        inv = local(outputs(root), value["invocation"]["path"])
        data = read(inv)
        data["freshContext"] = False
        write(inv, data)
        value["invocation"] = receipt(outputs(root), inv)
    if mutation == "input":
        inv = local(outputs(root), value["invocation"]["path"])
        data = read(inv)
        data["inputPaths"] = ["trial.png"]
        write(inv, data)
        value["invocation"] = receipt(outputs(root), inv)
    if mutation == "pack":
        (pack / "evidence-0000.png").write_bytes(b"damaged")
    if mutation == "old-version":
        value["version"] = 1
    write(path, value)
    with pytest.raises(M2VError):
        reviews.import_report(root, manifest, path)


def test_failed_review_close_reopen_and_cycle_isolation(work):
    root, manifest = work
    submit(work, verdict="fail")
    problem = issues.load(root)[0]
    assert problem["status"] == "open" and problem["required"]
    degraded = submit(work, who="self", isolation="self-review")
    problem.update(
        status="closed", cause="implementation", closureReportId=degraded["id"]
    )
    with pytest.raises(M2VError, match="独立通过"):
        issues.update(root, problem)
    accepted = submit(work, who="fresh")
    problem["closureReportId"] = accepted["id"]
    issues.update(root, problem)
    assert issues.load(root)[0]["status"] == "closed"
    problem["status"] = "open"
    issues.update(root, problem)
    assert issues.load(root)[0]["reportId"] == problem["reportId"]
    ledger.start(root, manifest)
    with pytest.raises(M2VError, match="跨周期"):
        issues.update(root, problem)
    assert list((outputs(root) / "production/history-notes").glob("*.md"))


def test_changed_scope_cannot_close_independent_problem(work):
    root, manifest = work
    submit(work, verdict="fail")
    problem = issues.load(root)[0]
    other = request()
    other["sources"] = ["unrelated.tsx"]
    pack = reviews.package(root, manifest, other)
    accepted = reviews.import_report(root, manifest, report(work, pack, who="fresh"))
    problem.update(status="closed", cause="design", closureReportId=accepted["id"])
    with pytest.raises(M2VError, match="对应范围"):
        issues.update(root, problem)


@pytest.mark.parametrize("conditions", [None, []])
def test_reference_without_observable_conditions_is_rejected_before_pack(work, conditions):
    root, manifest = work
    req = request()
    req["references"] = ["trial.png"]
    if conditions is not None:
        req["conditions"] = conditions
    with pytest.raises(M2VError, match="conditions"):
        reviews.package(root, manifest, req)
    assert not (outputs(root) / "review-pack").exists()


def test_target_comparison_follows_own_blind_observation(work):
    root, manifest = work
    Image.new("RGB", (640, 360), "red").save(outputs(root) / "target.png")
    r = request()
    r["references"] = ["target.png"]
    r["conditions"] = ["主体色彩与目标对应，边缘保持清晰"]
    pack = reviews.package(root, manifest, r)
    assert not list(pack.glob("target-*"))
    assert not (pack / "conditions.json").exists()
    blind = reviews.import_report(root, manifest, report(work, pack))
    assert ledger.status(root, manifest)["trial"][0]["status"] == "insufficient"
    r.update(reviewType="consistency", blindId=blind["id"])
    compare = reviews.package(root, manifest, r)
    target = next(compare.glob("target-*"))
    assert target.name in {f["path"] for f in read(compare / "manifest.json")["files"]}
    with Image.open(target) as image:
        assert image.getpixel((0, 0)) == (255, 0, 0)
    assert read(compare / "conditions.json") == r["conditions"]
    with pytest.raises(M2VError, match="同一评审者"):
        reviews.import_report(root, manifest, report(work, compare, who="another"))
    reviews.import_report(root, manifest, report(work, compare))
    assert ledger.status(root, manifest)["trial"][0]["status"] == "pass"


def test_neutral_conditions_are_withheld_until_blind_import(work):
    root, manifest = work
    r = request()
    r["conditions"] = ["观察必要主体在当前手机窗口中的辨识度"]
    pack = reviews.package(root, manifest, r)
    assert not (pack / "conditions.json").exists()
    blind = reviews.import_report(root, manifest, report(work, pack))
    r.update(reviewType="consistency", blindId=blind["id"])
    changed = copy.deepcopy(r)
    changed["conditions"] = ["改变原条件"]
    with pytest.raises(M2VError, match="相同媒体"):
        reviews.package(root, manifest, changed)
    added_target = copy.deepcopy(r)
    added_target["references"] = ["trial.png"]
    with pytest.raises(M2VError, match="相同媒体"):
        reviews.package(root, manifest, added_target)
    compare = reviews.package(root, manifest, r)
    assert read(compare / "conditions.json") == r["conditions"]
    reviews.import_report(root, manifest, report(work, compare))
    assert ledger.status(root, manifest)["trial"][0]["status"] == "pass"


def test_history_corruption_and_new_cycle_keep_old_files(work):
    root, manifest = work
    submit(work)
    path = ledger.directory(root) / "history.jsonl"
    original = path.read_bytes()
    with path.open("a") as stream:
        stream.write("{broken")
    assert not ledger.status(root, manifest)["complete"]
    assert ledger.status(root, manifest)["diagnostics"]
    with pytest.raises(M2VError, match="损坏"):
        reviews.package(root, manifest, request())
    ledger.start(root, manifest)
    assert path.read_bytes() == original + b"{broken"


def test_baseline_references_protect_and_invalid_records_block_prune(work):
    root, manifest = work
    media = outputs(root) / "video.mp4"
    media.write_bytes(b"baseline")
    versions = [
        baselines.create(root, manifest, reason="compare", files=["video.mp4"])
        for _ in range(3)
    ]
    write(
        outputs(root) / "production/comparisons.json",
        [{"status": "active", "versionRefs": [v["id"] for v in versions]}],
    )
    assert baselines.prune(root, manifest)["pruned"] == []
    write(outputs(root) / "production/comparisons.json", [])
    assert baselines.prune(root, manifest)["fullVersions"] == 3
    write(
        outputs(root) / "production/comparisons.json",
        [{"status": "active", "versionRefs": ["unknown"]}],
    )
    with pytest.raises(M2VError, match="未知"):
        baselines.prune(root, manifest)


def test_baseline_preserves_and_prunes_deep_report_paths(work):
    root, manifest = work
    base = outputs(root)
    (base / "video.mp4").write_bytes(b"baseline")
    report_path = ledger.directory(root) / "reports" / ("a" * 64 + ".json")
    # 让源路径仍可用普通 Win32 IO，嵌入基线 records 后才跨过 260；
    # Linux 的临时目录通常更短，因此按实际路径长度补一个目录层。
    if len(str(report_path.resolve())) < 230:
        report_path = report_path.parent / ("x" * max(1, 229 - len(str(report_path.resolve())))) / report_path.name
    write(report_path, {"evidence": "deep report"})
    versions = [baselines.create(root, manifest, reason="compare", files=["video.mp4"])
                for _ in range(3)]
    directory = baselines._baseline_directory(root) / versions[1]["id"]
    saved = directory / "records" / report_path.relative_to(base)
    assert len(str(saved)) > 260
    assert digest(saved) == digest(report_path)
    # 降级会重验每条记录；覆盖创建之外的长路径读取和恢复清理。
    assert versions[1]["id"] in baselines.prune(root, manifest)["pruned"]
    assert saved.is_file()


def test_path_safety_and_writer_lock(work):
    root, manifest = work
    with pytest.raises(M2VError):
        local(outputs(root), "../project.json")
    with locked(root), pytest.raises(M2VError):
        with locked(root):
            pass
    history_path = ledger.directory(root) / "history.jsonl"
    history_path.write_bytes(history_path.read_bytes().rstrip(b"\n"))
    ledger.append(root, manifest, "render-request")
    assert len(ledger.history(root)[0]) == 2 and not ledger.history(root)[1]


def test_baseline_cleanup_resumes_after_interruption(work, monkeypatch):
    root, manifest = work
    out = outputs(root)
    (out / "video.mp4").write_bytes(b"baseline")
    versions = [
        baselines.create(root, manifest, reason="compare", files=["video.mp4"])
        for _ in range(3)
    ]
    original = Path.unlink

    def interrupt(path, *args, **kwargs):
        if versions[1]["id"] in str(path) and path.suffix == ".mp4":
            raise OSError("模拟删除中断")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", interrupt)
    with pytest.raises(OSError):
        baselines.prune(root, manifest)
    target = out / "baselines" / versions[1]["id"] / "manifest.json"
    assert read(target)["pendingDelete"]
    monkeypatch.setattr(Path, "unlink", original)
    baselines.prune(root, manifest)
    assert read(target)["prunedAt"] and read(target)["pendingDelete"] == []


@pytest.mark.media
def test_real_video_window_frames_and_metadata(tmp_path):
    from m2v.production.model import ffmpeg

    root = tmp_path / "work"
    root.mkdir()
    out = outputs(root)
    out.mkdir()
    manifest = {"id": "work", "type": "text-motion"}
    ledger.start(root, manifest)
    ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x90:rate=30:duration=0.4",
            "-metadata",
            "author=private-author",
            "-pix_fmt",
            "yuv420p",
            str(out / "clip.mp4"),
        ]
    )
    r = request()
    r["sources"] = []
    r["items"] = [dict(id="window-1", path="clip.mp4", window=[3, 9], dynamic=True)]
    pack = reviews.package(root, manifest, r)
    data = read(pack / "manifest.json")
    item = data["items"][0]
    assert [x["frame"] for x in item["sequence"]] == list(range(3, 9))
    assert len(list((pack / "evidence-0000").glob("*-393.png"))) == 6
    assert ledger.evidence_valid_at(pack, data["files"])
    r["items"][0]["window"] = [0, 60]
    with pytest.raises(M2VError, match="完整观察"):
        reviews.package(root, manifest, r)


@pytest.mark.media
def test_real_image_metadata_removed(tmp_path):
    root = tmp_path / "work"
    root.mkdir()
    out = outputs(root)
    out.mkdir()
    manifest = {"id": "work"}
    ledger.start(root, manifest)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Author", "private-author")
    Image.new("RGB", (160, 90), "blue").save(out / "trial.png", pnginfo=metadata)
    Image.new("RGB", (160, 90), "red").save(out / "target.png", pnginfo=metadata)
    r = request()
    r["sources"] = []
    r["references"] = ["target.png"]
    r["conditions"] = ["主体轮廓及色彩与目标对应"]
    pack = reviews.package(root, manifest, r)
    with Image.open(pack / "evidence-0000.png") as image:
        assert "Author" not in image.info
    assert not list(pack.glob("target-*")) and not (pack / "conditions.json").exists()
    blind = reviews.import_report(root, manifest, report((root, manifest), pack))
    r.update(reviewType="consistency", blindId=blind["id"])
    compare = reviews.package(root, manifest, r)
    with Image.open(next(compare.glob("target-*"))) as image:
        assert "Author" not in image.info
        assert image.convert("RGB").getpixel((0, 0)) == (255, 0, 0)
    assert read(compare / "conditions.json") == r["conditions"]


@pytest.mark.media
def test_final_requires_current_qa_fresh_reviewer_and_complete_candidate(
    work, monkeypatch
):
    from m2v.production.model import ffmpeg

    root, manifest = work
    out = outputs(root)
    submit(work, who="trial-author")
    monkeypatch.setattr(reviews, "ffmpeg", ffmpeg)
    ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x90:rate=30:duration=0.4",
            "-pix_fmt",
            "yuv420p",
            str(out / "final.mp4"),
        ]
    )
    prepared = {"preparedFingerprint": "current", "durationInFrames": 12, "fps": 30,
                "width": 1920, "height": 1080, "type": "text-motion",
                "inputs": {"implementation": "own", "renderer": "own"}}
    monkeypatch.setattr("m2v.commands._prepared", lambda *_: prepared)
    write(root / "storyboard.json", {"scenes": []})
    parameters = {"crf": 18}
    from m2v.core.delivery import binding
    from m2v.core.fingerprints import fingerprint
    record = {**binding(root, prepared, parameters), "key": fingerprint(binding(root, prepared, parameters)),
              "status": "delivered", "path": "outputs/final.mp4",
              "sha256": digest(out / "final.mp4")}
    write(out / "delivery.json", record)
    write(
        out / "qa.json",
        {"status": "pass", "preparedFingerprint": "current", "videoSha256": "wrong"},
    )
    r = request()
    r.update(round="final", sources=[])
    r["items"] = [dict(id="whole-film", path="final.mp4", window=[0, 12], dynamic=True)]
    with pytest.raises(M2VError, match="技术 QA"):
        reviews.package(root, manifest, r)
    write(
        out / "qa.json",
        {
            "status": "pass",
            "preparedFingerprint": "current",
            "videoSha256": digest(out / "final.mp4"),
        },
    )
    short = copy.deepcopy(r)
    short["items"][0]["window"] = [0, 6]
    with pytest.raises(M2VError, match="全片窗口"):
        reviews.package(root, manifest, short)
    pack = reviews.package(root, manifest, r)
    with pytest.raises(M2VError, match="新评审者"):
        reviews.import_report(root, manifest, report(work, pack, who="trial-author"))
    reviews.import_report(root, manifest, report(work, pack, who="final-fresh"))
    assert ledger.status(root, manifest)["complete"]
    reviews.import_report(
        root, manifest, report(work, pack, who="final-failure", verdict="fail")
    )
    problem = issues.load(root)[0]
    # 修复可缩短全片；当前整片终审仍能关闭原整片问题，不要求保留旧时长。
    shortened = out / "shortened.mp4"
    ffmpeg(["-i", str(out / "final.mp4"), "-frames:v", "6", str(shortened)])
    prepared["durationInFrames"] = 6
    delivery = read(out / "delivery.json")
    delivery.update(path="outputs/shortened.mp4", sha256=digest(shortened))
    refreshed = binding(root, prepared, delivery["parameters"])
    delivery.update(refreshed)
    delivery["key"] = fingerprint(refreshed)
    write(out / "delivery.json", delivery)
    write(
        out / "qa.json",
        {
            "status": "pass",
            "preparedFingerprint": "current",
            "videoSha256": digest(shortened),
        },
    )
    r["items"][0].update(path="shortened.mp4", window=[0, 6])
    repaired = reviews.package(root, manifest, r)
    accepted = reviews.import_report(
        root, manifest, report(work, repaired, who="final-recheck")
    )
    problem.update(status="closed", cause="design", closureReportId=accepted["id"])
    issues.update(root, problem)
    assert ledger.status(root, manifest)["complete"]
    ledger.start(root, manifest, split_final=True, basis="结构与文案需要分工覆盖")
    submit(work, who="new-trial")
    pack = reviews.package(root, manifest, r)
    reviews.import_report(
        root, manifest, report(work, pack, who="final-a", focus="structure")
    )
    assert not ledger.status(root, manifest)["complete"]
    with pytest.raises(M2VError, match="不同评审者"):
        reviews.import_report(
            root, manifest, report(work, pack, who="final-a", focus="visual-copy")
        )
    reviews.import_report(
        root, manifest, report(work, pack, who="final-b", focus="visual-copy")
    )
    assert ledger.status(root, manifest)["complete"]
    shortened.write_bytes(b"changed")
    assert not ledger.status(root, manifest)["complete"]


def test_closed_problem_reopens_when_its_evidence_changes(work):
    root, manifest = work
    submit(work, verdict="fail")
    problem = issues.load(root)[0]
    accepted = submit(work, who="fresh")
    problem.update(
        status="closed", cause="implementation", closureReportId=accepted["id"]
    )
    issues.update(root, problem)
    (root / "core.tsx").write_text("changed", encoding="utf-8")
    assert issues.load(root)[0]["status"] == "open"
    # 删除失败问题块不能抹掉事件中保存的独立失败。
    issues.save(root, [])
    assert ledger.status(root, manifest)["diagnostics"]


def test_status_reuses_history_in_one_query_and_rechecks_next_time(work, monkeypatch):
    root, manifest = work
    submit(work)
    calls = []
    original = ledger._history
    monkeypatch.setattr(
        ledger, "_history", lambda root: calls.append(root) or original(root)
    )
    ledger.status(root, manifest)
    assert len(calls) == 1
    ledger.status(root, manifest)
    assert len(calls) == 2


def test_issue_read_deduplicates_proof_but_rechecks_each_independent_read(work, monkeypatch):
    root, _ = work
    submit(work, verdict="fail", who="first-failure")
    submit(work, verdict="fail", who="second-failure")
    accepted = submit(work, who="fresh")
    for problem in issues.load(root):
        problem.update(status="closed", cause="implementation", closureReportId=accepted["id"])
        issues.update(root, problem)
    source = root / "core.tsx"
    original_source = source.read_text(encoding="utf-8")
    original, calls = reviews._current_report, []

    def checked(root, manifest, identity):
        calls.append(identity)
        return original(root, manifest, identity)

    monkeypatch.setattr(reviews, "_current_report", checked)
    assert {item["status"] for item in issues.load(root)} == {"closed"}
    assert calls == [accepted["id"]]
    source.write_text("changed", encoding="utf-8")
    assert {item["status"] for item in issues.load(root)} == {"open"}
    assert calls == [accepted["id"]] * 2
    # 失败缓存也只属于上次读取；恢复来源后能够重验通过，问题原记录不被投影改写。
    source.write_text(original_source, encoding="utf-8")
    with ledger.query():
        assert {item["status"] for item in issues.load(root)} == {"closed"}
        assert {item["status"] for item in issues.load(root)} == {"closed"}
    assert calls == [accepted["id"]] * 3
    saved = issues.parse((outputs(root) / "visual-notes.md").read_text(encoding="utf-8"))
    assert {item["status"] for item in saved["items"]} == {"closed"}


def test_report_import_is_idempotent_and_recovers_interrupted_problem_write(work):
    root, manifest = work
    pack = reviews.package(root, manifest, request())
    path = report(work, pack, verdict="fail")
    first = reviews.import_report(root, manifest, path)
    issues.save(root, [])  # 模拟事件追加后、问题原子替换前中断。
    second = reviews.import_report(root, manifest, path)
    assert first == second and len(issues.load(root)) == 1
    assert len([e for e in ledger.history(root)[0] if e["type"] == "review"]) == 1


def test_removing_target_cannot_close_original_visual_failure(work):
    root, manifest = work
    r = request()
    r["references"] = ["trial.png"]
    r["conditions"] = ["主体轮廓与目标对应"]
    pack = reviews.package(root, manifest, r)
    reviews.import_report(root, manifest, report(work, pack, verdict="fail"))
    problem = issues.load(root)[0]
    accepted = submit(work, who="fresh")
    problem.update(status="closed", cause="design", closureReportId=accepted["id"])
    with pytest.raises(M2VError, match="对应范围"):
        issues.update(root, problem)


def test_closure_validates_only_its_own_comparison_and_rejects_damage(work, monkeypatch):
    root, manifest = work
    unrelated = submit(work, who="unrelated")
    req = request()
    req.update(references=["trial.png"], conditions=["主体轮廓与目标对应"])
    failed_pack = reviews.package(root, manifest, req)
    reviews.import_report(root, manifest, report(work, failed_pack, verdict="fail"))
    problem = issues.load(root)[0]
    blind_pack = reviews.package(root, manifest, req)
    blind = reviews.import_report(root, manifest, report(work, blind_pack, who="fresh"))
    req.update(reviewType="consistency", blindId=blind["id"])
    comparison_pack = reviews.package(root, manifest, req)
    comparison = reviews.import_report(root, manifest, report(work, comparison_pack, who="fresh"))
    problem.update(status="closed", cause="design", closureReportId=blind["id"])
    original, calls = reviews.current_report, []

    def checked(root, manifest, identity):
        calls.append(identity)
        return original(root, manifest, identity)

    monkeypatch.setattr(reviews, "current_report", checked)
    issues.validate_closure(root, problem)
    assert set(calls) == {blind["id"], comparison["id"]}
    assert unrelated["id"] not in calls
    (comparison_pack / "evidence-0000.png").write_bytes(b"damaged")
    with pytest.raises(M2VError, match="缺少同轮目标对照"):
        issues.validate_closure(root, problem)


@pytest.mark.slow
def test_full_timeline_uses_prepared_composition_without_review_or_encode(
    tmp_path, monkeypatch, chromium_ready
):
    from m2v.production import timeline
    from m2v.production.model import ffmpeg
    from m2v.engine.http_server import LocalServer
    from m2v.core import frames
    from playwright.sync_api import sync_playwright

    root = tmp_path / "work"
    root.mkdir()
    clip = root / "clip.mp4"
    ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=1920x1080:r=30:d=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(clip),
        ]
    )
    props = {
        "version": 9,
        "schemaVersion": 9,
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "title": "",
        "durationInFrames": 30,
        "subtitle": frames.spec(1920, 1080)["subtitle"],
        "subtitleCues": [],
        "compiledScenes": [
            {
                "id": "one",
                "startFrame": 0,
                "endFrame": 30,
                "durationInFrames": 30,
                "transitionFrames": 0,
                "transition": "cut",
                "mediaPath": "clip.mp4",
            }
        ],
    }
    prepared = {
        "props": props,
        "durationInFrames": 30,
        "fps": 30,
        "width": 1920,
        "height": 1080,
    }
    monkeypatch.setattr("m2v.commands._prepared", lambda *_: prepared)
    monkeypatch.setattr(
        "m2v.types.scene_film.code_scenes.materialize", lambda *_: prepared
    )
    monkeypatch.setattr("m2v.engine.lookdev.sample_audio", lambda *_: (False, None))
    target = timeline.build(root, {"id": "work"})
    assert (
        not (target / "video.mp4").exists()
        and (target / "evidence-0000.mp4").read_bytes() == clip.read_bytes()
    )
    errors = []
    with LocalServer(target) as server, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(server.base_url + "/index.html")
            page.locator("video").wait_for()
            assert not errors
        finally:
            browser.close()
