"""多日地图游记材料契约：`trip.json` 与每日 `routes/day-XX.json`。

作品只有一份编排材料。每日路线由 `trip.json` 的 `days[].route` 引用，不进入
`project.materials`；手填的总里程、每日时长与起终点坐标一律拒绝，全部从路线
与时间轴派生。旁白、卡片、音效与事实来源都在这份材料里，渲染不访问网络。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from m2v.core import frames as frame_engine
from m2v.core.errors import M2VError
from m2v.core.validate import fail, obj, text
from m2v.core.video_config import ROAD_TRIP_FPS
from m2v.types import route_common
from m2v.types.driving_route import layout as driving_layout
from m2v.types.road_trip import layout as layout_module

WIDTH = 1080
HEIGHT = 1920
FPS = ROAD_TRIP_FPS

MATERIALS = {"trip": "trip.json"}
ROUTES_DIR = "routes"
BASEMAP_DIR = "assets/basemap/road-trip"
BASEMAP_INDEX = f"{BASEMAP_DIR}/index.json"

MAX_DAYS = 14
MAX_TARGET_SECONDS = 540
MAX_EFFECTS = 64
ANCHOR_KINDS = frozenset({"trip-start", "trip-end", "day-start", "day-arrival",
                          "segment-start", "segment-end", "landmark"})
BASEMAP_STYLES = {"road": "road-tiles", "satellite": "satellite-tiles"}

_DAY_ID = re.compile(r"day-\d{2}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_PLACEHOLDER = route_common.PLACEHOLDER


def request_identity(trip: dict[str, Any], day: dict[str, Any], index: int) -> dict[str, Any]:
    """只覆盖会改变路线的字段；旁白、卡片与时长不参与。"""
    identity: dict[str, Any] = {
        "dayId": day["id"],
        "destination": {"city": day["destination"]["city"],
                        "address": day["destination"]["address"]},
        "via": [{"city": place["city"], "address": place["address"]}
                for place in day.get("via", [])],
        "routePreference": trip["routePreference"],
        "coordinateSystem": "GCJ-02",
    }
    if index == 0:
        identity["start"] = {"city": trip["start"]["city"], "address": trip["start"]["address"]}
    else:
        identity["start"] = "previous-end"
    return identity


def request_digest(trip: dict[str, Any], day: dict[str, Any], index: int) -> str:
    return route_common.canonical_digest(request_identity(trip, day, index))


def route_path(day_id: str) -> str:
    return f"{ROUTES_DIR}/{day_id}.json"


def _load_trip(root: Path) -> dict[str, Any]:
    return route_common.load_json(
        root / MATERIALS["trip"], 1,
        hint="旧材料不被支持；请重新运行 m2v init --type road-trip 并填写 trip.json",
    )


def _load_route(root: Path, relative: str) -> dict[str, Any]:
    return route_common.load_json(
        root / relative, 1,
        hint="旧路线材料不被支持；请重新运行 m2v road-trip fetch",
    )


def _validate_sources(value: Any) -> dict[str, dict[str, Any]]:
    where = "trip.json.sources"
    if not isinstance(value, list) or not 1 <= len(value) <= 64:
        fail(where, "必须记录 1～64 条事实来源")
    sources: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(value):
        item_where = f"{where}[{index}]"
        source = obj(raw, item_where, {"id", "title", "url", "publisher", "publishedOn"})
        identity = text(source.get("id"), f"{item_where}.id")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", identity):
            fail(f"{item_where}.id", "必须是 1～64 位小写字母、数字或连字符")
        if identity in sources:
            fail(f"{item_where}.id", f"来源重复：{identity}")
        route_common.content_text(source.get("title"), f"{item_where}.title")
        route_common.https_url(source.get("url"), f"{item_where}.url")
        for field in ("publisher", "publishedOn"):
            if field in source:
                route_common.content_text(source[field], f"{item_where}.{field}")
        sources[identity] = source
    return sources


def _validate_narration(value: Any, where: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 24:
        fail(where, "必须包含 1～24 段旁白")
    seen: set[str] = set()
    segments = []
    for index, raw in enumerate(value):
        item_where = f"{where}[{index}]"
        segment = obj(raw, item_where, {"id", "text", "anchor"})
        identity = text(segment.get("id"), f"{item_where}.id")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", identity):
            fail(f"{item_where}.id", "必须是 1～64 位小写字母、数字或连字符")
        if identity in seen:
            fail(f"{item_where}.id", f"旁白段重复：{identity}")
        seen.add(identity)
        content = route_common.content_text(segment.get("text"), f"{item_where}.text")
        if len(content) > 180:
            fail(f"{item_where}.text", "单段旁白不得超过 180 字；请拆分")
        resolved = {"id": identity, "text": content}
        if "anchor" in segment:
            anchor = obj(segment["anchor"], f"{item_where}.anchor", {"kind", "landmarkId"})
            kind = anchor.get("kind")
            if kind not in {"landmark", "arrival"}:
                fail(f"{item_where}.anchor.kind", "必须为 landmark 或 arrival")
            if kind == "landmark":
                landmark_id = text(anchor.get("landmarkId"), f"{item_where}.anchor.landmarkId")
                resolved["anchor"] = {"kind": kind, "landmarkId": landmark_id}
            else:
                resolved["anchor"] = {"kind": kind}
        segments.append(resolved)
    return segments


def _validate_cards(value: Any, where: str, sources: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 1:
        fail(where, "每天最多 1 张数据卡；多条事实放在同一张卡内")
    cards = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        item_where = f"{where}[{index}]"
        card = obj(raw, item_where, {"id", "title", "facts"})
        identity = text(card.get("id"), f"{item_where}.id")
        if identity in seen:
            fail(f"{item_where}.id", f"数据卡重复：{identity}")
        seen.add(identity)
        title = route_common.content_text(card.get("title"), f"{item_where}.title")
        facts = card.get("facts")
        if not isinstance(facts, list) or not 1 <= len(facts) <= 6:
            fail(f"{item_where}.facts", "必须包含 1～6 条事实")
        resolved = []
        for fact_index, raw_fact in enumerate(facts):
            fact_where = f"{item_where}.facts[{fact_index}]"
            fact = obj(raw_fact, fact_where, {"id", "label", "value", "sourceId"})
            fact_id = text(fact.get("id"), f"{fact_where}.id")
            label = route_common.content_text(fact.get("label"), f"{fact_where}.label")
            value_text = route_common.content_text(fact.get("value"), f"{fact_where}.value")
            source_id = fact.get("sourceId")
            if not isinstance(source_id, str) or not source_id.strip():
                fail(f"{fact_where}.sourceId",
                     f"事实「{label}」带数值 {value_text!r} 但没有来源；无来源事实不得进入画面")
            if source_id not in sources:
                fail(f"{fact_where}.sourceId", f"未知来源：{source_id}")
            resolved.append({"id": fact_id, "label": label, "value": value_text,
                             "sourceId": source_id})
        cards.append({"id": identity, "title": title, "facts": resolved})
    return cards


def _validate_landmarks(value: Any, where: str, via_count: int) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 8:
        fail(where, "必须是最多 8 个地标")
    seen: set[str] = set()
    landmarks = []
    for index, raw in enumerate(value):
        item_where = f"{where}[{index}]"
        landmark = obj(raw, item_where, {"id", "label", "viaIndex"})
        identity = text(landmark.get("id"), f"{item_where}.id")
        if identity in seen:
            fail(f"{item_where}.id", f"地标重复：{identity}")
        seen.add(identity)
        label = route_common.content_text(landmark.get("label"), f"{item_where}.label")
        via_index = landmark.get("viaIndex")
        if type(via_index) is not int or not 0 <= via_index < via_count:
            fail(f"{item_where}.viaIndex", f"必须指向 0～{via_count - 1} 的 via 节点")
        landmarks.append({"id": identity, "label": label, "viaIndex": via_index})
    return landmarks


def _validate_effects(value: Any, days: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if value is None:
        return []
    where = "trip.json.effects"
    if not isinstance(value, list) or len(value) > MAX_EFFECTS:
        fail(where, f"必须是最多 {MAX_EFFECTS} 项的音效数组")
    seen: set[str] = set()
    effects = []
    for index, raw in enumerate(value):
        item_where = f"{where}[{index}]"
        effect = obj(raw, item_where, {"id", "anchor", "builtin", "synthesis", "assetId", "sourceRef",
                                       "gainDb", "offsetMs", "trimStartMs", "durationMs", "loop",
                                       "fadeInMs", "fadeOutMs"})
        identity = text(effect.get("id"), f"{item_where}.id")
        if identity in seen:
            fail(f"{item_where}.id", f"音效重复：{identity}")
        seen.add(identity)
        sources = [key for key in ("builtin", "synthesis", "assetId", "sourceRef") if key in effect]
        if len(sources) != 1:
            fail(item_where, "音效来源必须在 builtin/synthesis/assetId/sourceRef 四选一")
        anchor = obj(effect.get("anchor"), f"{item_where}.anchor",
                     {"kind", "dayId", "segmentId", "landmarkId"})
        kind = anchor.get("kind")
        if kind not in ANCHOR_KINDS:
            fail(f"{item_where}.anchor.kind", f"必须是 {sorted(ANCHOR_KINDS)} 之一")
        if kind in {"day-start", "day-arrival", "segment-start", "segment-end", "landmark"}:
            day_id = anchor.get("dayId")
            if not isinstance(day_id, str) or day_id not in days:
                fail(f"{item_where}.anchor.dayId", "必须引用材料中的天")
        if kind in {"segment-start", "segment-end"}:
            segment_id = anchor.get("segmentId")
            if not isinstance(segment_id, str) or segment_id not in {
                    segment["id"] for segment in days[anchor["dayId"]]["narration"]}:
                fail(f"{item_where}.anchor.segmentId", "必须引用当天的旁白段")
        if kind == "landmark":
            landmark_id = anchor.get("landmarkId")
            if not isinstance(landmark_id, str) or landmark_id not in {
                    landmark["id"] for landmark in days[anchor["dayId"]]["landmarks"]}:
                fail(f"{item_where}.anchor.landmarkId", "必须引用当天的地标")
        for field in ("gainDb", "offsetMs", "trimStartMs", "durationMs", "fadeInMs", "fadeOutMs"):
            if field in effect and type(effect[field]) is not int:
                fail(f"{item_where}.{field}", "必须是整数")
        if type(effect.get("loop", False)) is not bool:
            fail(f"{item_where}.loop", "必须是布尔值")
        effects.append({"id": identity, **{key: effect[key] for key in effect if key != "id"}})
    return effects


def _validate_trip(trip: dict[str, Any]) -> dict[str, Any]:
    obj(trip, "trip.json", {"schemaVersion", "title", "start", "end", "routePreference",
                            "targetSeconds", "sourceUsage", "sources", "days", "effects"})
    route_common.content_text(trip.get("title"), "trip.json.title")
    route_common.validate_place(trip.get("start"), "trip.json.start")
    route_common.validate_place(trip.get("end"), "trip.json.end")
    if trip.get("routePreference") != "g318":
        fail("trip.json.routePreference", "当前仅支持 g318（避开高速，沿国道走廊）")
    target = trip.get("targetSeconds")
    if type(target) is not int or not 60 <= target <= MAX_TARGET_SECONDS:
        fail("trip.json.targetSeconds", f"必须是 60～{MAX_TARGET_SECONDS} 的整数秒")
    route_common.validate_source_usage(trip.get("sourceUsage"), "trip.json.sourceUsage")
    sources = _validate_sources(trip.get("sources"))
    days = trip.get("days")
    if not isinstance(days, list) or not 1 <= len(days) <= MAX_DAYS:
        fail("trip.json.days", f"必须包含 1～{MAX_DAYS} 天")
    resolved_days: list[dict[str, Any]] = []
    seen: set[str] = set()
    narration_total = 0
    for index, raw in enumerate(days):
        where = f"trip.json.days[{index}]"
        day = obj(raw, where, {"id", "title", "subtitle", "destination", "via", "route",
                               "basemapStyle", "narration", "cards", "landmarks"})
        identity = text(day.get("id"), f"{where}.id")
        if not _DAY_ID.fullmatch(identity):
            fail(f"{where}.id", "必须形如 day-01")
        if identity in seen:
            fail(f"{where}.id", f"天重复：{identity}")
        seen.add(identity)
        title = route_common.content_text(day.get("title"), f"{where}.title")
        subtitle = ""
        if "subtitle" in day:
            subtitle = route_common.content_text(day["subtitle"], f"{where}.subtitle")
        route_common.validate_place(day.get("destination"), f"{where}.destination")
        via = day.get("via")
        if not isinstance(via, list) or len(via) > 20:
            fail(f"{where}.via", "必须是最多 20 个途经点")
        resolved_via = []
        for via_index, raw_via in enumerate(via):
            via_where = f"{where}.via[{via_index}]"
            place = obj(raw_via, via_where, {"city", "address", "label"})
            route_common.content_text(place.get("city"), f"{via_where}.city")
            route_common.content_text(place.get("address"), f"{via_where}.address")
            label = place.get("label", place["address"])
            route_common.content_text(label, f"{via_where}.label")
            resolved_via.append({"city": place["city"], "address": place["address"],
                                 "label": label})
        if day.get("route") != route_path(identity):
            fail(f"{where}.route", f"固定为 {route_path(identity)}")
        style = day.get("basemapStyle", "road")
        if style not in BASEMAP_STYLES:
            fail(f"{where}.basemapStyle", "必须为 road 或 satellite")
        narration = _validate_narration(day.get("narration"), f"{where}.narration")
        narration_total += sum(len(segment["text"]) for segment in narration)
        cards = _validate_cards(day.get("cards"), f"{where}.cards", sources)
        landmarks = _validate_landmarks(day.get("landmarks"), f"{where}.landmarks", len(resolved_via))
        landmark_ids = {landmark["id"] for landmark in landmarks}
        for segment in narration:
            anchor = segment.get("anchor")
            if anchor and anchor["kind"] == "landmark" and anchor["landmarkId"] not in landmark_ids:
                fail(f"{where}.narration", f"旁白锚点引用未知地标：{anchor['landmarkId']}")
        resolved_days.append({"id": identity, "title": title, "subtitle": subtitle,
                              "destination": day["destination"], "via": resolved_via,
                              "route": route_path(identity), "basemapStyle": style,
                              "narration": narration, "cards": cards, "landmarks": landmarks})
    if narration_total == 0:
        fail("trip.json.days", "至少需要一段非空旁白；road-trip 为有声类型")
    effects = _validate_effects(trip.get("effects"),
                                {day["id"]: day for day in resolved_days})
    return {"trip": trip, "days": resolved_days, "effects": effects}


def _validate_route(route: dict[str, Any], trip_doc: dict[str, Any], day: dict[str, Any],
                    index: int, previous: dict[str, Any] | None) -> None:
    trip = trip_doc
    where = f"{day['route']}"
    obj(route, where, {"schemaVersion", "dayId", "start", "destination", "via",
                       "routePreference", "requestDigest", "coordinateSystem", "origin",
                       "endPlace", "viaPoints", "route", "cost", "cities",
                       "administrativePlaces", "acquisition"})
    if route.get("dayId") != day["id"]:
        fail(f"{where}.dayId", f"必须为 {day['id']}")
    if route.get("routePreference") != trip["routePreference"]:
        fail(f"{where}.routePreference", "必须与 trip.json 一致")
    if route.get("coordinateSystem") != "GCJ-02":
        fail(f"{where}.coordinateSystem", "必须为 GCJ-02")

    start = obj(route.get("start"), f"{where}.start", {"kind", "city", "address", "label"})
    if index == 0:
        if start.get("kind") != "trip-start":
            fail(f"{where}.start.kind", "第 1 天必须从行程起点定位")
        for field in ("city", "address"):
            if start.get(field) != trip["start"][field]:
                fail(f"{where}.start.{field}", "必须与 trip.json.start 一致；请重新取数")
    elif start.get("kind") != "previous-end":
        fail(f"{where}.start.kind", "第 N 天起点必须直接使用第 N-1 天终点")

    destination = obj(route.get("destination"), f"{where}.destination", {"city", "address", "label"})
    for field in ("city", "address"):
        if destination.get(field) != day["destination"][field]:
            fail(f"{where}.destination.{field}", "必须与 trip.json 当天目的地一致")
    via = route.get("via")
    if not isinstance(via, list) or len(via) != len(day["via"]):
        fail(f"{where}.via", "必须与 trip.json 当天的 via 一致")
    for via_index, place in enumerate(via):
        item_where = f"{where}.via[{via_index}]"
        item = obj(place, item_where, {"city", "address", "label"})
        for field in ("city", "address"):
            if item.get(field) != day["via"][via_index][field]:
                fail(f"{item_where}.{field}", "必须与 trip.json 当天的 via 一致")

    digest = route.get("requestDigest")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        fail(f"{where}.requestDigest", "必须是 64 位十六进制 SHA-256 摘要")
    if digest != request_digest(trip, day, index):
        fail(f"{where}.requestDigest", "与当前 trip.json 不匹配；请重新运行 m2v road-trip fetch")

    origin = route.get("origin")
    if index == 0:
        route_common.validate_geocoded_place(origin, f"{where}.origin", trip["start"]["city"])
    elif origin is not None:
        fail(f"{where}.origin", "第 N 天起点直接使用前一天终点，不得二次定位")
    end_location = route_common.validate_geocoded_place(
        route.get("endPlace"), f"{where}.endPlace", day["destination"]["city"])

    path = obj(route.get("route"), f"{where}.route",
               {"distanceMeters", "startPoint", "endPoint", "steps"})
    distance_meters = route_common.positive_number(path.get("distanceMeters"),
                                                   f"{where}.route.distanceMeters")
    start_point = route_common.coordinate(path.get("startPoint"), f"{where}.route.startPoint")
    end_point = route_common.coordinate(path.get("endPoint"), f"{where}.route.endPoint")
    steps = path.get("steps")
    first_point, last_point = route_common.validate_steps(steps, f"{where}.route.steps")
    if route_common.haversine_meters(start_point, first_point) > route_common.START_END_TOLERANCE_METERS:
        fail(f"{where}.route.startPoint", "必须与首个道路段的第一个坐标一致")
    if route_common.haversine_meters(end_point, last_point) > route_common.START_END_TOLERANCE_METERS:
        fail(f"{where}.route.endPoint", "必须与最后一个道路段的最后一个坐标一致")
    if index == 0 and route_common.haversine_meters(
            route["origin"]["location"], start_point) > route_common.ENDPOINT_TOLERANCE_METERS:
        fail(f"{where}.route.startPoint", "距定位点超过 1 公里")
    if route_common.haversine_meters(end_location, end_point) > route_common.ENDPOINT_TOLERANCE_METERS:
        fail(f"{where}.route.endPoint", "距定位点超过 1 公里")
    if route_common.route_length(steps) <= 0:
        fail(f"{where}.route.steps", "路线总长度必须大于 0")
    if previous is not None:
        previous_end = route_common.coordinate(
            previous["route"]["endPoint"], f"{previous['dayId']}.route.endPoint")
        if route_common.haversine_meters(previous_end, start_point) > 1.0:
            fail(f"{where}.route.startPoint", "与前一天终点相距超过 1 米；请重新运行 fetch")

    via_points = route.get("viaPoints")
    if not isinstance(via_points, list) or len(via_points) != len(day["landmarks"]) + len(day["via"]):
        fail(f"{where}.viaPoints", "必须为每个 via 与地标记录路子上的位置")
    expected_ids = [f"via-{node_index}" for node_index in range(len(day["via"]))]
    expected_ids += [landmark["id"] for landmark in day["landmarks"]]
    seen_ids: set[str] = set()
    for point_index, raw in enumerate(via_points):
        item_where = f"{where}.viaPoints[{point_index}]"
        point = obj(raw, item_where, {"id", "name", "location", "distanceMeters", "point"})
        identity = text(point.get("id"), f"{item_where}.id")
        if identity not in expected_ids or identity in seen_ids:
            fail(f"{item_where}.id", "必须依次对应 via 与地标，且不重复")
        seen_ids.add(identity)
        route_common.content_text(point.get("name"), f"{item_where}.name")
        route_common.coordinate(point.get("location"), f"{item_where}.location")
        route_common.coordinate(point.get("point"), f"{item_where}.point")
        route_common.finite_number(point.get("distanceMeters"), f"{item_where}.distanceMeters",
                                   low=0, high=distance_meters + 1)
    if seen_ids != set(expected_ids):
        fail(f"{where}.viaPoints", "必须覆盖全部 via 与地标")

    route_common.validate_acquisition(route.get("acquisition"), strategy=3,
                                      where=f"{where}.acquisition")
    route_common.validate_cost(route.get("cost"), distance_meters, f"{where}.cost")
    route_common.validate_cities(route.get("cities"), f"{where}.cities")
    route_common.validate_administrative_places(
        route.get("administrativePlaces"), route.get("cities"),
        f"{where}.administrativePlaces")


def _validate_index(root: Path, index_data: dict[str, Any], trip_doc: dict[str, Any],
                    routes: dict[str, dict[str, Any]]) -> None:
    where = BASEMAP_INDEX
    obj(index_data, where, {"schemaVersion", "layoutVersion", "provider", "attribution",
                            "fetchedAt", "global", "days"})
    if index_data.get("schemaVersion") != 1:
        fail(f"{where}.schemaVersion", "必须为 1")
    if index_data.get("layoutVersion") != layout_module.layout_version():
        fail(f"{where}.layoutVersion", "布局版本不匹配；请重新运行 m2v road-trip basemap")
    if index_data.get("provider") != "amap":
        fail(f"{where}.provider", "必须为 amap")
    route_common.content_text(index_data.get("attribution"), f"{where}.attribution")
    fetched = text(index_data.get("fetchedAt"), f"{where}.fetchedAt")
    try:
        parsed = datetime.fromisoformat(fetched)
    except ValueError:
        fail(f"{where}.fetchedAt", f"不是有效 ISO 时间：{fetched!r}")
    if parsed.tzinfo is None:
        fail(f"{where}.fetchedAt", "必须包含时区")
    _validate_layer(root, index_data.get("global"), f"{where}.global", follow=False)
    trip_geom = layout_module.trip_geometry([routes[day["id"]] for day in trip_doc["days"]])
    global_required, _global_scale = layout_module.trip_overview_bbox(trip_geom, WIDTH, HEIGHT)
    _require_bbox_covers(index_data["global"]["bbox"], global_required,
                         f"{where}.global.bbox")
    days = index_data.get("days")
    if not isinstance(days, dict):
        fail(f"{where}.days", "必须是按天索引的对象")
    expected = {day["id"] for day in trip_doc["days"]}
    if set(days) != expected:
        missing = expected - set(days)
        extra = set(days) - expected
        detail = []
        if missing:
            detail.append("缺少 " + "、".join(sorted(missing)))
        if extra:
            detail.append("多出 " + "、".join(sorted(extra)))
        fail(f"{where}.days", "；".join(detail))
    total_tiles = 0
    total_bytes = 0
    for index, day in enumerate(trip_doc["days"]):
        entry = days[day["id"]]
        item_where = f"{where}.days.{day['id']}"
        record = obj(entry, item_where, {"style", "service", "overview", "followTiles"})
        style = record.get("style")
        if style != day["basemapStyle"]:
            fail(f"{item_where}.style", f"必须与 trip.json 一致：{day['basemapStyle']}")
        if record.get("service") != BASEMAP_STYLES[style]:
            fail(f"{item_where}.service", "与底图样式不一致")
        _validate_layer(root, record.get("overview"), f"{item_where}.overview", follow=False,
                        day=day)
        route = routes[day["id"]]
        geom = layout_module.day_geometry(route, trim_origin=index == 0)
        required, _scale = layout_module.day_overview_bbox(geom, WIDTH, HEIGHT)
        _require_bbox_covers(record["overview"]["bbox"], required,
                             f"{item_where}.overview.bbox")
        follow = record.get("followTiles")
        _validate_layer(root, follow, f"{item_where}.followTiles", follow=True, day=day,
                        pixels=512 if style == "road" else 256)
        total_tiles += follow["tileCount"]
        total_bytes += _referenced_bytes(root, record)
        tile_style = 8 if style == "road" else 6
        plan = layout_module.corridor_plan(route, day["id"], follow["zoom"], day_index=index,
                                           tile_style=tile_style)
        if follow.get("planDigest") != plan["planDigest"]:
            fail(f"{item_where}.followTiles.planDigest",
                 "与当前路线、布局或缩放不一致；请重新运行 basemap")
        if {(tile["x"], tile["y"]) for tile in follow["tiles"]} != {
                (tile["x"], tile["y"]) for tile in plan["tiles"]}:
            fail(f"{item_where}.followTiles.tiles", "瓦片集合与走廊计划不一致")
        if follow.get("bbox") != plan["bbox"]:
            fail(f"{item_where}.followTiles.bbox", "与走廊计划不一致")
    if total_tiles > layout_module.MAX_TRIP_TILES:
        fail(f"{where}.days", f"全片需要 {total_tiles} 块跟随瓦片，超过上限 "
                              f"{layout_module.MAX_TRIP_TILES}；请调整路线或倍率")
    if total_bytes > layout_module.MAX_TRIP_BYTES:
        fail(f"{where}.days", f"底图共 {total_bytes / 1024 / 1024:.1f} MB，超过上限 "
                              f"{layout_module.MAX_TRIP_BYTES / 1024 / 1024:.0f} MB")


def _validate_layer(root: Path, value: Any, where: str, *, follow: bool,
                    day: dict[str, Any] | None = None, pixels: int | None = None) -> None:
    if follow:
        layer = obj(value, where, {"zoom", "tileSize", "tileCount", "planDigest",
                                   "manifestDigest", "bbox", "request", "tiles", "manifest"})
        zoom = layer.get("zoom")
        if type(zoom) is not int or not 1 <= zoom <= 18:
            fail(f"{where}.zoom", "必须是 1～18 的整数")
        if layer.get("tileSize") != 256:
            fail(f"{where}.tileSize", "必须为 256")
        count = layer.get("tileCount")
        if type(count) is not int or not 1 <= count <= layout_module.MAX_DAY_TILES:
            fail(f"{where}.tileCount", f"必须是 1～{layout_module.MAX_DAY_TILES} 的整数")
        if not isinstance(layer.get("tiles"), list) or len(layer["tiles"]) != count:
            fail(f"{where}.tiles", "必须与 tileCount 一致")
        for field in ("planDigest", "manifestDigest"):
            digest = layer.get(field)
            if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                fail(f"{where}.{field}", "必须是 64 位十六进制 SHA-256")
        route_common.validate_bbox(layer.get("bbox"), f"{where}.bbox")
        route_common.validate_request_record(layer.get("request"), f"{where}.request")
        manifest = layer.get("manifest")
        route_common.validate_path_beneath(manifest, f"{where}.manifest",
                                           "assets/basemap/road-trip/", {".json"})
        manifest_file = (root / manifest).resolve()
        if not manifest_file.is_file() or not manifest_file.is_relative_to(root.resolve()):
            fail(f"{where}.manifest", f"每日底图清单不存在：{manifest}")
        records = []
        keys: set[tuple[int, int]] = set()
        limit = (1 << zoom) - 1
        for tile_index, raw in enumerate(layer["tiles"]):
            item_where = f"{where}.tiles[{tile_index}]"
            tile = obj(raw, item_where, {"x", "y", "z", "path", "sha256", "width", "height",
                                         "projected"})
            x, y, z = tile.get("x"), tile.get("y"), tile.get("z")
            if type(x) is not int or type(y) is not int or type(z) is not int:
                fail(item_where, "x/y/z 必须是整数")
            if z != zoom or not (0 <= x <= limit and 0 <= y <= limit):
                fail(item_where, "x/y/z 超出 zoom 范围或与 zoom 不一致")
            if (x, y) in keys:
                fail(item_where, f"瓦片重复：{x}:{y}")
            keys.add((x, y))
            if pixels is not None and (tile.get("width") != pixels
                                       or tile.get("height") != pixels):
                fail(item_where, f"瓦片尺寸必须为 {pixels}×{pixels}")
            relative = route_common.validate_path_beneath(
                tile.get("path"), f"{item_where}.path", "assets/basemap/road-trip/",
                {".jpg", ".jpeg"})
            file = (root / relative).resolve()
            if not file.is_file() or not file.is_relative_to(root.resolve()):
                fail(f"{item_where}.path", f"瓦片不存在：{relative}")
            digest = tile.get("sha256")
            if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
                fail(f"{item_where}.sha256", "瓦片摘要不匹配；请重新运行 basemap")
            expected = driving_layout.tile_projected_rect(x, y, zoom)
            projected = obj(tile.get("projected"), f"{item_where}.projected",
                            {"left", "top", "width", "height"})
            for field in ("left", "top", "width", "height"):
                actual = route_common.finite_number(projected.get(field),
                                                    f"{item_where}.projected.{field}")
                if abs(actual - expected[field]) > max(1e-3, abs(expected[field]) * 1e-9):
                    fail(f"{item_where}.projected.{field}", "与 x/y/z 推导的投影矩形不一致")
            records.append({"x": x, "y": y, "sha256": digest})
        if driving_layout.manifest_digest(
                layer["planDigest"], records) != layer["manifestDigest"]:
            fail(f"{where}.manifestDigest", "与瓦片摘要不一致；请重新运行 basemap")
        return
    layer = obj(value, where, {"zoom", "bbox", "image", "projected", "tileCount", "request"})
    zoom = layer.get("zoom")
    if type(zoom) is not int or not 1 <= zoom <= 18:
        fail(f"{where}.zoom", "必须是 1～18 的整数")
    route_common.validate_bbox(layer.get("bbox"), f"{where}.bbox")
    image = obj(layer.get("image"), f"{where}.image", {"path", "sha256", "width", "height"})
    relative = route_common.validate_path_beneath(image.get("path"), f"{where}.image.path",
                                                  "assets/basemap/road-trip/", {".jpg", ".jpeg"})
    file = (root / relative).resolve()
    if not file.is_file() or not file.is_relative_to(root.resolve()):
        fail(f"{where}.image.path", f"影像不存在：{relative}")
    if hashlib.sha256(file.read_bytes()).hexdigest() != image.get("sha256"):
        fail(f"{where}.image.sha256", "影像摘要不匹配；请重新运行 basemap")
    for field in ("width", "height"):
        value_int = image.get(field)
        if type(value_int) is not int or value_int <= 0:
            fail(f"{where}.image.{field}", "必须是正整数")
    projected = obj(layer.get("projected"), f"{where}.projected",
                    {"left", "top", "width", "height"})
    for field in ("left", "top", "width", "height"):
        route_common.finite_number(projected.get(field), f"{where}.projected.{field}")
    if projected["width"] <= 0 or projected["height"] <= 0:
        fail(f"{where}.projected", "宽高必须大于 0")
    count = layer.get("tileCount")
    if type(count) is not int or count <= 0:
        fail(f"{where}.tileCount", "必须是正整数")
    route_common.validate_request_record(layer.get("request"), f"{where}.request")


def _require_bbox_covers(actual: list[float], required: list[float], where: str) -> None:
    tolerance = 2e-6
    if not (actual[0] <= required[0] + tolerance and actual[1] <= required[1] + tolerance
            and actual[2] >= required[2] - tolerance and actual[3] >= required[3] - tolerance):
        fail(where, "概览影像未覆盖当前相机视口；请重新运行 m2v road-trip basemap")


def _referenced_bytes(root: Path, record: dict[str, Any]) -> int:
    total = (root / record["overview"]["image"]["path"]).stat().st_size
    for tile in record["followTiles"]["tiles"]:
        total += (root / tile["path"]).stat().st_size
    return total


def load_project(project_dir: str | Path, *, require_basemap: bool = True) -> dict[str, Any]:
    """读取并交叉校验全部材料；任何绑定、几何或底图问题都在这里失败。"""
    root = Path(project_dir).resolve()
    if not root.is_dir():
        fail("作品目录", f"目录不存在：{root}")
    trip_doc = _validate_trip(_load_trip(root))
    routes: dict[str, dict[str, Any]] = {}
    previous = None
    for index, day in enumerate(trip_doc["days"]):
        route = _load_route(root, day["route"])
        _validate_route(route, trip_doc["trip"], day, index, previous)
        routes[day["id"]] = route
        previous = route
    index_data = None
    index_path = root / BASEMAP_INDEX
    # 底图命令只需要 trip 与路线：旧索引可能已随路线失效，不能拦住重新取图。
    if require_basemap and index_path.is_file():
        index_data = route_common.load_json(index_path, 1,
                                            hint="请重新运行 m2v road-trip basemap")
        _validate_index(root, index_data, trip_doc, routes)
    if (require_basemap and trip_doc["trip"]["sourceUsage"].get("mapTiles") is True
            and index_data is None):
        fail(BASEMAP_INDEX, "已授权道路底图但缺少底图索引；请先运行 m2v road-trip basemap")
    return {"root": root, "trip": trip_doc["trip"], "days": trip_doc["days"],
            "effects": trip_doc["effects"], "routes": routes, "basemap": index_data}


def load_request(root: Path) -> dict[str, Any]:
    """只读取并校验编排材料；取数前使用，不要求路线已存在。"""
    return _validate_trip(_load_trip(root))


def validate_route_document(trip_doc: dict[str, Any], route: dict[str, Any], day: dict[str, Any],
                            index: int, previous: dict[str, Any] | None) -> None:
    _validate_route(route, trip_doc, day, index, previous)


def _clean_steps(route: dict[str, Any], *, trim_origin: bool) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for step in route_common_steps(route, trim_origin=trim_origin):
        points: list[list[float]] = []
        for point in step["points"]:
            coordinate = [float(point[0]), float(point[1])]
            if not points or points[-1] != coordinate:
                points.append(coordinate)
        if len(points) >= 2:
            steps.append({"road": step["road"], "points": points})
    if not steps:
        fail("route.steps", "去除连续重复点后没有可绘制的道路段")
    return steps


def route_common_steps(route: dict[str, Any], *, trim_origin: bool) -> list[dict[str, Any]]:
    from m2v.types.driving_route import geometry
    return geometry.route_steps_for_render(route, trim_origin=trim_origin)


def build_render_props(docs: dict[str, Any], timeline: dict[str, Any] | None = None,
                       cues: list[dict[str, Any]] | None = None,
                       narration_windows: dict[str, dict[str, int]] | None = None) -> dict[str, Any]:
    """材料 → composition props；底图只保存路径，渲染时注入本地资源基址。"""
    trip = docs["trip"]
    width, height = WIDTH, HEIGHT
    frame = frame_engine.spec(width, height)
    day_records = timeline["days"] if timeline else []
    by_id = {day["id"]: day for day in docs["days"]}
    days_out: list[dict[str, Any]] = []
    for index, day in enumerate(docs["days"]):
        route = docs["routes"][day["id"]]
        timing = day_records[index] if day_records else {}
        props_day: dict[str, Any] = {
            "id": day["id"],
            "title": day["title"],
            "subtitle": day["subtitle"],
            "originLabel": trip["start"]["label"] if index == 0
            else docs["days"][index - 1]["destination"]["label"],
            "destinationLabel": day["destination"]["label"],
            "startFrame": timing.get("startFrame", 0),
            "durationInFrames": timing.get("durationInFrames", 0),
            "steps": _clean_steps(route, trim_origin=index == 0),
            "totalDistanceMeters": route_common_visual_distance(route, index == 0),
            "administrativePlaces": route["administrativePlaces"],
            "cities": route["cities"],
            "card": day["cards"][0] if day["cards"] else None,
            "landmarks": [{"id": point["id"], "label": point["name"],
                           "distanceMeters": point["distanceMeters"]}
                          for point in route["viaPoints"]],
            "narration": day["narration"],
        }
        if timing:
            props_day.update({
                "chapterFrames": timing["chapterFrames"],
                "openingStart": timing["openingStart"],
                "openingFrames": timing["openingFrames"],
                "followStart": timing["followStart"],
                "arrivalLocalFrame": timing["arrivalLocalFrame"],
                "pulloutFrames": timing["pulloutFrames"],
            })
        if narration_windows:
            props_day["segmentWindows"] = narration_windows.get(day["id"], {})
        if docs["basemap"] is not None:
            entry = docs["basemap"]["days"][day["id"]]
            props_day["basemap"] = _basemap_props(entry)
        days_out.append(props_day)
    props: dict[str, Any] = {
        "schemaVersion": 1,
        "durationInFrames": timeline["totalFrames"] if timeline else 0,
        "fps": FPS,
        "width": width,
        "height": height,
        "title": trip["title"],
        "originLabel": trip["start"]["label"],
        "destinationLabel": trip["end"]["label"],
        "attribution": trip["sourceUsage"]["attribution"],
        "sources": {source["id"]: {"title": source["title"],
                                   "publisher": source.get("publisher", "")}
                    for source in trip["sources"]},
        "subtitle": frame["subtitle"],
        "days": days_out,
        "subtitleCues": cues or [],
    }
    if docs["basemap"] is not None:
        props["globalBasemap"] = _overview_props(docs["basemap"]["global"])
    return props


def _overview_props(layer: dict[str, Any]) -> dict[str, Any]:
    return {"path": layer["image"]["path"], "projected": layer["projected"],
            "width": layer["image"]["width"], "height": layer["image"]["height"]}


def _basemap_props(entry: dict[str, Any]) -> dict[str, Any]:
    follow = entry["followTiles"]
    return {
        "style": entry["style"],
        "overview": _overview_props(entry["overview"]),
        "followTiles": {
            "zoom": follow["zoom"],
            "tiles": [{"x": tile["x"], "y": tile["y"], "z": tile["z"],
                       "path": tile["path"], "projected": tile["projected"]}
                      for tile in follow["tiles"]],
        },
    }


def route_common_visual_distance(route: dict[str, Any], trim: bool) -> float:
    from m2v.types.driving_route import geometry
    return geometry.visual_distance_meters(route, trim_origin=trim)


def render_inputs_digest(project_dir: str | Path) -> str:
    """绑定材料、每日路线、底图索引/清单与实现源码。"""
    root = Path(project_dir).resolve()
    docs = load_project(root)
    from m2v.engine import render_pipeline, remotion
    from m2v.core.assets import REPOSITORY_ROOT

    digest = hashlib.sha256()
    web = REPOSITORY_ROOT / "web"
    web_inputs = remotion.build_inputs()
    inputs: list[tuple[Path, Path]] = [(root, root / MATERIALS["trip"])]
    inputs.extend((root, root / day["route"]) for day in docs["days"])
    inputs.extend((web, path) for path in web_inputs if path.is_relative_to(web))
    inputs.extend((REPOSITORY_ROOT, path) for path in web_inputs if not path.is_relative_to(web))
    package = Path(__file__).resolve().parent
    inputs.extend((package, path) for path in sorted(package.glob("*.py")))
    inputs.append((REPOSITORY_ROOT, Path(render_pipeline.__file__)))
    inputs.extend((REPOSITORY_ROOT, path) for path in remotion.implementation_files())
    if docs["basemap"] is not None:
        inputs.append((root, root / BASEMAP_INDEX))
        for day in docs["days"]:
            entry = docs["basemap"]["days"][day["id"]]
            inputs.append((root, root / entry["followTiles"]["manifest"]))
    for base, path in inputs:
        try:
            content = path.read_bytes()
        except OSError as exc:
            fail("渲染输入摘要", f"无法读取绑定文件 {path.name}：{exc}")
        digest.update(path.relative_to(base).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()
