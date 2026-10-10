"""Financial time-series materials and deterministic timeline validation."""
from __future__ import annotations

import json
import hashlib
import math
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .errors import A2VError

MATERIALS = ("request.json", "prices.json", "animation-plan.json")
FPS = 30
WIDTH = 1080
HEIGHT = 1920


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
    if type(data.get("schemaVersion")) is not int or data.get("schemaVersion") not in {1, 2, 3, 4, 5, 6, 7}:
        _fail(path.name, "schemaVersion 必须为 1 至 7 的整数")
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
    """Load and cross-validate the three immutable, offline-render inputs."""
    root = Path(project_dir).resolve()
    if not root.is_dir():
        _fail("作品目录", f"目录不存在：{root}")
    docs = {name: _load(root / name) for name in MATERIALS}
    request, prices, plan = (docs[name] for name in MATERIALS)
    if request["schemaVersion"] != 1:
        _fail("request.json", "当前必须为 version 1")
    if prices["schemaVersion"] != 3 or plan["schemaVersion"] != 7:
        _fail("材料版本", "需要 v3 价格和 v7 动画计划；请运行 financial_video.py migrate-line --project-dir <作品目录>")
    if (root / "events.json").exists():
        _fail("events.json", "事件材料已移除；请运行 financial_video.py migrate-line --project-dir <作品目录> 清理旧材料")
    _validate_request(request)
    _validate_prices(prices, request, root)
    _validate_plan(plan, request, prices)
    return {"request": request, "prices": prices, "plan": plan}


def legibility_review_digest(project_dir: str | Path) -> str:
    """Bind the visual review to exact materials and shared rendering sources."""
    root = Path(project_dir).resolve()
    web = Path(__file__).resolve().parents[5] / "web"
    inputs = [(root, root / name) for name in MATERIALS]
    from . import remotion
    # 金融画面是共享受信代码，从不加载作品级代码场景：显式声明空模块集，
    # 避免共享的 .gen/scene-manifest.json 残留上一篇文章的场景而污染摘要。
    inputs.extend((web, path) for path in remotion.build_inputs(scene_modules=()))
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
    if not isinstance(review, dict) or review.get("schemaVersion") != 2:
        _fail("outputs/legibility-review.json", "schemaVersion 必须为 2（含手机缩放证据）")
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
    for key in ("mobileScale", "safeArea"):
        item = evidence.get(key)
        if not isinstance(item, dict) or item.get("reviewed") is not True or not isinstance(item.get("details"), str) or not item["details"].strip():
            _fail(f"outputs/legibility-review.json.evidence.{key}", "须记录已检查状态和可复核证据")



def _validate_request(request: dict[str, Any]) -> None:
    instrument = request.get("instrument")
    _required_text(request.get("originalRequest"), "request.json.originalRequest")
    if not isinstance(instrument, dict):
        _fail("request.json.instrument", "必须声明标的对象")
    if instrument.get("kind") not in {"stock", "index"}:
        _fail("request.json.instrument.kind", "必须为 stock 或 index")
    for key in ("name", "code", "market", "unit"):
        _required_text(instrument.get(key), f"request.json.instrument.{key}")
    if "displayName" in instrument:
        _required_text(instrument["displayName"], "request.json.instrument.displayName")
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
    investment = request.setdefault("investment", {"year": display_dates[0].year, "principal": 1_000_000})
    if not isinstance(investment, dict):
        _fail("request.json.investment", "必须为 year 和 principal 组成的对象")
    year = investment.get("year")
    principal = investment.get("principal")
    if isinstance(year, bool) or not isinstance(year, int) or year < display_dates[0].year or year > display_dates[1].year:
        _fail("request.json.investment.year", "必须是展示范围内的有效年份")
    if isinstance(principal, bool) or not isinstance(principal, (int, float)) or not math.isfinite(principal) or principal <= 0:
        _fail("request.json.investment.principal", "必须是有限正数")
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
    if not any(item.year == request["investment"]["year"] for item in point_dates):
        _fail("request.json.investment.year", "该投资年份没有可用交易日收盘价")
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


