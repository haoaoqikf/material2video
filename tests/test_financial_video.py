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
