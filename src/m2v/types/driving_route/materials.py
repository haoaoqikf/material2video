"""自驾路线材料契约：请求、真实路线与渲染输入的离线校验。

材料两份：``request.json`` 声明起终点、画面名称、高速优先策略、时长与来源使用
依据；``route.json`` 保存与当前请求绑定的真实定位及驾车路线。渲染只读取这两份
文件，不访问网络，也不需要地图 Key。

几何口径统一使用 GCJ-02 经纬度；距离用球面 haversine 计算，仅用于确定沿路进度，
画面显示的公里数始终取路线材料的 API 距离，不把投影长度冒充实际里程。
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from m2v.core.schema import validate_document
from m2v.core.validate import fail, obj, text
from m2v.core.video_config import DRIVING_ROUTE_FPS
from m2v.types import route_common
from m2v.types.driving_route import geometry, layout as layout_module
from m2v.types.driving_route.schema import DrivingRequest, DrivingRoute

#: 画幅与帧率是类型契约，不由作品或请求临时覆盖。
WIDTH = 1080
HEIGHT = 1920
FPS = DRIVING_ROUTE_FPS

#: 作品清单里的固定材料入口。
MATERIALS = {"request": "request.json", "route": "route.json"}

#: 时长下限：首尾各 2 秒，必须留出至少 1 帧行驶。
MIN_DURATION_SECONDS = 6

#: 共享路线判定；常量与函数保持本模块的历史名字，调用方与错误文案不需要改。
STEP_TOLERANCE_METERS = route_common.STEP_TOLERANCE_METERS
ENDPOINT_TOLERANCE_METERS = route_common.ENDPOINT_TOLERANCE_METERS
START_END_TOLERANCE_METERS = route_common.START_END_TOLERANCE_METERS
EARTH_RADIUS_METERS = route_common.EARTH_RADIUS_METERS
COARSE_LEVELS = route_common.COARSE_LEVELS

_pairs = route_common.pairs_hook
_content_text = route_common.content_text
_date_text = route_common.date_text
_https_url = route_common.https_url
_finite_number = route_common.finite_number
_positive_number = route_common.positive_number
_coordinate = route_common.coordinate
_point_list = route_common.point_list
haversine_meters = route_common.haversine_meters
same_city = route_common.same_city


def _load(path: Path, expected_version: int = 2) -> dict[str, Any]:
    return route_common.load_json(
        path, expected_version,
        hint="旧材料请重新运行 m2v driving-route fetch",
    )


def request_digest(request: dict[str, Any]) -> str:
    """请求的规范化摘要；覆盖全部请求内容，不含任何凭据。"""
    return route_common.canonical_digest(request)


def _validate_place(value: Any, where: str) -> None:
    route_common.validate_place(value, where)


def _validate_source_usage(value: Any, where: str) -> None:
    route_common.validate_source_usage(value, where)


def _validate_request(request: dict[str, Any]) -> None:
    validate_document(DrivingRequest, request, "request.json")
    _validate_place(request.get("origin"), "request.json.origin")
    _validate_place(request.get("destination"), "request.json.destination")
    if request.get("strategy") != "highway-first":
        fail("request.json.strategy", "当前仅支持 highway-first（高速优先）")
    duration = request.get("durationSeconds")
    if type(duration) is not int or duration <= MIN_DURATION_SECONDS:
        fail("request.json.durationSeconds", f"必须是大于 {MIN_DURATION_SECONDS} 的整数秒")
    canvas = obj(request.get("canvas"), "request.json.canvas", {"width", "height"})
    if canvas.get("width") != WIDTH or canvas.get("height") != HEIGHT:
        fail("request.json.canvas", f"固定为 {WIDTH}×{HEIGHT}")
    _validate_source_usage(request.get("sourceUsage"), "request.json.sourceUsage")


def _validate_geocoded_place(value: Any, where: str, expected_city: str) -> tuple[float, float]:
    return route_common.validate_geocoded_place(value, where, expected_city)


def _validate_acquisition(value: Any) -> None:
    route_common.validate_acquisition(value, strategy=34, where="route.json.acquisition")
    acquisition = value
    if len(acquisition["requests"]) > 200:
        fail("route.json.acquisition.requests", "必须记录 1～200 条不含凭据的请求")


def _validate_administrative_places(value: Any, cities: list[dict[str, Any]]) -> None:
    route_common.validate_administrative_places(value, cities, "route.json.administrativePlaces")


def _validate_cost(value: Any, distance_meters: float) -> None:
    route_common.validate_cost(value, distance_meters, "route.json.cost")


def _validate_cities(value: Any) -> None:
    route_common.validate_cities(value, "route.json.cities")


def _validate_bbox(value: Any, where: str) -> list[float]:
    return route_common.validate_bbox(value, where)


def _validate_request_record(value: Any, where: str) -> None:
    route_common.validate_request_record(value, where)


def _validate_basemap_layer(value: Any, where: str) -> None:
    layer = obj(value, where, {"zoom", "bbox", "image", "projected", "tileCount", "request"})
    zoom = layer.get("zoom")
    if type(zoom) is not int or not 1 <= zoom <= 18:
        fail(f"{where}.zoom", "必须是 1～18 的整数")
    _validate_bbox(layer.get("bbox"), f"{where}.bbox")
    image = obj(layer.get("image"), f"{where}.image", {"path", "sha256", "width", "height"})
    path = text(image.get("path"), f"{where}.image.path")
    normalized = Path(path)
    if normalized.is_absolute() or ".." in normalized.parts or not path.startswith("assets/basemap/"):
        fail(f"{where}.image.path", "必须是 assets/basemap/ 下的相对路径")
    if normalized.suffix.lower() not in {".jpg", ".jpeg"}:
        fail(f"{where}.image.path", "必须是 JPEG 影像")
    digest = text(image.get("sha256"), f"{where}.image.sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        fail(f"{where}.image.sha256", "必须是 64 位十六进制 SHA-256")
    for field in ("width", "height"):
        value_int = image.get(field)
        if type(value_int) is not int or value_int <= 0:
            fail(f"{where}.image.{field}", "必须是正整数")
    projected = obj(layer.get("projected"), f"{where}.projected",
                    {"left", "top", "width", "height"})
    for field in ("left", "top", "width", "height"):
        _finite_number(projected.get(field), f"{where}.projected.{field}")
    if projected["width"] <= 0 or projected["height"] <= 0:
        fail(f"{where}.projected", "宽高必须大于 0")
    tile_count = layer.get("tileCount")
    if type(tile_count) is not int or tile_count <= 0:
        fail(f"{where}.tileCount", "必须是正整数")
    _validate_request_record(layer.get("request"), f"{where}.request")


def _validate_follow_tiles(value: Any, where: str, request: dict[str, Any],
                           route: dict[str, Any], tile_style: int) -> None:
    follow = obj(value, where, {"zoom", "tileSize", "tileCount", "planDigest",
                                "manifestDigest", "bbox", "request", "tiles"})
    zoom = follow.get("zoom")
    if type(zoom) is not int or not 1 <= zoom <= 18:
        fail(f"{where}.zoom", "必须是 1～18 的整数")
    if follow.get("tileSize") != 256:
        fail(f"{where}.tileSize", "必须为 256")
    tile_count = follow.get("tileCount")
    if type(tile_count) is not int or not 1 <= tile_count <= layout_module.MAX_CORRIDOR_TILES:
        fail(f"{where}.tileCount", f"必须是 1～{layout_module.MAX_CORRIDOR_TILES} 的整数")
    for field in ("planDigest", "manifestDigest"):
        digest = text(follow.get(field), f"{where}.{field}")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"{where}.{field}", "必须是 64 位十六进制 SHA-256")
    _validate_bbox(follow.get("bbox"), f"{where}.bbox")
    _validate_request_record(follow.get("request"), f"{where}.request")
    tiles = follow.get("tiles")
    if not isinstance(tiles, list) or len(tiles) != tile_count:
        fail(f"{where}.tiles", "必须与 tileCount 一致")
    expected_pixels = 512 if tile_style == 8 else 256
    keys: set[tuple[int, int]] = set()
    records: list[dict[str, Any]] = []
    limit = (1 << zoom) - 1
    for index, raw in enumerate(tiles):
        item_where = f"{where}.tiles[{index}]"
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
        path = text(tile.get("path"), f"{item_where}.path")
        normalized = Path(path)
        if (normalized.is_absolute() or ".." in normalized.parts
                or not path.startswith("assets/basemap/follow-tiles-")):
            fail(f"{item_where}.path", "必须是 assets/basemap/follow-tiles- 下的相对路径")
        if normalized.suffix.lower() not in {".jpg", ".jpeg"}:
            fail(f"{item_where}.path", "必须是 JPEG 瓦片")
        digest = text(tile.get("sha256"), f"{item_where}.sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"{item_where}.sha256", "必须是 64 位十六进制 SHA-256")
        if tile.get("width") != expected_pixels or tile.get("height") != expected_pixels:
            fail(f"{item_where}", f"瓦片尺寸必须为 {expected_pixels}×{expected_pixels}")
        projected = obj(tile.get("projected"), f"{item_where}.projected",
                        {"left", "top", "width", "height"})
        expected = layout_module.tile_projected_rect(x, y, z)
        for field in ("left", "top", "width", "height"):
            actual = _finite_number(projected.get(field), f"{item_where}.projected.{field}")
            if abs(actual - expected[field]) > max(1e-3, abs(expected[field]) * 1e-9):
                fail(f"{item_where}.projected.{field}", "与 x/y/z 推导的投影矩形不一致")
        records.append({"x": x, "y": y, "sha256": digest})

    plan = layout_module.corridor_plan(route, request["durationSeconds"], FPS, zoom,
                                       tile_style=tile_style)
    if follow.get("planDigest") != plan["planDigest"]:
        fail(f"{where}.planDigest", "与当前路线/时长/帧率/底图样式不匹配；请重新运行 basemap")
    if {tile["x"] for tile in plan["tiles"]} and keys != {(tile["x"], tile["y"])
                                                         for tile in plan["tiles"]}:
        fail(f"{where}.tiles", "瓦片集合与相机走廊计划不一致；请重新运行 basemap")
    if follow.get("bbox") != plan["bbox"]:
        fail(f"{where}.bbox", "与相机走廊计划不一致")
    if layout_module.manifest_digest(plan["planDigest"], records) != follow.get("manifestDigest"):
        fail(f"{where}.manifestDigest", "与瓦片摘要不一致；请重新运行 basemap")


def _validate_basemap(value: Any, request: dict[str, Any], route: dict[str, Any]) -> None:
    where = "route.json.basemap"
    basemap = obj(value, where, {"layoutVersion", "provider", "service", "attribution",
                                 "fetchedAt", "overview", "followTiles"})
    version = basemap.get("layoutVersion")
    if type(version) is not int or version != layout_module.layout_version():
        fail(f"{where}.layoutVersion", "布局版本不匹配；请重新运行 m2v driving-route basemap")
    service = basemap.get("service")
    if basemap.get("provider") != "amap" or service not in {"road-tiles", "satellite-tiles"}:
        fail(where, "当前底图只支持 amap road-tiles 或 satellite-tiles")
    if service == "road-tiles":
        for key in ("overview", "followTiles"):
            tile_request = basemap.get(key, {}).get("request")
            params = tile_request.get("params") if isinstance(tile_request, dict) else None
            if (not isinstance(params, dict) or params.get("style") != "8"
                    or params.get("scl") != "2"):
                fail(f"{where}.{key}.request",
                     "道路底图必须使用 style=8、scl=2 的无注记 512 px 瓦片；请重新运行 basemap")
    tile_style = 6 if service == "satellite-tiles" else 8
    _content_text(basemap.get("attribution"), f"{where}.attribution")
    fetched_at = text(basemap.get("fetchedAt"), f"{where}.fetchedAt")
    try:
        parsed = datetime.fromisoformat(fetched_at)
    except ValueError:
        fail(f"{where}.fetchedAt", f"不是有效 ISO 时间：{fetched_at!r}")
    if parsed.tzinfo is None:
        fail(f"{where}.fetchedAt", "必须包含时区")
    _validate_basemap_layer(basemap.get("overview"), f"{where}.overview")
    overview = basemap.get("overview")
    if isinstance(overview, dict) and overview.get("request", {}).get("params", {}).get("style") != str(tile_style):
        fail(f"{where}.overview.request.params.style", f"必须为 {tile_style}")
    follow = basemap.get("followTiles")
    if isinstance(follow, dict) and follow.get("request", {}).get("params", {}).get("style") != str(tile_style):
        fail(f"{where}.followTiles.request.params.style", f"必须为 {tile_style}")
    _validate_follow_tiles(follow, f"{where}.followTiles", request, route, tile_style)


def _route_bbox(steps: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    lngs = [point[0] for step in steps for point in step["points"]]
    lats = [point[1] for step in steps for point in step["points"]]
    return min(lngs), min(lats), max(lngs), max(lats)


def _required_bbox(route_box: tuple[float, float, float, float],
                   half_x: float, half_y: float) -> list[float]:
    min_lng, min_lat = geometry.unproject(route_box[0] - half_x, route_box[1] - half_y)
    max_lng, max_lat = geometry.unproject(route_box[2] + half_x, route_box[3] + half_y)
    return [min_lng, min_lat, max_lng, max_lat]


def _expected_projected_rect(bbox: list[float], zoom: int) -> dict[str, float]:
    left = geometry.project(bbox[0], bbox[3])[0]
    top = -geometry.project(bbox[0], bbox[3])[1]
    right = geometry.project(bbox[2], bbox[1])[0]
    bottom = -geometry.project(bbox[2], bbox[1])[1]
    return {"left": left, "top": top, "width": right - left, "height": bottom - top}


def _validate_basemap_image(root: Path, basemap: dict[str, Any], request: dict[str, Any],
                            route: dict[str, Any]) -> None:
    """校验概览影像与跟随瓦片的文件、摘要、尺寸和逐帧覆盖。"""
    from PIL import Image

    route_box = geometry.route_projected_bbox(route)
    envelope = layout_module.camera_envelope(
        route_box, geometry.projected_length(route), geometry.visual_distance_meters(route))
    overview_need = _required_bbox(route_box, envelope["overview_half_x"],
                                   envelope["overview_half_y"])
    overview = basemap["overview"]
    follow = basemap["followTiles"]
    expected_zoom = layout_module.zoom_for_scale(envelope["follow_scale"], minimum=9)
    if follow["zoom"] != expected_zoom:
        fail("route.json.basemap.followTiles.zoom",
             f"跟随瓦片应为 z{expected_zoom}；请重新运行 m2v driving-route basemap")
    where = "route.json.basemap.overview"
    relative = Path(overview["image"]["path"])
    file = (root / relative).resolve()
    if not file.is_relative_to(root.resolve()) or not file.is_file():
        fail(f"{where}.image.path", f"影像不存在：{relative}")
    content = file.read_bytes()
    if hashlib.sha256(content).hexdigest() != overview["image"]["sha256"]:
        fail(f"{where}.image.sha256", "影像摘要不匹配；请重新运行 m2v driving-route basemap")
    try:
        with Image.open(file) as image:
            size = image.size
    except Exception as exc:  # noqa: BLE001 - 任意解码失败都转为材料错误
        fail(f"{where}.image", f"无法解码影像：{exc}")
    if size != (overview["image"]["width"], overview["image"]["height"]):
        fail(f"{where}.image", "影像尺寸与记录不一致")
    bbox = overview["bbox"]
    if not (bbox[0] <= overview_need[0] + 2e-6 and bbox[1] <= overview_need[1] + 2e-6
            and bbox[2] >= overview_need[2] - 2e-6 and bbox[3] >= overview_need[3] - 2e-6):
        fail(f"{where}.bbox", "道路底图包围盒未覆盖当前相机视口；请重新运行 basemap")
    expected_projected = _expected_projected_rect(bbox, overview["zoom"])
    tolerance = 2.5 * geometry.WORLD / ((1 << overview["zoom"]) * 256)
    for field, expected in expected_projected.items():
        if abs(overview["projected"][field] - expected) > tolerance:
            fail(f"{where}.projected.{field}", "与包围盒/缩放推导的投影矩形不一致；请重新运行 basemap")

    stored: set[tuple[int, int]] = set()
    for index, tile in enumerate(follow["tiles"]):
        item_where = f"route.json.basemap.followTiles.tiles[{index}]"
        tile_path = (root / tile["path"]).resolve()
        if not tile_path.is_relative_to(root.resolve()) or not tile_path.is_file():
            fail(f"{item_where}.path", f"瓦片不存在：{tile['path']}")
        tile_bytes = tile_path.read_bytes()
        if hashlib.sha256(tile_bytes).hexdigest() != tile["sha256"]:
            fail(f"{item_where}.sha256", "瓦片摘要不匹配；请重新运行 m2v driving-route basemap")
        try:
            with Image.open(tile_path) as image:
                tile_size = image.size
        except Exception as exc:  # noqa: BLE001
            fail(item_where, f"无法解码瓦片：{exc}")
        if tile_size != (tile["width"], tile["height"]):
            fail(item_where, "瓦片尺寸与记录不一致")
        stored.add((tile["x"], tile["y"]))

    tile_style = 6 if basemap.get("service") == "satellite-tiles" else 8
    missing = layout_module.missing_corridor_tiles(
        route, request["durationSeconds"], FPS, follow["zoom"], stored, tile_style)
    if missing:
        x, y = sorted(missing)[0]
        fail("route.json.basemap.followTiles",
             f"缺少 {len(missing)} 块相机走廊瓦片（首块 {x}:{y}）；请重新运行 basemap")


def _validate_route(request: dict[str, Any], route: dict[str, Any]) -> None:
    validate_document(DrivingRoute, route, "route.json")
    digest = text(route.get("requestDigest"), "route.json.requestDigest")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        fail("route.json.requestDigest", "必须是 64 位十六进制 SHA-256 摘要")
    if digest != request_digest(request):
        fail("route.json.requestDigest", "与当前 request.json 不匹配；请重新运行 m2v driving-route fetch")
    if route.get("coordinateSystem") != "GCJ-02":
        fail("route.json.coordinateSystem", "必须为 GCJ-02")

    origin_location = _validate_geocoded_place(
        route.get("origin"), "route.json.origin", request["origin"]["city"])
    destination_location = _validate_geocoded_place(
        route.get("destination"), "route.json.destination", request["destination"]["city"])

    path = obj(route.get("route"), "route.json.route",
               {"distanceMeters", "startPoint", "endPoint", "steps"})
    distance_meters = _positive_number(path.get("distanceMeters"), "route.json.route.distanceMeters")
    start_point = _coordinate(path.get("startPoint"), "route.json.route.startPoint")
    end_point = _coordinate(path.get("endPoint"), "route.json.route.endPoint")
    steps = path.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 5000:
        fail("route.json.route.steps", "必须包含 1～5000 个道路段")
    previous_last: tuple[float, float] | None = None
    first_point: tuple[float, float] | None = None
    last_point: tuple[float, float] | None = None
    for index, raw in enumerate(steps):
        where = f"route.json.route.steps[{index}]"
        step = obj(raw, where, {"road", "distanceMeters", "points"})
        _content_text(step.get("road"), f"{where}.road")
        _finite_number(step.get("distanceMeters"), f"{where}.distanceMeters", low=0)
        points = _point_list(step.get("points"), f"{where}.points")
        if first_point is None:
            first_point = points[0]
        if previous_last is not None:
            gap = haversine_meters(previous_last, points[0])
            if gap > STEP_TOLERANCE_METERS:
                fail(where, f"与上一段终点相距 {gap:.1f} 米，超过 {STEP_TOLERANCE_METERS:g} 米容差；"
                            "拒绝跨缺口连接")
        previous_last = points[-1]
        last_point = points[-1]

    assert first_point is not None and last_point is not None
    if haversine_meters(start_point, first_point) > START_END_TOLERANCE_METERS:
        fail("route.json.route.startPoint", "必须与首个道路段的第一个坐标一致")
    if haversine_meters(end_point, last_point) > START_END_TOLERANCE_METERS:
        fail("route.json.route.endPoint", "必须与最后一个道路段的最后一个坐标一致")
    if haversine_meters(origin_location, start_point) > ENDPOINT_TOLERANCE_METERS:
        fail("route.json.route.startPoint", "距定位点超过 1 公里；不能把定位与吸附端点混作一处")
    if haversine_meters(destination_location, end_point) > ENDPOINT_TOLERANCE_METERS:
        fail("route.json.route.endPoint", "距定位点超过 1 公里；不能把定位与吸附端点混作一处")
    if _route_length(steps) <= 0:
        fail("route.json.route.steps", "路线总长度必须大于 0")

    _validate_acquisition(route.get("acquisition"))
    _validate_source_usage(route.get("sourceUsage"), "route.json.sourceUsage")
    if route["sourceUsage"] != request["sourceUsage"]:
        fail("route.json.sourceUsage", "必须与当前 request.json.sourceUsage 一致；请重新运行 m2v driving-route fetch")
    _validate_cost(route.get("cost"), distance_meters)
    _validate_cities(route.get("cities"))
    _validate_administrative_places(route.get("administrativePlaces"), route.get("cities"))
    if "basemap" in route:
        _validate_basemap(route["basemap"], request, route)


def _route_length(steps: list[dict[str, Any]]) -> float:
    total = 0.0
    for step in steps:
        points = step["points"]
        for index in range(1, len(points)):
            total += haversine_meters(tuple(points[index - 1]), tuple(points[index]))
    return total


def load_request(project_dir: str | Path) -> dict[str, Any]:
    """只读取并校验请求；取数前使用，不要求路线已存在。"""
    root = Path(project_dir).resolve()
    request = _load(root / MATERIALS["request"], 2)
    _validate_request(request)
    return request


def _require_basemap(request: dict[str, Any], route: dict[str, Any]) -> None:
    if request["sourceUsage"].get("mapTiles") is True and "basemap" not in route:
        fail("route.json.basemap",
             "已授权道路底图但缺少底图材料；请先运行 m2v driving-route basemap；"
             "如不需要道路底图，请将 mapTiles 设为 false")


def load_project(project_dir: str | Path) -> dict[str, Any]:
    """读取并交叉校验两份材料；任何绑定或几何问题都在这里失败。"""
    root = Path(project_dir).resolve()
    if not root.is_dir():
        fail("作品目录", f"目录不存在：{root}")
    request = _load(root / MATERIALS["request"], 2)
    route = _load(root / MATERIALS["route"], 3)
    _validate_request(request)
    _validate_route(request, route)
    _require_basemap(request, route)
    docs = {"request": request, "route": route}
    if "basemap" in route:
        _validate_basemap_image(root, route["basemap"], request, route)
        overview_path = root / route["basemap"]["overview"]["image"]["path"]
        docs["basemapDataUris"] = {
            "overview": "data:image/jpeg;base64," + base64.b64encode(
                overview_path.read_bytes()).decode("ascii"),
            "followTiles": [
                "data:image/jpeg;base64," + base64.b64encode(
                    (root / tile["path"]).read_bytes()).decode("ascii")
                for tile in route["basemap"]["followTiles"]["tiles"]
            ],
        }
    return docs


def validate_route_document(request: dict[str, Any], route: dict[str, Any]) -> None:
    """取数写入前的完整校验；与离线读取共用同一套规则。"""
    _validate_route(request, route)


def build_render_props(docs: dict[str, Any]) -> dict[str, Any]:
    """材料 → composition props。连续重复点在这里被去除，渲染不再处理脏坐标。"""
    request, route = docs["request"], docs["route"]
    _require_basemap(request, route)
    steps: list[dict[str, Any]] = []
    render_steps = geometry.route_steps_for_render(route)
    for step in render_steps:
        points: list[list[float]] = []
        for point in step["points"]:
            coordinate = [float(point[0]), float(point[1])]
            if not points or points[-1] != coordinate:
                points.append(coordinate)
        if len(points) >= 2:
            steps.append({"road": step["road"], "points": points})
    if not steps:
        fail("route.json.route.steps", "去除连续重复点后没有可绘制的道路段")
    props = {
        "schemaVersion": 2,
        "durationInFrames": request["durationSeconds"] * FPS,
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "originLabel": request["origin"]["label"],
        "destinationLabel": request["destination"]["label"],
        "origin": route["origin"]["location"],
        "destination": route["destination"]["location"],
        "routeStart": steps[0]["points"][0],
        "routeEnd": route["route"]["endPoint"],
        "totalDistanceMeters": geometry.visual_distance_meters(route),
        "attribution": request["sourceUsage"]["attribution"],
        "cost": route["cost"],
        "cities": route["cities"],
        "administrativePlaces": route["administrativePlaces"],
        "steps": steps,
    }
    if "basemap" in route:
        data_uris = docs.get("basemapDataUris")
        if not isinstance(data_uris, dict) or set(data_uris) != {"overview", "followTiles"}:
            fail("route.json.basemap", "缺少已加载的道路底图影像；请重新 prepare")
        follow = route["basemap"]["followTiles"]
        uris = data_uris["followTiles"]
        if not isinstance(uris, list) or len(uris) != len(follow["tiles"]):
            fail("route.json.basemap.followTiles", "瓦片影像数量与记录不一致；请重新 prepare")
        props["basemap"] = {
            "provider": route["basemap"]["provider"],
            "service": route["basemap"]["service"],
            "attribution": route["basemap"]["attribution"],
            "fetchedAt": route["basemap"]["fetchedAt"],
            "overview": {**route["basemap"]["overview"], "dataUri": data_uris["overview"]},
            "followTiles": {
                "zoom": follow["zoom"],
                "tileSize": follow["tileSize"],
                "tiles": [
                    {"x": tile["x"], "y": tile["y"], "z": tile["z"],
                     "projected": tile["projected"], "dataUri": uri}
                    for tile, uri in zip(follow["tiles"], uris, strict=True)
                ],
            },
        }
    return props


def render_inputs_digest(project_dir: str | Path) -> str:
    """把材料、共享画面源码与本类型实现绑定到候选与预演。"""
    root = Path(project_dir).resolve()
    from m2v.core.assets import REPOSITORY_ROOT
    import m2v.engine.remotion as remotion
    from m2v.engine import render_pipeline

    web = REPOSITORY_ROOT / "web"
    web_inputs = remotion.build_inputs()
    inputs: list[tuple[Path, Path]] = [(root, root / name) for name in MATERIALS.values()]
    inputs.extend((web, path) for path in web_inputs if path.is_relative_to(web))
    inputs.extend((REPOSITORY_ROOT, path) for path in web_inputs if not path.is_relative_to(web))
    package = Path(__file__).resolve().parent
    inputs.extend((package, path) for path in sorted(package.glob("*.py")))
    inputs.append((REPOSITORY_ROOT, Path(render_pipeline.__file__)))
    inputs.extend((REPOSITORY_ROOT, path) for path in remotion.implementation_files())
    route = _load(root / MATERIALS["route"], 3)
    if "basemap" in route:
        overview = root / route["basemap"]["overview"]["image"]["path"]
        if not overview.is_file():
            fail("route.json.basemap.overview.image.path", f"道路底图影像不存在：{overview}")
        inputs.append((root, overview))
        for index, tile in enumerate(route["basemap"]["followTiles"]["tiles"]):
            image = root / tile["path"]
            if not image.is_file():
                fail(f"route.json.basemap.followTiles.tiles[{index}].path",
                     f"跟随瓦片不存在：{image}")
            inputs.append((root, image))

    digest = hashlib.sha256()
    for base, path in inputs:
        try:
            content = path.read_bytes()
        except OSError as exc:
            fail("渲染输入摘要", f"无法读取绑定文件 {path.name}：{exc}")
        digest.update(path.relative_to(base).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()
