"""Financial time-series materials and deterministic timeline validation."""
from __future__ import annotations

import json
import hashlib
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .errors import A2VError

MATERIALS = ("request.json", "prices.json", "events.json", "animation-plan.json")
FPS = 30
WIDTH = 1920
HEIGHT = 1080


def _fail(where: str, reason: str) -> None:
    raise A2VError(f"{where}: {reason}")


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON 对象包含重复键 {key!r}")
        result[key] = value
    return result


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object_pairs)
    except (OSError, UnicodeError, ValueError) as exc:
        _fail(path.name, f"无法读取有效 UTF-8 JSON：{exc}")
    if not isinstance(data, dict):
        _fail(path.name, "顶层必须是 JSON 对象")
    if type(data.get("schemaVersion")) is not int or data.get("schemaVersion") != 1:
        _fail(path.name, "schemaVersion 必须为 1")
    return data


def _date(value: Any, where: str) -> date:
    if not isinstance(value, str):
        _fail(where, "必须是 YYYY-MM-DD 日期字符串")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail(where, f"不是有效日期：{value!r}")
    if parsed.isoformat() != value:
        _fail(where, f"日期必須使用 YYYY-MM-DD：{value!r}")
    return parsed


def _required_text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(where, "不能为空")
    return value.strip()


def _https_url(value: Any, where: str) -> str:
    url = _required_text(value, where)
    try:
        parsed = urlsplit(url)
        valid = parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None and parsed.password is None
    except ValueError:
        valid = False
    if not valid:
        _fail(where, "必须是有效 HTTPS 链接且不能包含内嵌凭据")
    return url


def _ordered_dates(values: Any, where: str) -> list[date]:
    if not isinstance(values, list) or not values:
        _fail(where, "必须是非空日期数组")
    result = [_date(item, f"{where}[{index}]") for index, item in enumerate(values)]
    if result != sorted(set(result)):
        _fail(where, "日期必须严格递增且不可重复")
    return result


def load_project(project_dir: str | Path) -> dict[str, Any]:
    """Load and cross-validate the four immutable, offline-render inputs."""
    root = Path(project_dir).resolve()
    if not root.is_dir():
        _fail("作品目录", f"目录不存在：{root}")
    docs = {name: _load(root / name) for name in MATERIALS}
    request, prices, events, plan = (docs[name] for name in MATERIALS)
    _validate_request(request)
    _validate_prices(prices, request, root)
    _validate_events(events, request)
    _validate_plan(plan, request, prices, events)
    return {"request": request, "prices": prices, "events": events, "plan": plan}


def _validate_request(request: dict[str, Any]) -> None:
    instrument = request.get("instrument")
    _required_text(request.get("originalRequest"), "request.json.originalRequest")
    if not isinstance(instrument, dict):
        _fail("request.json.instrument", "必须声明标的对象")
    if instrument.get("kind") not in {"stock", "index"}:
        _fail("request.json.instrument.kind", "必须为 stock 或 index")
    for key in ("name", "code", "market", "unit"):
        _required_text(instrument.get(key), f"request.json.instrument.{key}")
    if instrument["kind"] == "stock":
        _date(instrument.get("listingDate"), "request.json.instrument.listingDate")
    else:
        _date(instrument.get("indexStartDate"), "request.json.instrument.indexStartDate")
    requested = request.get("requestedRange")
    display = request.get("displayRange")
    if not isinstance(requested, list) or len(requested) != 2:
        _fail("request.json.requestedRange", "必须是 [开始日期, 结束日期]")
    if not isinstance(display, list) or len(display) != 2:
        _fail("request.json.displayRange", "必须是 [开始日期, 结束日期]")
    requested_dates = [_date(item, f"request.json.requestedRange[{i}]") for i, item in enumerate(requested)]
    display_dates = [_date(item, f"request.json.displayRange[{i}]") for i, item in enumerate(display)]
    if requested_dates[0] > requested_dates[1] or display_dates[0] > display_dates[1]:
        _fail("request.json", "请求和展示日期必须从早到晚")
    if display_dates[0] < requested_dates[0] or display_dates[1] > requested_dates[1]:
        _fail("request.json.displayRange", "实际展示范围不得超出请求范围")
    if instrument["kind"] == "stock":
        listing = _date(instrument["listingDate"], "request.json.instrument.listingDate")
        if display_dates[0] < listing:
            _fail("request.json.displayRange", "展示范围包含上市日期之前；须更新已确认的展示范围")
    else:
        index_start = _date(instrument["indexStartDate"], "request.json.instrument.indexStartDate")
        if display_dates[0] < index_start:
            _fail("request.json.displayRange", "展示范围早于指数起始日")
    today = date.today()
    if display_dates[1] > today:
        _fail("request.json.displayRange", f"展示范围超过当前日期 {today.isoformat()}；未来日期不能生成历史价格")
    if display != requested:
        confirmations = request.get("confirmations")
        if not isinstance(confirmations, list) or not confirmations:
            _fail("request.json.confirmations", "缩短展示范围必须记录用户确认")


