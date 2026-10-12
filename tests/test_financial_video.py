"""Financial time-series materials, integrity rules, and frame mapping."""
from __future__ import annotations

import json
import hashlib
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m2v.types.financial import financial
from m2v.types.financial import financial_render
from m2v.core.errors import M2VError
from m2v.types.financial import commands as financial_video


def project(tmp_path: Path) -> Path:
    root = tmp_path / "demo"
    root.mkdir()
    raw_snapshot = b"date,close\n2020-01-02,100\n2020-01-03,102\n"
    (root / "raw-prices.csv").write_bytes(raw_snapshot)
    docs = {
        "request.json": {
            "schemaVersion": 1, "originalRequest": "合成标的 2020 年无声走势",
            "instrument": {"kind": "stock", "name": "合成公司", "code": "SYN", "market": "TEST", "unit": "USD", "listingDate": "2010-01-01"},
            "requestedRange": ["2020-01-01", "2020-12-31"], "displayRange": ["2020-01-01", "2020-01-03"], "confirmations": ["合成测试确认缩短日期范围"],
            "investment": {"year": 2020, "principal": 1_000_000},
        },
        "prices.json": {
            "schemaVersion": 3, "unit": "USD", "priceBasis": "split-adjusted", "adjustmentBaseDate": "2020-01-03",
            "adjustmentDefinition": "仅拆合股调整，不计分红再投资；合成数据",
            "splitAdjustments": [], "expectedTradingDates": ["2020-01-02", "2020-01-03"],
            "expectedTradingDatesSource": ["https://example.invalid/calendar"],
            "points": [{"date": "2020-01-02", "close": 100.0}, {"date": "2020-01-03", "close": 102.0}],
            "sources": [{"url": "https://example.invalid/prices", "fetchedAt": "2026-10-05T00:00:00Z", "coverage": ["2020-01-01", "2020-12-31"], "adjustmentDefinition": "合成来源口径"}],
            "rawSnapshots": [{"path": "raw-prices.csv", "sha256": hashlib.sha256(raw_snapshot).hexdigest(), "sourceUrl": "https://example.invalid/prices"}],
        },
        "animation-plan.json": financial.build_line_plan(
            {"displayRange": ["2020-01-01", "2020-01-03"]},
            duration=15,
        ),
    }
    for name, data in docs.items():
        (root / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return root


def edit(root: Path, name: str, mutate) -> None:
    path = root / name
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_valid_materials_and_deterministic_frame_mapping(tmp_path):
    root = project(tmp_path)
    docs = financial.load_project(root)
    assert len(docs["prices"]["points"]) == 2
    assert financial.frame_date(docs["plan"], 0).isoformat() == "2020-01-01"
    assert financial.frame_date(docs["plan"], 30).isoformat() == "2020-01-01"
    assert financial.frame_date(docs["plan"], 210).isoformat() == "2020-01-02"
    assert financial.frame_date(docs["plan"], 389).isoformat() == "2020-01-03"
    assert financial.frame_date(docs["plan"], 449).isoformat() == "2020-01-03"
    assert docs["request"]["investment"] == {"year": 2020, "principal": 1_000_000}
    assert financial.build_render_props(docs)["request"]["investment"]["principal"] == 1_000_000


@pytest.mark.parametrize(
    ("investment", "message"),
    [
        ({"year": 2019, "principal": 100}, "展示范围内"),
        ({"year": 2020, "principal": 0}, "有限正数"),
        ({"year": True, "principal": 100}, "展示范围内"),
    ],
)
def test_rejects_invalid_investment_settings(tmp_path, investment, message):
    root = project(tmp_path)
    edit(root, "request.json", lambda data: data.update(investment=investment))
    with pytest.raises(M2VError, match=message):
        financial.load_project(root)


@pytest.mark.parametrize(
    ("file", "mutate", "message"),
    [
        ("prices.json", lambda d: d.update(priceBasis="total-return"), "priceBasis"),
        ("prices.json", lambda d: d["points"].pop(), "完全一致"),
        ("prices.json", lambda d: d["points"][1].update(close=float("nan")), "有限正数"),
        ("animation-plan.json", lambda d: d["segments"][1].update(frames=[14, 90]), "连续"),
        ("animation-plan.json", lambda d: d.update(canvas={"width": 1920, "height": 1080}), "1080"),
        ("animation-plan.json", lambda d: d["axis"].pop("dateScale"), "dateScale"),
        ("animation-plan.json", lambda d: d["axis"].update(visibleWindowMonths=0), "滚动窗口已移除"),
        ("animation-plan.json", lambda d: d["axis"].update(visibleWindowMonths=True), "滚动窗口已移除"),
        ("animation-plan.json", lambda d: d["axis"].update(valueScale="fixed"), "revealed-linear"),
        ("animation-plan.json", lambda d: d["axis"].update(valueRange=[0, 250]), "不接受固定 valueRange"),
    ],
)
def test_rejects_invalid_financial_materials(tmp_path, file, mutate, message):
    root = project(tmp_path)
    edit(root, file, mutate)
    with pytest.raises(M2VError, match=message):
        financial.load_project(root)


def test_stock_range_before_listing_requires_a_confirmed_shorter_range(tmp_path):
    root = project(tmp_path)
    edit(root, "request.json", lambda d: d["instrument"].update(listingDate="2021-01-01"))
    with pytest.raises(M2VError, match="上市日期之前"):
        financial.load_project(root)


def test_full_year_request_can_be_confirmed_to_actual_dates(tmp_path):
    root = project(tmp_path)
    today = date.today().isoformat()
    request = json.loads((root / "request.json").read_text(encoding="utf-8"))
    request["requestedRange"] = [f"{date.today().year}-01-01", f"{date.today().year}-12-31"]
    request["displayRange"] = [f"{date.today().year}-01-01", today]
    request["investment"] = {"year": date.today().year, "principal": 1_000_000}
    request["confirmations"] = ["用户确认使用截至当前日期的实际行情范围"]
    financial._validate_request(request)


def test_future_display_dates_are_rejected(tmp_path):
    root = project(tmp_path)
    request = json.loads((root / "request.json").read_text(encoding="utf-8"))
    future = date(date.today().year + 1, 1, 1).isoformat()
    request["requestedRange"] = ["2020-01-01", future]
    request["displayRange"] = ["2020-01-01", future]
    request["confirmations"] = ["合成确认"]
    with pytest.raises(M2VError, match="未来日期"):
        financial._validate_request(request)


def test_legacy_events_file_requires_migration(tmp_path):
    root = project(tmp_path)
    (root / "events.json").write_text("{}", encoding="utf-8")
    with pytest.raises(M2VError, match="事件材料已移除"):
        financial.load_project(root)


def test_index_material_uses_official_points_not_stock_adjustment(tmp_path):
    root = project(tmp_path)
    edit(root, "request.json", lambda d: d["instrument"].update(kind="index", indexStartDate="2010-01-01", unit="points"))
    edit(root, "prices.json", lambda d: d.update(
        unit="points", priceBasis="official-index-points", adjustmentBaseDate=None,
        adjustmentDefinition=None, splitAdjustments=None, indexType="合成价格指数",
    ))
    assert financial.load_project(root)["prices"]["indexType"] == "合成价格指数"


def test_raw_snapshot_hash_and_workspace_boundary_are_enforced(tmp_path):
    root = project(tmp_path)
    edit(root, "prices.json", lambda d: d["rawSnapshots"][0].update(sha256="0" * 64))
    with pytest.raises(M2VError, match="摘要不匹配"):
        financial.load_project(root)
    edit(root, "prices.json", lambda d: d["rawSnapshots"][0].update(path="../outside.csv"))
    with pytest.raises(M2VError, match="相对路径"):
        financial.load_project(root)


def test_explicit_migration_preserves_daily_closes_sources_and_backups(tmp_path):
    root = project(tmp_path)
    original = json.loads((root / "prices.json").read_text(encoding="utf-8"))
    old = {**original, "schemaVersion": 2, "points": [{**point, "open": point["close"], "high": point["close"] + 1, "low": point["close"] - 1} for point in original["points"]]}
    (root / "prices.json").write_text(json.dumps(old), encoding="utf-8")
    edit(root, "animation-plan.json", lambda data: data.update(schemaVersion=2, chartType="candlestick"))
    (root / "events.json").write_text(json.dumps({"selected": [{"title": "旧事件"}]}), encoding="utf-8")
    with pytest.raises(M2VError, match="migrate-line"):
        financial.load_project(root)
    backup = financial.migrate_line(root, duration=15)
    assert json.loads((backup / "prices.json").read_text(encoding="utf-8")) == old
    assert financial.load_project(root)["prices"] == original
    assert not (root / "events.json").exists()
    assert (backup / "events.json").exists()
    with pytest.raises(M2VError, match="计划已是 v8"):
        financial.migrate_line(root)


def test_v3_plan_migrates_without_changing_prices_and_discards_event_material(tmp_path):
    root = project(tmp_path)
    original_prices = (root / "prices.json").read_bytes()
    (root / "events.json").write_text("legacy event material", encoding="utf-8")
    (root / "outputs").mkdir()
    (root / "outputs" / "legibility-review.json").write_text("stale", encoding="utf-8")
    (root / "outputs" / "previews").mkdir()
    (root / "outputs" / "previews" / "preview-record.json").write_text("stale", encoding="utf-8")
    edit(root, "animation-plan.json", lambda plan: plan.update(schemaVersion=3, eventDisplays=[{"eventId": "e1", "frames": [100, 190]}]))

    backup = financial.migrate_line(root, duration=15)

    assert (root / "prices.json").read_bytes() == original_prices
    assert financial.load_project(root)["plan"]["schemaVersion"] == 8
    assert not (root / "events.json").exists()
    assert not (root / "outputs" / "legibility-review.json").exists()
    assert not (root / "outputs" / "previews" / "preview-record.json").exists()
    assert (backup / "events.json").exists()
    assert (backup / "animation-plan.json").exists()


def test_migration_rejects_bad_data_before_writing(tmp_path):
    root = project(tmp_path)
    edit(root, "prices.json", lambda data: data.update(schemaVersion=1))
    edit(root, "animation-plan.json", lambda data: data.update(schemaVersion=1))
    edit(root, "prices.json", lambda data: data["points"][0].update(close=0))
    originals = {name: (root / name).read_bytes() for name in financial.MATERIALS}
    with pytest.raises(M2VError, match="有限正数"):
        financial.migrate_line(root)
    assert {name: (root / name).read_bytes() for name in financial.MATERIALS} == originals


def test_plan_uses_short_holds_and_uniform_60_second_default():
    request = {"displayRange": ["1999-01-22", "2026-10-08"]}
    plan = financial.build_line_plan(request)
    assert plan["schemaVersion"] == 8
    assert plan["durationSeconds"] == 60
    assert plan["axis"]["dateScale"] == "staged-expanding"
    assert [segment["kind"] for segment in plan["segments"]] == ["opening", "advance", "ending"]
    assert [segment["frames"] for segment in plan["segments"]] == [[0, 30], [30, 1740], [1740, 1800]]
    assert "eventDisplays" not in plan
    dates = [financial.frame_date(plan, frame) for frame in range(1800)]
    assert dates == sorted(dates)
    assert dates[-1].isoformat() == "2026-10-08"
    with pytest.raises(M2VError, match="至少需要 4 秒"):
        financial.build_line_plan(request, duration=3)
    under_20 = financial.build_line_plan({"displayRange": ["2000-02-29", "2020-02-29"]})
    over_20 = financial.build_line_plan({"displayRange": ["2000-02-29", "2020-03-01"]})
    assert under_20["durationSeconds"] == 60
    assert [part["frames"] for part in under_20["segments"]] == [[0, 30], [30, 1740], [1740, 1800]]
    assert over_20["durationSeconds"] == 60
    assert [part["frames"] for part in over_20["segments"]] == [[0, 30], [30, 1740], [1740, 1800]]
    explicit = financial.build_line_plan(request, duration=90)
    assert explicit["durationSeconds"] == 90
    assert [part["frames"] for part in explicit["segments"]] == [[0, 30], [30, 2640], [2640, 2700]]
    four_seconds = financial.build_line_plan({"displayRange": ["2020-01-01", "2020-01-02"]}, duration=4)
    assert [part["frames"] for part in four_seconds["segments"]] == [[0, 30], [30, 60], [60, 120]]
    with pytest.raises(M2VError, match="至少需要 4 秒"):
        financial.build_line_plan(request, duration=3)
    single_day = financial.build_line_plan({"displayRange": ["2020-01-01", "2020-01-01"]}, duration=4)
    assert all(financial.frame_date(single_day, frame).isoformat() == "2020-01-01" for frame in range(120))


@pytest.mark.parametrize("values", [[100, 100, 100, 100], [100, 101, 400, 402], [400, 399, 100, 99]])
def test_monthly_pacing_is_monotone_bounded_and_weights_both_directions(values):
    request = {"displayRange": ["2020-01-01", "2020-03-01"], "investment": {"year": 2020, "principal": 100_000}}
    points = [{"date": day, "close": value} for day, value in zip(
        ["2020-01-01", "2020-01-31", "2020-02-02", "2020-03-01"], values)]
    plan = financial.build_line_plan(request, prices={"points": points})
    financial._validate_plan(plan, request, {"points": points})
    dates = [financial.frame_date(plan, frame) for frame in range(1800)]
    assert dates == sorted(dates)
    assert dates[30] == date(2020, 1, 1) and dates[1739] == date(2020, 3, 1)
    for frame in reversed(range(len(dates))):
        assert financial.frame_date(plan, frame) == dates[frame]
    anchors = plan["pacing"]["anchors"]
    if len(set(values)) == 1:
        assert len(anchors) == 2
    else:
        feb = anchors[1]
        assert feb["date"] == "2020-02-01"
        assert feb["frame"] - 30 < 1739 - feb["frame"]


def test_existing_v8_plan_keeps_its_saved_hold_durations(tmp_path):
    root = project(tmp_path)
    def use_previous_v8_timing(plan):
        plan["durationSeconds"] = 60
        plan["segments"] = [
            {"frames": [0, 90], "dates": ["2020-01-01", "2020-01-01"], "kind": "opening"},
            {"frames": [90, 1620], "dates": ["2020-01-01", "2020-01-03"], "kind": "advance"},
            {"frames": [1620, 1800], "dates": ["2020-01-03", "2020-01-03"], "kind": "ending"},
        ]
        plan["pacing"] = {"mode": "uniform", "anchors": [
            {"frame": 90, "date": "2020-01-01"}, {"frame": 1619, "date": "2020-01-03"},
        ]}
    edit(root, "animation-plan.json", use_previous_v8_timing)
    docs = financial.load_project(root)
    assert docs["plan"]["segments"][0]["frames"] == [0, 90]
    assert financial.review_metrics(docs)["endingSeconds"] == 6
    assert financial.review_metrics(docs)["safeArea"] == {"x": [140, 940], "y": [180, 1500]}
    assert financial.review_metrics(docs)["valueAxisSafeArea"] == financial.review_metrics(docs)["safeArea"]


def test_v7_compatibility_and_explicit_backup_upgrade(tmp_path):
    root = project(tmp_path)
    def legacy(plan):
        plan["schemaVersion"] = 7
        plan.pop("pacing")
        plan["segments"][0]["frames"] = [0, 90]
        plan["segments"][1]["frames"][0] = 90
        plan["segments"][1]["frames"][1] = 330
        plan["segments"][2]["frames"][0] = 330
    edit(root, "animation-plan.json", legacy)
    docs = financial.load_project(root)
    assert financial.review_metrics(docs)["endingSeconds"] == 4
    assert financial.frame_date(docs["plan"], 210) == date(2020, 1, 2)
    with pytest.raises(M2VError, match="显式"):
        financial.prepare_line_plan(root, 15)
    originals = {name: (root / name).read_bytes() for name in financial.MATERIALS}
    outputs = root / "outputs"
    outputs.mkdir(exist_ok=True)
    unified_records = ("prepared.json", "review.json", "preview-record.json")
    for name in unified_records:
        (outputs / name).write_bytes(b"old unified record")
    backup = financial.migrate_line(root, 15)
    assert all((backup / name).read_bytes() == content for name, content in originals.items())
    assert (root / "prices.json").read_bytes() == originals["prices.json"]
    for name in unified_records:
        assert (backup / "outputs" / name).read_bytes() == b"old unified record"
        assert not (outputs / name).exists()
    assert financial.review_metrics(financial.load_project(root))["endingSeconds"] == 2


@pytest.mark.parametrize("mutation", [
    lambda a: a[1].update(frame=a[0]["frame"]),
    lambda a: a[0].update(date="2019-12-31"),
    lambda a: a[-1].update(frame=1618),
    lambda a: a[-1].update(date="2020-01-01"),
    lambda a: a[0].update(frame=True),
])
def test_invalid_v8_anchors_are_rejected(mutation):
    request = {"displayRange": ["2020-01-01", "2020-03-01"]}
    plan = financial.build_line_plan(request)
    mutation(plan["pacing"]["anchors"])
    with pytest.raises(M2VError, match="anchors"):
        financial._validate_plan(plan, request, {"points": []})


def test_short_many_months_and_single_point_pacing():
    request = {"displayRange": ["1999-01-22", "2026-10-08"]}
    points = [{"date": f"{year}-02-01", "close": year - 1998} for year in range(1999, 2027)]
    plan = financial.build_line_plan(request, 10, {"points": points})
    financial._validate_plan(plan, request, {"points": points})
    assert len(plan["pacing"]["anchors"]) <= 210
    assert financial.frame_date(plan, 239) == date(2026, 10, 8)
    single = financial.build_line_plan({"displayRange": ["2020-01-01", "2020-01-02"]}, 10,
                                       {"points": [{"date": "2020-01-02", "close": 100}]})
    assert len(single["pacing"]["anchors"]) == 2


def preview_fixture(root, docs):
    folder = root / "outputs" / "previews"
    folder.mkdir(parents=True)
    video = folder / "test.mp4"
    video.write_bytes(b"synthetic preview fixture")
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    (folder / "preview-record.json").write_text(json.dumps({
        "path": "outputs/previews/test.mp4", "sha256": digest,
        "frames": docs["plan"]["durationSeconds"] * 30,
        "materialsAndAssetsSha256": financial.legibility_review_digest(root),
    }), encoding="utf-8")
    return digest


def test_full_video_review_gate_binds_inputs_preview_and_evidence(tmp_path):
    root = project(tmp_path)
    docs = financial.load_project(root)
    with pytest.raises(M2VError, match="需要当前完整视频"):
        financial.validate_legibility_review(root, docs)
    preview_digest = preview_fixture(root, docs)
    assert financial_video.main(["review-template", "--project-dir", str(root)]) == 0
    path = root / "outputs" / "legibility-review.json"
    review = json.loads(path.read_text(encoding="utf-8"))
    assert review["metrics"]["safeArea"] == {"x": [140, 940], "y": [180, 1500]}
    assert review["evidence"]["valueAxisSafeArea"]["bounds"] == {"x": [140, 940], "y": [180, 1500]}
    with pytest.raises(M2VError, match="只接受完整视频评审通过"):
        financial.validate_legibility_review(root, docs)
    review.update(result="pass", fullVideo=True, sampleTimecodes=["00:00:03"],
        checks={key: True for key in financial.REVIEW_CHECKS}, evidence={**{key: "合成证据" for key in financial.REVIEW_CHECKS},
            "mobileScale": {"width": 360, "height": 640, "reviewed": True, "details": "合成缩放证据"},
            "safeArea": {"bounds": {"x": [140, 940], "y": [180, 1500]}, "reviewed": True, "details": "合成安全区证据"},
            "valueAxisSafeArea": {"bounds": {"x": [140, 940], "y": [180, 1500]}, "reviewed": True, "details": "纵轴统一安全区证据"}})
    assert review["previewSha256"] == preview_digest
    path.write_text(json.dumps({**review, "metrics": {"durationSeconds": 60, "endingSeconds": 4}}), encoding="utf-8")
    with pytest.raises(M2VError, match="review.json.metrics"):
        financial.validate_legibility_review(root, docs)
    missing_mobile = json.loads(json.dumps(review))
    missing_mobile["evidence"]["mobileScale"].update(reviewed=False, details="")
    path.write_text(json.dumps(missing_mobile), encoding="utf-8")
    with pytest.raises(M2VError, match="evidence.mobileScale"):
        financial.validate_legibility_review(root, docs)
    path.write_text(json.dumps(review), encoding="utf-8")
    financial.validate_legibility_review(root, docs)
    (root / "outputs/previews/test.mp4").write_bytes(b"changed preview")
    with pytest.raises(M2VError, match="摘要不一致"):
        financial.validate_legibility_review(root, docs)
    path.write_text(json.dumps({**review, "materialsAndAssetsSha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(M2VError, match="已过期"):
        financial.validate_legibility_review(root, docs)


def test_plan_validates_data_before_overwriting_and_rejects_legacy(tmp_path):
    root = project(tmp_path)
    old = (root / "animation-plan.json").read_bytes()
    edit(root, "prices.json", lambda data: data["points"].pop())
    assert financial_video.main(["plan", "--project-dir", str(root)]) == 2
    assert (root / "animation-plan.json").read_bytes() == old
    with pytest.raises(SystemExit):
        financial_video.main(["plan", "--project-dir", str(root), "--period", "year"])


def test_migration_rolls_back_if_post_write_validation_fails(tmp_path, monkeypatch):
    root = project(tmp_path)
    edit(root, "prices.json", lambda data: data.update(schemaVersion=1))
    edit(root, "animation-plan.json", lambda data: data.update(schemaVersion=1))
    legacy_events = b'{"selected":[]}'
    legacy_review = b'{"result":"pass"}'
    (root / "events.json").write_bytes(legacy_events)
    (root / "outputs").mkdir()
    (root / "outputs" / "legibility-review.json").write_bytes(legacy_review)
    originals = {name: (root / name).read_bytes() for name in financial.MATERIALS}

    def reject(_root):
        raise M2VError("合成写入后故障")

    monkeypatch.setattr(financial, "load_project", reject)
    with pytest.raises(M2VError, match="写入后故障"):
        financial.migrate_line(root, duration=15)
    assert {name: (root / name).read_bytes() for name in financial.MATERIALS} == originals
    assert (root / "events.json").read_bytes() == legacy_events
    assert (root / "outputs" / "legibility-review.json").read_bytes() == legacy_review


def test_close_only_legacy_migration_and_mixed_versions(tmp_path):
    root = project(tmp_path)
    edit(root, "prices.json", lambda data: data.update(schemaVersion=1))
    with pytest.raises(M2VError, match="需要 v3 价格和 v7/v8 动画计划"):
        financial.load_project(root)
    edit(root, "animation-plan.json", lambda data: data.update(schemaVersion=1))
    backup = financial.migrate_line(root, duration=15)
    assert backup.is_dir()
    assert financial.load_project(root)["plan"]["schemaVersion"] == 8


def test_short_or_asset_stale_preview_cannot_supply_review(tmp_path, monkeypatch):
    import m2v.engine.remotion as remotion

    root = project(tmp_path)
    docs = financial.load_project(root)
    preview_fixture(root, docs)
    path = root / "outputs/previews/preview-record.json"
    edit_record = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**edit_record, "frames": 2}), encoding="utf-8")
    with pytest.raises(M2VError, match="完整时长"):
        financial.load_preview_record(root, docs)
    path.write_text(json.dumps(edit_record), encoding="utf-8")
    monkeypatch.setattr(remotion, "build_inputs", lambda **kwargs: [])
    with pytest.raises(M2VError, match="资产已变化"):
        financial.load_preview_record(root, docs)


def test_preview_cannot_overwrite_a_final_video(tmp_path):
    root = project(tmp_path)
    docs = financial.load_project(root)
    destination = root / "outputs/old-final.mp4"
    destination.parent.mkdir()
    destination.write_bytes(b"original final")
    with pytest.raises(M2VError, match="不能覆盖正式成片"):
        financial_render.render(root, docs, output=destination, preview=True)
    assert destination.read_bytes() == b"original final"


def test_preview_with_explicit_out_does_not_replace_the_recorded_preview(tmp_path, monkeypatch):
    """复核用的旁路预演 `--out` 不得顶掉已登记的完整预演，否则评审会静默失效。"""
    from types import SimpleNamespace

    import m2v.engine.remotion as remotion
    import m2v.engine.output_validation as output_validation

    root = project(tmp_path)
    docs = financial.load_project(root)
    preview_fixture(root, docs)
    record_path = root / "outputs/previews/preview-record.json"
    recorded = record_path.read_bytes()
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    monkeypatch.setattr(remotion, "web_dir", lambda: tmp_path)
    monkeypatch.setattr(remotion, "require_environment", lambda web: None)
    monkeypatch.setattr(remotion, "bundle", lambda **kwargs: SimpleNamespace(path=bundle, build_seconds=0.0,
        cache_seconds=0.0, cache_status="hit", cache_key="test", cache_detail="test"))
    monkeypatch.setattr(financial_render, "_assert_no_audio", lambda video: None)
    monkeypatch.setattr(output_validation, "verify_output", lambda *args, **kwargs: None)
    def fake_session(**kwargs):
        render = kwargs["on_metadata"](SimpleNamespace(fps=30, width=1080, height=1920,
            duration_in_frames=docs["plan"]["durationSeconds"] * 30))
        Path(render["out"]).write_bytes(b"bypass preview")
        return {"readySeconds": 0.01}
    monkeypatch.setattr(remotion, "render_session", fake_session)

    output = financial_render.render(
        root, docs, preview=True, limit_frames=2, preset="ultrafast",
        output=root / "outputs/previews/verify-current-code.mp4",
    )
    assert output.read_bytes() == b"bypass preview"
    assert record_path.read_bytes() == recorded, "旁路预演不得改写已登记的预演记录"
    assert financial.load_preview_record(root, docs)["path"] == "outputs/previews/test.mp4"


@pytest.mark.parametrize("preview", [False, True])
def test_delivered_video_gets_inherited_access_after_being_moved(tmp_path, monkeypatch, preview):
    """交付文件必须重新继承父目录权限，且修复要在搬运之后、预演也一样。

    中转临时目录的 ACL 是刻意收紧的（只有 SYSTEM/Administrators/OWNER RIGHTS）。
    若在 temp 里就修复，`/reset` 只是把那份限制性 ACL 再套一遍；搬运后再 `/reset`
    才会继承 outputs 目录的可访问权限，否则标准权限播放器报 0x80070005。
    """
    from types import SimpleNamespace

    import m2v.engine.remotion as remotion
    import m2v.engine.output_validation as output_validation
    import m2v.core.security as security

    root = project(tmp_path)
    docs = financial.load_project(root)
    if not preview:
        monkeypatch.setattr(financial, "validate_legibility_review", lambda *args, **kwargs: None)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    monkeypatch.setattr(remotion, "web_dir", lambda: tmp_path)
    monkeypatch.setattr(remotion, "require_environment", lambda web: None)
    monkeypatch.setattr(remotion, "bundle", lambda **kwargs: SimpleNamespace(path=bundle, build_seconds=0.0,
        cache_seconds=0.0, cache_status="hit", cache_key="test", cache_detail="test"))
    monkeypatch.setattr(financial_render, "_assert_no_audio", lambda video: None)
    monkeypatch.setattr(output_validation, "verify_output", lambda *args, **kwargs: None)
    def fake_session(**kwargs):
        render = kwargs["on_metadata"](SimpleNamespace(fps=30, width=1080, height=1920,
            duration_in_frames=docs["plan"]["durationSeconds"] * 30))
        Path(render["out"]).write_bytes(b"video")
        return {"readySeconds": 0.01}
    monkeypatch.setattr(remotion, "render_session", fake_session)

    granted: list[Path] = []
    monkeypatch.setattr(security, "grant_inherited_access",
                        lambda path: granted.append(Path(path)) or True)

    output = financial_render.render(
        root, docs, preview=preview, limit_frames=2 if preview else None, preset="ultrafast",
    )
    assert output.is_file()
    assert granted == [output], f"应只对最终落地的文件授予一次访问权限，实际 {granted}"
    assert granted[0].parent in (root / "outputs", root / "outputs/previews")


def test_init_creates_content_templates_for_a_stock_or_index(tmp_path, capsys):
    stock = tmp_path / "stock"
    assert financial_video.main([
        "init", "--out-dir", str(stock), "--kind", "stock", "--name", "合成公司",
        "--code", "SYN", "--display-name", "短名称", "--market", "TEST", "--unit", "USD", "--listing-date", "2010-01-01",
        "--start-date", "2020-01-01", "--end-date", "2020-12-31",
    ]) == 0
    assert all((stock / name).is_file() for name in financial.MATERIALS)
    stock_request = json.loads((stock / "request.json").read_text(encoding="utf-8"))
    assert stock_request["instrument"]["displayName"] == "短名称"
    assert stock_request["instrument"]["name"] == "合成公司"
    assert stock_request["instrument"]["code"] == "SYN"
    assert stock_request["investment"] == {"year": 2020, "principal": 100_000}
    stock_plan = json.loads((stock / "animation-plan.json").read_text(encoding="utf-8"))
    assert stock_plan["schemaVersion"] == 8 and stock_plan["canvas"] == {"width": 1080, "height": 1920}
    assert not (stock / "events.json").exists()
    index = tmp_path / "index"
    assert financial_video.main([
        "init", "--out-dir", str(index), "--kind", "index", "--name", "合成指数",
        "--code", "IDX", "--market", "TEST", "--unit", "points", "--index-start-date", "2010-01-01",
        "--start-date", "2020-01-01", "--end-date", "2020-12-31",
    ]) == 0
    index_request = json.loads((index / "request.json").read_text(encoding="utf-8"))
    assert index_request["instrument"]["indexStartDate"] == "2010-01-01"
    assert index_request["investment"] == {"year": 2020, "principal": 100_000}
    assert not (index / "events.json").exists()
    assert "初始化" in capsys.readouterr().out


def test_init_rejects_blank_display_name_without_creating_materials(tmp_path, capsys):
    output = tmp_path / "blank-name"
    assert financial_video.main([
        "init", "--out-dir", str(output), "--kind", "stock", "--name", "公司", "--code", "ABC",
        "--display-name", "  ", "--market", "TEST", "--unit", "USD", "--listing-date", "2010-01-01",
        "--start-date", "2020-01-01", "--end-date", "2020-12-31",
    ]) == 2
    assert "--display-name 不能为空" in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.slow
@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "web" / "node_modules").is_dir()
    or not shutil.which("node") or not shutil.which("npx"),
    reason="Remotion 前端依赖或 Node 未安装，无法执行金融视频端到端渲染",
)
def test_financial_preview_renders_widescreen_mp4_without_audio(tmp_path):
    root = project(tmp_path)
    docs = financial.load_project(root)
    output = financial_render.render(root, docs, preview=True, limit_frames=2, preset="ultrafast")
    assert output.is_file() and output.stat().st_size > 0


