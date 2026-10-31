"""自驾路线画面布局的唯一常量源（与前端 layout.json 同源）。"""
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

LAYOUT_PATH = REPOSITORY_ROOT / "web/src/compositions/driving/layout.json"
EARTH_RADIUS_METERS = 6371008.8
TILE_SIZE = 256
TILE_STYLE = 8
TILE_LANG = "zh_cn"
SAMPLE_STEP_METERS = 1000.0
MAX_CORRIDOR_TILES = 2200


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


def camera_envelope(route_bbox: tuple[float, float, float, float],
                    projected_length: float,
                    route_length_meters: float) -> dict[str, float]:
    """计算全程/跟随底图需要覆盖的投影半宽/半高与相机比例。

    route_bbox 与 projected_length 使用与前端一致的 Web Mercator 米；底层只服务
    本类型的底图取图与校验，不替代前端相机。
    """
    spec = layout()
    content = content_rect()
    span_x = max(route_bbox[2] - route_bbox[0], 1.0)
    span_y = max(route_bbox[3] - route_bbox[1], 1.0)
    inner_w = content["inner_right"] - content["inner_left"]
    inner_h = content["inner_bottom"] - content["inner_top"]
    full_scale = min(inner_w / span_x, inner_h / span_y)
    camera = spec["camera"]
    follow_scale = full_scale * camera["followZoom"]
    opening_scale = full_scale * camera["openingStartZoom"]
    meters_per_projected = (route_length_meters / projected_length) if projected_length > 0 else 1.0
    visible_meters = min(spec["width"], spec["height"]) / follow_scale * meters_per_projected
    lookahead_meters = min(route_length_meters * camera["lookaheadRouteFraction"],
                           visible_meters * camera["lookaheadViewFraction"])
    lookahead_projected = lookahead_meters / meters_per_projected if meters_per_projected > 0 else 0.0
    # 相机中心在内容区中心（略低于画幅中心），上下覆盖必须取到画幅边缘的最大距离。
    vertical_half = max(content["cy"], spec["height"] - content["cy"]) / full_scale
    overview_half_x = spec["width"] / (2 * full_scale) + lookahead_projected / 2
    overview_half_y = vertical_half + lookahead_projected / 2
    follow_half_x = max(spec["width"] / (2 * follow_scale),
                        spec["width"] / (2 * opening_scale)) + lookahead_projected / 2
    follow_half_y = max(vertical_half * full_scale / follow_scale,
                        vertical_half * full_scale / opening_scale) + lookahead_projected / 2
    return {
        "full_scale": full_scale,
        "follow_scale": follow_scale,
        "opening_scale": opening_scale,
        "lookahead_meters": lookahead_meters,
        "lookahead_projected": lookahead_projected,
        "overview_half_x": overview_half_x,
        "overview_half_y": overview_half_y,
        "follow_half_x": follow_half_x,
        "follow_half_y": follow_half_y,
    }


def _haversine_meters(a: tuple[float, float], b: tuple[float, float]) -> float:
    lng1, lat1 = math.radians(a[0]), math.radians(a[1])
    lng2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.asin(min(1.0, math.sqrt(h)))


