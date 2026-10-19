"""金融测试的共享夹具：作品目录、材料改写与预演替身。"""
from __future__ import annotations

import json
import hashlib
from datetime import date
from pathlib import Path
from m2v.types.financial import financial



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




def crypto_project(tmp_path: Path) -> Path:
    root = tmp_path / "crypto"
    root.mkdir()
    btc_raw = b"date,close\n2020-01-03,10\n2020-01-04,11\n2020-01-05,12\n2020-01-06,13\n"
    fx_raw = b"date,close\n2020-01-03,7.0\n2020-01-06,7.2\n"
    (root / "raw-btc.csv").write_bytes(btc_raw)
    (root / "raw-fx.csv").write_bytes(fx_raw)
    btc_url, fx_url = "https://example.invalid/btc", "https://example.invalid/fx"
    source = lambda url: {"url": url, "fetchedAt": "2026-10-05T00:00:00Z", "coverage": ["2020-01-03", "2020-01-06"], "adjustmentDefinition": "合成日线来源"}
    request = {"schemaVersion": 1, "originalRequest": "crypto CNY 测试", "instrument": {"kind": "crypto", "name": "Bitcoin", "code": "BTC-USD", "market": "TEST", "unit": "USD"},
        "requestedRange": ["2020-01-03", "2020-01-06"], "displayRange": ["2020-01-03", "2020-01-06"],
        "investment": {"date": "2020-01-04", "principal": 100_000, "currency": "CNY"}, "confirmations": []}
    prices_dates = ["2020-01-03", "2020-01-04", "2020-01-05", "2020-01-06"]
    prices = {"schemaVersion": 4, "unit": "USD", "priceBasis": "crypto-spot-close", "expectedTradingDates": prices_dates,
        "expectedTradingDatesSource": [btc_url], "points": [{"date": day, "close": close} for day, close in zip(prices_dates, [10, 11, 12, 13])],
        "sources": [source(btc_url)], "rawSnapshots": [{"path": "raw-btc.csv", "sha256": hashlib.sha256(btc_raw).hexdigest(), "sourceUrl": btc_url}],
        "fx": {"pair": "USD/CNY", "unit": "CNY per USD", "expectedTradingDates": ["2020-01-03", "2020-01-06"], "expectedTradingDatesSource": [fx_url],
            "points": [{"date": "2020-01-03", "close": 7.0}, {"date": "2020-01-06", "close": 7.2}], "sources": [source(fx_url)],
            "rawSnapshots": [{"path": "raw-fx.csv", "sha256": hashlib.sha256(fx_raw).hexdigest(), "sourceUrl": fx_url}]}}
    plan = financial.build_line_plan(request, duration=10, prices=prices)
    for name, data in (("request.json", request), ("prices.json", prices), ("animation-plan.json", plan)):
        (root / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return root




def preview_fixture(root, docs):
    folder = root / "outputs" / "previews"
    folder.mkdir(parents=True)
    video = folder / "test.mp4"
    video.write_bytes(b"synthetic preview fixture")
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    (folder / "preview-record.json").write_text(json.dumps({
        "path": "outputs/previews/test.mp4", "sha256": digest,
        "frames": docs["plan"]["durationSeconds"] * 60,
        "materialsAndAssetsSha256": financial.render_inputs_digest(root),
    }), encoding="utf-8")
    return digest
