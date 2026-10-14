"""Annual residential sale-price materials and deterministic frame mapping."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from m2v.core.errors import M2VError

FPS = 30
WIDTH = 1080
HEIGHT = 1920
DEFAULT_DURATION_SECONDS = 30
MATERIAL = "series.json"


def _fail(where: str, reason: str) -> None:
    raise M2VError(f"{where}: {reason}")


def _number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        _fail(where, "必须是有限正数")
    return float(value)


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(where, "不能为空")
    return value.strip()


def load_project(root: str | Path, project: dict) -> dict:
    directory = Path(root).resolve()
    expected = {"series": MATERIAL}
    if project.get("materials") != expected:
        _fail("project.json", "房价类型材料入口固定为 series.json")
    path = directory / MATERIAL
    try:
        series = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(MATERIAL, f"无法读取有效 UTF-8 JSON：{exc}")
    _validate_series(series)
    return series


def _validate_series(series: Any) -> None:
    if not isinstance(series, dict) or type(series.get("schemaVersion")) is not int or series["schemaVersion"] != 1:
        _fail(MATERIAL, "schemaVersion 必须为 1，顶层必须为对象")
    _text(series.get("city"), "city")
    _text(series.get("metric"), "metric")
    if series.get("unit") != "元/平方米":
        _fail("unit", "年度住宅均价单位必须为 元/平方米")
    if series.get("areaUnit") != "万平方米" or series.get("salesAmountUnit") != "亿元":
        _fail("units", "salesAreaWanSquareMeters 使用 万平方米，salesAmountYiYuan 使用 亿元")
    if series.get("formula") != "salesAmountYiYuan / salesAreaWanSquareMeters * 10000":
        _fail("formula", "必须声明亿元、万平方米到元/平方米的换算公式")
    _text(series.get("calculationPrecisionNote"), "calculationPrecisionNote")
    _text(series.get("methodologyNote"), "methodologyNote")
    duration = series.get("durationSeconds", DEFAULT_DURATION_SECONDS)
    if type(duration) is not int or not 10 <= duration <= 180:
        _fail("durationSeconds", "必须为 10 至 180 的整数")
    sources = series.get("sources")
    if not isinstance(sources, list) or not sources:
        _fail("sources", "必须至少提供一个来源")
    for index, source in enumerate(sources):
        where = f"sources[{index}]"
        if not isinstance(source, dict):
            _fail(where, "必须是对象")
        _text(source.get("title"), f"{where}.title")
        url = _text(source.get("url"), f"{where}.url")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            _fail(f"{where}.url", "必须是无内嵌凭据的 HTTPS 链接")
    points = series.get("points")
    if not isinstance(points, list) or len(points) < 2:
        _fail("points", "必须至少包含两个连续年度数据点")
    years: list[int] = []
    for index, point in enumerate(points):
        where = f"points[{index}]"
        if not isinstance(point, dict):
            _fail(where, "必须是对象")
        year = point.get("year")
        if type(year) is not int or year < 1800 or year > 2200:
            _fail(f"{where}.year", "必须是有效年份整数")
        years.append(year)
        area = _number(point.get("salesAreaWanSquareMeters"), f"{where}.salesAreaWanSquareMeters")
        amount = _number(point.get("salesAmountYiYuan"), f"{where}.salesAmountYiYuan")
        price = _number(point.get("averagePriceYuanPerSquareMeter"), f"{where}.averagePriceYuanPerSquareMeter")
        expected = round(amount / area * 10000, 2)
        if abs(price - expected) > 0.001:
            _fail(f"{where}.averagePriceYuanPerSquareMeter", f"应为销售额/销售面积换算值 {expected:.2f}")
    if years != list(range(years[0], years[-1] + 1)):
        _fail("points.year", "年份必须严格连续递增且不可重复")
    breakpoints = series.get("breakpoints", [])
    if not isinstance(breakpoints, list):
        _fail("breakpoints", "必须是数组")
    for index, item in enumerate(breakpoints):
        if not isinstance(item, dict):
            _fail(f"breakpoints[{index}]", "必须是对象")
        year = item.get("year")
        if type(year) is not int or year not in years:
            _fail(f"breakpoints[{index}].year", "必须对应序列中的年份")
        _text(item.get("label"), f"breakpoints[{index}].label")


def build_render_props(series: dict) -> dict:
    return {"series": series, "durationInFrames": series.get("durationSeconds", DEFAULT_DURATION_SECONDS) * FPS,
            "fps": FPS, "width": WIDTH, "height": HEIGHT}
