"""多日地图游记的共享布局、每日相机与底图走廊。

Python 与前端读同一份 `web/src/types/road_trip/layout.json`：章节卡、
相机倍率、跟随倍率窗口与字幕安全区的口径不在这里另写一遍。几何投影与瓦片
反算复用 `driving_route` 的实现，保证两类地图视频的底图坐标完全一致。
"""
from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from m2v.core.assets import REPOSITORY_ROOT
from m2v.core.errors import M2VError
from m2v.types.driving_route import geometry
from m2v.types.driving_route import layout as driving_layout

LAYOUT_PATH = REPOSITORY_ROOT / "web/src/types/road_trip/layout.json"
TILE_SIZE = driving_layout.TILE_SIZE
SAMPLE_STEP_METERS = 400.0
#: 相机平滑取样步长固定为米制，不随天数或旁白时长变化；否则走廊清单会随
#: 旁白修改而漂移，违背「改旁白不重取瓦片」。
SMOOTHING_STEP_METERS = 400.0
MAX_DAY_TILES = 2200
MAX_TRIP_TILES = 6000
MAX_TRIP_BYTES = 500 * 1024 * 1024


@lru_cache(maxsize=1)
def layout() -> dict[str, Any]:
    return json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))


def layout_version() -> int:
    return int(layout()["version"])


