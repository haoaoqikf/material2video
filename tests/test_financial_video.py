"""Financial time-series materials, integrity rules, and frame mapping."""
from __future__ import annotations

import json
import hashlib
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents" / "skills" / "article2video" / "scripts"))

from a2v import financial  # noqa: E402
from a2v import financial_render  # noqa: E402
from a2v.errors import A2VError  # noqa: E402
import financial_video  # noqa: E402


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
        },
        "prices.json": {
            "schemaVersion": 1, "unit": "USD", "priceBasis": "split-adjusted", "adjustmentBaseDate": "2020-01-03",
            "adjustmentDefinition": "仅拆合股调整，不计分红再投资；合成数据",
            "splitAdjustments": [], "expectedTradingDates": ["2020-01-02", "2020-01-03"],
            "expectedTradingDatesSource": ["https://example.invalid/calendar"],
            "points": [{"date": "2020-01-02", "close": 100.0}, {"date": "2020-01-03", "close": 102.0}],
            "sources": [{"url": "https://example.invalid/prices", "fetchedAt": "2026-10-05T00:00:00Z", "coverage": ["2020-01-01", "2020-12-31"], "adjustmentDefinition": "合成来源口径"}],
            "rawSnapshots": [{"path": "raw-prices.csv", "sha256": hashlib.sha256(raw_snapshot).hexdigest(), "sourceUrl": "https://example.invalid/prices"}],
        },
        "events.json": {
            "schemaVersion": 1,
            "candidates": [{"id": "e1", "date": "2020-01-02", "dateBasis": "announced", "title": "合成公告", "sources": ["https://example.invalid/event"], "reason": "合成资料"}],
            "selected": [{"id": "e1", "date": "2020-01-02", "dateBasis": "announced", "title": "合成公告", "sources": ["https://example.invalid/event"], "reason": "合成资料"}], "excluded": [],
        },
        "animation-plan.json": {
            "schemaVersion": 1, "durationSeconds": 6, "fps": 30, "canvas": {"width": 1920, "height": 1080},
            "axis": {"dateRange": ["2020-01-01", "2020-01-03"], "visibleWindowMonths": 3, "valueScale": "rolling-linear"},
            "segments": [
                {"frames": [0, 15], "dates": ["2020-01-01", "2020-01-01"], "kind": "opening"},
                {"frames": [15, 90], "dates": ["2020-01-01", "2020-01-03"], "kind": "advance"},
                {"frames": [90, 180], "dates": ["2020-01-03", "2020-01-03"], "kind": "ending"},
            ],
            "eventDisplays": [{"eventId": "e1", "frames": [53, 70]}], "rationale": "合成测试编排",
        },
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
    assert financial.frame_date(docs["plan"], 52).isoformat() == "2020-01-02"
    assert financial.frame_date(docs["plan"], 179).isoformat() == "2020-01-03"


@pytest.mark.parametrize(
    ("file", "mutate", "message"),
    [
        ("prices.json", lambda d: d.update(priceBasis="total-return"), "priceBasis"),
        ("prices.json", lambda d: d["points"].pop(), "完全一致"),
        ("prices.json", lambda d: d["points"][1].update(close=float("nan")), "有限正数"),
        ("events.json", lambda d: (d["selected"][0].update(date="2019-12-31"), d["candidates"][0].update(date="2019-12-31")), "展示范围"),
        ("animation-plan.json", lambda d: d["segments"][1].update(frames=[14, 90]), "连续"),
        ("events.json", lambda d: (d["selected"][0].update(date="2020-01-03"), d["candidates"][0].update(date="2020-01-03")), "早于事件"),
        ("animation-plan.json", lambda d: d.update(canvas={"width": 1080, "height": 1920}), "1920"),
        ("animation-plan.json", lambda d: d["axis"].pop("visibleWindowMonths"), "visibleWindowMonths"),
        ("animation-plan.json", lambda d: d["axis"].update(visibleWindowMonths=0), "1 到 1200"),
        ("animation-plan.json", lambda d: d["axis"].update(visibleWindowMonths=True), "1 到 1200"),
        ("animation-plan.json", lambda d: d["axis"].update(valueScale="fixed"), "rolling-linear"),
        ("animation-plan.json", lambda d: d["axis"].update(valueRange=[0, 250]), "不接受固定 valueRange"),
    ],
)
def test_rejects_invalid_financial_materials(tmp_path, file, mutate, message):
    root = project(tmp_path)
    edit(root, file, mutate)
    with pytest.raises(A2VError, match=message):
        financial.load_project(root)


def test_stock_range_before_listing_requires_a_confirmed_shorter_range(tmp_path):
    root = project(tmp_path)
    edit(root, "request.json", lambda d: d["instrument"].update(listingDate="2021-01-01"))
    with pytest.raises(A2VError, match="上市日期之前"):
        financial.load_project(root)