def test_v4_plan_requires_explicit_migration_with_complete_backup(tmp_path):
    root = project(tmp_path)
    edit(root, "animation-plan.json", lambda data: data.update(schemaVersion=4))
    original = {name: (root / name).read_bytes() for name in financial.MATERIALS}
    with pytest.raises(M2VError, match="migrate-line"):
        financial.load_project(root)
    assert financial_video.main(["plan", "--project-dir", str(root)]) == 2
    assert (root / "animation-plan.json").read_bytes() == original["animation-plan.json"]
    final = root / "outputs" / "existing.mp4"
    final.parent.mkdir()
    final.write_bytes(b"existing final")
    backup = financial.migrate_line(root)
    assert {name: (backup / name).read_bytes() for name in financial.MATERIALS} == original
    assert final.read_bytes() == b"existing final"
    assert financial.load_project(root)["plan"]["schemaVersion"] == 8


def test_v5_plan_migrates_explicitly_and_preserves_existing_video(tmp_path):
    root = project(tmp_path)
    edit(root, "animation-plan.json", lambda plan: plan.update(schemaVersion=5, axis={**plan["axis"], "dateScale": "full-range"}))
    existing = root / "outputs" / "financial-line.mp4"
    existing.parent.mkdir()
    existing.write_bytes(b"existing user video")
    review = root / "outputs" / "legibility-review.json"
    review.write_text('{"result":"pass"}', encoding="utf-8")

    with pytest.raises(M2VError, match="需要 v3 价格和 v7/v8 动画计划"):
        financial.load_project(root)
    backup = financial.migrate_line(root, duration=15)

    assert json.loads((backup / "animation-plan.json").read_text(encoding="utf-8"))["schemaVersion"] == 5
    assert financial.load_project(root)["plan"]["schemaVersion"] == 8
    assert financial.load_project(root)["plan"]["axis"]["dateScale"] == "staged-expanding"
    assert existing.read_bytes() == b"existing user video"
    assert not review.exists()


@pytest.mark.parametrize("option", ["--window-months", "--window-months=12"])
def test_removed_window_argument_explains_staged_axis(option, capsys):
    with pytest.raises(SystemExit):
        financial_video.main(["plan", "--project-dir", "unused", option])
    assert "横轴按阶段扩展至完整日期范围" in capsys.readouterr().err
