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
from m2v.production import ledger, reviews, issues
from m2v.production.storage import read, write, receipt, local, locked


def install_test_style(root):
    """隔离测试只使用生成的本地参考原件，不访问外部参考站点。"""
    from m2v.core import style_binding as style
    path = root/style.BINDING
    data = read(path)
    visual = data['visualStyle']
    image = root/'design/reference-test.png'
    Image.new('RGB', (20, 16), 'green').save(image)
    sha = digest(image)
    for ref in visual['references']:
        ref['evidence']['sha256'] = sha
    visual['snapshot'] = {ref['id']: {'path': 'design/reference-test.png', 'sha256': sha}
                          for ref in visual['references']}
    data['referenceDigest'] = style.fingerprint(visual)
    write(path, data)
    release = read(root/style.RELEASE)
    write(root/style.RELEASE, {**release, 'referenceDigest': data['referenceDigest']})


@pytest.fixture
def work(tmp_path, monkeypatch):
    root = tmp_path / "work"
    create_project(root, "text-motion", {"storyboard": "storyboard.json"})
    install_test_style(root)
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
        version=ledger.VERSION,
        round="trial",
        purpose="keyframe",
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


def test_render_cleanup_preserves_internal_issue_evidence(work):
    from m2v.production.cleanup import cleanup_render_outputs

    root, _ = work
    base = outputs(root)
    current = base / "video.mp4"
    current.write_bytes(b"current")
    proof = base / "previews/fixed.png"
    proof.parent.mkdir()
    proof.write_bytes(b"verified frame")
    issues.update(root, dict(
        id="cropping", cycleId=ledger.cycle(root)["cycleId"], status="closed",
        required=True, round="internal", scope={"window": [0, 1]}, reportId=None,
        versionRefs=["current"], cause="implementation", observations="已复查裁切",
        evidence=[receipt(base, proof)],
    ))

    assert cleanup_render_outputs(root, current) == []
    assert not (base / "trial.png").exists()
    assert issues.load(root)[0]["status"] == "closed"


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
            inputPaths=[(pack / name).relative_to(outputs(root)).as_posix()
                        for name in ["manifest.json", *(f["path"] for f in data["files"])]],
            readReportIds=[data["blindId"]] if data["reviewType"] == "consistency" else [],
        ),
    )
    result = dict(
        version=ledger.VERSION,
        round=data["round"],
        reviewType=data["reviewType"],
        packPath=(pack / "manifest.json").relative_to(outputs(root)).as_posix(),
        packSha256=digest(pack / "manifest.json"),
        reviewerId=who,
        isolation=isolation,
        focus=focus,
        verdict=verdict,
        adoption="adopt" if verdict == "pass" else "reject",
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
                adoption="adopt" if verdict == "pass" else "reject",
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


def submit(work, *, compare=False, req=None, **kwargs):
    root, manifest = work
    req = dict(req or request())
    req.setdefault("conditions", ["当前尺寸能分辨主体与背景"])
    pack = reviews.package(root, manifest, req)
    first = reviews.import_report(root, manifest, report(work, pack, **kwargs))
    if compare:
        paired = reviews.compare(root, manifest, first["id"])
        reviews.import_report(root, manifest, report(work, paired, **kwargs))
    return first


def test_local_trial_without_design_or_board_and_readonly_state(work):
    root, manifest = work
    assert not (root / "DESIGN.md").exists() and not (root / "storyboard.json").exists()
    accepted = submit(work, compare=True)
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
    accepted = submit(work, compare=True)
    (root / "unrelated.tsx").write_text("changed", encoding="utf-8")
    assert ledger.status(root, manifest)["trial"][0]["status"] == "pass"
    (root / "core.tsx").write_text("changed", encoding="utf-8")
    assert ledger.status(root, manifest)["trial"][0]["status"] == "stale"
    blind = read(ledger.directory(root) / "reports" / (accepted["id"] + ".json"))
    private = ledger.directory(root) / "packages" / (Path(blind["packPath"]).parent.name + ".json")
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
    submit(work, req=r, compare=True)
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
    accepted = submit(work, who="fresh", compare=True)
    problem["closureReportId"] = accepted["id"]
    issues.update(root, problem)
    assert issues.load(root)[0]["status"] == "closed"
    problem["status"] = "open"
    issues.update(root, problem)
    assert issues.load(root)[0]["reportId"] == problem["reportId"]
    with pytest.raises(M2VError, match="不能重开周期"):
        ledger.start(root, manifest)
    problem["status"] = "closed"
    issues.update(root, problem)
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


def test_history_corruption_blocks_new_cycle_without_rewriting_old_files(work):
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
    with pytest.raises(M2VError, match="不能重开周期"):
        ledger.start(root, manifest)
    assert path.read_bytes() == original + b"{broken"


def test_status_keeps_historical_baseline_events_without_projecting_retention(work, capsys):
    from m2v.cli import main

    root, manifest = work
    previous = outputs(root) / "baselines" / "old-version" / "manifest.json"
    previous.parent.mkdir(parents=True)
    previous.write_bytes(b"retired snapshot")
    ledger.append(root, manifest, "baseline-created", data={"id": "old-version", "reset": True})
    history = ledger.directory(root) / "history.jsonl"
    original = history.read_bytes()

    assert main(["status", "--project", str(root), "--history"]) == 0
    state = json.loads(capsys.readouterr().out)["production"]

    assert "baselines" not in state
    assert not state["diagnostics"]
    assert any(event["type"] == "baseline-created" for event in ledger.history(root)[0])
    assert history.read_bytes() == original
    assert previous.read_bytes() == b"retired snapshot"


def test_baseline_command_is_retired(capsys):
    from m2v.cli import _parser

    parser = _parser()
    with pytest.raises(SystemExit) as error:
        parser.parse_args(["baseline", "create", "--project", "unused"])
    assert error.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


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


@pytest.mark.media
def test_real_video_window_frames_and_metadata(tmp_path):
    from m2v.production.model import ffmpeg

    root = tmp_path / "work"
    create_project(root, "text-motion", {"storyboard": "storyboard.json"})
    install_test_style(root)
    manifest = load_project(root)[1]
    out = outputs(root)
    out.mkdir()
    ledger.start(root, manifest)
    ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x90:rate=30:duration=0.4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.4",
            "-metadata",
            "author=private-author",
            "-pix_fmt",
            "yuv420p",
            str(out / "clip.mp4"),
        ]
    )
    r = request()
    r.update(sources=[], displaySizes=[393, 160], purpose="process",
             reviewType="blind", blindReason="核对完整状态变化与身份连续")
    r["items"] = [dict(id="window-1", path="clip.mp4", window=[3, 9], dynamic=True)]
    pack = reviews.package(root, manifest, r)
    data = read(pack / "manifest.json")
    item = data["items"][0]
    assert [x["frame"] for x in item["sequence"]] == list(range(3, 9))
    sealed_paths = [record["path"] for record in data["files"]]
    for frame in item["sequence"]:
        phone = Path(frame["path"]).with_suffix("").as_posix() + "-393.png"
        assert frame["displayPaths"] == [phone, frame["path"]]
        assert sealed_paths.count(frame["path"]) == 1
    assert len(list((pack / "evidence-0000").glob("*-393.png"))) == 6
    assert not list((pack / "evidence-0000").glob("*-160.png"))
    assert ledger.evidence_valid_at(pack, data["files"])
    ffmpeg(["-i", str(pack / item["path"]), "-map", "0:a:0", "-f", "null", "-"])
    direct = {key: value for key, value in r.items() if key not in ("reviewType", "blindReason")}
    direct["conditions"] = ["核对当前时窗中测试图形的位置变化"]
    process = reviews.package(root, manifest, direct)
    current = read(process / "manifest.json")
    assert current["reviewType"] == "process" and current["blindId"] is None
    assert read(process / "style-references.json")["conditionsAvailable"]
    assert reviews.import_report(root, manifest, report((root, manifest), process))["verdict"] == "pass"
    r["items"][0]["window"] = [0, 60]
    with pytest.raises(M2VError, match="完整观察"):
        reviews.package(root, manifest, r)


