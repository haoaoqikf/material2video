"""真实驾车路线材料的共享校验原语。

`driving-route` 与 `road-trip` 都保存高德返回的真实路线：定位点、道路步骤、
成本、城市与行政区。两份契约曾经各写一遍这些规则，错误文案也会随修改漂移。
这里只放**两个类型都成立**的判定；类型自己的材料形状、绑定摘要与渲染字段仍
留在各自模块。

依赖方向：共享底座不导入任何类型包，只依赖 `m2v.core`。
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from m2v.core.geodesy import EARTH_RADIUS_METERS, distance_meters
from m2v.core.schema import validate_document
from m2v.core.validate import fail, obj, text
from m2v.types.route_schema import Place, SourceUsage

#: 球面距离口径；只用于沿路进度与连续性判定，不冒充公路里程。
__all__ = ["EARTH_RADIUS_METERS", "haversine_meters"]

#: 相邻道路段端点的服务采样容差。
STEP_TOLERANCE_METERS = 25.0
#: 路线实际端点与定位点的最大距离。
ENDPOINT_TOLERANCE_METERS = 1000.0
#: 保存的起终点与实际路线首尾点的最大差异。
START_END_TOLERANCE_METERS = 1.0

#: 城市级或更粗的定位不能证明地址唯一，直接拒绝。
COARSE_LEVELS = frozenset({"国家", "省份", "城市", "区县", "乡镇"})

#: 初始化模板中的占位文字；校验时必须替换。
PLACEHOLDER = re.compile(r"^(填写|待填写|待\s*fetch|YYYY-MM-DD)")

_CITY_SUFFIX = re.compile(r"(市|地区|盟|自治州|特别行政区)$")


def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON 对象包含重复键 {key!r}")
        result[key] = value
    return result


def load_json(path: Path, expected_version: int, *, hint: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs_hook)
    except (OSError, UnicodeError, ValueError) as exc:
        fail(path.name, f"无法读取有效 UTF-8 JSON：{exc}")
    if not isinstance(data, dict):
        fail(path.name, "顶层必须是 JSON 对象")
    if type(data.get("schemaVersion")) is not int or data["schemaVersion"] != expected_version:
        fail(f"{path.name}.schemaVersion", f"当前必须为 {expected_version}；{hint}")
    return data


def content_text(value: Any, where: str) -> str:
    """非空文本，并拒绝初始化模板留下的占位内容。"""
    result = text(value, where).strip()
    if PLACEHOLDER.match(result):
        fail(where, f"仍是占位内容：{result!r}；请填写真实信息")
    return result


def date_text(value: Any, where: str) -> date:
    if not isinstance(value, str):
        fail(where, "必须是 YYYY-MM-DD 日期字符串")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        fail(where, f"不是有效日期：{value!r}")
    if parsed.isoformat() != value:
        fail(where, f"日期必须使用 YYYY-MM-DD：{value!r}")
    return parsed


def https_url(value: Any, where: str) -> str:
    url = content_text(value, where)
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == "https" and bool(parsed.hostname)
                 and parsed.username is None and parsed.password is None)
    except ValueError:
        valid = False
    if not valid:
        fail(where, "必须是有效 HTTPS 链接且不能包含内嵌凭据")
    return url


def finite_number(value: Any, where: str, *, low: float | None = None,
                  high: float | None = None) -> float:
    if type(value) not in (int, float):
        fail(where, "必须是有限数字")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        fail(where, "超出可表示的有限范围")
    if not math.isfinite(number):
        fail(where, "必须是有限数字")
    if low is not None and number < low:
        fail(where, f"必须不小于 {low:g}")
    if high is not None and number > high:
        fail(where, f"必须不大于 {high:g}")
    return number


def positive_number(value: Any, where: str) -> float:
    result = finite_number(value, where)
    if result <= 0:
        fail(where, "必须大于 0")
    return result


def coordinate(value: Any, where: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        fail(where, "必须是 [经度, 纬度] 坐标")
    lng = finite_number(value[0], f"{where}[0]", low=-180, high=180)
    lat = finite_number(value[1], f"{where}[1]", low=-90, high=90)
    return lng, lat


def point_list(value: Any, where: str) -> list[tuple[float, float]]:
    if not isinstance(value, list) or not 2 <= len(value) <= 50000:
        fail(where, "必须是至少两个坐标点的数组")
    return [coordinate(item, f"{where}[{index}]") for index, item in enumerate(value)]


def haversine_meters(a: tuple[float, float], b: tuple[float, float]) -> float:
    """两点间球面距离（米）；经纬度顺序为 (经度, 纬度)。"""
    return distance_meters(a, b)


def _normalize_city(value: str) -> str:
    return _CITY_SUFFIX.sub("", value.strip())


def same_city(first: str, second: str) -> bool:
    """比较城市名时忽略“市/地区/自治州”等行政后缀。"""
    return bool(first.strip()) and bool(second.strip()) and _normalize_city(first) == _normalize_city(second)


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                         allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_place(value: Any, where: str) -> None:
    validate_document(Place, value, where)
    for field in ("city", "address", "label"):
        content_text(value.get(field), f"{where}.{field}")


def validate_source_usage(value: Any, where: str) -> None:
    validate_document(SourceUsage, value, where)
    date_text(value.get("verifiedOn"), f"{where}.verifiedOn")
    documents = value["documents"]
    if not 1 <= len(documents) <= 8:
        fail(f"{where}.documents", "必须记录 1～8 份政策或授权文档引用")
    for index, document in enumerate(documents):
        item_where = f"{where}.documents[{index}]"
        content_text(document.get("title"), f"{item_where}.title")
        https_url(document.get("url"), f"{item_where}.url")
        if "note" in document:
            content_text(document["note"], f"{item_where}.note")
    content_text(value.get("account"), f"{where}.account")
    content_text(value.get("purpose"), f"{where}.purpose")
    for field in ("offlineStorage", "derivativeFrames", "videoPublication"):
        if value.get(field) is not True:
            fail(f"{where}.{field}", "必须确认该用途已获授权（true）；未落实时不得取数或制作")
    content_text(value.get("attribution"), f"{where}.attribution")


def validate_geocoded_place(value: Any, where: str, expected_city: str) -> tuple[float, float]:
    place = obj(value, where, {"location", "formattedAddress", "city", "level"})
    location = coordinate(place.get("location"), f"{where}.location")
    content_text(place.get("formattedAddress"), f"{where}.formattedAddress")
    city = content_text(place.get("city"), f"{where}.city")
    level = content_text(place.get("level"), f"{where}.level")
    if level in COARSE_LEVELS:
        fail(f"{where}.level", f"定位精度仅到「{level}」，不是具体地点；请提供更具体的地址后重新取数")
    if _normalize_city(city) != _normalize_city(expected_city):
        fail(f"{where}.city", f"定位城市 {city!r} 与请求城市 {expected_city!r} 不一致；"
                              "请核对地址后重新取数")
    return location


def validate_acquisition(value: Any, *, strategy: int, where: str = "acquisition") -> None:
    acquisition = obj(value, where, {"provider", "service", "apiVersion", "strategy",
                                     "requestedAt", "requests"})
    for field, expected in (("provider", "amap"), ("service", "webservice"), ("apiVersion", "v5")):
        if acquisition.get(field) != expected:
            fail(f"{where}.{field}", f"当前必须为 {expected!r}")
    if type(acquisition.get("strategy")) is not int or acquisition["strategy"] != strategy:
        fail(f"{where}.strategy", f"必须是当前路线策略代码 {strategy}")
    requested_at = text(acquisition.get("requestedAt"), f"{where}.requestedAt")
    try:
        parsed = datetime.fromisoformat(requested_at)
    except ValueError:
        fail(f"{where}.requestedAt", f"不是有效 ISO 时间：{requested_at!r}")
    if parsed.tzinfo is None:
        fail(f"{where}.requestedAt", "必须包含时区")
    requests = acquisition.get("requests")
    if not isinstance(requests, list) or not 1 <= len(requests) <= 400:
        fail(f"{where}.requests", "必须记录 1～400 条不含凭据的请求")
    recorded_paths: set[str] = set()
    for index, raw in enumerate(requests):
        item_where = f"{where}.requests[{index}]"
        item = obj(raw, item_where, {"path", "params"})
        path = text(item.get("path"), f"{item_where}.path")
        if not path.startswith("/"):
            fail(f"{item_where}.path", "必须是服务路径，例如 /v5/direction/driving")
        recorded_paths.add(path)
        params = item.get("params")
        if not isinstance(params, dict) or not params:
            fail(f"{item_where}.params", "必须记录非空的请求参数")
        for key, param in params.items():
            normalized_key = key.lower().replace("-", "_")
            if "key" in normalized_key and normalized_key != "keywords":
                fail(f"{item_where}.params", "不得保存凭据字段；Key 只能来自环境变量")
            if not isinstance(param, str) or not param.strip():
                fail(f"{item_where}.params.{key}", "必须是记录用的非空字符串")
    expected_requests = {"/v3/geocode/geo", "/v5/direction/driving", "/v3/config/district"}
    if not expected_requests.issubset(recorded_paths):
        fail(f"{where}.requests", "必须同时记录定位、驾车规划与行政区请求")


def validate_request_record(value: Any, where: str) -> None:
    request = obj(value, where, {"path", "params"})
    path_text = text(request.get("path"), f"{where}.path")
    if not path_text.startswith("/"):
        fail(f"{where}.path", "必须是服务路径")
    params = request.get("params")
    if not isinstance(params, dict) or not params:
        fail(f"{where}.params", "必须记录非空请求参数")
    for key, value_text in params.items():
        normalized_key = key.lower().replace("-", "_")
        if "key" in normalized_key and normalized_key != "keywords":
            fail(f"{where}.params", "不得保存凭据字段")
        if not isinstance(value_text, str) or not value_text.strip():
            fail(f"{where}.params.{key}", "必须是记录用的非空字符串")


def validate_bbox(value: Any, where: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 4:
        fail(where, "必须是 [minLng, minLat, maxLng, maxLat]")
    min_lng = finite_number(value[0], f"{where}[0]", low=-180, high=180)
    min_lat = finite_number(value[1], f"{where}[1]", low=-90, high=90)
    max_lng = finite_number(value[2], f"{where}[2]", low=-180, high=180)
    max_lat = finite_number(value[3], f"{where}[3]", low=-90, high=90)
    if not (min_lng < max_lng and min_lat < max_lat):
        fail(where, "最小经纬度必须小于最大经纬度")
    return [min_lng, min_lat, max_lng, max_lat]


def validate_steps(steps: Any, where: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """道路步骤的连续性判定；返回首尾坐标。"""
    if not isinstance(steps, list) or not 1 <= len(steps) <= 5000:
        fail(where, "必须包含 1～5000 个道路段")
    previous_last: tuple[float, float] | None = None
    first_point: tuple[float, float] | None = None
    last_point: tuple[float, float] | None = None
    for index, raw in enumerate(steps):
        item_where = f"{where}[{index}]"
        step = obj(raw, item_where, {"road", "distanceMeters", "points"})
        content_text(step.get("road"), f"{item_where}.road")
        finite_number(step.get("distanceMeters"), f"{item_where}.distanceMeters", low=0)
        points = point_list(step.get("points"), f"{item_where}.points")
        if first_point is None:
            first_point = points[0]
        if previous_last is not None:
            gap = haversine_meters(previous_last, points[0])
            if gap > STEP_TOLERANCE_METERS:
                fail(item_where, f"与上一段终点相距 {gap:.1f} 米，超过 {STEP_TOLERANCE_METERS:g} 米容差；"
                                 "拒绝跨缺口连接")
        previous_last = points[-1]
        last_point = points[-1]
    assert first_point is not None and last_point is not None
    return first_point, last_point


def route_length(steps: list[dict[str, Any]]) -> float:
    total = 0.0
    for step in steps:
        points = step["points"]
        for index in range(1, len(points)):
            total += haversine_meters(tuple(points[index - 1]), tuple(points[index]))
    return total


def validate_cost(value: Any, distance_meters: float, where: str = "cost") -> None:
    cost = obj(value, where, {"durationSeconds", "tollsYuan", "tollDistanceMeters", "trafficLights"})
    fields = (("durationSeconds", "预计耗时", 1), ("tollsYuan", "过路费", 0),
              ("tollDistanceMeters", "收费里程", 0), ("trafficLights", "红绿灯", 0))
    for field, label, minimum in fields:
        item = cost.get(field)
        if type(item) is not int or item < minimum:
            fail(f"{where}.{field}", f"{label}必须是不小于 {minimum} 的整数")
    if cost["tollDistanceMeters"] > distance_meters + 1:
        fail(f"{where}.tollDistanceMeters", "不能超过路线总距离")


def validate_cities(value: Any, where: str = "cities") -> None:
    if not isinstance(value, list) or len(value) > 100:
        fail(where, "必须是最多 100 项的城市数组")
    seen: set[str] = set()
    for index, raw in enumerate(value):
        item_where = f"{where}[{index}]"
        city = obj(raw, item_where, {"name", "adcode", "location"})
        name = content_text(city.get("name"), f"{item_where}.name")
        adcode = content_text(city.get("adcode"), f"{item_where}.adcode")
        coordinate(city.get("location"), f"{item_where}.location")
        if not re.fullmatch(r"\d{6}", adcode):
            fail(f"{item_where}.adcode", "必须是 6 位行政区划代码")
        if name in seen:
            fail(item_where, f"城市重复：{name}")
        seen.add(name)


def validate_administrative_places(value: Any, cities: list[dict[str, Any]],
                                    where: str = "administrativePlaces") -> None:
    if not isinstance(value, list) or not 1 <= len(value) <= 1000:
        fail(where, "必须包含 1～1000 个市/县行政区中心点")
    city_adcodes = {city["adcode"] for city in cities}
    seen: set[str] = set()
    city_places: set[str] = set()
    for index, raw in enumerate(value):
        item_where = f"{where}[{index}]"
        place = obj(raw, item_where, {"name", "level", "adcode", "center", "parentAdcode"})
        name = content_text(place.get("name"), f"{item_where}.name")
        level = place.get("level")
        if level not in {"city", "county"}:
            fail(f"{item_where}.level", "必须为 city 或 county")
        adcode = content_text(place.get("adcode"), f"{item_where}.adcode")
        if not re.fullmatch(r"\d{6}", adcode):
            fail(f"{item_where}.adcode", "必须是 6 位行政区划代码")
        if adcode in seen:
            fail(item_where, f"行政区重复：{name}")
        seen.add(adcode)
        coordinate(place.get("center"), f"{item_where}.center")
        if level == "city":
            if adcode not in city_adcodes:
                fail(f"{item_where}.adcode", "市级中心点必须是路线城市之一")
            city_places.add(adcode)
        else:
            parent = place.get("parentAdcode")
            if not isinstance(parent, str) or parent not in city_adcodes:
                fail(f"{item_where}.parentAdcode", "必须指向路线中的城市")
    if city_places != city_adcodes:
        fail(where, "每个路线城市都必须有市级中心点")


def validate_path_beneath(value: Any, where: str, prefix: str, suffixes: set[str]) -> Path:
    """`assets/` 下的相对路径：不允许绝对路径、上跳段或未知扩展名。"""
    path = text(value, where)
    normalized = Path(path)
    if normalized.is_absolute() or ".." in normalized.parts or not path.startswith(prefix):
        fail(where, f"必须是 {prefix} 下的相对路径")
    if normalized.suffix.lower() not in suffixes:
        fail(where, f"必须是 {'/'.join(sorted(suffixes))} 文件")
    return normalized
