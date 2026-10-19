"""金融折线编排、节奏锚点与显式迁移。

材料契约与校验在 `materials.py`；本模块只构造与升级计划，单向依赖它。
"""
from __future__ import annotations

import json
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from m2v.core.errors import M2VError
from m2v.core.validate import fail
from m2v.core.video_config import FPS
from m2v.types.financial.pacing import build_pacing, anchor_date
from .materials import HEIGHT, MATERIALS, WIDTH, _date, _load, _validate_plan, _validate_prices, _validate_request, load_project


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


def prepare_line_plan(root: Path, duration: int | None = None) -> dict[str, Any]:
    if (root / "events.json").exists():
        fail("events.json", "事件材料已移除；请先显式运行 migrate-line 清理旧材料")
    request, prices = (_load(root / name) for name in MATERIALS[:2])
    old_plan = _load(root / "animation-plan.json")
    if old_plan.get("schemaVersion") != 8:
        fail("animation-plan.json", "旧计划请先显式运行 migrate-line，备份后迁移到 v8")
    expected_price_version = 4 if request.get("instrument", {}).get("kind") == "crypto" else 3
    if request["schemaVersion"] != 1 or prices["schemaVersion"] != expected_price_version:
        fail("材料版本", f"需 version 1 请求和 version {expected_price_version} 价格；旧材料请运行 migrate-line")
    _validate_request(request)
    _validate_prices(prices, request, root)
    plan = build_line_plan(request, duration, prices)
    _validate_plan(plan, request, prices)
    return plan


def migrate_line(root: Path, duration: int = 60) -> Path:
    """Migrate old prices/plans and strip event inputs only after new materials validate."""
    source_names = ("request.json", "prices.json", "animation-plan.json")
    originals = {name: (root / name).read_bytes() for name in source_names}
    event_path = root / "events.json"
    event_original = event_path.read_bytes() if event_path.is_file() else None
    review_path = root / "outputs" / "legibility-review.json"
    review_original = review_path.read_bytes() if review_path.is_file() else None
    preview_record = root / "outputs" / "previews" / "preview-record.json"
    preview_original = preview_record.read_bytes() if preview_record.is_file() else None
    unified_paths = [root / "outputs" / name for name in ("prepared.json", "review.json", "preview-record.json")]
    unified_originals = {path: path.read_bytes() for path in unified_paths if path.is_file()}
    request, prices, old_plan = (_load(root / name) for name in source_names)
    if old_plan["schemaVersion"] == 8:
        fail("材料版本", "计划已是 v8，拒绝重复迁移")
    if request["schemaVersion"] != 1:
        fail("request.json", "迁移仅接受 version 1 请求材料")
    if prices["schemaVersion"] not in {1, 2, 3} or old_plan["schemaVersion"] not in {1, 2, 3, 4, 5, 6, 7}:
        fail("材料版本", "迁移仅接受旧 version 1/2 价格或 version 1～7 计划")
    if prices["schemaVersion"] in {1, 2} and prices["schemaVersion"] != old_plan["schemaVersion"]:
        fail("材料版本", "旧价格与计划版本不一致；拒绝混合迁移")
    if prices["schemaVersion"] == 3 and old_plan["schemaVersion"] not in {3, 4, 5, 6, 7}:
        fail("材料版本", "v3 价格必须与 v3～v7 动画计划一起迁移")
    points = prices.get("points")
    if not isinstance(points, list) or any(not isinstance(point, dict) for point in points):
        fail("prices.json.points", "旧价格点须为对象数组")
    normalized = {**prices, "schemaVersion": 3, "points": [{"date": point.get("date"), "close": point.get("close")} for point in points]}
    _validate_request(request)
    _validate_prices(normalized, request, root)
    plan = build_line_plan(request, duration, normalized)
    _validate_plan(plan, request, normalized)
    backups = root / "outputs" / "material-backups"
    backups.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=f"before-line-v{old_plan['schemaVersion']}-", dir=backups))
    for name, content in originals.items():
        (backup / name).write_bytes(content)
    for path, content in unified_originals.items():
        destination = backup / path.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    for name, content in (("events.json", event_original), ("legibility-review.json", review_original), ("preview-record.json", preview_original)):
        if content is not None:
            (backup / name).write_bytes(content)
    try:
        writes = [("animation-plan.json", plan)]
        if prices["schemaVersion"] in {1, 2}:
            writes.insert(0, ("prices.json", normalized))
        for name, value in writes:
            (root / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        event_path.unlink(missing_ok=True)
        review_path.unlink(missing_ok=True)
        preview_record.unlink(missing_ok=True)
        load_project(root)
        for path in unified_originals:
            path.unlink(missing_ok=True)
    except (OSError, M2VError):
        for name, content in originals.items():
            (root / name).write_bytes(content)
        if event_original is not None:
            event_path.write_bytes(event_original)
        if review_original is not None:
            review_path.write_bytes(review_original)
        if preview_original is not None:
            preview_record.write_bytes(preview_original)
        for path, content in unified_originals.items():
            path.write_bytes(content)
        raise
    return backup


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
