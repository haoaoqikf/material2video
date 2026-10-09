"""Financial time-series materials and deterministic timeline validation."""
from __future__ import annotations

import json
import hashlib
import math
import shutil
import tempfile
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
    if type(data.get("schemaVersion")) is not int or data.get("schemaVersion") not in {1, 2, 3}:
        _fail(path.name, "schemaVersion 必须为 1、2 或 3")
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
    if request["schemaVersion"] != 1 or events["schemaVersion"] != 1:
        _fail("材料版本", "request.json 和 events.json 当前必须为 version 1")
    if prices["schemaVersion"] != plan["schemaVersion"]:
        _fail("材料版本", "prices.json 与 animation-plan.json 版本必须一致，拒绝混合版本")
    if prices["schemaVersion"] != 3:
        _fail("材料版本", "旧材料不能直接渲染；请运行 financial_video.py migrate-line --project-dir <作品目录>")
    _validate_request(request)
    _validate_prices(prices, request, root)
    _validate_events(events, request)
    _validate_plan(plan, request, prices, events)
    return {"request": request, "prices": prices, "events": events, "plan": plan}


def legibility_review_digest(project_dir: str | Path) -> str:
    """Bind the visual review to exact materials and shared rendering sources."""
    root = Path(project_dir).resolve()
    web = Path(__file__).resolve().parents[5] / "web"
    inputs = [(root, root / name) for name in MATERIALS]
    from . import remotion
    inputs.extend((web, path) for path in remotion.build_inputs())
    scripts = Path(__file__).resolve().parents[1]
    inputs.extend((scripts, path) for path in (
        scripts / "a2v/financial.py", scripts / "a2v/financial_render.py",
        scripts / "a2v/remotion.py", scripts / "financial_video.py",
    ))
    digest = hashlib.sha256()
    for base, path in inputs:
        try:
            content = path.read_bytes()
        except OSError as exc:
            _fail("可读性评审摘要", f"无法读取绑定文件 {path.name}：{exc}")
        digest.update(path.relative_to(base).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()


def validate_legibility_review(project_dir: str | Path, docs: dict[str, Any]) -> None:
    """Reject a missing, stale, or failed full-video review."""
    path = Path(project_dir).resolve() / "outputs" / "legibility-review.json"
    try:
        review = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object_pairs)
    except (OSError, UnicodeError, ValueError) as exc:
        _fail("outputs/legibility-review.json", f"正式折线渲染需要当前完整视频的评审记录：{exc}")
    if not isinstance(review, dict) or review.get("schemaVersion") != 1:
        _fail("outputs/legibility-review.json", "schemaVersion 必须为 1")
    if review.get("materialsAndAssetsSha256") != legibility_review_digest(project_dir):
        _fail("outputs/legibility-review.json", "材料或渲染资产已变化；评审记录已过期")
    if review.get("result") != "pass" or review.get("fullVideo") is not True:
        _fail("outputs/legibility-review.json", "正式折线渲染只接受完整视频评审通过的记录")
    checks = review.get("checks")
    required = set(REVIEW_CHECKS)
    if not isinstance(checks, dict) or set(checks) != required or any(value is not True for value in checks.values()):
        _fail("outputs/legibility-review.json.checks", "全部可读性结论必须全部通过")
    timestamps = review.get("sampleTimecodes")
    if not isinstance(timestamps, list) or not timestamps or any(not isinstance(item, str) or not item.strip() for item in timestamps):
        _fail("outputs/legibility-review.json.sampleTimecodes", "必须记录完整视频的抽检时间码")
    if review.get("metrics") != review_metrics(docs):
        _fail("outputs/legibility-review.json.metrics", "评审指标与当前折线编排不一致")
    preview = load_preview_record(project_dir, docs)
    if review.get("previewSha256") != preview["sha256"]:
        _fail("outputs/legibility-review.json", "预演文件已变化；请重新评审")
    evidence = review.get("evidence")
    if not isinstance(evidence, dict) or any(not isinstance(evidence.get(key), str) or not evidence[key].strip() for key in REVIEW_CHECKS):
        _fail("outputs/legibility-review.json.evidence", "须填写每项可观察证据")



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
        if set(point) != {"date", "close"}:
            _fail(where, "折线价格点只能包含 date 和 close；旧材料请使用 migrate-line")
        value = point.get("close")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            _fail(f"{where}.close", "收盘价必须为有限正数")
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