@pytest.mark.media
def test_real_image_metadata_removed(tmp_path):
    root = tmp_path / "work"
    create_project(root, "text-motion", {"storyboard": "storyboard.json"})
    install_test_style(root)
    manifest = load_project(root)[1]
    out = outputs(root)
    out.mkdir()
    ledger.start(root, manifest)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Author", "private-author")
    Image.new("RGB", (160, 90), "blue").save(out / "trial.png", pnginfo=metadata)
    Image.new("RGB", (160, 90), "red").save(out / "target.png", pnginfo=metadata)
    r = request()
    r.update(sources=[], displaySizes=[160, 393])
    r["references"] = ["target.png"]
    r["conditions"] = ["主体轮廓及色彩与目标对应"]
    pack = reviews.package(root, manifest, r)
    frame = read(pack / "manifest.json")["items"][0]["sequence"][0]
    assert frame["displayPaths"] == [frame["path"], "evidence-0000-393.png"]
    assert not (pack / "evidence-0000-160.png").exists()
    with Image.open(pack / frame["path"]) as image:
        assert "Author" not in image.info
    assert not list(pack.glob("target-*")) and not (pack / "conditions.json").exists()
    blind = reviews.import_report(root, manifest, report((root, manifest), pack))
    r.update(reviewType="consistency", blindId=blind["id"])
    compare = reviews.package(root, manifest, r)
    with Image.open(next(compare.glob("target-*"))) as image:
        assert "Author" not in image.info
        assert image.convert("RGB").getpixel((0, 0)) == (255, 0, 0)
    assert read(compare / "conditions.json") == r["conditions"]



