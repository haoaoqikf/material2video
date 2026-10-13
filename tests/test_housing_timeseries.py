from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m2v.core.errors import M2VError
from m2v.types.housing.housing import load_project


def _project(tmp_path: Path, points: list[dict] | None = None) -> tuple[Path, dict]:
    root = tmp_path / "housing"
    root.mkdir()
    series = {
        "schemaVersion": 1, "city": "郑州市", "metric": "住宅商品房平均销售价格", "unit": "元/平方米",
        "areaUnit": "万平方米", "salesAmountUnit": "亿元",
        "formula": "salesAmountYiYuan / salesAreaWanSquareMeters * 10000",
        "durationSeconds": 60, "calculationPrecisionNote": "公布值取整至 0.1。",
        "methodologyNote": "使用住宅商品房销售额和销售面积计算。",
        "sources": [{"title": "来源", "url": "https://example.org/source"}],
        "breakpoints": [{"year": 2003, "label": "测试口径变化"}],
        "points": points or [
            {"year": 2002, "salesAreaWanSquareMeters": 10, "salesAmountYiYuan": 2,
             "averagePriceYuanPerSquareMeter": 2000},
            {"year": 2003, "salesAreaWanSquareMeters": 10, "salesAmountYiYuan": 2.2,
             "averagePriceYuanPerSquareMeter": 2200},
        ],
    }
    (root / "series.json").write_text(json.dumps(series, ensure_ascii=False), encoding="utf-8")
    return root, {"materials": {"series": "series.json"}}


def test_loads_valid_annual_series(tmp_path: Path) -> None:
    root, project = _project(tmp_path)
    series = load_project(root, project)
    assert [point["year"] for point in series["points"]] == [2002, 2003]


@pytest.mark.parametrize("mutation,match", [
    (lambda points: points.pop(), "至少包含两个"),
    (lambda points: points.__setitem__(1, {**points[1], "year": 2002}), "连续递增"),
    (lambda points: points.__setitem__(1, {**points[1], "salesAreaWanSquareMeters": 0}), "有限正数"),
    (lambda points: points.__setitem__(1, {**points[1], "salesAmountYiYuan": -1}), "有限正数"),
    (lambda points: points.__setitem__(1, {**points[1], "averagePriceYuanPerSquareMeter": 1000}), "应为销售额"),
])
def test_rejects_invalid_values_and_incomplete_years(tmp_path: Path, mutation, match: str) -> None:
    points = [
        {"year": 2002, "salesAreaWanSquareMeters": 10, "salesAmountYiYuan": 2, "averagePriceYuanPerSquareMeter": 2000},
        {"year": 2003, "salesAreaWanSquareMeters": 10, "salesAmountYiYuan": 2.2, "averagePriceYuanPerSquareMeter": 2200},
    ]
    mutation(points)
    root, project = _project(tmp_path, points)
    with pytest.raises(M2VError, match=match):
        load_project(root, project)


def test_rejects_wrong_units_and_noncontinuous_years(tmp_path: Path) -> None:
    root, project = _project(tmp_path)
    path = root / "series.json"
    series = json.loads(path.read_text(encoding="utf-8"))
    series["unit"] = "万元/平方米"
    path.write_text(json.dumps(series), encoding="utf-8")
    with pytest.raises(M2VError, match="单位必须为"):
        load_project(root, project)
    series["unit"] = "元/平方米"
    series["points"][1]["year"] = 2004
    path.write_text(json.dumps(series), encoding="utf-8")
    with pytest.raises(M2VError, match="年份必须严格连续"):
        load_project(root, project)


def test_rejects_breakpoint_outside_the_annual_range(tmp_path: Path) -> None:
    root, project = _project(tmp_path)
    path = root / "series.json"
    series = json.loads(path.read_text(encoding="utf-8"))
    series["breakpoints"] = [{"year": 2005, "label": "口径变更"}]
    path.write_text(json.dumps(series), encoding="utf-8")
    with pytest.raises(M2VError, match="必须对应序列中的年份"):
        load_project(root, project)
