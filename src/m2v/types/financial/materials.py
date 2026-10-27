"""金融材料契约：请求、价格、汇率、快照与渲染输入的校验。

材料三份（`request.json`、`prices.json`、`animation-plan.json`）的读取与逐字段校验都在这里；
折线编排、节奏锚点与显式迁移在 `plan.py`，本模块不依赖它。
"""
from __future__ import annotations

import json
import hashlib
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from m2v.core.validate import fail
from m2v.core.video_config import FPS
from m2v.types.financial.valuation import crypto_investment_values, expected_daily_dates


MATERIALS = ("request.json", "prices.json", "animation-plan.json")


WIDTH = 1080


HEIGHT = 1920


LAYOUT_BOUNDS_X = (140, 940)


LAYOUT_BOUNDS_Y = (180, 1740)


CANVAS_CENTER_Y = HEIGHT / 2


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
        fail(path.name, f"无法读取有效 UTF-8 JSON：{exc}")
    if not isinstance(data, dict):
        fail(path.name, "顶层必须是 JSON 对象")
    if type(data.get("schemaVersion")) is not int or data.get("schemaVersion") not in {1, 2, 3, 4, 5, 6, 7, 8}:
        fail(path.name, "schemaVersion 必须为 1 至 8 的整数")
    return data


def _date(value: Any, where: str) -> date:
    if not isinstance(value, str):
        fail(where, "必须是 YYYY-MM-DD 日期字符串")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        fail(where, f"不是有效日期：{value!r}")
    if parsed.isoformat() != value:
        fail(where, f"日期必須使用 YYYY-MM-DD：{value!r}")
    return parsed


def _required_text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(where, "不能为空")
    return value.strip()


def _https_url(value: Any, where: str) -> str:
    url = _required_text(value, where)
    try:
        parsed = urlsplit(url)
        valid = parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None and parsed.password is None
    except ValueError:
        valid = False
    if not valid:
        fail(where, "必须是有效 HTTPS 链接且不能包含内嵌凭据")
    return url


def _ordered_dates(values: Any, where: str) -> list[date]:
    if not isinstance(values, list) or not values:
        fail(where, "必须是非空日期数组")
    result = [_date(item, f"{where}[{index}]") for index, item in enumerate(values)]
    if result != sorted(set(result)):
        fail(where, "日期必须严格递增且不可重复")
    return result


