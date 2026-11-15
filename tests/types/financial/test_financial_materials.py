"""金融材料与估值：请求、价格、crypto 汇率与快照留证的校验。"""
from __future__ import annotations

import json
from datetime import date

import pytest

from m2v.types.financial import financial, materials
from m2v.core.errors import M2VError
from m2v.types.financial.valuation import crypto_investment_values
from helpers.financial import crypto_project, edit, project



def test_crypto_cny_valuation_uses_buy_day_fx_and_carries_weekend_rate():
    request = {"investment": {"date": "2020-01-04", "principal": 100_000}}
    prices = {
        "points": [
            {"date": "2020-01-04", "close": 10},
            {"date": "2020-01-05", "close": 20},
            {"date": "2020-01-06", "close": 20},
        ],
        "fx": {"points": [
            {"date": "2020-01-03", "close": 7.0},
            {"date": "2020-01-06", "close": 7.2},
        ]},
    }
    values = crypto_investment_values(request, prices)
    assert values[0]["close"] == 100_000
    assert values[1]["close"] == 200_000
    assert values[2]["close"] == pytest.approx(205_714.285714)




def test_crypto_valuation_rejects_missing_buy_day_or_prior_fx():
    request = {"investment": {"date": "2020-01-04", "principal": 100_000}}
    with pytest.raises(M2VError, match="BTC/USD"):
        crypto_investment_values(request, {"points": [{"date": "2020-01-03", "close": 10}], "fx": {"points": []}})
    with pytest.raises(M2VError, match="USD/CNY"):
        crypto_investment_values(request, {"points": [{"date": "2020-01-04", "close": 10}], "fx": {"points": []}})




def test_crypto_material_v4_validates_daily_coverage_and_fx_snapshots(tmp_path):
    root = crypto_project(tmp_path)
    docs = financial.load_project(root)
    assert len(docs["prices"]["points"]) == 4
    assert docs["prices"]["fx"]["points"][0]["date"] == "2020-01-03"




@pytest.mark.parametrize("value", ["", "   ", "x" * 181, 123])
def test_crypto_material_rejects_invalid_legal_status_notice(tmp_path, value):
    root = crypto_project(tmp_path)
    edit(root, "request.json", lambda data: data["investment"].update(legalStatusNotice=value))
    with pytest.raises(M2VError, match="legalStatusNotice"):
        financial.load_project(root)




def test_stock_material_rejects_crypto_legal_status_notice(tmp_path):
    root = project(tmp_path)
    edit(root, "request.json", lambda data: data["investment"].update(legalStatusNotice="crypto only"))
    with pytest.raises(M2VError, match="仅 crypto"):
        financial.load_project(root)




@pytest.mark.parametrize(
    ("file", "mutate", "message"),
    [
        ("prices.json", lambda data: data["points"].pop(2), "逐日覆盖"),
        ("prices.json", lambda data: data["fx"]["rawSnapshots"][0].update(sha256="0" * 64), "摘要不匹配"),
        ("prices.json", lambda data: data["fx"]["points"].append({"date": "2020-01-07", "close": 7.2}) or data["fx"]["expectedTradingDates"].append("2020-01-07"), "不得使用未来汇率"),
    ],
)
def test_crypto_material_v4_rejects_gaps_bad_snapshots_and_future_fx(tmp_path, file, mutate, message):
    root = crypto_project(tmp_path)
    edit(root, file, mutate)
    with pytest.raises(M2VError, match=message):
        financial.load_project(root)




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




@pytest.mark.parametrize("design", [
    None,
    {},
    {"profile": "ledger"},
    {"profile": "signal", "accent": "#A8B0BD", "titleMode": "subject", "personality": "corporate"},
    {"profile": "archive", "accent": "#6F8CA8", "titleMode": "premise", "personality": "calm"},
])
def test_accepts_optional_design_profile(tmp_path, design):
    root = project(tmp_path)
    edit(root, "request.json", lambda data: data.update(design=design))
    docs = financial.load_project(root)
    assert docs["request"].get("design") == design
    assert financial.build_render_props(docs)["request"].get("design") == design


@pytest.mark.parametrize(
    ("design", "message"),
    [
        ({"profile": "unknown"}, "design.profile"),
        ({"profile": []}, "design.profile"),
        ({"titleMode": {}}, "design.titleMode"),
        ({"personality": 1}, "design.personality"),
        ({"accent": "#FFF"}, "design.accent"),
        ({"accent": "#GGGGGG"}, "design.accent"),
        ({"accent": "#FF5A4E"}, "design.accent"),
        ({"accent": "#4bd39a"}, "design.accent"),
        ({"acccent": "#A8B0BD"}, "未知字段"),
    ],
)
def test_rejects_invalid_design_profile(tmp_path, design, message):
    root = project(tmp_path)
    edit(root, "request.json", lambda data: data.update(design=design))
    with pytest.raises(M2VError, match=message):
        financial.load_project(root)


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
    materials._validate_request(request)




def test_future_display_dates_are_rejected(tmp_path):
    root = project(tmp_path)
    request = json.loads((root / "request.json").read_text(encoding="utf-8"))
    future = date(date.today().year + 1, 1, 1).isoformat()
    request["requestedRange"] = ["2020-01-01", future]
    request["displayRange"] = ["2020-01-01", future]
    request["confirmations"] = ["合成确认"]
    with pytest.raises(M2VError, match="未来日期"):
        materials._validate_request(request)




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