def _validate_prices(prices: dict[str, Any], request: dict[str, Any], project_root: Path) -> None:
    instrument = request["instrument"]
    expected_basis = "split-adjusted" if instrument["kind"] == "stock" else "official-index-points"
    if prices.get("priceBasis") != expected_basis:
        _fail("prices.json.priceBasis", f"{instrument['kind']} 标的必须使用 {expected_basis}")
    if prices.get("unit") != instrument["unit"]:
        _fail("prices.json.unit", "必须与 request.json 的 unit 一致")
    start, end = (_date(item, "request.json.displayRange") for item in request["displayRange"])
    expected = _ordered_dates(prices.get("expectedTradingDates"), "prices.json.expectedTradingDates")
    if expected[0] < start or expected[-1] > end:
        _fail("prices.json.expectedTradingDates", "日期超出实际展示范围")
    if not isinstance(prices.get("expectedTradingDatesSource"), list) or not prices["expectedTradingDatesSource"]:
        _fail("prices.json.expectedTradingDatesSource", "须记录核验预期交易日清单的来源")
    for index, url in enumerate(prices["expectedTradingDatesSource"]):
        _https_url(url, f"prices.json.expectedTradingDatesSource[{index}]")
    points = prices.get("points")
    if not isinstance(points, list) or not points:
        _fail("prices.json.points", "必须包含有效日线点")
    point_dates: list[date] = []
    for index, point in enumerate(points):
        where = f"prices.json.points[{index}]"
        if not isinstance(point, dict):
            _fail(where, "必须是对象")
        point_dates.append(_date(point.get("date"), f"{where}.date"))
        value = point.get("close")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            _fail(f"{where}.close", "收盘值必须是有限正数")
    if point_dates != expected:
        missing = sorted(set(expected) - set(point_dates))
        extra = sorted(set(point_dates) - set(expected))
        _fail("prices.json.points", f"日期必须与核实的预期交易日完全一致；缺失 {len(missing)} 项，额外 {len(extra)} 项")
    sources = prices.get("sources")
    if not isinstance(sources, list) or not sources:
        _fail("prices.json.sources", "必须保留原始数据来源")
    for index, source in enumerate(sources):
        _validate_source(source, f"prices.json.sources[{index}]", start, end)
    snapshots = prices.get("rawSnapshots")
    if not isinstance(snapshots, list) or not snapshots:
        _fail("prices.json.rawSnapshots", "须保留至少一份原始行情文件快照")
    source_urls = {source["url"] for source in sources}
    for index, snapshot in enumerate(snapshots):
        where = f"prices.json.rawSnapshots[{index}]"
        if not isinstance(snapshot, dict):
            _fail(where, "必须是对象")
        relative = Path(_required_text(snapshot.get("path"), f"{where}.path"))
        if relative.is_absolute() or ".." in relative.parts:
            _fail(f"{where}.path", "快照路径必须是作品目录内的相对路径")
        target = (project_root / relative).resolve()
        if not target.is_relative_to(project_root) or not target.is_file():
            _fail(f"{where}.path", "快照文件缺失或越过作品目录")
        digest = _required_text(snapshot.get("sha256"), f"{where}.sha256")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
            _fail(f"{where}.sha256", "必须是 SHA-256 十六进制摘要")
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest.lower():
            _fail(f"{where}.sha256", "原始行情快照摘要不匹配")
        if snapshot.get("sourceUrl") not in source_urls:
            _fail(f"{where}.sourceUrl", "必须引用 prices.json.sources 中的来源")
    if instrument["kind"] == "stock":
        display_end = _date(request["displayRange"][1], "request.json.displayRange")
        if _date(prices.get("adjustmentBaseDate"), "prices.json.adjustmentBaseDate") != display_end:
            _fail("prices.json.adjustmentBaseDate", "拆合股调整基准必须为展示范围结束日")
        if not isinstance(prices.get("adjustmentDefinition"), str) or not prices["adjustmentDefinition"].strip():
            _fail("prices.json.adjustmentDefinition", "须明确说明仅拆合股调整且不计分红再投资")
        adjustments = prices.get("splitAdjustments", [])
        if not isinstance(adjustments, list):
            _fail("prices.json.splitAdjustments", "必须是数组")
        for index, adjustment in enumerate(adjustments):
            where = f"prices.json.splitAdjustments[{index}]"
            if not isinstance(adjustment, dict):
                _fail(where, "必须是对象")
            _date(adjustment.get("effectiveDate"), f"{where}.effectiveDate")
            ratio = adjustment.get("newSharesPerOldShare")
            if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(ratio) or ratio <= 0:
                _fail(f"{where}.newSharesPerOldShare", "必须是有限正数")
            _required_text(adjustment.get("source"), f"{where}.source")
    else:
        _required_text(prices.get("indexType"), "prices.json.indexType")


