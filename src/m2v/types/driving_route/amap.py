"""高德 Web 服务客户端：只负责请求与响应解析，不写作品文件。

凭据只从环境变量读取并由调用方传入；本模块不回显请求 URL，不把 Key 放进异常、
日志或解析结果。传输层可注入，测试用脱敏合成响应覆盖成功与各类失败。

端点口径（2026-10-30 核查，见 openspec/changes/add-driving-route-video/design.md）：

- 地理编码 ``/v3/geocode/geo``，带城市约束，只接受唯一具体地点；
- 驾车路径规划 2.0 ``/v5/direction/driving``，``strategy=34``（高速优先），
  显式请求 ``show_fields=polyline``。
"""
from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol

from m2v.core.errors import M2VError

DEFAULT_API_BASE = "https://restapi.amap.com"
DEFAULT_TIMEOUT_SECONDS = 30.0

#: 比城市中心更粗的定位结果不能证明地址唯一。
COARSE_LEVELS = frozenset({"国家", "省份", "城市", "区县", "乡镇"})

#: 相邻道路段端点的服务采样容差，与材料校验保持一致。
STEP_TOLERANCE_METERS = 25.0

EARTH_RADIUS_METERS = 6371008.8


class Transport(Protocol):
    def __call__(self, url: str, timeout: float) -> tuple[int, bytes]: ...


