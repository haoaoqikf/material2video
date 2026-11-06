"""金融来源的折线编排与节奏锚点。

材料契约与校验在 `materials.py`；本模块构造当前 v8 来源计划，单向依赖它。
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from m2v.core.errors import M2VError
from m2v.core.validate import fail
from m2v.core.video_config import FPS
from m2v.types.financial.pacing import build_pacing, anchor_date
from .materials import HEIGHT, WIDTH, _date, _load, _validate_plan, _validate_prices, _validate_request


def build_line_plan(request: dict[str, Any], duration: int | None = None, prices: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a deterministic, event-free timeline with staged date-axis expansion."""
    if duration is None:
        duration = 60
    if type(duration) is not int:
        raise M2VError("时长必须为整数")
    if duration < 4:
        raise M2VError("无事件计划至少需要 4 秒：开场 1 秒、行情推进及结尾 2 秒")
    start, end = (date.fromisoformat(value) for value in request["displayRange"])
    total_frames = duration * FPS
    opening_frames, ending_frames = FPS, 2 * FPS
    advance_end = total_frames - ending_frames
    segments = [
        {"frames": [0, opening_frames], "dates": [start.isoformat(), start.isoformat()], "kind": "opening"},
        {"frames": [opening_frames, advance_end], "dates": [start.isoformat(), end.isoformat()], "kind": "advance"},
        {"frames": [advance_end, total_frames], "dates": [end.isoformat(), end.isoformat()], "kind": "ending"},
    ]
    return {
        "schemaVersion": 8, "chartType": "line", "durationSeconds": duration, "fps": FPS,
        "canvas": {"width": WIDTH, "height": HEIGHT},
        "axis": {"dateRange": request["displayRange"], "dateScale": "staged-expanding", "valueScale": "revealed-linear"},
        "segments": segments,
        "pacing": build_pacing(request, prices, opening_frames, advance_end - 1) if prices is not None else {"mode": "uniform", "anchors": [{"frame": opening_frames, "date": start.isoformat()}, {"frame": advance_end - 1, "date": end.isoformat()}]},
        "rationale": "以真实日收盘价计算假设投资组合价值，横轴按年度阶段平滑扩展；开场 1 秒、连续推进、完整历史停留 2 秒。所有新计划默认总长 60 秒；纵轴随已展示组合价值自适应。",
    }


def prepare_line_plan(root: Path, duration: int | None = None, *, files: dict[str, str]) -> dict[str, Any]:
    """由新版分镜声明的请求和行情生成计划，不读取旧计划。"""
    if (root / "events.json").exists():
        fail("events.json", "旧金融事件材料已移除")
    request = _load(root / files["request"])
    prices = _load(root / files["prices"])
    expected_price_version = 4 if request.get("instrument", {}).get("kind") == "crypto" else 3
    if request["schemaVersion"] != 1 or prices["schemaVersion"] != expected_price_version:
        fail("材料版本", f"金融来源需要 v1 请求和 v{expected_price_version} 价格")
    _validate_request(request)
    _validate_prices(prices, request, root)
    plan = build_line_plan(request, duration, prices)
    _validate_plan(plan, request, prices)
    return plan


def frame_date(plan: dict[str, Any], frame: int) -> date:
    """Map a global frame to local calendar date using stable floor rounding."""
    duration = plan["durationSeconds"] * plan["fps"]
    if not 0 <= frame < duration:
        fail("frame", f"帧号须处于 [0, {duration})")
    segments = plan["segments"]
    for segment in segments:
        start, end = segment["frames"]
        if start <= frame < end:
            date_start, date_end = (_date(value, "animation-plan segment") for value in segment["dates"])
            if segment["kind"] != "advance":
                return date_start
            if plan["schemaVersion"] == 8:
                return anchor_date(plan["pacing"]["anchors"], frame)
            offset = frame - start
            span = end - start - 1
            days = (date_end - date_start).days
            return date.fromordinal(date_start.toordinal() + (offset * days // span))
    fail("animation-plan", "帧号未被任一时间段覆盖")