def test_closed_problem_reopens_when_its_evidence_changes(work):
    root, manifest = work
    submit(work, verdict="fail")
    problem = issues.load(root)[0]
    accepted = submit(work, who="fresh", compare=True)
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
    accepted = submit(work, who="fresh", compare=True)
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
    pair = calls.copy()
    assert len(pair) == 2 and pair[0] == accepted["id"] and pair[0] != pair[1]
    source.write_text("changed", encoding="utf-8")
    assert {item["status"] for item in issues.load(root)} == {"open"}
    assert calls == pair + [accepted["id"]]
    # 失败缓存也只属于上次读取；恢复来源后能够重验通过，问题原记录不被投影改写。
    source.write_text(original_source, encoding="utf-8")
    with ledger.query():
        assert {item["status"] for item in issues.load(root)} == {"closed"}
        assert {item["status"] for item in issues.load(root)} == {"closed"}
    assert calls == pair + [accepted["id"]] + pair
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


def test_archived_review_can_be_compared_and_exported_as_an_isolated_copy(work):
    from m2v.production import review_blobs

    root, manifest = work
    req = request()
    req["conditions"] = ["核对主体清晰度"]
    pack = reviews.package(root, manifest, req)
    blind = reviews.import_report(root, manifest, report(work, pack))
    before = digest(pack / "manifest.json")
    path = pack / "evidence-0000.png"
    original = receipt(outputs(root), path)
    initial = review_blobs.compact(pack)

    assert initial["archivedFiles"] == 2
    assert not path.exists()
    assert ledger.evidence_valid(root, [original])
    assert digest(pack / "manifest.json") == before

    compare = reviews.compare(root, manifest, blind["id"])
    reviews.import_report(root, manifest, report(work, compare))
    # 盲包已封存候选帧；对照包新增唯一参考媒体对象。
    reference_size = next(compare.glob("style-*.png")).stat().st_size
    compacted = review_blobs.compact(compare)
    assert compacted["objectBytesAdded"] == reference_size
    assert ledger.status(root, manifest)["trial"][0]["status"] == "pass"

    destination = root / "isolated-review"
    review_blobs.export(root, pack.name, destination)
    copied = destination / path.name
    assert digest(copied) == original["sha256"]
    copied.write_bytes(b"external edit")
    assert ledger.evidence_valid(root, [original])