def _validate_source(source: Any, where: str, start: date, end: date) -> None:
    if not isinstance(source, dict):
        _fail(where, "必须是对象")
    url = _https_url(source.get("url"), f"{where}.url")
    fetched = _required_text(source.get("fetchedAt"), f"{where}.fetchedAt")
    try:
        parsed = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
    except ValueError:
        _fail(f"{where}.fetchedAt", "必须包含时区的 ISO-8601 时间")
    if parsed.tzinfo is None:
        _fail(f"{where}.fetchedAt", "必须包含时区")
    coverage = source.get("coverage")
    if not isinstance(coverage, list) or len(coverage) != 2:
        _fail(f"{where}.coverage", "必须是 [开始日期, 结束日期]")
    covered_start, covered_end = (_date(item, f"{where}.coverage") for item in coverage)
    if covered_start > start or covered_end < end:
        _fail(f"{where}.coverage", "来源覆盖范围未覆盖完整展示日期")
    _required_text(source.get("adjustmentDefinition"), f"{where}.adjustmentDefinition")


def _validate_events(events: dict[str, Any], request: dict[str, Any]) -> None:
    start, end = (_date(item, "request.json.displayRange") for item in request["displayRange"])
    selected = events.get("selected")
    candidates = events.get("candidates")
    excluded = events.get("excluded")
    if not isinstance(selected, list) or len(selected) > 8:
        _fail("events.json.selected", "必须是最多八个事件的数组")
    if not isinstance(candidates, list) or not isinstance(excluded, list):
        _fail("events.json", "candidates 和 excluded 必须是数组")
    candidate_ids_seen: set[str] = set()
    selected_ids_seen: set[str] = set()
    for group, values, group_seen in (("candidates", candidates, candidate_ids_seen), ("selected", selected, selected_ids_seen)):
        for index, event in enumerate(values):
            where = f"events.json.{group}[{index}]"
            _validate_event(event, where, start, end)
            event_id = event["id"]
            if event_id in group_seen:
                _fail(f"{where}.id", "同一清单内事件 ID 必须唯一")
            group_seen.add(event_id)
    candidate_ids = {event["id"] for event in candidates}
    selected_ids = {event["id"] for event in selected}
    if not selected_ids.issubset(candidate_ids):
        _fail("events.json.selected", "入选事件必须来自 candidates")
    by_candidate = {event["id"]: event for event in candidates}
    for event in selected:
        if any(event.get(key) != by_candidate[event["id"]].get(key)
               for key in ("date", "dateBasis", "title", "sources")):
            _fail(f"events.json.selected[{event['id']}]", "入选事件信息必须与对应候选一致")
    excluded_ids: set[str] = set()
    for index, item in enumerate(excluded):
        where = f"events.json.excluded[{index}]"
        if not isinstance(item, dict):
            _fail(where, "必須是对象")
        event_id = _required_text(item.get("id"), f"{where}.id")
        if event_id not in candidate_ids or event_id in selected_ids:
            _fail(f"{where}.id", "排除项必须引用未入选的候选事件")
        if event_id in excluded_ids:
            _fail(f"{where}.id", "排除事件 ID 必须唯一")
        excluded_ids.add(event_id)
        _required_text(item.get("reason"), f"{where}.reason")