def _validate_request(request: dict[str, Any]) -> None:
    instrument = request.get("instrument")
    _required_text(request.get("originalRequest"), "request.json.originalRequest")
    if not isinstance(instrument, dict):
        fail("request.json.instrument", "必须声明标的对象")
    if instrument.get("kind") not in {"stock", "index", "crypto"}:
        fail("request.json.instrument.kind", "必须为 stock、index 或 crypto")
    for key in ("name", "code", "market", "unit"):
        _required_text(instrument.get(key), f"request.json.instrument.{key}")
    if "displayName" in instrument:
        _required_text(instrument["displayName"], "request.json.instrument.displayName")
    if instrument["kind"] == "stock":
        _date(instrument.get("listingDate"), "request.json.instrument.listingDate")
    elif instrument["kind"] == "index":
        _date(instrument.get("indexStartDate"), "request.json.instrument.indexStartDate")
    requested = request.get("requestedRange")
    display = request.get("displayRange")
    if not isinstance(requested, list) or len(requested) != 2:
        fail("request.json.requestedRange", "必须是 [开始日期, 结束日期]")
    if not isinstance(display, list) or len(display) != 2:
        fail("request.json.displayRange", "必须是 [开始日期, 结束日期]")
    requested_dates = [_date(item, f"request.json.requestedRange[{i}]") for i, item in enumerate(requested)]
    display_dates = [_date(item, f"request.json.displayRange[{i}]") for i, item in enumerate(display)]
    if requested_dates[0] > requested_dates[1] or display_dates[0] > display_dates[1]:
        fail("request.json", "请求和展示日期必须从早到晚")
    if display_dates[0] < requested_dates[0] or display_dates[1] > requested_dates[1]:
        fail("request.json.displayRange", "实际展示范围不得超出请求范围")
    investment = request.setdefault("investment", {"year": display_dates[0].year, "principal": 1_000_000})
    if not isinstance(investment, dict):
        fail("request.json.investment", "必须是包含本金的对象")
    principal = investment.get("principal")
    if isinstance(principal, bool) or not isinstance(principal, (int, float)) or not math.isfinite(principal) or principal <= 0:
        fail("request.json.investment.principal", "必须是有限正数")
    if instrument["kind"] == "crypto":
        entry_date = _date(investment.get("date"), "request.json.investment.date")
        if not display_dates[0] <= entry_date <= display_dates[1]:
            fail("request.json.investment.date", "必须位于展示范围内")
        if investment.get("currency") != "CNY":
            fail("request.json.investment.currency", "crypto 本金必须使用 CNY")
        rationale = investment.get("startRationale")
        if rationale is not None and (not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 180):
            fail("request.json.investment.startRationale", "必须为 1～180 个字符的非空说明")
        legal_notice = investment.get("legalStatusNotice")
        if legal_notice is not None and (not isinstance(legal_notice, str) or not legal_notice.strip() or len(legal_notice) > 180):
            fail("request.json.investment.legalStatusNotice", "必须为 1～180 个字符的非空说明")
    else:
        if "legalStatusNotice" in investment:
            fail("request.json.investment.legalStatusNotice", "仅 crypto 投资支持法律地位说明")
        year = investment.get("year")
        if isinstance(year, bool) or not isinstance(year, int) or year < display_dates[0].year or year > display_dates[1].year:
            fail("request.json.investment.year", "必须是展示范围内的有效年份")
    if instrument["kind"] == "stock":
        listing = _date(instrument["listingDate"], "request.json.instrument.listingDate")
        if display_dates[0] < listing:
            fail("request.json.displayRange", "展示范围包含上市日期之前；须更新已确认的展示范围")
    elif instrument["kind"] == "index":
        index_start = _date(instrument["indexStartDate"], "request.json.instrument.indexStartDate")
        if display_dates[0] < index_start:
            fail("request.json.displayRange", "展示范围早于指数起始日")
    today = date.today()
    if display_dates[1] > today:
        fail("request.json.displayRange", f"展示范围超过当前日期 {today.isoformat()}；未来日期不能生成历史价格")
    if display != requested:
        confirmations = request.get("confirmations")
        if not isinstance(confirmations, list) or not confirmations:
            fail("request.json.confirmations", "缩短展示范围必须记录用户确认")