def build_line_plan(request: dict[str, Any], duration: int = 60) -> dict[str, Any]:
    """Build a deterministic, event-free timeline with staged date-axis expansion."""
    if type(duration) is not int:
        raise A2VError("时长必须为整数")
    if duration < 10:
        raise A2VError("无事件计划至少需要 10 秒：开场 3 秒、行情推进及结尾 4 秒")
    start, end = (date.fromisoformat(value) for value in request["displayRange"])
    total_frames = duration * FPS
    advance_end = total_frames - 120
    segments = [
        {"frames": [0, 90], "dates": [start.isoformat(), start.isoformat()], "kind": "opening"},
        {"frames": [90, advance_end], "dates": [start.isoformat(), end.isoformat()], "kind": "advance"},
        {"frames": [advance_end, total_frames], "dates": [end.isoformat(), end.isoformat()], "kind": "ending"},
    ]
    return {
        "schemaVersion": 7, "chartType": "line", "durationSeconds": duration, "fps": FPS,
        "canvas": {"width": WIDTH, "height": HEIGHT},
        "axis": {"dateRange": request["displayRange"], "dateScale": "staged-expanding", "valueScale": "revealed-linear"},
        "segments": segments,
        "rationale": "以真实日收盘价计算假设投资组合价值，横轴按年度阶段平滑扩展；开场 3 秒、连续推进、完整历史停留 4 秒，纵轴随已展示组合价值自适应。",
    }


def prepare_line_plan(root: Path, duration: int) -> dict[str, Any]:
    if (root / "events.json").exists():
        _fail("events.json", "事件材料已移除；请先显式运行 migrate-line 清理旧材料")
    request, prices = (_load(root / name) for name in MATERIALS[:2])
    old_plan = _load(root / "animation-plan.json")
    if old_plan.get("schemaVersion") != 7:
        _fail("animation-plan.json", "旧计划请先显式运行 migrate-line，备份后迁移到 v7")
    if request["schemaVersion"] != 1 or prices["schemaVersion"] != 3:
        _fail("材料版本", "需 version 1 请求和 version 3 价格；旧材料请运行 migrate-line")
    _validate_request(request)
    _validate_prices(prices, request, root)
    plan = build_line_plan(request, duration)
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
    request, prices, old_plan = (_load(root / name) for name in source_names)
    if old_plan["schemaVersion"] == 7:
        _fail("材料版本", "计划已是 v7，拒绝重复迁移")
    if request["schemaVersion"] != 1:
        _fail("request.json", "迁移仅接受 version 1 请求材料")
    if prices["schemaVersion"] not in {1, 2, 3} or old_plan["schemaVersion"] not in {1, 2, 3, 4, 5, 6}:
        _fail("材料版本", "迁移仅接受旧 version 1/2 价格或 version 3/4/5 折线计划")
    if prices["schemaVersion"] in {1, 2} and prices["schemaVersion"] != old_plan["schemaVersion"]:
        _fail("材料版本", "旧价格与计划版本不一致；拒绝混合迁移")
    if prices["schemaVersion"] == 3 and old_plan["schemaVersion"] not in {3, 4, 5, 6}:
        _fail("材料版本", "v3 价格必须与 v3/v4/v5 动画计划一起迁移")
    points = prices.get("points")
    if not isinstance(points, list) or any(not isinstance(point, dict) for point in points):
        _fail("prices.json.points", "旧价格点须为对象数组")
    normalized = {**prices, "schemaVersion": 3, "points": [{"date": point.get("date"), "close": point.get("close")} for point in points]}
    _validate_request(request)
    _validate_prices(normalized, request, root)
    plan = build_line_plan(request, duration)
    _validate_plan(plan, request, normalized)
    backups = root / "outputs" / "material-backups"
    backups.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=f"before-line-v{old_plan['schemaVersion']}-", dir=backups))
    for name, content in originals.items():
        (backup / name).write_bytes(content)
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
    except (OSError, A2VError):
        for name, content in originals.items():
            (root / name).write_bytes(content)
        if event_original is not None:
            event_path.write_bytes(event_original)
        if review_original is not None:
            review_path.write_bytes(review_original)
        if preview_original is not None:
            preview_record.write_bytes(preview_original)
        raise
    return backup