def _validate_event(event: Any, where: str, start: date, end: date) -> None:
    if not isinstance(event, dict):
        _fail(where, "必须是对象")
    _required_text(event.get("id"), f"{where}.id")
    event_date = _date(event.get("date"), f"{where}.date")
    if event_date < start or event_date > end:
        _fail(f"{where}.date", "事件日期必须处于实际展示范围")
    title = _required_text(event.get("title"), f"{where}.title")
    if len(title) > 100:
        _fail(f"{where}.title", "事件标题最多 100 个字符")
    sources = event.get("sources")
    if not isinstance(sources, list) or not sources:
        _fail(f"{where}.sources", "至少需要一个可核查来源")
    for index, url in enumerate(sources):
        _https_url(url, f"{where}.sources[{index}]")
    _required_text(event.get("dateBasis"), f"{where}.dateBasis")
    if event["dateBasis"] not in {"occurred", "announced", "reported"}:
        _fail(f"{where}.dateBasis", "必须区分 occurred、announced 或 reported 日期")
    _required_text(event.get("reason"), f"{where}.reason")


def _validate_plan(plan: dict[str, Any], request: dict[str, Any], prices: dict[str, Any], events: dict[str, Any]) -> None:
    if plan.get("fps") != FPS or plan.get("canvas") != {"width": WIDTH, "height": HEIGHT}:
        _fail("animation-plan.json", "必须使用 1920×1080、30 fps")
    duration = plan.get("durationSeconds")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration < 6:
        _fail("animation-plan.json.durationSeconds", "必须是至少 6 秒的整数")
    total_frames = duration * FPS
    axis = plan.get("axis")
    if not isinstance(axis, dict) or axis.get("dateRange") != request["displayRange"]:
        _fail("animation-plan.json.axis.dateRange", "必须与实际展示范围一致")
    value_range = axis.get("valueRange")
    if not isinstance(value_range, list) or len(value_range) != 2:
        _fail("animation-plan.json.axis.valueRange", "必须声明固定的 [最小值, 最大值]")
    low, high = value_range
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value_range) or low >= high:
        _fail("animation-plan.json.axis.valueRange", "上下界必须是有限数字且严格递增")
    values = [point["close"] for point in prices["points"]]
    if min(values) < low or max(values) > high:
        _fail("animation-plan.json.axis.valueRange", "固定纵轴必须覆盖全部有效价格点")
    segments = plan.get("segments")
    if not isinstance(segments, list) or len(segments) < 2:
        _fail("animation-plan.json.segments", "至少需要开头与结尾时间段")
    display_start, display_end = (_date(item, "request.json.displayRange") for item in request["displayRange"])
    previous_frame = 0
    previous_date: date | None = None
    for index, segment in enumerate(segments):
        where = f"animation-plan.json.segments[{index}]"
        if not isinstance(segment, dict):
            _fail(where, "必须是对象")
        frames = segment.get("frames")
        dates = segment.get("dates")
        if not isinstance(frames, list) or len(frames) != 2 or any(isinstance(x, bool) or not isinstance(x, int) for x in frames):
            _fail(f"{where}.frames", "必须是整数半开帧区间 [开始, 结束)")
        start_frame, end_frame = frames
        if start_frame != previous_frame or end_frame <= start_frame or end_frame > total_frames:
            _fail(f"{where}.frames", "时间段必须从 0 连续、无重叠地覆盖至总帧数")
        if not isinstance(dates, list) or len(dates) != 2:
            _fail(f"{where}.dates", "必须是起止日组成的数组")
        date_start, date_end = (_date(item, f"{where}.dates") for item in dates)
        if date_start > date_end or date_start < display_start or date_end > display_end:
            _fail(f"{where}.dates", "日期必须递增且位于展示范围")
        if previous_date is not None and date_start != previous_date:
            _fail(f"{where}.dates", "相邻时间段日期边界必须连续")
        kind = segment.get("kind")
        if kind not in {"opening", "advance", "hold", "ending"}:
            _fail(f"{where}.kind", "必须为 opening、advance、hold 或 ending")
        if kind == "advance" and (date_start >= date_end or end_frame - start_frame < 2):
            _fail(where, "advance 必须跨日期且至少占两帧")
        if kind in {"opening", "hold", "ending"} and date_start != date_end:
            _fail(where, f"{kind} 段必须停留在同一日期")
        if index == 0 and (kind != "opening" or start_frame != 0 or date_start != display_start):
            _fail(where, "首段必须从第 0 帧在展示起始日 opening")
        if index == len(segments) - 1 and (kind != "ending" or date_end != display_end or end_frame != total_frames or end_frame - start_frame < 90):
            _fail(where, "尾段必须在展示结束日停留至少 90 帧并覆盖终帧")
        if index not in {0, len(segments) - 1} and kind in {"opening", "ending"}:
            _fail(where, "opening 与 ending 只能位于首尾")
        previous_frame, previous_date = end_frame, date_end
    if previous_frame != total_frames or previous_date != display_end:
        _fail("animation-plan.json.segments", "时间段必须覆盖完整时长和展示日期")
    _required_text(plan.get("rationale"), "animation-plan.json.rationale")
    displays = plan.get("eventDisplays")
    if not isinstance(displays, list):
        _fail("animation-plan.json.eventDisplays", "必须是数组")
    selected_by_id = {item["id"]: item for item in events["selected"]}
    if {item.get("eventId") for item in displays if isinstance(item, dict)} != set(selected_by_id):
        _fail("animation-plan.json.eventDisplays", "每个且仅每个入选事件须有一个展示区间")
    previous_event_end = -1
    for index, display in enumerate(displays):
        where = f"animation-plan.json.eventDisplays[{index}]"
        if not isinstance(display, dict) or display.get("eventId") not in selected_by_id:
            _fail(where, "引用的事件必须已入选")
        frames = display.get("frames")
        if not isinstance(frames, list) or len(frames) != 2 or any(isinstance(x, bool) or not isinstance(x, int) for x in frames):
            _fail(f"{where}.frames", "必须是整数半开帧区间")
        start_frame, end_frame = frames
        event_day = _date(selected_by_id[display["eventId"]]["date"], f"events.{display['eventId']}.date")
        if start_frame < 0 or end_frame <= start_frame or end_frame > total_frames:
            _fail(f"{where}.frames", "事件展示区间超出视频范围或为空")
        if start_frame < previous_event_end:
            _fail(f"{where}.frames", "事件说明区间不得重叠，须依次展示")
        if frame_date(plan, start_frame) < event_day:
            _fail(f"{where}.frames", "事件说明不得早于事件实际日期出现")
        if index and event_day < prior_event_day:
            _fail(f"{where}.eventId", "事件说明必须按真实日期顺序展示")
        previous_event_end = end_frame
        prior_event_day = event_day


def frame_date(plan: dict[str, Any], frame: int) -> date:
    """Map a global frame to local calendar date using stable floor rounding."""
    duration = plan["durationSeconds"] * plan["fps"]
    if not 0 <= frame < duration:
        _fail("frame", f"帧号须处于 [0, {duration})")
    segments = plan["segments"]
    for segment in segments:
        start, end = segment["frames"]
        if start <= frame < end:
            date_start, date_end = (_date(value, "animation-plan segment") for value in segment["dates"])
            if segment["kind"] != "advance":
                return date_start
            offset = frame - start
            span = end - start - 1
            days = (date_end - date_start).days
            return date.fromordinal(date_start.toordinal() + (offset * days // span))
    _fail("animation-plan", "帧号未被任一时间段覆盖")


def build_render_props(docs: dict[str, Any]) -> dict[str, Any]:
    plan = docs["plan"]
    return {
        "request": docs["request"], "prices": docs["prices"], "events": docs["events"],
        "plan": plan, "durationInFrames": plan["durationSeconds"] * FPS,
        "fps": FPS, "width": WIDTH, "height": HEIGHT,
    }