def _validate_prices(prices: dict[str, Any], request: dict[str, Any], project_root: Path) -> None:
    instrument = request["instrument"]
    if instrument["kind"] == "crypto":
        _validate_crypto_prices(prices, request, project_root)
        return
    if prices.get("schemaVersion") != 3:
        fail("prices.json.schemaVersion", "股票和指数必须使用 version 3")
    expected_basis = "split-adjusted" if instrument["kind"] == "stock" else "official-index-points"
    if prices.get("priceBasis") != expected_basis:
        fail("prices.json.priceBasis", f"{instrument['kind']} 标的必须使用 {expected_basis}")
    if prices.get("unit") != instrument["unit"]:
        fail("prices.json.unit", "必须与 request.json 的 unit 一致")
    start, end = (_date(item, "request.json.displayRange") for item in request["displayRange"])
    expected = _ordered_dates(prices.get("expectedTradingDates"), "prices.json.expectedTradingDates")
    if expected[0] < start or expected[-1] > end:
        fail("prices.json.expectedTradingDates", "日期超出实际展示范围")
    if not isinstance(prices.get("expectedTradingDatesSource"), list) or not prices["expectedTradingDatesSource"]:
        fail("prices.json.expectedTradingDatesSource", "须记录核验预期交易日清单的来源")
    for index, url in enumerate(prices["expectedTradingDatesSource"]):
        _https_url(url, f"prices.json.expectedTradingDatesSource[{index}]")
    points = prices.get("points")
    if not isinstance(points, list) or not points:
        fail("prices.json.points", "必须包含有效日线点")
    point_dates: list[date] = []
    for index, point in enumerate(points):
        where = f"prices.json.points[{index}]"
        if not isinstance(point, dict):
            fail(where, "必须是对象")
        point_dates.append(_date(point.get("date"), f"{where}.date"))
        if set(point) != {"date", "close"}:
            fail(where, "折线价格点只能包含 date 和 close；旧材料请使用 migrate-line")
        value = point.get("close")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            fail(f"{where}.close", "收盘价必须为有限正数")
    if point_dates != expected:
        missing = sorted(set(expected) - set(point_dates))
        extra = sorted(set(point_dates) - set(expected))
        fail("prices.json.points", f"日期必须与核实的预期交易日完全一致；缺失 {len(missing)} 项，额外 {len(extra)} 项")
    if not any(item.year == request["investment"]["year"] for item in point_dates):
        fail("request.json.investment.year", "该投资年份没有可用交易日收盘价")
    sources = prices.get("sources")
    if not isinstance(sources, list) or not sources:
        fail("prices.json.sources", "必须保留原始数据来源")
    for index, source in enumerate(sources):
        _validate_source(source, f"prices.json.sources[{index}]", start, end)
    snapshots = prices.get("rawSnapshots")
    if not isinstance(snapshots, list) or not snapshots:
        fail("prices.json.rawSnapshots", "须保留至少一份原始行情文件快照")
    source_urls = {source["url"] for source in sources}
    for index, snapshot in enumerate(snapshots):
        where = f"prices.json.rawSnapshots[{index}]"
        if not isinstance(snapshot, dict):
            fail(where, "必须是对象")
        relative = Path(_required_text(snapshot.get("path"), f"{where}.path"))
        if relative.is_absolute() or ".." in relative.parts:
            fail(f"{where}.path", "快照路径必须是作品目录内的相对路径")
        target = (project_root / relative).resolve()
        if not target.is_relative_to(project_root) or not target.is_file():
            fail(f"{where}.path", "快照文件缺失或越过作品目录")
        digest = _required_text(snapshot.get("sha256"), f"{where}.sha256")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
            fail(f"{where}.sha256", "必须是 SHA-256 十六进制摘要")
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest.lower():
            fail(f"{where}.sha256", "原始行情快照摘要不匹配")
        if snapshot.get("sourceUrl") not in source_urls:
            fail(f"{where}.sourceUrl", "必须引用 prices.json.sources 中的来源")
    if instrument["kind"] == "stock":
        display_end = _date(request["displayRange"][1], "request.json.displayRange")
        if _date(prices.get("adjustmentBaseDate"), "prices.json.adjustmentBaseDate") != display_end:
            fail("prices.json.adjustmentBaseDate", "拆合股调整基准必须为展示范围结束日")
        if not isinstance(prices.get("adjustmentDefinition"), str) or not prices["adjustmentDefinition"].strip():
            fail("prices.json.adjustmentDefinition", "须明确说明仅拆合股调整且不计分红再投资")
        adjustments = prices.get("splitAdjustments", [])
        if not isinstance(adjustments, list):
            fail("prices.json.splitAdjustments", "必须是数组")
        for index, adjustment in enumerate(adjustments):
            where = f"prices.json.splitAdjustments[{index}]"
            if not isinstance(adjustment, dict):
                fail(where, "必须是对象")
            _date(adjustment.get("effectiveDate"), f"{where}.effectiveDate")
            ratio = adjustment.get("newSharesPerOldShare")
            if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(ratio) or ratio <= 0:
                fail(f"{where}.newSharesPerOldShare", "必须是有限正数")
            _required_text(adjustment.get("source"), f"{where}.source")
    else:
        _required_text(prices.get("indexType"), "prices.json.indexType")


