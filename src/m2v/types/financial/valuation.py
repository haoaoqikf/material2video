"""Pure offline investment-value calculations shared by planning and validation."""
from __future__ import annotations

from bisect import bisect_right
from datetime import date
from typing import Any

from m2v.core.errors import M2VError


def fx_rate_on_or_before(fx_points: list[dict[str, Any]], day: str) -> float:
    """Return the latest USD/CNY observation available on a UTC calendar date."""
    dates = [point["date"] for point in fx_points]
    index = bisect_right(dates, day) - 1
    if index < 0:
        raise M2VError(f"缺少 {day} 当日或此前的 USD/CNY 汇率")
    return float(fx_points[index]["close"])


def crypto_investment_values(request: dict[str, Any], prices: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive CNY holdings from USD closes and the nearest prior CNY/USD rate."""
    investment = request["investment"]
    entry_date = investment["date"]
    points = prices["points"]
    index = next((i for i, point in enumerate(points) if point["date"] == entry_date), None)
    if index is None:
        raise M2VError(f"买入日 {entry_date} 没有 BTC/USD 收盘价")
    fx_points = prices["fx"]["points"]
    fx_dates = [point["date"] for point in fx_points]
    entry_close = float(points[index]["close"])
    entry_fx_index = bisect_right(fx_dates, entry_date) - 1
    if entry_fx_index < 0:
        raise M2VError(f"缺少 {entry_date} 当日或此前的 USD/CNY 汇率")
    entry_fx = float(fx_points[entry_fx_index]["close"])
    principal = float(investment["principal"])
    values: list[dict[str, Any]] = []
    fx_index = entry_fx_index
    for point in points[index:]:
        while fx_index + 1 < len(fx_points) and fx_dates[fx_index + 1] <= point["date"]:
            fx_index += 1
        fx = float(fx_points[fx_index]["close"])
        values.append({
            "date": point["date"],
            "close": principal * (float(point["close"]) / entry_close) * (fx / entry_fx),
        })
    return values


def expected_daily_dates(start: str, end: str) -> list[str]:
    """Enumerate inclusive UTC calendar dates for always-on crypto markets."""
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    return [date.fromordinal(day).isoformat() for day in range(first.toordinal(), last.toordinal() + 1)]