def default_transport(url: str, timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "material2video/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    lng1, lat1 = math.radians(a[0]), math.radians(a[1])
    lng2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.asin(min(1.0, math.sqrt(h)))


def _finite(value: Any, what: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise M2VError(f"高德响应中的{what}不是数字") from None
    if not math.isfinite(number):
        raise M2VError(f"高德响应中的{what}不是有限数字")
    return number


def _integer_string(value: Any, what: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise M2VError(f"高德响应中的{what}不是整数")
    try:
        number = int(value)
    except ValueError:
        raise M2VError(f"高德响应中的{what}不是整数") from None
    if number < minimum:
        raise M2VError(f"高德响应中的{what}小于 {minimum}")
    return number


def _coordinate(value: Any, what: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise M2VError(f"高德响应中的{what}不是 [经度, 纬度] 坐标")
    lng, lat = _finite(value[0], f"{what}经度"), _finite(value[1], f"{what}纬度")
    if not -180 <= lng <= 180 or not -90 <= lat <= 90:
        raise M2VError(f"高德响应中的{what}超出经纬度范围")
    return lng, lat


def _location(value: Any, what: str) -> tuple[float, float]:
    if not isinstance(value, str) or "," not in value:
        raise M2VError(f"高德响应中的{what}不是“经度,纬度”文本")
    parts = value.split(",")
    if len(parts) != 2:
        raise M2VError(f"高德响应中的{what}不是“经度,纬度”文本")
    return _coordinate([parts[0], parts[1]], what)


def _polyline(value: Any, where: str) -> list[list[float]]:
    if not isinstance(value, str) or not value.strip():
        raise M2VError(f"高德响应缺少{where}的 polyline；请确认已请求 show_fields=polyline")
    points: list[list[float]] = []
    for token in value.split(";"):
        if not token.strip():
            continue
        parts = token.split(",")
        if len(parts) != 2:
            raise M2VError(f"高德响应{where}的 polyline 格式无效")
        lng, lat = _coordinate([parts[0], parts[1]], f"{where}的 polyline")
        point = [lng, lat]
        if not points or points[-1] != point:
            points.append(point)
    if len(points) < 2:
        raise M2VError(f"高德响应{where}的 polyline 去除重复点后不足两个坐标")
    return points


class AmapClient:
    """高德 Web 服务的最小客户端。错误信息绝不包含请求 URL。"""

    def __init__(self, key: str, *, api_base: str = DEFAULT_API_BASE,
                 timeout: float = DEFAULT_TIMEOUT_SECONDS, transport: Transport | None = None) -> None:
        if not key.strip():
            raise M2VError("缺少地图凭据")
        self._key = key.strip()
        self._api_base = api_base.rstrip("/")
        self._timeout = timeout
        self._transport = transport or default_transport

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"{self._api_base}{path}?{urllib.parse.urlencode({**params, 'key': self._key})}"
        try:
            status, body = self._transport(url, self._timeout)
        except Exception as exc:  # noqa: BLE001 - 任何传输失败都只报类型，不回显 URL
            raise M2VError(f"高德服务请求失败（{type(exc).__name__}）；请检查网络后重试") from None
        if status != 200:
            raise M2VError(f"高德服务返回 HTTP {status}；请稍后重试")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeError, ValueError):
            raise M2VError("高德服务返回非 JSON 响应") from None
        if not isinstance(payload, dict):
            raise M2VError("高德服务返回的响应结构无效")
        if payload.get("status") != "1":
            code = payload.get("infocode") or "未知错误码"
            info = payload.get("info") or "请求失败"
            raise M2VError(f"高德服务拒绝请求：{info}（infocode={code}）")
        return payload

    def geocode(self, address: str, city: str) -> dict[str, Any]:
        payload = self._get("/v3/geocode/geo", {"address": address, "city": city, "output": "JSON"})
        geocodes = payload.get("geocodes")
        if not isinstance(geocodes, list):
            raise M2VError("高德地理编码响应缺少 geocodes")
        if not geocodes:
            raise M2VError(f"高德未找到地点：{address}；请核对地址")
        if len(geocodes) != 1:
            raise M2VError(f"高德定位结果不唯一（{len(geocodes)} 个候选）：{address}；请提供更具体的地址")
        item = geocodes[0]
        if not isinstance(item, dict):
            raise M2VError("高德地理编码结果结构无效")
        location = _location(item.get("location"), "定位结果")
        formatted = item.get("formatted_address")
        if not isinstance(formatted, str) or not formatted.strip():
            raise M2VError("高德地理编码结果缺少 formatted_address")
        level = item.get("level")
        if not isinstance(level, str) or not level.strip():
            raise M2VError("高德地理编码结果缺少 level；无法确认地点精度")
        if level in COARSE_LEVELS:
            raise M2VError(f"高德定位精度仅到「{level}」，不是具体地点：{address}；请提供更具体的地址")
        detected_city = item.get("city") or item.get("province")
        if not isinstance(detected_city, str) or not detected_city.strip():
            raise M2VError(f"高德定位结果缺少城市信息：{address}")
        return {
            "location": [location[0], location[1]],
            "formattedAddress": formatted.strip(),
            "city": detected_city.strip(),
            "level": level.strip(),
        }

    def drive(self, origin: tuple[float, float],
              destination: tuple[float, float]) -> dict[str, Any]:
        payload = self._get("/v5/direction/driving", {
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "strategy": "34",
            "show_fields": "polyline",
        })
        route = payload.get("route")
        paths = route.get("paths") if isinstance(route, dict) else None
        if not isinstance(paths, list) or not paths:
            raise M2VError("高德驾车规划没有返回可用路线")
        path = paths[0]
        if not isinstance(path, dict):
            raise M2VError("高德驾车规划结果结构无效")
        distance = _integer_string(path.get("distance"), "路线总距离", minimum=1)
        raw_steps = path.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise M2VError("高德驾车规划没有返回道路分段")
        steps: list[dict[str, Any]] = []
        previous_last: list[float] | None = None
        for index, raw in enumerate(raw_steps):
            where = f"第 {index + 1} 段"
            if not isinstance(raw, dict):
                raise M2VError(f"高德驾车规划{where}结构无效")
            polyline = raw.get("polyline")
            if not isinstance(polyline, str) or not polyline.strip():
                # 极短的零长度段可能没有几何；由后续连续性校验决定是否可接受。
                continue
            points = _polyline(polyline, where)
            road = raw.get("road_name")
            road_name = road.strip() if isinstance(road, str) and road.strip() else "未命名道路"
            step_distance = raw.get("step_distance")
            try:
                step_meters = _integer_string(step_distance, f"{where}距离", minimum=0)
            except M2VError:
                step_meters = 0
            if previous_last is not None:
                gap = _haversine((previous_last[0], previous_last[1]),
                                 (points[0][0], points[0][1]))
                if gap > STEP_TOLERANCE_METERS:
                    raise M2VError(f"高德驾车规划{where}与上一段终点相距 {gap:.1f} 米，"
                                   f"超过 {STEP_TOLERANCE_METERS:g} 米容差；拒绝跨缺口连接")
            steps.append({"road": road_name, "distanceMeters": step_meters, "points": points})
            previous_last = points[-1]
        if not steps:
            raise M2VError("高德驾车规划的所有道路段都缺少有效几何")
        return {"distanceMeters": distance, "steps": steps,
                "startPoint": steps[0]["points"][0], "endPoint": steps[-1]["points"][-1]}