def _validate_crypto_prices(prices: dict[str, Any], request: dict[str, Any], project_root: Path) -> None:
    if prices.get("schemaVersion") != 4:
        fail("prices.json.schemaVersion", "crypto 必须使用 version 4")
    if prices.get("unit") != "USD" or prices.get("priceBasis") != "crypto-spot-close":
        fail("prices.json", "crypto 行情必须是 USD 计价的 crypto-spot-close")
    start_text, end_text = request["displayRange"]
    start, end = date.fromisoformat(start_text), date.fromisoformat(end_text)
    full_dates = expected_daily_dates(start_text, end_text)
    expected = _ordered_dates(prices.get("expectedTradingDates"), "prices.json.expectedTradingDates")
    date_sources = prices.get("expectedTradingDatesSource")
    if not isinstance(date_sources, list) or not date_sources:
        fail("prices.json.expectedTradingDatesSource", "须记录 crypto 日历日期清单来源")
    for index, url in enumerate(date_sources):
        _https_url(url, f"prices.json.expectedTradingDatesSource[{index}]")
    points = prices.get("points")
    if not isinstance(points, list) or not points:
        fail("prices.json.points", "必须包含完整 BTC/USD 日线")
    point_dates: list[date] = []
    for index, point in enumerate(points):
        where = f"prices.json.points[{index}]"
        if not isinstance(point, dict) or set(point) != {"date", "close"}:
            fail(where, "价格点只能包含 date 和 close")
        point_dates.append(_date(point.get("date"), f"{where}.date"))
        value = point.get("close")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            fail(f"{where}.close", "收盘价必须为有限正数")
    if point_dates != expected or [item.isoformat() for item in expected] != full_dates:
        fail("prices.json.points", "crypto 行情必须逐日覆盖展示日期，无缺失或额外日期")
    if request["investment"]["date"] not in full_dates:
        fail("request.json.investment.date", "买入日必须有真实 crypto 收盘价")

    sources = prices.get("sources")
    if not isinstance(sources, list) or not sources:
        fail("prices.json.sources", "必须保留 BTC 行情来源")
    source_urls: set[str] = set()
    covered: set[date] = set()
    for index, source in enumerate(sources):
        coverage_start, coverage_end = _validate_source(
            source, f"prices.json.sources[{index}]", start, end, require_full_coverage=False,
        )
        source_urls.add(source["url"])
        covered.update(day for day in expected if coverage_start <= day <= coverage_end)
    if len(covered) != len(expected):
        fail("prices.json.sources", "BTC 行情来源区间未覆盖全部展示日期")
    _validate_snapshots(prices.get("rawSnapshots"), source_urls, project_root, "prices.json.rawSnapshots")

    fx = prices.get("fx")
    if not isinstance(fx, dict) or fx.get("pair") != "USD/CNY" or fx.get("unit") != "CNY per USD":
        fail("prices.json.fx", "必须提供 USD/CNY、单位 CNY per USD 的汇率材料")
    fx_dates = _ordered_dates(fx.get("expectedTradingDates"), "prices.json.fx.expectedTradingDates")
    fx_date_sources = fx.get("expectedTradingDatesSource")
    if not isinstance(fx_date_sources, list) or not fx_date_sources:
        fail("prices.json.fx.expectedTradingDatesSource", "须记录汇率观测日期清单来源")
    for index, url in enumerate(fx_date_sources):
        _https_url(url, f"prices.json.fx.expectedTradingDatesSource[{index}]")
    fx_points = fx.get("points")
    if not isinstance(fx_points, list) or not fx_points:
        fail("prices.json.fx.points", "必须包含汇率点")
    fx_point_dates: list[date] = []
    for index, point in enumerate(fx_points):
        where = f"prices.json.fx.points[{index}]"
        if not isinstance(point, dict) or set(point) != {"date", "close"}:
            fail(where, "汇率点只能包含 date 和 close")
        fx_point_dates.append(_date(point.get("date"), f"{where}.date"))
        value = point.get("close")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            fail(f"{where}.close", "汇率必须为有限正数")
    entry_date = date.fromisoformat(request["investment"]["date"])
    if fx_dates != fx_point_dates or fx_dates[0] > entry_date or fx_dates[-1] > end:
        fail("prices.json.fx.points", "汇率点须匹配核验日期、覆盖买入日且不得使用未来汇率")
    fx_sources = fx.get("sources")
    if not isinstance(fx_sources, list) or not fx_sources:
        fail("prices.json.fx.sources", "必须保留汇率来源")
    fx_urls: set[str] = set()
    fx_covered: set[date] = set()
    for index, source in enumerate(fx_sources):
        coverage_start, coverage_end = _validate_source(source, f"prices.json.fx.sources[{index}]", start, end, require_full_coverage=False)
        fx_urls.add(source["url"])
        fx_covered.update(day for day in fx_dates if coverage_start <= day <= coverage_end)
    if len(fx_covered) != len(fx_dates):
        fail("prices.json.fx.sources", "汇率来源区间未覆盖所有汇率观测日期")
    _validate_snapshots(fx.get("rawSnapshots"), fx_urls, project_root, "prices.json.fx.rawSnapshots")
    crypto_investment_values(request, prices)