def test_full_year_request_can_be_confirmed_to_actual_dates(tmp_path):
    root = project(tmp_path)
    today = date.today().isoformat()
    request = json.loads((root / "request.json").read_text(encoding="utf-8"))
    request["requestedRange"] = [f"{date.today().year}-01-01", f"{date.today().year}-12-31"]
    request["displayRange"] = [f"{date.today().year}-01-01", today]
    request["confirmations"] = ["用户确认使用截至当前日期的实际行情范围"]
    financial._validate_request(request)


def test_future_display_dates_are_rejected(tmp_path):
    root = project(tmp_path)
    request = json.loads((root / "request.json").read_text(encoding="utf-8"))
    future = date(date.today().year + 1, 1, 1).isoformat()
    request["requestedRange"] = ["2020-01-01", future]
    request["displayRange"] = ["2020-01-01", future]
    request["confirmations"] = ["合成确认"]
    with pytest.raises(A2VError, match="未来日期"):
        financial._validate_request(request)


def test_out_of_order_selected_events_are_rejected(tmp_path):
    root = project(tmp_path)
    edit(root, "events.json", lambda d: (d["selected"].append({**d["selected"][0], "id": "e2"}), d["candidates"].append({**d["candidates"][0], "id": "e2"})))
    edit(root, "animation-plan.json", lambda d: d["eventDisplays"].append({"eventId": "e2", "frames": [69, 80]}))
    with pytest.raises(A2VError, match="不得重叠"):
        financial.load_project(root)


def test_zero_reliable_events_is_valid(tmp_path):
    root = project(tmp_path)
    edit(root, "events.json", lambda d: d.update(candidates=[], selected=[], excluded=[]))
    edit(root, "animation-plan.json", lambda d: d.update(eventDisplays=[]))
    assert financial.load_project(root)["events"]["selected"] == []


def test_more_than_eight_selected_events_are_rejected(tmp_path):
    root = project(tmp_path)
    def add_events(data):
        template = data["candidates"][0]
        data["candidates"] = [{**template, "id": f"e{i}"} for i in range(9)]
        data["selected"] = [{**event} for event in data["candidates"]]
    edit(root, "events.json", add_events)
    with pytest.raises(A2VError, match="最多八个"):
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
    with pytest.raises(A2VError, match="摘要不匹配"):
        financial.load_project(root)
    edit(root, "prices.json", lambda d: d["rawSnapshots"][0].update(path="../outside.csv"))
    with pytest.raises(A2VError, match="相对路径"):
        financial.load_project(root)


def test_v2_ohlc_requires_valid_order_and_matching_plan_version(tmp_path):
    root = project(tmp_path)
    raw = b"synthetic OHLC fixture"
    (root / "raw-prices.csv").write_bytes(raw)
    def make_v2(data):
        data.update(schemaVersion=2, points=[
            {"date": "2020-01-02", "open": 99, "high": 101, "low": 98, "close": 100},
            {"date": "2020-01-03", "open": 100, "high": 103, "low": 99, "close": 102},
        ], rawSnapshots=[{"path": "raw-prices.csv", "sha256": hashlib.sha256(raw).hexdigest(), "sourceUrl": "https://example.invalid/prices"}])
    edit(root, "prices.json", make_v2)
    with pytest.raises(A2VError, match="版本必须一致"):
        financial.load_project(root)
    edit(root, "animation-plan.json", lambda data: data.update(schemaVersion=2))
    with pytest.raises(A2VError, match="OHLC 顺序无效"):
        edit(root, "prices.json", lambda data: data["points"][0].update(high=90))
        financial.load_project(root)


def test_nvidia_ohlc_material_selects_yearly_period_at_60_seconds():
    from datetime import date, timedelta
    points = []
    day = date(1999, 1, 22)
    while day <= date(2026, 10, 8):
        if day.weekday() < 5:
            value = 1.0 + (day - date(1999, 1, 22)).days / 100
            points.append({"date": day.isoformat(), "open": value, "high": value + 0.2, "low": value - 0.2, "close": value + 0.1})
        day += timedelta(days=1)
    stats = financial.candle_period_stats(points, ["1999-01-22", "2026-10-08"], 60, 8)
    assert stats["month"]["count"] > 300 and not stats["month"]["eligible"]
    assert stats["year"]["count"] == 28 and stats["year"]["eligible"]
    request = {"displayRange": ["1999-01-22", "2026-10-08"], "instrument": {"kind": "stock"}}
    event_list = {"selected": [{"id": str(i), "date": d} for i, d in enumerate([
        "1999-01-22", "1999-10-11", "2007-02-16", "2020-04-27", "2023-05-24", "2024-06-10", "2025-02-26", "2026-08-26"])]}
    plan = financial.build_candle_plan(request, {"points": points}, event_list)
    assert plan["selectedPeriod"] == "year"
    assert plan["durationSeconds"] == 60
    assert plan["selectionReport"]["choiceMode"] == "automatic"
    assert len(plan["segments"]) == 18
    assert max(segment["readability"]["revealedBarsPerSecond"] for segment in plan["segments"] if segment["kind"] == "advance") <= 4
    explicit = financial.build_candle_plan(request, {"points": points}, event_list, duration=60, selected_period="year")
    assert explicit["selectionReport"]["choiceMode"] == "explicit"
    assert explicit["selectionReport"]["requestedPeriod"] == "year"
    with pytest.raises(A2VError, match="指定 month K"):
        financial.build_candle_plan(request, {"points": points}, event_list, duration=60, selected_period="month")


