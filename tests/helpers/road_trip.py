"""多日地图游记测试夹具：合成 trip/route 材料与脱敏高德传输层。"""
from __future__ import annotations

import copy
import io
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

from m2v.core.project import create_project
from m2v.types.road_trip import materials

FIXED_NOW = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=8)))

START = (121.4700, 31.2300)
VIA = (121.4800, 31.2400)
DAY1_END = (121.4900, 31.2500)
DAY2_END = (121.5000, 31.2600)


def source_usage(map_tiles: bool = False) -> dict:
    return {
        "verifiedOn": "2026-11-01",
        "documents": [{"title": "合成许可记录", "url": "https://example.invalid/license"}],
        "account": "合成测试账号范围",
        "purpose": "离线保存路线与道路底图并制作竖屏游记视频",
        "offlineStorage": True,
        "derivativeFrames": True,
        "videoPublication": True,
        "mapTiles": map_tiles,
        "attribution": "地图数据 © 高德地图（合成测试）",
    }


def trip_document(*, map_tiles: bool = False, two_days: bool = True, card: bool = False) -> dict:
    days = [{
        "id": "day-01",
        "title": "上海出发",
        "subtitle": "合成第一天",
        "destination": {"city": "上海市", "address": "上海市合成第一天终点", "label": "合成东"},
        "via": [{"city": "上海市", "address": "上海市合成途经点", "label": "合成中"}],
        "route": "routes/day-01.json",
        "basemapStyle": "road",
        "narration": [{"id": "day-01-opening", "text": "第一天从合成起点出发。"}],
        "cards": ([{"id": "day-01-card", "title": "合成数据",
                    "facts": [{"id": "alt", "label": "海拔", "value": "4298 米", "sourceId": "s1"}]}]
                  if card else []),
        "landmarks": [],
    }]
    if two_days:
        days.append({
            "id": "day-02",
            "title": "抵达合成终点",
            "subtitle": "合成第二天",
            "destination": {"city": "上海市", "address": "上海市合成第二天终点", "label": "合成终"},
            "via": [],
            "route": "routes/day-02.json",
            "basemapStyle": "road",
            "narration": [{"id": "day-02-opening", "text": "第二天抵达合成终点。"}],
            "cards": [],
            "landmarks": [],
        })
    return {
        "schemaVersion": 1,
        "title": "合成多日游记",
        "start": {"city": "上海市", "address": "上海市合成起点", "label": "合成起"},
        "end": {"city": "上海市", "address": "上海市合成第二天终点", "label": "合成终"},
        "routePreference": "g318",
        "targetSeconds": 60,
        "sourceUsage": source_usage(map_tiles),
        "sources": [{"id": "s1", "title": "合成来源", "url": "https://example.invalid/source",
                     "publisher": "合成测试"}],
        "days": days,
        "effects": [{"id": "start-01", "anchor": {"kind": "day-start", "dayId": "day-01"},
                     "builtin": "transition", "gainDb": -22}],
    }


def _place(location, address: str, city: str = "上海市") -> dict:
    return {"location": [location[0], location[1]], "formattedAddress": address,
            "city": city, "level": "兴趣点"}


def _acquisition(trip: dict, index: int, points: list[tuple[float, float]]) -> dict:
    requests = [{"path": "/v3/geocode/geo",
                 "params": {"address": trip["days"][index]["destination"]["address"],
                            "city": "上海市", "output": "JSON"}}]
    if index == 0:
        requests.insert(0, {"path": "/v3/geocode/geo",
                            "params": {"address": trip["start"]["address"],
                                       "city": "上海市", "output": "JSON"}})
    for start, end in zip(points, points[1:]):
        requests.append({"path": "/v5/direction/driving",
                         "params": {"origin": f"{start[0]},{start[1]}",
                                    "destination": f"{end[0]},{end[1]}",
                                    "strategy": "3", "show_fields": "cost,cities,polyline"}})
    requests.append({"path": "/v3/config/district",
                     "params": {"keywords": "310000", "subdistrict": "2",
                                "extensions": "base"}})
    return {"provider": "amap", "service": "webservice", "apiVersion": "v5", "strategy": 3,
            "requestedAt": FIXED_NOW.isoformat(timespec="seconds"), "requests": requests}