def _validate_snapshots(snapshots: Any, source_urls: set[str], project_root: Path, where: str) -> None:
    if not isinstance(snapshots, list) or not snapshots:
        fail(where, "须保留至少一份原始数据快照")
    for index, snapshot in enumerate(snapshots):
        item_where = f"{where}[{index}]"
        if not isinstance(snapshot, dict):
            fail(item_where, "必须是对象")
        relative = Path(_required_text(snapshot.get("path"), f"{item_where}.path"))
        if relative.is_absolute() or ".." in relative.parts:
            fail(f"{item_where}.path", "快照路径必须是作品目录内的相对路径")
        target = (project_root / relative).resolve()
        if not target.is_relative_to(project_root) or not target.is_file():
            fail(f"{item_where}.path", "快照文件缺失或越过作品目录")
        digest = _required_text(snapshot.get("sha256"), f"{item_where}.sha256")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
            fail(f"{item_where}.sha256", "必须是 SHA-256 十六进制摘要")
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest.lower():
            fail(f"{item_where}.sha256", "原始数据快照摘要不匹配")
        if snapshot.get("sourceUrl") not in source_urls:
            fail(f"{item_where}.sourceUrl", "必须引用对应来源清单中的来源")


def _validate_source(source: Any, where: str, start: date, end: date, *, require_full_coverage: bool = True) -> tuple[date, date]:
    if not isinstance(source, dict):
        fail(where, "必须是对象")
    url = _https_url(source.get("url"), f"{where}.url")
    fetched = _required_text(source.get("fetchedAt"), f"{where}.fetchedAt")
    try:
        parsed = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
    except ValueError:
        fail(f"{where}.fetchedAt", "必须包含时区的 ISO-8601 时间")
    if parsed.tzinfo is None:
        fail(f"{where}.fetchedAt", "必须包含时区")
    coverage = source.get("coverage")
    if not isinstance(coverage, list) or len(coverage) != 2:
        fail(f"{where}.coverage", "必须是 [开始日期, 结束日期]")
    covered_start, covered_end = (_date(item, f"{where}.coverage") for item in coverage)
    if require_full_coverage and (covered_start > start or covered_end < end):
        fail(f"{where}.coverage", "来源覆盖范围未覆盖完整展示日期")
    _required_text(source.get("adjustmentDefinition"), f"{where}.adjustmentDefinition")
    return covered_start, covered_end