def test_ohlc_aggregation_tracks_calendar_boundaries_and_review_gate(tmp_path):
    points = [
        {"date": "2020-12-31", "open": 10, "high": 12, "low": 9, "close": 11},
        {"date": "2021-01-01", "open": 11, "high": 14, "low": 10, "close": 13},
        {"date": "2021-01-04", "open": 13, "high": 15, "low": 12, "close": 14},
    ]
    weekly = financial.aggregate_ohlc(points, "week")
    assert weekly[0]["key"] == "2020-W53"
    assert weekly[0]["firstTradingDate"] == "2020-12-31"
    assert weekly[0]["lastTradingDate"] == "2021-01-01"
    assert (weekly[0]["open"], weekly[0]["high"], weekly[0]["low"], weekly[0]["close"]) == (10, 14, 9, 13)
    assert len(financial.aggregate_ohlc(points, "year")) == 2

    root = project(tmp_path)
    docs = financial.load_project(root)
    docs["plan"] = {"schemaVersion": 2, "selectionReport": {"selectedPeriod": "year", "maxBarsPerSecond": 1,
        "candidates": {"year": {"minCenterSpacingPx": 57.5, "windowReplacementSeconds": 20}}}}
    with pytest.raises(A2VError, match="需要当前完整视频"):
        financial.validate_legibility_review(root, docs)
    review_path = root / "outputs" / "legibility-review.json"
    review_path.parent.mkdir()
    review = {"schemaVersion": 1, "materialsAndAssetsSha256": financial.legibility_review_digest(root),
        "result": "pass", "fullVideo": True, "sampleTimecodes": ["00:00:10"],
        "metrics": {"maxBarsPerSecond": 1, "minCenterSpacingPx": 57.5, "windowReplacementSeconds": 20},
        "checks": {"labelsReadable": True, "scrollTrackable": True, "axisStable": True, "eventsDoNotOverlap": True}}
    review_path.write_text(json.dumps(review), encoding="utf-8")
    financial.validate_legibility_review(root, docs)
    failed_review = {**review, "result": "fail"}
    review_path.write_text(json.dumps(failed_review), encoding="utf-8")
    with pytest.raises(A2VError, match="只接受完整视频评审通过"):
        financial.validate_legibility_review(root, docs)
    review_path.write_text(json.dumps({**review, "materialsAndAssetsSha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(A2VError, match="已过期"):
        financial.validate_legibility_review(root, docs)


def test_init_creates_content_templates_for_a_stock_or_index(tmp_path, capsys):
    stock = tmp_path / "stock"
    assert financial_video.main([
        "init", "--out-dir", str(stock), "--kind", "stock", "--name", "合成公司",
        "--code", "SYN", "--market", "TEST", "--unit", "USD", "--listing-date", "2010-01-01",
        "--start-date", "2020-01-01", "--end-date", "2020-12-31",
    ]) == 0
    assert all((stock / name).is_file() for name in financial.MATERIALS)
    index = tmp_path / "index"
    assert financial_video.main([
        "init", "--out-dir", str(index), "--kind", "index", "--name", "合成指数",
        "--code", "IDX", "--market", "TEST", "--unit", "points", "--index-start-date", "2010-01-01",
        "--start-date", "2020-01-01", "--end-date", "2020-12-31",
    ]) == 0
    assert json.loads((index / "request.json").read_text(encoding="utf-8"))["instrument"]["indexStartDate"] == "2010-01-01"
    assert "初始化" in capsys.readouterr().out


@pytest.mark.slow
@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "web" / "node_modules").is_dir()
    or not shutil.which("node") or not shutil.which("npx"),
    reason="Remotion 前端依赖或 Node 未安装，无法执行金融视频端到端渲染",
)
def test_financial_preview_renders_widescreen_mp4_without_audio(tmp_path):
    root = project(tmp_path)
    docs = financial.load_project(root)
    output = financial_render.render(root, docs, limit_frames=2, preset="ultrafast")
    assert output.is_file() and output.stat().st_size > 0