REVIEW_CHECKS = ("labelsReadable", "advanceTrackable", "stagedAxisStable", "axisStable", "overviewComplete")


def review_metrics(docs: dict[str, Any]) -> dict[str, Any]:
    return {"durationSeconds": docs["plan"]["durationSeconds"], "dateScale": "staged-expanding", "valueScale": "revealed-linear", "endingSeconds": 4,
            "canvas": {"width": WIDTH, "height": HEIGHT}, "mobileCheck": {"width": 360, "height": 640},
            "safeArea": {"x": [64, 1016], "y": [180, 1500]}}


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


def _validate_plan(plan: dict[str, Any], request: dict[str, Any], prices: dict[str, Any]) -> None:
    if plan.get("fps") != FPS or plan.get("canvas") != {"width": WIDTH, "height": HEIGHT}:
        _fail("animation-plan.json", "必须使用 1080×1920、30 fps")
    duration = plan.get("durationSeconds")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration < 10:
        _fail("animation-plan.json.durationSeconds", "无事件计划必须至少为 10 秒")
    total_frames = duration * FPS
    axis = plan.get("axis")
    if not isinstance(axis, dict) or axis.get("dateRange") != request["displayRange"]:
        _fail("animation-plan.json.axis.dateRange", "必须与实际展示范围一致")
    if plan.get("schemaVersion") != 7 or plan.get("chartType") != "line":
        _fail("animation-plan.json", "必须为 version 7、chartType=line；旧材料请使用 migrate-line")
    if any(key in plan for key in ("selectedPeriod", "selectionReport", "eventDisplays")) or "visibleWindowBars" in axis:
        _fail("animation-plan.json", "计划包含已移除的周期、柱数或事件字段；请使用 migrate-line")
    if "visibleWindowMonths" in axis:
        _fail("animation-plan.json.axis.visibleWindowMonths", "滚动窗口已移除；请使用 migrate-line")
    if axis.get("dateScale") != "staged-expanding":
        _fail("animation-plan.json.axis.dateScale", "必须使用 staged-expanding 分阶段扩展横轴")
    if axis.get("valueScale") != "revealed-linear":
        _fail("animation-plan.json.axis.valueScale", "必须使用 revealed-linear 已展示组合价值自适应纵轴")
    if "valueRange" in axis:
        _fail("animation-plan.json.axis.valueRange", "纵轴由已展示组合价值动态计算，不接受固定 valueRange")
    segments = plan.get("segments")
    if not isinstance(segments, list) or len(segments) != 3:
        _fail("animation-plan.json.segments", "必须恰有 opening、advance 和 ending 三段")
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
        if kind not in {"opening", "advance", "ending"}:
            _fail(f"{where}.kind", "只能为 opening、advance 或 ending；不接受事件停顿")
        if kind == "advance" and ((date_start >= date_end and display_start != display_end) or end_frame - start_frame < 2):
            _fail(where, "多日 advance 必须跨日期且至少占两帧；单日范围允许日期不变")
        if kind in {"opening", "ending"} and date_start != date_end:
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
    expected_kinds = ["opening", "advance", "ending"]
    if [segment["kind"] for segment in segments] != expected_kinds:
        _fail("animation-plan.json.segments", "三段顺序必须为 opening、advance、ending")
    advance_end = total_frames - 120
    if segments[0]["frames"] != [0, 90] or segments[1]["frames"] != [90, advance_end]:
        _fail("animation-plan.json.segments", "opening 固定 90 帧，advance 必须覆盖到结尾前 120 帧")
    if segments[2]["frames"] != [advance_end, total_frames]:
        _fail("animation-plan.json.segments", "ending 必须停留 120 帧")
    _required_text(plan.get("rationale"), "animation-plan.json.rationale")


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
        "request": docs["request"], "prices": prices,
        "plan": plan, "durationInFrames": plan["durationSeconds"] * FPS,
        "fps": FPS, "width": WIDTH, "height": HEIGHT,
    }