def _validate_plan(plan: dict[str, Any], request: dict[str, Any], prices: dict[str, Any]) -> None:
    if plan.get("fps") != FPS or plan.get("canvas") != {"width": WIDTH, "height": HEIGHT}:
        fail("animation-plan.json", "必须使用 1080×1920、60 fps")
    duration = plan.get("durationSeconds")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration < (4 if plan.get("schemaVersion") == 8 else 10):
        fail("animation-plan.json.durationSeconds", "无事件 v8 计划至少为 4 秒；v7 计划至少为 10 秒")
    total_frames = duration * FPS
    ending_frames = 120 if plan.get("schemaVersion") == 7 else None
    opening_frames = 90 if plan.get("schemaVersion") == 7 else None
    axis = plan.get("axis")
    if not isinstance(axis, dict) or axis.get("dateRange") != request["displayRange"]:
        fail("animation-plan.json.axis.dateRange", "必须与实际展示范围一致")
    if plan.get("schemaVersion") not in {7, 8} or plan.get("chartType") != "line":
        fail("animation-plan.json", "必须为 version 7/8、chartType=line；旧材料请使用 migrate-line")
    if any(key in plan for key in ("selectedPeriod", "selectionReport", "eventDisplays")) or "visibleWindowBars" in axis:
        fail("animation-plan.json", "计划包含已移除的周期、柱数或事件字段；请使用 migrate-line")
    if "visibleWindowMonths" in axis:
        fail("animation-plan.json.axis.visibleWindowMonths", "滚动窗口已移除；请使用 migrate-line")
    if axis.get("dateScale") != "staged-expanding":
        fail("animation-plan.json.axis.dateScale", "必须使用 staged-expanding 分阶段扩展横轴")
    if axis.get("valueScale") != "revealed-linear":
        fail("animation-plan.json.axis.valueScale", "必须使用 revealed-linear 已展示组合价值自适应纵轴")
    if "valueRange" in axis:
        fail("animation-plan.json.axis.valueRange", "纵轴由已展示组合价值动态计算，不接受固定 valueRange")
    segments = plan.get("segments")
    if not isinstance(segments, list) or len(segments) != 3:
        fail("animation-plan.json.segments", "必须恰有 opening、advance 和 ending 三段")
    display_start, display_end = (_date(item, "request.json.displayRange") for item in request["displayRange"])
    previous_frame = 0
    previous_date: date | None = None
    for index, segment in enumerate(segments):
        where = f"animation-plan.json.segments[{index}]"
        if not isinstance(segment, dict):
            fail(where, "必须是对象")
        frames = segment.get("frames")
        dates = segment.get("dates")
        if not isinstance(frames, list) or len(frames) != 2 or any(isinstance(x, bool) or not isinstance(x, int) for x in frames):
            fail(f"{where}.frames", "必须是整数半开帧区间 [开始, 结束)")
        start_frame, end_frame = frames
        if start_frame != previous_frame or end_frame <= start_frame or end_frame > total_frames:
            fail(f"{where}.frames", "时间段必须从 0 连续、无重叠地覆盖至总帧数")
        if not isinstance(dates, list) or len(dates) != 2:
            fail(f"{where}.dates", "必须是起止日组成的数组")
        date_start, date_end = (_date(item, f"{where}.dates") for item in dates)
        if date_start > date_end or date_start < display_start or date_end > display_end:
            fail(f"{where}.dates", "日期必须递增且位于展示范围")
        if previous_date is not None and date_start != previous_date:
            fail(f"{where}.dates", "相邻时间段日期边界必须连续")
        kind = segment.get("kind")
        if kind not in {"opening", "advance", "ending"}:
            fail(f"{where}.kind", "只能为 opening、advance 或 ending；不接受事件停顿")
        if kind == "advance" and ((date_start >= date_end and display_start != display_end) or end_frame - start_frame < 2):
            fail(where, "多日 advance 必须跨日期且至少占两帧；单日范围允许日期不变")
        if kind in {"opening", "ending"} and date_start != date_end:
            fail(where, f"{kind} 段必须停留在同一日期")
        if index == 0 and (kind != "opening" or start_frame != 0 or date_start != display_start):
            fail(where, "首段必须从第 0 帧在展示起始日 opening")
        if index == len(segments) - 1 and (kind != "ending" or date_end != display_end or end_frame != total_frames or (ending_frames is not None and end_frame - start_frame != ending_frames)):
            fail(where, "尾段必须在展示结束日停留规定帧数并覆盖终帧")
        if index not in {0, len(segments) - 1} and kind in {"opening", "ending"}:
            fail(where, "opening 与 ending 只能位于首尾")
        previous_frame, previous_date = end_frame, date_end
    if previous_frame != total_frames or previous_date != display_end:
        fail("animation-plan.json.segments", "时间段必须覆盖完整时长和展示日期")
    expected_kinds = ["opening", "advance", "ending"]
    if [segment["kind"] for segment in segments] != expected_kinds:
        fail("animation-plan.json.segments", "三段顺序必须为 opening、advance、ending")
    opening_end = segments[0]["frames"][1]
    advance_end = segments[2]["frames"][0]
    if plan["schemaVersion"] == 7 and (opening_end != opening_frames or advance_end != total_frames - ending_frames):
        fail("animation-plan.json.segments", "v7 opening 与 ending 帧数必须保持原值")
    if plan["schemaVersion"] == 8 and (opening_end, total_frames - advance_end) not in {(FPS, 2 * FPS), (3 * FPS, 6 * FPS)}:
        fail("animation-plan.json.segments", "v8 仅接受 60/120 帧或 180/360 帧开场/结尾")
    if segments[1]["frames"] != [opening_end, advance_end]:
        fail("animation-plan.json.segments", "advance 必须连续覆盖到规定结尾之前")
    if segments[2]["frames"] != [advance_end, total_frames]:
        fail("animation-plan.json.segments", "ending 必须覆盖至终帧")
    if plan["schemaVersion"] == 8:
        _validate_pacing(plan, display_start, display_end, opening_end, advance_end)
    _required_text(plan.get("rationale"), "animation-plan.json.rationale")