def content_rect(width: int | None = None, height: int | None = None) -> dict[str, float]:
    spec = layout()
    width = int(width or spec["width"])
    height = int(height or spec["height"])
    top = spec["title"]["height"] + spec["content"]["topGap"]
    bottom = height - spec["content"]["bottomMargin"]
    left = spec["content"]["sideMargin"]
    right = width - spec["content"]["sideMargin"]
    padding = spec["content"]["padding"]
    return {
        "top": top, "bottom": bottom, "left": left, "right": right,
        "inner_top": top + padding, "inner_bottom": bottom - padding,
        "inner_left": left + padding, "inner_right": right - padding,
        "cx": (left + right) / 2, "cy": (top + bottom) / 2,
    }


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def _smoothstep(value: float) -> float:
    t = _clamp(value, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _ease_out_quad(value: float) -> float:
    t = _clamp(value, 0.0, 1.0)
    return 1 - (1 - t) * (1 - t)


def day_geometry(route: dict[str, Any], *, trim_origin: bool) -> dict[str, Any]:
    """与前端 buildRouteModel 同口径；只有第 1 天裁掉起点接驳路。"""
    coordinates: list[tuple[float, float]] = []
    for step in geometry.route_steps_for_render(route, trim_origin=trim_origin):
        for raw in step["points"]:
            point = (float(raw[0]), float(raw[1]))
            if not coordinates or coordinates[-1] != point:
                coordinates.append(point)
    if len(coordinates) < 2:
        raise M2VError("路线至少需要两个不同坐标点")
    projected = [(x, -y) for x, y in (geometry.project(point[0], point[1]) for point in coordinates)]
    cumulative = [0.0]
    for index in range(1, len(coordinates)):
        cumulative.append(cumulative[-1] + driving_layout._haversine_meters(
            coordinates[index - 1], coordinates[index]))
    projected_length = sum(
        math.dist(projected[index - 1], projected[index]) for index in range(1, len(projected)))
    xs = [point[0] for point in projected]
    ys = [point[1] for point in projected]
    return {
        "coordinates": coordinates,
        "projected": projected,
        "cumulative": cumulative,
        "length_meters": cumulative[-1],
        "projected_length": projected_length,
        "bounds": (min(xs), min(ys), max(xs), max(ys)),
    }


def full_scale(geom: dict[str, Any], width: int, height: int) -> float:
    content = content_rect(width, height)
    span_x = max(geom["bounds"][2] - geom["bounds"][0], 1e-6)
    span_y = max(geom["bounds"][3] - geom["bounds"][1], 1e-6)
    return min((content["inner_right"] - content["inner_left"]) / span_x,
               (content["inner_bottom"] - content["inner_top"]) / span_y)


def day_spans(day_frames: int, fps: int) -> dict[str, int]:
    """每日镜头账本：章节卡 → 开场推近 → 跟随 → 当天概览收束。"""
    spec = layout()
    chapter = min(spec["timeline"]["chapterFrames"], max(0, day_frames - 2))
    opening = min(round(spec["camera"]["openingSeconds"] * fps),
                  max(0, day_frames - chapter - 1))
    pullout = min(round(spec["camera"]["pulloutSeconds"] * fps),
                  max(1, day_frames - chapter - opening - 1))
    arrival = day_frames - pullout
    return {
        "chapter_frames": chapter,
        "opening_start": chapter,
        "opening_frames": opening,
        "follow_start": chapter + opening,
        "arrival_frame": arrival,
        "drive_frames": max(1, arrival - chapter - opening),
        "pullout_frames": pullout,
        "day_frames": day_frames,
    }


def landmark_fraction(route: dict[str, Any], landmark_id: str, *, trim_origin: bool) -> float:
    """地标在当天路线上的里程比例；没有地标时返回 0。"""
    geom = day_geometry(route, trim_origin=trim_origin)
    for landmark in route.get("viaPoints", []):
        if landmark.get("id") == landmark_id:
            return _clamp(float(landmark["distanceMeters"]) / max(1.0, geom["length_meters"]),
                          0.0, 1.0)
    raise M2VError(f"当天路线没有地标 {landmark_id} 的位置记录；请重新运行 road-trip fetch")


def zoom_window(day_id: str) -> dict[str, Any] | None:
    for window in layout()["followZoomWindows"]:
        if window["dayId"] == day_id:
            return window
    return None


def follow_multiplier(day_id: str, route: dict[str, Any], distance_fraction: float,
                      *, trim_origin: bool) -> float:
    """跟随倍率：静态布局声明的窗口内平滑提高，不使用随机或逐帧计算。"""
    window = zoom_window(day_id)
    base = float(layout()["camera"]["followZoom"])
    if not window:
        return base
    center = landmark_fraction(route, window["landmarkId"], trim_origin=trim_origin)
    span = max(1e-6, 0.06)
    near = _clamp(1 - abs(distance_fraction - center) / span, 0.0, 1.0)
    return base + (float(window["zoom"]) - base) * _smoothstep(near)


def max_follow_multiplier(day_id: str) -> float:
    window = zoom_window(day_id)
    return float(window["zoom"]) if window else float(layout()["camera"]["followZoom"])


def distance_for_local_frame(geom: dict[str, Any], local_frame: int, day_frames: int,
                             fps: int) -> float:
    spans = day_spans(day_frames, fps)
    if local_frame < spans["follow_start"]:
        return 0.0
    if local_frame >= spans["arrival_frame"]:
        return geom["length_meters"]
    progress = _clamp((local_frame - spans["follow_start"] + 1) / spans["drive_frames"], 0.0, 1.0)
    return geom["length_meters"] * progress


def _smoothed_point(geom: dict[str, Any], distance: float, frame_step_meters: float,
                    half_frames: int) -> tuple[float, float]:
    sx = sy = 0.0
    count = 2 * half_frames + 1
    for offset in range(-half_frames, half_frames + 1):
        point = driving_layout._point_at_distance(geom, distance + offset * frame_step_meters)
        sx += point[0]
        sy += point[1]
    return sx / count, sy / count


def follow_camera(geom: dict[str, Any], distance: float, width: int, height: int,
                  frame_step_meters: float, half_frames: int, day_id: str,
                  route: dict[str, Any], *, trim_origin: bool) -> dict[str, float]:
    content = content_rect(width, height)
    full = full_scale(geom, width, height)
    fraction = _clamp(distance / max(1.0, geom["length_meters"]), 0.0, 1.0)
    scale = full * follow_multiplier(day_id, route, fraction, trim_origin=trim_origin)
    meters_per_projected = (geom["length_meters"] / geom["projected_length"]
                            if geom["projected_length"] > 0 else 1.0)
    visible_meters = (min(width, height) / scale) * meters_per_projected
    lookahead = min(geom["length_meters"] * layout()["camera"].get("lookaheadRouteFraction", 0.02),
                    visible_meters * layout()["camera"].get("lookaheadViewFraction", 0.2))
    target_distance = min(distance + lookahead * layout()["camera"].get("lookaheadTargetFraction", 0.5),
                          geom["length_meters"])
    target = _smoothed_point(geom, target_distance, frame_step_meters, half_frames)
    # 整像素平移：底图、路线与标签共享同一重采样相位。
    return {
        "scale": scale,
        "tx": round(content["cx"] - target[0] * scale),
        "ty": round(content["cy"] - target[1] * scale),
    }


def opening_camera(geom: dict[str, Any], amount: float, width: int, height: int) -> dict[str, float]:
    content = content_rect(width, height)
    full = full_scale(geom, width, height)
    start_scale = full * layout()["camera"]["openingStartZoom"]
    end_scale = full * layout()["camera"]["openingEndZoom"]
    scale = start_scale + (end_scale - start_scale) * _ease_out_quad(amount)
    start = geom["projected"][0]
    return {"scale": scale, "tx": content["cx"] - start[0] * scale,
            "ty": content["cy"] - start[1] * scale}


def overview_camera(geom: dict[str, Any], width: int, height: int) -> dict[str, float]:
    content = content_rect(width, height)
    scale = full_scale(geom, width, height)
    return {
        "scale": scale,
        "tx": content["cx"] - (geom["bounds"][0] + geom["bounds"][2]) / 2 * scale,
        "ty": content["cy"] - (geom["bounds"][1] + geom["bounds"][3]) / 2 * scale,
    }


def _mix_camera(first: dict[str, float], second: dict[str, float], amount: float) -> dict[str, float]:
    t = _smoothstep(amount)
    return {"scale": first["scale"] + (second["scale"] - first["scale"]) * t,
            "tx": first["tx"] + (second["tx"] - first["tx"]) * t,
            "ty": first["ty"] + (second["ty"] - first["ty"]) * t}


def camera_for_local_frame(geom: dict[str, Any], local_frame: int, day_frames: int, fps: int,
                           width: int, height: int, day_id: str, route: dict[str, Any],
                           *, trim_origin: bool) -> dict[str, float]:
    spans = day_spans(day_frames, fps)
    frame_step_meters = SMOOTHING_STEP_METERS
    half_frames = int(layout()["camera"]["cameraSmoothingSeconds"] * fps + 0.5)
    distance = distance_for_local_frame(geom, local_frame, day_frames, fps)
    if local_frame < spans["opening_start"]:
        return overview_camera(geom, width, height)
    if local_frame < spans["follow_start"]:
        amount = (1.0 if spans["opening_frames"] <= 1
                  else (local_frame - spans["opening_start"]) / spans["opening_frames"])
        return opening_camera(geom, amount, width, height)
    if local_frame < spans["arrival_frame"]:
        return follow_camera(geom, distance, width, height, frame_step_meters, half_frames,
                             day_id, route, trim_origin=trim_origin)
    return _mix_camera(
        follow_camera(geom, geom["length_meters"], width, height, frame_step_meters, half_frames,
                      day_id, route, trim_origin=trim_origin),
        overview_camera(geom, width, height),
        (local_frame - spans["arrival_frame"] + 1) / spans["pullout_frames"])


def day_overview_bbox(geom: dict[str, Any], width: int, height: int) -> tuple[list[float], float]:
    """当天概览影像的经纬度包围盒与缩放。"""
    scale = full_scale(geom, width, height)
    content = content_rect(width, height)
    # 屏幕视口半宽（像素）换算成投影米；概览相机把路线 bbox 中心放在内容区中心。
    half_x = width / (2 * scale) * 1.04
    half_y = max(content["cy"], height - content["cy"]) / scale * 1.04
    center_x = (geom["bounds"][0] + geom["bounds"][2]) / 2
    center_y = (geom["bounds"][1] + geom["bounds"][3]) / 2
    left = center_x - half_x
    right = center_x + half_x
    top = center_y - half_y
    bottom = center_y + half_y
    # 屏幕 y 向下为正，Web Mercator 的 y 向上为正，换算前取负。
    min_lng, min_lat = geometry.unproject(left, -bottom)
    max_lng, max_lat = geometry.unproject(right, -top)
    return [round(min_lng, 6), round(min_lat, 6), round(max_lng, 6), round(max_lat, 6)], scale


def trip_geometry(days: list[dict[str, Any]]) -> dict[str, Any]:
    coordinates: list[tuple[float, float]] = []
    for index, route in enumerate(days):
        geom = day_geometry(route, trim_origin=index == 0)
        coordinates.extend(geom["coordinates"])
    projected = [(x, -y) for x, y in (geometry.project(point[0], point[1]) for point in coordinates)]
    xs = [point[0] for point in projected]
    ys = [point[1] for point in projected]
    return {
        "coordinates": coordinates,
        "projected": projected,
        "bounds": (min(xs), min(ys), max(xs), max(ys)),
        "length_meters": 1.0,
        "projected_length": 1.0,
        "cumulative": [0.0, 1.0],
    }


def trip_overview_bbox(geom: dict[str, Any], width: int, height: int) -> tuple[list[float], float]:
    return day_overview_bbox(geom, width, height)


def plan_digest(keys: set[tuple[int, int]], zoom: int, day_id: str, width: int, height: int,
                tile_style: int) -> str:
    canonical = {
        "layoutVersion": layout_version(), "kind": "road-trip-day",
        "dayId": day_id, "width": width, "height": height,
        "zoom": zoom, "tileSize": TILE_SIZE, "style": tile_style,
        "tiles": [[x, y] for x, y in sorted(keys)],
    }
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def corridor_plan(route: dict[str, Any], day_id: str, zoom: int, *, day_index: int,
                  width: int = 1080, height: int = 1920,
                  tile_style: int = driving_layout.TILE_STYLE) -> dict[str, Any]:
    """每日跟随走廊：按整条路线取样相机视口并集。

    走廊只依赖路线与静态布局，不读取旁白、帧数或视频时长；改旁白只重编译
    时间轴，不会让底图清单变化。prepare 再用编译后的逐帧相机复核覆盖。
    """
    trim_origin = day_index == 0
    geom = day_geometry(route, trim_origin=trim_origin)
    frame_step_meters = SMOOTHING_STEP_METERS
    half_frames = int(layout()["camera"]["cameraSmoothingSeconds"] * 30 + 0.5)
    keys: set[tuple[int, int]] = set()
    for step in range(17):
        keys |= driving_layout.view_tile_keys(
            opening_camera(geom, step / 16, width, height), width, height, zoom, 2)
    distance = 0.0
    while distance <= geom["length_meters"]:
        keys |= driving_layout.view_tile_keys(
            follow_camera(geom, distance, width, height, frame_step_meters, half_frames,
                          day_id, route, trim_origin=trim_origin), width, height, zoom, 2)
        distance += SAMPLE_STEP_METERS
    tail = follow_camera(geom, geom["length_meters"], width, height, frame_step_meters,
                         half_frames, day_id, route, trim_origin=trim_origin)
    for step in range(17):
        keys |= driving_layout.view_tile_keys(
            _mix_camera(tail, overview_camera(geom, width, height), step / 16),
            width, height, zoom, 2)
    if len(keys) > MAX_DAY_TILES:
        raise M2VError(f"第 {day_id} 天跟随走廊需要 {len(keys)} 块瓦片，超过单日上限 "
                       f"{MAX_DAY_TILES}；请调整跟随倍率，不得静默降低缩放")
    ordered = sorted(keys, key=lambda key: (key[1], key[0]))
    tiles = [{"x": x, "y": y, "z": zoom,
              "projected": driving_layout.tile_projected_rect(x, y, zoom)}
             for x, y in ordered]
    return {
        "dayId": day_id,
        "zoom": zoom,
        "tileSize": TILE_SIZE,
        "tileCount": len(tiles),
        "planDigest": plan_digest(keys, zoom, day_id, width, height, tile_style),
        "bbox": driving_layout._tile_bbox(keys, zoom),
        "request": {"path": "/appmaptile",
                    "params": {"style": str(tile_style), "lang": driving_layout.TILE_LANG,
                               "zoom": str(zoom),
                               **({"scl": "2"}
                                  if tile_style == driving_layout.TILE_STYLE else {})}},
        "tiles": tiles,
    }


def follow_zoom(route: dict[str, Any], day_id: str, day_index: int, *,
                width: int = 1080, height: int = 1920,
                tile_style: int = driving_layout.TILE_STYLE) -> int:
    """跟随瓦片缩放：按屏幕像素选一块约 1.5 倍过采样的瓦片。

    自驾路线按整像素过采样选 zoom；多日行程动辄数百公里，同样的口径会把
    单日走廊推到数千块。这里允许约 1.5 倍过采样，画面仍清晰，块数可控。
    """
    geom = day_geometry(route, trim_origin=day_index == 0)
    scale = full_scale(geom, width, height) * max_follow_multiplier(day_id)
    pixels = 512 if tile_style == driving_layout.TILE_STYLE else 256
    raw = scale * geometry.WORLD / (pixels * 1.5)
    zoom = 0 if raw <= 1 else int(math.floor(math.log2(raw)))
    return max(9, min(18, zoom))


def missing_corridor_tiles(route: dict[str, Any], day_id: str, zoom: int,
                           stored: set[tuple[int, int]], *, day_index: int,
                           width: int = 1080, height: int = 1920,
                           tile_style: int = driving_layout.TILE_STYLE) -> set[tuple[int, int]]:
    plan = corridor_plan(route, day_id, zoom, day_index=day_index,
                         width=width, height=height, tile_style=tile_style)
    return {(tile["x"], tile["y"]) for tile in plan["tiles"]} - stored


def visible_tiles_for_frame(route: dict[str, Any], day_id: str, day_index: int,
                            local_frame: int, day_frames: int, fps: int, zoom: int,
                            *, width: int = 1080, height: int = 1920) -> set[tuple[int, int]]:
    """编译后的逐帧相机实际需要的瓦片；prepare 用它复核走廊覆盖。"""
    geom = day_geometry(route, trim_origin=day_index == 0)
    camera = camera_for_local_frame(geom, local_frame, day_frames, fps, width, height,
                                    day_id, route, trim_origin=day_index == 0)
    return driving_layout.view_tile_keys(camera, width, height, zoom, 2)
