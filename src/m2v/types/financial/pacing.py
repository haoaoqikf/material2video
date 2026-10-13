"""Offline monthly pacing; frame anchors are the only rendering-time input."""
from __future__ import annotations

import math
from datetime import date
from typing import Any
from m2v.types.financial.valuation import crypto_investment_values


def build_pacing(request: dict[str, Any], prices: dict[str, Any], first: int, last: int) -> dict[str, Any]:
    start, end = (date.fromisoformat(value) for value in request["displayRange"])
    endpoints = [{"frame": first, "date": start.isoformat()}, {"frame": last, "date": end.isoformat()}]
    if start == end:
        return {"mode": "volatility", "anchors": endpoints}
    boundaries = [start]
    cursor = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    while cursor < end:
        boundaries.append(cursor)
        cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
    boundaries.append(end)
    changes: dict[str, list[float]] = {}
    investment = request.get("investment", {"year": start.year, "principal": 100_000})
    if request.get("instrument", {}).get("kind") == "crypto":
        invested = crypto_investment_values(request, prices)
        shares = 1.0
    else:
        invested = [point for point in prices["points"] if int(point["date"][:4]) >= investment["year"]]
        shares = investment["principal"] / invested[0]["close"] if invested else 0.0
    if invested:
        for previous, current in zip(invested, invested[1:]):
            if not start.isoformat() <= current["date"] <= end.isoformat():
                continue
            bucket = changes.setdefault(current["date"][:7], [0.0, 0.0])
            bucket[0] += abs(math.log(current["close"]) - math.log(previous["close"]))
            bucket[1] += abs(current["close"] - previous["close"]) * shares
    max_relative = max((value[0] for value in changes.values()), default=0)
    max_absolute = max((value[1] for value in changes.values()), default=0)
    if not max_relative and not max_absolute:
        return {"mode": "volatility", "anchors": endpoints}
    weights = []
    for left, right in zip(boundaries, boundaries[1:]):
        relative, absolute = changes.get(left.isoformat()[:7], [0, 0])
        score = 0.4 * (relative / max_relative if max_relative else 0) + 0.6 * (absolute / max_absolute if max_absolute else 0)
        weights.append((right - left).days * (1 + 2 * score))
    total = sum(weights)
    cumulative = 0.0
    anchors = [endpoints[0]]
    for boundary, weight in zip(boundaries[1:-1], weights):
        cumulative += weight
        frame = first + math.floor((last - first) * cumulative / total + 0.5)
        # Rounded months may share a frame. Preserve exact start/end instead of
        # allowing zero-length interpolation or replacing the opening date.
        if first < frame < last:
            anchor = {"frame": frame, "date": boundary.isoformat()}
            if anchors[-1]["frame"] == frame:
                anchors[-1] = anchor
            else:
                anchors.append(anchor)
    anchors.append(endpoints[1])
    return {"mode": "volatility", "anchors": anchors}


def anchor_date(anchors: list[dict[str, Any]], frame: int) -> date:
    """Integer interpolation mirrors the browser's floor date exactly."""
    low, high = 0, len(anchors) - 1
    while low + 1 < high:
        mid = (low + high) // 2
        if anchors[mid]["frame"] <= frame:
            low = mid
        else:
            high = mid
    left, right = anchors[low], anchors[high]
    start, end = (date.fromisoformat(item["date"]) for item in (left, right))
    return date.fromordinal(start.toordinal() + (frame - left["frame"]) * (end - start).days // (right["frame"] - left["frame"]))