def build_line_plan(request: dict[str, Any], events: dict[str, Any], duration: int = 60, window_months: int = 12) -> dict[str, Any]:
    """Allocate exact frame budgets by calendar span, including same-day events."""
    if type(duration) is not int or type(window_months) is not int or not 1 <= window_months <= 1200:
        raise A2VError("时长必须为整数；窗口必须是 1 到 1200 之间的整数日历月")
    start, end = (date.fromisoformat(value) for value in request["displayRange"])
    selected = sorted(events["selected"], key=lambda item: item["date"])
    waypoints = [start, *(date.fromisoformat(item["date"]) for item in selected), end]
    gaps = [(right - left).days for left, right in zip(waypoints, waypoints[1:])]
    if any(gap < 0 for gap in gaps):
        raise A2VError("事件须位于展示范围内")
    positive = [index for index, gap in enumerate(gaps) if gap > 0]
    fixed = FPS * (9 + 3 * len(selected))
    available = duration * FPS - fixed
    minimum = fixed + 2 * len(positive)
    if available < 2 * len(positive) or (not positive and available != 0):
        raise A2VError(f"时长预算不满足开场、事件和全貌停留；至少需要 {math.ceil(minimum / FPS)} 秒；单日范围请使用恰好 {fixed / FPS:g} 秒")
    allocations = [0] * len(gaps)
    if positive:
        remainder = available - 2 * len(positive)
        total_days = sum(gaps)
        quotas = {index: remainder * gaps[index] / total_days for index in positive}
        for index in positive:
            allocations[index] = 2 + int(quotas[index])
        for index in sorted(positive, key=lambda index: quotas[index] % 1, reverse=True)[:available - sum(allocations)]:
            allocations[index] += 1
    segments = [{"frames": [0, 90], "dates": [start.isoformat(), start.isoformat()], "kind": "opening"}]
    displays = []
    cursor = 90
    for index, gap in enumerate(gaps):
        left, right = waypoints[index], waypoints[index + 1]
        if gap > 0:
            next_frame = cursor + allocations[index]
            segments.append({"frames": [cursor, next_frame], "dates": [left.isoformat(), right.isoformat()], "kind": "advance"})
            cursor = next_frame
        if index < len(selected):
            segments.append({"frames": [cursor, cursor + 90], "dates": [right.isoformat(), right.isoformat()], "kind": "hold"})
            displays.append({"eventId": selected[index]["id"], "frames": [cursor, cursor + 90]})
            cursor += 90
    segments.extend([
        {"frames": [cursor, cursor + 60], "dates": [end.isoformat(), end.isoformat()], "kind": "overview"},
        {"frames": [cursor + 60, cursor + 180], "dates": [end.isoformat(), end.isoformat()], "kind": "ending"},
    ])
    return {"schemaVersion": 3, "chartType": "line", "durationSeconds": duration, "fps": FPS,
        "canvas": {"width": WIDTH, "height": HEIGHT},
        "axis": {"dateRange": request["displayRange"], "visibleWindowMonths": window_months, "valueScale": "rolling-linear"},
        "segments": segments, "eventDisplays": displays,
        "rationale": f"真实日收盘价，近 {window_months} 个月连续滚动；开场及事件各 3 秒，结尾 2 秒展开全历史并停留 4 秒。"}


def prepare_line_plan(root: Path, duration: int, window_months: int) -> dict[str, Any]:
    request, prices, events = (_load(root / name) for name in MATERIALS[:3])
    if request["schemaVersion"] != 1 or events["schemaVersion"] != 1 or prices["schemaVersion"] != 3:
        _fail("材料版本", "需 version 3 价格；旧材料请运行 migrate-line")
    _validate_request(request)
    _validate_prices(prices, request, root)
    _validate_events(events, request)
    plan = build_line_plan(request, events, duration, window_months)
    _validate_plan(plan, request, prices, events)
    return plan