def _validate_pacing(plan: dict[str, Any], start: date, end: date, opening_end: int, advance_end: int) -> None:
    pacing = plan.get("pacing")
    if not isinstance(pacing, dict) or pacing.get("mode") not in {"uniform", "volatility"}:
        fail("animation-plan.json.pacing", "须声明 uniform 或 volatility 节奏模式")
    anchors = pacing.get("anchors")
    if not isinstance(anchors, list) or len(anchors) < 2:
        fail("animation-plan.json.pacing.anchors", "须至少包含推进首末两个锚点")
    previous_frame, previous_date = opening_end - 1, start
    for index, anchor in enumerate(anchors):
        where = f"animation-plan.json.pacing.anchors[{index}]"
        if not isinstance(anchor, dict) or type(anchor.get("frame")) is not int:
            fail(where, "锚点须包含整数 frame 和日期 date")
        frame = anchor["frame"]
        day = _date(anchor.get("date"), where)
        if not previous_frame < frame < advance_end or not previous_date <= day <= end:
            fail(where, "锚点帧须严格递增且位于推进范围，日期须单调且位于展示范围")
        previous_frame, previous_date = frame, day
    if anchors[0] != {"frame": opening_end, "date": start.isoformat()} or anchors[-1] != {"frame": advance_end - 1, "date": end.isoformat()}:
        fail("animation-plan.json.pacing.anchors", "锚点须精确覆盖推进首末帧和展示起止日")
    if pacing["mode"] == "uniform" and len(anchors) != 2:
        fail("animation-plan.json.pacing.anchors", "uniform 模式仅接受首末两个锚点")


def load_project(project_dir: str | Path) -> dict[str, Any]:
    """Load and cross-validate the three immutable, offline-render inputs."""
    root = Path(project_dir).resolve()
    if not root.is_dir():
        fail("作品目录", f"目录不存在：{root}")
    docs = {name: _load(root / name) for name in MATERIALS}
    request, prices, plan = (docs[name] for name in MATERIALS)
    if request["schemaVersion"] != 1:
        fail("request.json", "当前必须为 version 1")
    instrument = request.get("instrument")
    kind = instrument.get("kind") if isinstance(instrument, dict) else None
    expected_price_version = 4 if kind == "crypto" else 3
    if prices["schemaVersion"] != expected_price_version or plan["schemaVersion"] not in {7, 8}:
        fail("材料版本", f"需要 v{expected_price_version} 价格和 v7/v8 动画计划；请运行 financial_video.py migrate-line --project-dir <作品目录>")
    if (root / "events.json").exists():
        fail("events.json", "事件材料已移除；请运行 financial_video.py migrate-line --project-dir <作品目录> 清理旧材料")
    _validate_request(request)
    _validate_prices(prices, request, root)
    _validate_plan(plan, request, prices)
    return {"request": request, "prices": prices, "plan": plan}


def render_inputs_digest(project_dir: str | Path) -> str:
    """Bind a full preview to exact materials and shared rendering sources."""
    root = Path(project_dir).resolve()
    from m2v.core.assets import REPOSITORY_ROOT
    web = REPOSITORY_ROOT / "web"
    inputs = [(root, root / name) for name in MATERIALS]
    import m2v.engine.remotion as remotion
    from m2v.engine import render_pipeline
    inputs.extend((web, path) for path in remotion.build_inputs() if path.is_relative_to(web))
    inputs.extend((REPOSITORY_ROOT, path) for path in remotion.build_inputs() if not path.is_relative_to(web))
    scripts = Path(__file__).resolve().parents[2]
    inputs.extend((scripts, path) for path in (
        Path(__file__), Path(__file__).with_name("financial_render.py"),
        Path(__file__).with_name("commands.py"), Path(__file__).with_name("pacing.py"),
        Path(__file__).with_name("valuation.py"), *remotion.implementation_files(),
        Path(render_pipeline.__file__),
    ))
    digest = hashlib.sha256()
    for base, path in inputs:
        try:
            content = path.read_bytes()
        except OSError as exc:
            fail("渲染输入摘要", f"无法读取绑定文件 {path.name}：{exc}")
        digest.update(path.relative_to(base).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()


def build_render_props(docs: dict[str, Any]) -> dict[str, Any]:
    plan = docs["plan"]
    prices = docs["prices"]
    return {
        "request": docs["request"], "prices": prices,
        "plan": plan, "durationInFrames": plan["durationSeconds"] * FPS,
        "fps": FPS, "width": WIDTH, "height": HEIGHT,
    }