def route_geometry(route: dict[str, Any]) -> dict[str, Any]:
    """与前端 buildRouteModel 同口径：去连续重复点、球面累计距离、投影折线。"""
    coordinates: list[tuple[float, float]] = []
    for step in geometry.route_steps_for_render(route):
        for raw in step["points"]:
            point = (float(raw[0]), float(raw[1]))
            if not coordinates or coordinates[-1] != point:
                coordinates.append(point)
    if len(coordinates) < 2:
        raise M2VError("路线至少需要两个不同坐标点")
    projected = [(x, -y) for x, y in (geometry.project(point[0], point[1]) for point in coordinates)]
    cumulative = [0.0]
    for index in range(1, len(coordinates)):
        cumulative.append(cumulative[-1] + _haversine_meters(coordinates[index - 1], coordinates[index]))
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


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def _smoothstep(value: float) -> float:
    t = _clamp(value, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _ease_out_quad(value: float) -> float:
    t = _clamp(value, 0.0, 1.0)
    return 1 - (1 - t) * (1 - t)


def _timeline(duration_in_frames: int, fps: int) -> dict[str, int]:
    camera = layout()["camera"]
    opening = round(camera["openingSeconds"] * fps)
    ending = round(camera["endingSeconds"] * fps)
    drive = max(1, duration_in_frames - opening - ending)
    transition = min(round(camera["openingTransitionSeconds"] * fps), drive)
    hold = min(round(camera["endingHoldSeconds"] * fps), max(0, ending - 1))
    return {
        "opening_frames": opening,
        "transition_frames": transition,
        "drive_frames": drive,
        "ending_frames": ending,
        "ending_hold_frames": hold,
        "pullout_frames": max(1, ending - hold),
        "ending_start": duration_in_frames - ending,
    }


def _full_scale(geom: dict[str, Any], width: int, height: int) -> float:
    content = content_rect(width, height)
    span_x = max(geom["bounds"][2] - geom["bounds"][0], 1e-6)
    span_y = max(geom["bounds"][3] - geom["bounds"][1], 1e-6)
    return min((content["inner_right"] - content["inner_left"]) / span_x,
               (content["inner_bottom"] - content["inner_top"]) / span_y)


def _point_at_distance(geom: dict[str, Any], distance: float) -> tuple[float, float, int]:
    d = _clamp(distance, 0.0, geom["length_meters"])
    low, high = 0, len(geom["cumulative"]) - 1
    while low + 1 < high:
        mid = (low + high) // 2
        if geom["cumulative"][mid] <= d:
            low = mid
        else:
            high = mid
    start = geom["projected"][low]
    end = geom["projected"][low + 1]
    span = geom["cumulative"][low + 1] - geom["cumulative"][low]
    t = _clamp((d - geom["cumulative"][low]) / span, 0.0, 1.0) if span > 0 else 0.0
    return start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t, low


def distance_for_frame(geom: dict[str, Any], frame: int, duration_in_frames: int, fps: int) -> float:
    spans = _timeline(duration_in_frames, fps)
    if frame < spans["opening_frames"]:
        return 0.0
    if frame >= spans["ending_start"]:
        return geom["length_meters"]
    progress = _smoothstep((frame - spans["opening_frames"] + 1) / spans["drive_frames"])
    return geom["length_meters"] * progress


def _smoothed_point(geom: dict[str, Any], distance: float, frame_step_meters: float,
                    half_frames: int) -> tuple[float, float]:
    """对目标点前后等距折线点做对称平均，压住折线拐点造成的高频抖动。"""
    sx = sy = 0.0
    count = 2 * half_frames + 1
    for offset in range(-half_frames, half_frames + 1):
        point = _point_at_distance(geom, distance + offset * frame_step_meters)
        sx += point[0]
        sy += point[1]
    return sx / count, sy / count


def _follow_camera(geom: dict[str, Any], distance: float, width: int, height: int,
                   frame_step_meters: float, half_frames: int) -> dict[str, float]:
    camera = layout()["camera"]
    content = content_rect(width, height)
    full = _full_scale(geom, width, height)
    follow_scale = full * camera["followZoom"]
    meters_per_projected = (geom["length_meters"] / geom["projected_length"]
                            if geom["projected_length"] > 0 else 1.0)
    visible_meters = (min(width, height) / follow_scale) * meters_per_projected
    lookahead = min(geom["length_meters"] * camera["lookaheadRouteFraction"],
                    visible_meters * camera["lookaheadViewFraction"])
    target_distance = min(distance + lookahead * camera["lookaheadTargetFraction"],
                          geom["length_meters"])
    target = _smoothed_point(geom, target_distance, frame_step_meters, half_frames)
    return {
        "scale": follow_scale,
        "tx": content["cx"] - target[0] * follow_scale,
        "ty": content["cy"] - target[1] * follow_scale,
    }


def _opening_camera(geom: dict[str, Any], amount: float, width: int, height: int) -> dict[str, float]:
    camera = layout()["camera"]
    content = content_rect(width, height)
    full = _full_scale(geom, width, height)
    start_scale = full * camera["openingStartZoom"]
    end_scale = full * camera["openingEndZoom"]
    scale = start_scale + (end_scale - start_scale) * _ease_out_quad(amount)
    start = geom["projected"][0]
    return {"scale": scale, "tx": content["cx"] - start[0] * scale,
            "ty": content["cy"] - start[1] * scale}


def _mix_camera(first: dict[str, float], second: dict[str, float], amount: float) -> dict[str, float]:
    t = _smoothstep(amount)
    return {"scale": first["scale"] + (second["scale"] - first["scale"]) * t,
            "tx": first["tx"] + (second["tx"] - first["tx"]) * t,
            "ty": first["ty"] + (second["ty"] - first["ty"]) * t}


def camera_for_frame(geom: dict[str, Any], frame: int, duration_in_frames: int,
                     fps: int, width: int, height: int) -> dict[str, float]:
    """与前端 cameraForFrame 同口径；结尾拉远只用于画面，不参与走廊取图。"""
    spans = _timeline(duration_in_frames, fps)
    content = content_rect(width, height)
    full = _full_scale(geom, width, height)
    full_camera = {
        "scale": full,
        "tx": content["cx"] - (geom["bounds"][0] + geom["bounds"][2]) / 2 * full,
        "ty": content["cy"] - (geom["bounds"][1] + geom["bounds"][3]) / 2 * full,
    }
    frame_step_meters = geom["length_meters"] / spans["drive_frames"]
    half_frames = int(layout()["camera"]["cameraSmoothingSeconds"] * fps + 0.5)
    distance = distance_for_frame(geom, frame, duration_in_frames, fps)
    if frame < spans["opening_frames"]:
        amount = 1.0 if spans["opening_frames"] <= 1 else frame / (spans["opening_frames"] - 1)
        return _opening_camera(geom, amount, width, height)
    if frame < spans["opening_frames"] + spans["transition_frames"]:
        amount = (1.0 if spans["transition_frames"] <= 0
                  else (frame - spans["opening_frames"] + 1) / spans["transition_frames"])
        return _mix_camera(_opening_camera(geom, 1.0, width, height),
                           _follow_camera(geom, distance, width, height,
                                          frame_step_meters, half_frames), amount)
    if frame < spans["ending_start"]:
        return _follow_camera(geom, distance, width, height, frame_step_meters, half_frames)
    if frame < spans["ending_start"] + spans["pullout_frames"]:
        return _mix_camera(_follow_camera(geom, geom["length_meters"], width, height,
                                          frame_step_meters, half_frames), full_camera,
                           (frame - spans["ending_start"] + 1) / spans["pullout_frames"])
    return full_camera


def zoom_for_scale(scale: float, minimum: int = 1) -> int:
    """按屏幕像素/投影米的清晰度目标选 zoom；不负责降级。"""
    if scale <= 0:
        return minimum
    target = 0 if scale * geometry.WORLD / TILE_SIZE <= 1 else int(
        math.ceil(math.log2(scale * geometry.WORLD / TILE_SIZE)))
    return max(minimum, min(18, target))


def tile_projected_rect(x: int, y: int, z: int) -> dict[str, float]:
    n = 1 << z
    size = geometry.WORLD / n
    return {
        "left": x / n * geometry.WORLD - math.pi * geometry.MERCATOR_RADIUS,
        "top": y / n * geometry.WORLD - math.pi * geometry.MERCATOR_RADIUS,
        "width": size,
        "height": size,
    }


def view_tile_keys(camera: dict[str, float], width: int, height: int, z: int,
                   margin: int = 2) -> set[tuple[int, int]]:
    """相机全屏视口覆盖的瓦片键；与前端 selectVisibleTiles 使用同一反算。"""
    n = 1 << z
    left = (0 - margin - camera["tx"]) / camera["scale"]
    top = (0 - margin - camera["ty"]) / camera["scale"]
    right = (width + margin - camera["tx"]) / camera["scale"]
    bottom = (height + margin - camera["ty"]) / camera["scale"]

    def px(value: float) -> float:
        return (value + math.pi * geometry.MERCATOR_RADIUS) / geometry.WORLD * n

    x0 = max(0, math.floor(px(left)))
    x1 = min(n - 1, math.floor(px(right) - 1e-9))
    y0 = max(0, math.floor(px(top)))
    y1 = min(n - 1, math.floor(px(bottom) - 1e-9))
    return {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}


def _tile_bbox(keys: set[tuple[int, int]], z: int) -> list[float]:
    n = 1 << z
    x0 = min(key[0] for key in keys)
    x1 = max(key[0] for key in keys)
    y0 = min(key[1] for key in keys)
    y1 = max(key[1] for key in keys)
    min_lng = x0 / n * 360.0 - 180.0
    max_lng = (x1 + 1) / n * 360.0 - 180.0
    max_lat = geometry.unproject(
        0, -(y0 / n * geometry.WORLD - math.pi * geometry.MERCATOR_RADIUS))[1]
    min_lat = geometry.unproject(
        0, -((y1 + 1) / n * geometry.WORLD - math.pi * geometry.MERCATOR_RADIUS))[1]
    return [round(min_lng, 6), round(min_lat, 6), round(max_lng, 6), round(max_lat, 6)]


def _plan_digest(keys: set[tuple[int, int]], zoom: int, duration_seconds: int, fps: int,
                 width: int, height: int, tile_style: int = TILE_STYLE) -> str:
    canonical = {
        "layoutVersion": layout_version(), "width": width, "height": height,
        "fps": fps, "durationSeconds": duration_seconds, "zoom": zoom,
        "tileSize": TILE_SIZE, "style": tile_style, "lang": TILE_LANG,
        "tiles": [[x, y] for x, y in sorted(keys)],
    }
    encoded = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                         allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def corridor_plan(route: dict[str, Any], duration_seconds: int, fps: int, zoom: int,
                  *, width: int = 1080, height: int = 1920,
                  max_tiles: int = MAX_CORRIDOR_TILES,
                  tile_style: int = TILE_STYLE) -> dict[str, Any]:
    """生成跟随段瓦片走廊：真实相机路径并集 + 逐帧复核。"""
    geom = route_geometry(route)
    total_frames = duration_seconds * fps
    spans = _timeline(total_frames, fps)
    frame_step_meters = geom["length_meters"] / spans["drive_frames"]
    half_frames = int(layout()["camera"]["cameraSmoothingSeconds"] * fps + 0.5)
    keys = view_tile_keys(_opening_camera(geom, 0.0, width, height), width, height, zoom, 2)
    distance = 0.0
    while distance < geom["length_meters"]:
        keys |= view_tile_keys(_follow_camera(geom, distance, width, height,
                                              frame_step_meters, half_frames),
                               width, height, zoom, 2)
        distance += SAMPLE_STEP_METERS
    keys |= view_tile_keys(_follow_camera(geom, geom["length_meters"], width, height,
                                          frame_step_meters, half_frames),
                           width, height, zoom, 2)
    # 采样只保证路径连续；逐帧再算一次，缺块直接补入，而不是留到渲染时空白。
    for frame in range(0, spans["ending_start"] + 1):
        keys |= view_tile_keys(camera_for_frame(geom, frame, total_frames, fps, width, height),
                               width, height, zoom, 2)
    if len(keys) > max_tiles:
        raise M2VError(
            f"跟随瓦片走廊需要 {len(keys)} 块，超过上限 {max_tiles}；"
            "请降低跟随倍率，不得静默降低缩放级别")
    ordered = sorted(keys, key=lambda key: (key[1], key[0]))
    tiles = [{"x": x, "y": y, "z": zoom, "projected": tile_projected_rect(x, y, zoom)}
             for x, y in ordered]
    return {
        "zoom": zoom,
        "tileSize": TILE_SIZE,
        "tileCount": len(tiles),
        "planDigest": _plan_digest(keys, zoom, duration_seconds, fps, width, height, tile_style),
        "bbox": _tile_bbox(keys, zoom),
        "request": {"path": "/appmaptile",
                    "params": {"style": str(tile_style), "lang": TILE_LANG, "zoom": str(zoom)}},
        "tiles": tiles,
    }


def manifest_digest(plan_digest: str, tiles: list[dict[str, Any]]) -> str:
    canonical = {
        "planDigest": plan_digest,
        "tiles": [[tile["x"], tile["y"], tile["sha256"]] for tile in tiles],
    }
    encoded = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                         allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def missing_corridor_tiles(route: dict[str, Any], duration_seconds: int, fps: int, zoom: int,
                           stored: set[tuple[int, int]],
                           tile_style: int = TILE_STYLE) -> set[tuple[int, int]]:
    plan = corridor_plan(route, duration_seconds, fps, zoom, tile_style=tile_style)
    planned = {(tile["x"], tile["y"]) for tile in plan["tiles"]}
    return planned - stored