def migrate_line(root: Path, duration: int = 60, window_months: int = 12) -> Path:
    """Validate before writing, back up inputs, restore on any publication failure."""
    originals = {name: (root / name).read_bytes() for name in MATERIALS}
    request, prices, events, old_plan = (_load(root / name) for name in MATERIALS)
    if request["schemaVersion"] != 1 or events["schemaVersion"] != 1:
        _fail("材料版本", "需求和事件必须为 version 1")
    if prices["schemaVersion"] not in {1, 2} or prices["schemaVersion"] != old_plan["schemaVersion"]:
        _fail("材料版本", "迁移仅接受一致的旧 version 1/2 价格与计划")
    points = prices.get("points")
    if not isinstance(points, list) or any(not isinstance(point, dict) for point in points):
        _fail("prices.json.points", "旧价格点须为对象数组")
    normalized = {**prices, "schemaVersion": 3, "points": [{"date": point.get("date"), "close": point.get("close")} for point in points]}
    _validate_request(request)
    _validate_prices(normalized, request, root)
    _validate_events(events, request)
    plan = build_line_plan(request, events, duration, window_months)
    _validate_plan(plan, request, normalized, events)
    backups = root / "outputs" / "material-backups"
    backups.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="before-line-", dir=backups))
    for name, content in originals.items():
        (backup / name).write_bytes(content)
    review = root / "outputs" / "legibility-review.json"
    if review.is_file():
        shutil.copy2(review, backup / review.name)
    try:
        for name, value in (("prices.json", normalized), ("animation-plan.json", plan)):
            (root / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        load_project(root)
    except (OSError, A2VError):
        for name, content in originals.items():
            (root / name).write_bytes(content)
        raise
    # The old review remains inspectable but its material digest is now stale.
    return backup


REVIEW_CHECKS = ("labelsReadable", "scrollTrackable", "axisStable", "eventsDoNotOverlap", "overviewComplete")


def review_metrics(docs: dict[str, Any]) -> dict[str, Any]:
    return {"durationSeconds": docs["plan"]["durationSeconds"], "visibleWindowMonths": docs["plan"]["axis"]["visibleWindowMonths"], "overviewSeconds": 2, "endingSeconds": 4}


def load_preview_record(project_dir: str | Path, docs: dict[str, Any]) -> dict[str, Any]:
    root = Path(project_dir).resolve()
    path = root / "outputs" / "previews" / "preview-record.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError("记录必须为对象")
        relative = record.get("path")
        if not isinstance(relative, str):
            raise ValueError("缺少预演路径")
        video = (root / relative).resolve()
        if not video.is_relative_to(root / "outputs" / "previews") or not video.is_file():
            raise ValueError("预演路径越界或文件缺失")
        if record.get("materialsAndAssetsSha256") != legibility_review_digest(root):
            raise ValueError("预演材料或资产已变化")
        if record.get("frames") != docs["plan"]["durationSeconds"] * FPS:
            raise ValueError("需要完整时长预演")
        if record.get("sha256") != hashlib.sha256(video.read_bytes()).hexdigest():
            raise ValueError("预演文件摘要不一致")
    except (OSError, ValueError) as exc:
        _fail("完整预演记录", str(exc))
    return record


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
    if plan.get("schemaVersion") != 3 or plan.get("chartType") != "line":
        _fail("animation-plan.json", "必须为 version 3、chartType=line；旧材料请使用 migrate-line")
    if any(key in plan for key in ("selectedPeriod", "selectionReport")) or "visibleWindowBars" in axis:
        _fail("animation-plan.json", "不再接受 K 线周期或柱数参数；请使用 migrate-line")
    window_months = axis.get("visibleWindowMonths")
    if type(window_months) is not int or not 1 <= window_months <= 1200:
        _fail("animation-plan.json.axis.visibleWindowMonths", "必须是 1 到 1200 之间的整数日历月")
    if axis.get("valueScale") != "rolling-linear":
        _fail("animation-plan.json.axis.valueScale", "必须使用 rolling-linear 窗口自适应纵轴")
    if "valueRange" in axis:
        _fail("animation-plan.json.axis.valueRange", "滚动视窗纵轴由可见价格动态计算，不接受固定 valueRange")
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
        if kind not in {"opening", "advance", "hold", "overview", "ending"}:
            _fail(f"{where}.kind", "必须为 opening、advance、hold、overview 或 ending")
        if kind == "advance" and (date_start >= date_end or end_frame - start_frame < 2):
            _fail(where, "advance 必须跨日期且至少占两帧")
        if kind in {"opening", "hold", "overview", "ending"} and date_start != date_end:
            _fail(where, f"{kind} 段必须停留在同一日期")
        if index == 0 and (kind != "opening" or start_frame != 0 or date_start != display_start):
            _fail(where, "首段必须从第 0 帧在展示起始日 opening")
        if index == len(segments) - 1 and (kind != "ending" or date_end != display_end or end_frame != total_frames or end_frame - start_frame != 120):
            _fail(where, "尾段必须在展示结束日停留 120 帧并覆盖终帧")
        if index not in {0, len(segments) - 1} and kind in {"opening", "ending"}:
            _fail(where, "opening 与 ending 只能位于首尾")
        previous_frame, previous_date = end_frame, date_end
    if previous_frame != total_frames or previous_date != display_end:
        _fail("animation-plan.json.segments", "时间段必须覆盖完整时长和展示日期")
    overview = segments[-2]
    if overview["kind"] != "overview" or overview["dates"] != [request["displayRange"][1]] * 2 or overview["frames"][1] - overview["frames"][0] != 60:
        _fail("animation-plan.json.segments", "倒数第二段须在终日用 60 帧展开全貌")
    if sum(segment["kind"] == "overview" for segment in segments) != 1 or segments[0]["frames"][1] != 90:
        _fail("animation-plan.json.segments", "只允许一次全貌展开，开场须为 90 帧")
    _required_text(plan.get("rationale"), "animation-plan.json.rationale")
    displays = plan.get("eventDisplays")
    if not isinstance(displays, list):
        _fail("animation-plan.json.eventDisplays", "必须是数组")
    selected_by_id = {item["id"]: item for item in events["selected"]}
    if {item.get("eventId") for item in displays if isinstance(item, dict)} != set(selected_by_id):
        _fail("animation-plan.json.eventDisplays", "每个且仅每个入选事件须有一个展示区间")
    if len(displays) != len(selected_by_id):
        _fail("animation-plan.json.eventDisplays", "事件展示不得重复")
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
        if end_frame - start_frame != 90 or not any(segment["kind"] == "hold" and segment["frames"] == frames and segment["dates"] == [event_day.isoformat()] * 2 for segment in segments):
            _fail(f"{where}.frames", "每个事件须在真实日期 hold 90 帧")
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
    prices = docs["prices"]
    return {
        "request": docs["request"], "prices": prices, "events": docs["events"],
        "plan": plan, "durationInFrames": plan["durationSeconds"] * FPS,
        "fps": FPS, "width": WIDTH, "height": HEIGHT,
    }
