"""`m2v road-trip fetch`：按天链式取得真实国道走廊并原子保存。

第 1 天从行程起点定位；第 N 天起点直接使用前一天路线终点，不二次定位。
每一天按 via 顺序分段规划并合并步骤，取数后检查 via 是否落在步骤链上。
全部路线先在内存中完整校验，再逐份原子替换；任一步失败恢复全部旧路线。

凭据只从 `M2V_AMAP_KEY` 读取；不写入材料、日志、异常或临时文件。
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from m2v.core.errors import M2VError
from m2v.core.project import load_project as load_manifest
from m2v.types import route_common
from m2v.types.driving_route import geometry
from m2v.types.driving_route.amap import AmapClient, Transport, default_transport
from m2v.types.road_trip import materials

KEY_ENV = "M2V_AMAP_KEY"
ROUTE_STRATEGY = 3
VIA_TOLERANCE_METERS = 3000.0


def _check_gate(trip: dict[str, Any]) -> None:
    usage = trip["sourceUsage"]
    missing = [field for field in ("offlineStorage", "derivativeFrames", "videoPublication")
               if usage.get(field) is not True]
    if usage.get("mapTiles") is not True:
        missing.append("mapTiles")
    if missing:
        raise M2VError("来源使用依据未落实：" + "、".join(missing) + "；拒绝在发起请求前继续")


def _geocode(client: AmapClient, place: dict[str, Any], where: str,
             requests: list[dict[str, Any]], *, expected_city: bool = True) -> dict[str, Any]:
    requests.append({"path": "/v3/geocode/geo",
                     "params": {"address": place["address"], "city": place["city"],
                                "output": "JSON"}})
    result = client.geocode(place["address"], place["city"])
    if expected_city and not route_common.same_city(result["city"], place["city"]):
        raise M2VError(f"{where} 定位城市 {result['city']!r} 与声明城市 {place['city']!r} 不一致")
    return result


def _leg_request(origin: tuple[float, float], destination: tuple[float, float],
                 requests: list[dict[str, Any]]) -> None:
    requests.append({
        "path": "/v5/direction/driving",
        "params": {"origin": f"{origin[0]},{origin[1]}",
                   "destination": f"{destination[0]},{destination[1]}",
                   "strategy": str(ROUTE_STRATEGY),
                   "show_fields": "cost,cities,polyline"},
    })


def _merge_path(segments: list[dict[str, Any]], requests: list[dict[str, Any]]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    cities: list[dict[str, Any]] = []
    seen_cities: set[str] = set()
    cost = {"durationSeconds": 0, "tollsYuan": 0, "tollDistanceMeters": 0, "trafficLights": 0}
    distance = 0
    previous: tuple[float, float] | None = None
    for segment in segments:
        distance += int(segment["distanceMeters"])
        for key in cost:
            cost[key] += int(segment["cost"][key])
        if steps and segment["steps"]:
            first = segment["steps"][0]["points"][0]
            gap = route_common.haversine_meters(
                (previous[0], previous[1]), (first[0], first[1])) if previous else 0.0
            if gap > route_common.STEP_TOLERANCE_METERS:
                raise M2VError(f"分段路线之间断开 {gap:.1f} 米；请调整 via 后重试")
        steps.extend(segment["steps"])
        previous = tuple(segment["endPoint"])
        for city in segment["cities"]:
            if city["adcode"] in seen_cities:
                continue
            seen_cities.add(city["adcode"])
            cities.append(city)
    if not steps:
        raise M2VError("路线没有可用的道路步骤")
    return {"distanceMeters": distance, "startPoint": steps[0]["points"][0],
            "endPoint": steps[-1]["points"][-1], "steps": steps,
            "cost": cost, "cities": cities}


def _administrative(client: AmapClient, cities: list[dict[str, Any]],
                    requests: list[dict[str, Any]], delay: float) -> list[dict[str, Any]]:
    places: list[dict[str, Any]] = []
    city_adcodes = [city["adcode"] for city in cities]
    seen: set[str] = set()
    for city_adcode in city_adcodes:
        requests.append({"path": "/v3/config/district",
                         "params": {"keywords": city_adcode, "subdistrict": "2",
                                    "extensions": "base"}})
        result = client.districts(city_adcode)
        if delay > 0:
            time.sleep(delay)
        if result["city"]["adcode"] not in seen:
            seen.add(result["city"]["adcode"])
            places.append(result["city"])
        for county in result["counties"]:
            if county["adcode"] in seen or county["adcode"] in city_adcodes:
                continue
            seen.add(county["adcode"])
            places.append(county)
    if not places:
        raise M2VError("路线沿途没有可用行政区中心点")
    return places


def _nearest_on_steps(steps: list[dict[str, Any]], location: tuple[float, float]) -> tuple[list[float], float]:
    """把定位点吸附到步骤链上最近的点，返回该点与沿路累计距离。"""
    best = (float("inf"), [location[0], location[1]], 0.0)
    cumulative = 0.0
    for step in steps:
        points = step["points"]
        for index in range(len(points)):
            point = points[index]
            gap = route_common.haversine_meters(location, (point[0], point[1]))
            if gap < best[0]:
                best = (gap, [point[0], point[1]], cumulative)
            if index:
                cumulative += route_common.haversine_meters(
                    (points[index - 1][0], points[index - 1][1]), (point[0], point[1]))
    return best[1], best[2]


def _via_points(day: dict[str, Any], path: dict[str, Any],
                geocoded_via: list[dict[str, Any]]) -> list[dict[str, Any]]:
    points = []
    for index, (place, result) in enumerate(zip(day["via"], geocoded_via)):
        point, distance = _nearest_on_steps(path["steps"], tuple(result["location"]))
        gap = route_common.haversine_meters(tuple(result["location"]), tuple(point))
        if gap > VIA_TOLERANCE_METERS:
            raise M2VError(f"{day['id']} 的 via「{place['label']}」偏离路线 {gap / 1000:.1f} 公里；"
                           "请调整 via 地址后重试")
        points.append({"id": f"via-{index}", "name": place["label"],
                       "location": result["location"], "point": point,
                       "distanceMeters": round(distance, 1)})
    for landmark in day["landmarks"]:
        via_point = points[landmark["viaIndex"]]
        points.append({"id": landmark["id"], "name": landmark["label"],
                       "location": via_point["location"], "point": via_point["point"],
                       "distanceMeters": via_point["distanceMeters"]})
    return points


def _day_document(trip: dict[str, Any], day: dict[str, Any], index: int,
                  previous: dict[str, Any] | None, client: AmapClient, *,
                  district_delay: float) -> dict[str, Any]:
    requests: list[dict[str, Any]] = []
    origin_place: dict[str, Any] | None = None
    if index == 0:
        origin_place = _geocode(client, trip["start"], f"{day['id']} 起点", requests)
        current = tuple(origin_place["location"])
        start_record = {"kind": "trip-start", **deepcopy(trip["start"])}
    else:
        current = tuple(previous["route"]["endPoint"])
        start_record = {"kind": "previous-end"}
    destination = _geocode(client, day["destination"], f"{day['id']} 终点", requests)
    geocoded_via = [_geocode(client, place, f"{day['id']} via", requests)
                    for place in day["via"]]

    targets = [(item["location"], item) for item in geocoded_via]
    targets.append((destination["location"], destination))
    segments: list[dict[str, Any]] = []
    for location, _place in targets:
        _leg_request(current, tuple(location), requests)
        segment = client.drive(current, tuple(location), strategy=ROUTE_STRATEGY,
                               bridge_gaps=60.0)
        segments.append(segment)
        current = tuple(segment["endPoint"])
    path = _merge_path(segments, requests)
    path["administrativePlaces"] = _administrative(client, path["cities"], requests,
                                                   district_delay)
    via_points = _via_points(day, path, geocoded_via)
    return {
        "schemaVersion": 1,
        "dayId": day["id"],
        "start": start_record,
        "destination": deepcopy(day["destination"]),
        "via": deepcopy(day["via"]),
        "routePreference": trip["routePreference"],
        "requestDigest": materials.request_digest(trip, day, index),
        "coordinateSystem": "GCJ-02",
        "origin": origin_place,
        "endPlace": destination,
        "viaPoints": via_points,
        "route": {key: path[key] for key in ("distanceMeters", "startPoint", "endPoint", "steps")},
        "cost": path["cost"],
        "cities": path["cities"],
        "administrativePlaces": path["administrativePlaces"],
        "acquisition": {
            "provider": "amap",
            "service": "webservice",
            "apiVersion": "v5",
            "strategy": ROUTE_STRATEGY,
            "requestedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "requests": requests,
        },
    }


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def fetch(project_dir: str | Path, *, transport: Transport | None = None,
          now: datetime | None = None, api_base: str | None = None,
          timeout: float | None = None, district_delay: float = 0.35) -> list[Path]:
    root, manifest = load_manifest(project_dir)
    if manifest["type"] != "road-trip" or manifest.get("materials") != materials.MATERIALS:
        raise M2VError("m2v road-trip fetch 仅适用于 road-trip 作品，且材料入口固定为 trip.json")
    trip_doc = materials.load_request(root)
    _check_gate(trip_doc["trip"])
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise M2VError(f"缺少地图凭据：请设置环境变量 {KEY_ENV}；凭据不写入作品")

    client = AmapClient(key, api_base=api_base or "https://restapi.amap.com",
                        timeout=timeout if timeout is not None else 30.0,
                        transport=transport or default_transport)
    documents: list[dict[str, Any]] = []
    previous = None
    for index, day in enumerate(trip_doc["days"]):
        document = _day_document(trip_doc["trip"], day, index, previous, client,
                                 district_delay=district_delay)
        if now is not None:
            document["acquisition"]["requestedAt"] = (
                now if now.tzinfo is not None else now.astimezone()).isoformat(timespec="seconds")
        materials.validate_route_document(trip_doc["trip"], document, day, index, previous)
        documents.append(document)
        previous = document

    # 联网期间 trip.json 可能被修改；落盘前复核，避免保存绑定旧编排的路线。
    current = materials.load_request(root)
    if route_common.canonical_digest(current) != route_common.canonical_digest(trip_doc):
        raise M2VError("取数期间 trip.json 已变化；未保存路线，请重新执行 fetch")

    routes_dir = root / materials.ROUTES_DIR
    routes_dir.mkdir(parents=True, exist_ok=True)
    targets = [root / day["route"] for day in trip_doc["days"]]
    snapshots = {target: target.read_bytes() if target.is_file() else None for target in targets}
    written: list[Path] = []
    try:
        for target, document in zip(targets, documents):
            _write_atomic(target, document)
            written.append(target)
    except Exception:
        for target in written:
            snapshot = snapshots[target]
            if snapshot is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(snapshot)
        raise
    return targets