def route_document(trip: dict, index: int = 0, *, start_point=None, steps=None,
                   end_place=None) -> dict:
    day = trip["days"][index]
    if index == 0:
        start = start_point or START
        origin = _place(start, trip["start"]["address"])
        start_record = {"kind": "trip-start", **copy.deepcopy(trip["start"])}
    else:
        start = start_point or route_document(trip, index - 1)["route"]["endPoint"]
        origin = None
        start_record = {"kind": "previous-end"}
    destination = DAY1_END if index == 0 else DAY2_END
    via = [VIA] if index == 0 else []
    if steps is None:
        points = [list(start)]
        if via:
            points.append(list(via[0]))
        points.append(list(destination))
        steps = [{"road": "G318合成", "distanceMeters": 3000,
                  "points": points[:2] if via else points}]
        if via:
            steps.append({"road": "G318合成", "distanceMeters": 3000, "points": points[1:]})
    distance = sum(step["distanceMeters"] for step in steps)
    points = [tuple(start), *([VIA] if via else []), tuple(destination)]
    via_points = [{"id": "via-0", "name": day["via"][0]["label"], "location": [VIA[0], VIA[1]],
                   "point": [VIA[0], VIA[1]], "distanceMeters": 3000.0}] if via else []
    return {
        "schemaVersion": 1,
        "dayId": day["id"],
        "start": start_record,
        "destination": copy.deepcopy(day["destination"]),
        "via": copy.deepcopy(day["via"]),
        "routePreference": trip["routePreference"],
        "requestDigest": materials.request_digest(trip, day, index),
        "coordinateSystem": "GCJ-02",
        "origin": origin,
        "endPlace": end_place or _place(destination, day["destination"]["address"]),
        "viaPoints": via_points,
        "route": {"distanceMeters": distance,
                  "startPoint": steps[0]["points"][0],
                  "endPoint": steps[-1]["points"][-1],
                  "steps": steps},
        "cost": {"durationSeconds": 1800, "tollsYuan": 0,
                 "tollDistanceMeters": 0, "trafficLights": 3},
        "cities": [{"name": "上海市", "adcode": "310000",
                    "location": [121.475, 31.235]}],
        "administrativePlaces": [
            {"name": "上海市", "level": "city", "adcode": "310000",
             "center": [121.475, 31.235]},
            {"name": "合成县", "level": "county", "adcode": "310100",
             "parentAdcode": "310000", "center": [121.480, 31.240]},
        ],
        "acquisition": _acquisition(trip, index, points),
    }


def write_project(root: Path, trip: dict | None = None, routes: list[dict] | None = None) -> Path:
    trip = trip or trip_document()
    create_project(root, "road-trip", materials.MATERIALS)
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
    routes = routes or [route_document(trip, index) for index in range(len(trip["days"]))]
    (root / "routes").mkdir(parents=True, exist_ok=True)
    for index, route in enumerate(routes):
        (root / "routes" / f"day-{index + 1:02d}.json").write_text(
            json.dumps(route, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root


def geocode_table() -> dict[str, tuple[float, float]]:
    trip = trip_document(two_days=True)
    return {
        trip["start"]["address"]: START,
        trip["days"][0]["destination"]["address"]: DAY1_END,
        trip["days"][0]["via"][0]["address"]: VIA,
        trip["days"][1]["destination"]["address"]: DAY2_END,
    }


def amap_transport(url: str, timeout: float) -> tuple[int, bytes]:
    """脱敏高德传输层：按地址表返回定位、分段路线、行政区。"""
    parsed = urllib.parse.urlsplit(url)
    query = dict(urllib.parse.parse_qsl(parsed.query))
    if parsed.path == "/v3/geocode/geo":
        address = query.get("address", "")
        location = geocode_table().get(address)
        if location is None:
            return 200, json.dumps({"status": "1", "geocodes": []}).encode()
        return 200, json.dumps({"status": "1", "geocodes": [{
            "location": f"{location[0]},{location[1]}",
            "formatted_address": address, "city": "上海市", "level": "兴趣点",
        }]}).encode()
    if parsed.path == "/v5/direction/driving":
        origin = [float(value) for value in query["origin"].split(",")]
        destination = [float(value) for value in query["destination"].split(",")]
        middle = [(origin[0] + destination[0]) / 2, (origin[1] + destination[1]) / 2]
        polyline = ";".join(f"{point[0]},{point[1]}" for point in (origin, middle, destination))
        return 200, json.dumps({"status": "1", "route": {"paths": [{
            "distance": "2000",
            "cost": {"duration": "900", "tolls": "0", "toll_distance": "0",
                     "traffic_lights": "1"},
            "steps": [{"road_name": "G318合成", "step_distance": "2000",
                       "polyline": polyline, "cities": [{"city": "上海市",
                                                         "adcode": "310000"}]}],
        }]}}).encode()
    if parsed.path == "/v3/config/district":
        return 200, json.dumps({"status": "1", "districts": [{
            "name": "上海市", "level": "province", "adcode": "310000",
            "center": "121.475,31.235",
            "districts": [{"name": "合成县", "level": "district", "adcode": "310100",
                           "center": "121.48,31.24", "districts": []}],
        }]}).encode()
    return 404, b""


def write_wav(path: Path, seconds: float, value: int = 1200) -> Path:
    import struct
    import wave
    from m2v.engine.audio import SAMPLE_RATE
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        stream.writeframes(struct.pack("<h", value) * round(seconds * SAMPLE_RATE))
    return path


def png_tile(style: int = 8) -> bytes:
    size = 512 if style == 8 else 256
    image = Image.new("RGB", (size, size), (240, 237, 230))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def tile_transport(url: str, timeout: float) -> tuple[int, bytes]:
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
    return 200, png_tile(int(query.get("style", "8")))
