"""高德普通道路瓦片采集、概览拼接与跟随走廊的离线底图记录。

底图与路线同为 GCJ-02 Web Mercator；本模块只负责取图、拼接、计算投影矩形与
原子写入，画面只读取本地影像。跟随段使用 z11 瓦片走廊，而不是整条路线拼接，
避免 10× 跟随视口被放大后发软。瓦片请求不带任何凭据，来源参数写入材料时也
不记录 Key。
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import shutil
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from m2v.core.errors import M2VError
from m2v.core.project import load_project as load_manifest
from m2v.types.driving_route import geometry, layout as layout_module, materials

TILE_SIZE = 256
ROAD_STYLE = 8
SATELLITE_STYLE = 6
TILE_STYLE = ROAD_STYLE
STYLE_SERVICES = {ROAD_STYLE: "road-tiles", SATELLITE_STYLE: "satellite-tiles"}
MAX_ZOOM = 18
MAX_TILES = 900
MAX_WIDTH = 10240
MAX_HEIGHT = 8192
MAX_CORRIDOR_TILES = layout_module.MAX_CORRIDOR_TILES
RETRIES = 3
DEFAULT_DELAY_SECONDS = 0.03
DEFAULT_TIMEOUT_SECONDS = 30.0

TileTransport = Callable[[str, float], tuple[int, bytes]]


def default_transport(url: str, timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "material2video/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def tile_url(x: int, y: int, z: int, subdomain: int = 1, style: int = TILE_STYLE) -> str:
    host = "webst" if style == SATELLITE_STYLE else "webrd"
    return (f"https://{host}0{subdomain}.is.autonavi.com/appmaptile"
            f"?lang=zh_cn&size=1&scale=1&style={style}&x={x}&y={y}&z={z}")


def zoom_for_scale(scale: float, minimum: int = 1) -> int:
    """按屏幕像素/投影米的清晰度目标选 zoom，再受上限约束。"""
    return layout_module.zoom_for_scale(scale, minimum)


def projected_rect(bbox: tuple[float, float, float, float], z: int,
                   crop: tuple[int, int, int, int],
                   tile_origin: tuple[int, int]) -> dict[str, float]:
    x0, y0 = tile_origin
    left, top, right, bottom = crop
    n = 1 << z
    px_left = x0 + left / TILE_SIZE
    px_top = y0 + top / TILE_SIZE
    px_right = x0 + right / TILE_SIZE
    px_bottom = y0 + bottom / TILE_SIZE
    return {
        "left": px_left / n * geometry.WORLD - math.pi * geometry.MERCATOR_RADIUS,
        "top": px_top / n * geometry.WORLD - math.pi * geometry.MERCATOR_RADIUS,
        "width": (px_right - px_left) / n * geometry.WORLD,
        "height": (px_bottom - px_top) / n * geometry.WORLD,
    }


def layer_plan(route_box: tuple[float, float, float, float], *, half_x: float, half_y: float,
               scale: float, minimum_zoom: int) -> tuple[int, int, int, int, int,
                                                         tuple[float, float, float, float]]:
    bbox_projected = (route_box[0] - half_x, route_box[1] - half_y,
                      route_box[2] + half_x, route_box[3] + half_y)
    bbox = (geometry.unproject(bbox_projected[0], bbox_projected[1])[0],
            geometry.unproject(bbox_projected[0], bbox_projected[1])[1],
            geometry.unproject(bbox_projected[2], bbox_projected[3])[0],
            geometry.unproject(bbox_projected[2], bbox_projected[3])[1])
    zoom = zoom_for_scale(scale, minimum_zoom)
    while zoom > 1:
        x0, y0, x1, y1 = geometry.tile_range(bbox, zoom)
        columns, rows = x1 - x0 + 1, y1 - y0 + 1
        if (columns * rows <= MAX_TILES and columns * TILE_SIZE <= MAX_WIDTH
                and rows * TILE_SIZE <= MAX_HEIGHT):
            return zoom, x0, y0, x1, y1, bbox
        zoom -= 1
    raise M2VError("路线包围盒过大，无法在限制内拼接道路底图")


def _fetch_tile(z: int, x: int, y: int, subdomain: int, transport: TileTransport, *,
                timeout: float, style: int = TILE_STYLE) -> bytes:
    last_message = f"高德道路瓦片请求失败（z={z}, x={x}, y={y}）"
    for attempt in range(RETRIES):
        url = tile_url(x, y, z, subdomain, style)
        try:
            status, body = transport(url, timeout)
        except Exception as exc:  # noqa: BLE001 - 传输失败只报类型，不回显 URL
            last_message = f"高德道路瓦片请求失败（{type(exc).__name__}；z={z}, x={x}, y={y}）"
            status, body = None, b""
        if status == 200:
            if not (body.startswith(b"\x89PNG\r\n\x1a\n") or body.startswith(b"\xff\xd8")):
                raise M2VError(f"高德瓦片不是 PNG/JPEG（z={z}, x={x}, y={y}）")
            return body
        if status is not None:
            last_message = f"高德道路瓦片返回 HTTP {status}（z={z}, x={x}, y={y}）"
        if attempt + 1 < RETRIES:
            time.sleep(0.15 * (attempt + 1))
    raise M2VError(last_message)


def _fetch_tiles(z: int, x0: int, y0: int, x1: int, y1: int,
                 transport: TileTransport, *, timeout: float,
                 delay: float, style: int = TILE_STYLE) -> dict[tuple[int, int], bytes]:
    tiles: dict[tuple[int, int], bytes] = {}
    index = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            tiles[(x, y)] = _fetch_tile(z, x, y, index % 4 + 1, transport,
                                        timeout=timeout, style=style)
            index += 1
            if delay > 0:
                time.sleep(delay)
    return tiles


def _decode_tile(body: bytes, z: int, x: int, y: int) -> Image.Image:
    try:
        with Image.open(io.BytesIO(body)) as tile:
            rgba = tile.convert("RGBA")
            if rgba.size != (TILE_SIZE, TILE_SIZE):
                raise M2VError(f"高德道路瓦片尺寸不是 {TILE_SIZE}×{TILE_SIZE}（z={z}, x={x}, y={y}）")
            background = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (255, 255, 255, 255))
            background.alpha_composite(rgba)
            return background.convert("RGB")
    except M2VError:
        raise
    except Exception as exc:  # noqa: BLE001 - 解码失败按瓦片错误处理
        raise M2VError(f"高德道路瓦片无法解码（z={z}, x={x}, y={y}）：{exc}") from None


def stitch_tiles(tiles: dict[tuple[int, int], bytes], bbox: tuple[float, float, float, float],
                 z: int, x0: int, y0: int, x1: int, y1: int) -> tuple[Image.Image, dict[str, float]]:
    canvas = Image.new("RGB", ((x1 - x0 + 1) * TILE_SIZE, (y1 - y0 + 1) * TILE_SIZE), "white")
    for (x, y), body in tiles.items():
        canvas.paste(_decode_tile(body, z, x, y), ((x - x0) * TILE_SIZE, (y - y0) * TILE_SIZE))
    min_lng, min_lat, max_lng, max_lat = bbox
    left = round((geometry.tile_x(min_lng, z) - x0) * TILE_SIZE)
    top = round((geometry.tile_y(max_lat, z) - y0) * TILE_SIZE)
    right = round((geometry.tile_x(max_lng, z) - x0) * TILE_SIZE)
    bottom = round((geometry.tile_y(min_lat, z) - y0) * TILE_SIZE)
    width, height = canvas.size
    left, top = max(0, left), max(0, top)
    right, bottom = min(width, right), min(height, bottom)
    if right - left < 2 or bottom - top < 2:
        raise M2VError("道路底图裁剪范围无效")
    crop = (left, top, right, bottom)
    return canvas.crop(crop), projected_rect(bbox, z, crop, (x0, y0))


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _render_layer(root: Path, name: str, plan: tuple[int, int, int, int, int,
                                                   tuple[float, float, float, float]],
                  transport: TileTransport, *, timeout: float, delay: float,
                  style: int = TILE_STYLE) -> tuple[dict[str, Any], Path, bool]:
    zoom, x0, y0, x1, y1, bbox = plan
    tiles = _fetch_tiles(zoom, x0, y0, x1, y1, transport, timeout=timeout, delay=delay,
                         style=style)
    image, projected = stitch_tiles(tiles, bbox, zoom, x0, y0, x1, y1)
    directory = root / "assets" / "basemap"
    directory.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90, optimize=True)
    content = buffer.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    target = directory / f"roadmap-{name}-z{zoom}-{digest[:8]}.jpg"
    created = True
    if target.exists():
        created = hashlib.sha256(target.read_bytes()).hexdigest() != digest
    if created:
        temporary = directory / f".{target.name}.tmp"
        try:
            temporary.write_bytes(content)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    layer = {
        "zoom": zoom,
        "bbox": [round(value, 6) for value in bbox],
        "image": {"path": target.relative_to(root).as_posix(), "sha256": digest,
                  "width": image.width, "height": image.height},
        "projected": {key: round(value, 3) for key, value in projected.items()},
        "tileCount": len(tiles),
        "request": {"path": "/appmaptile",
                    "params": {"style": str(style), "lang": "zh_cn", "zoom": str(zoom)}},
    }
    return layer, target, created


def _directory_tiles_valid(final: Path, records: list[dict[str, Any]], zoom: int) -> bool:
    for record in records:
        file = final / f"z{zoom}" / str(record["x"]) / f"{record['y']}.jpg"
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != record["sha256"]:
            return False
    return True


def _fetch_corridor(root: Path, plan: dict[str, Any], transport: TileTransport, *,
                    timeout: float, delay: float,
                    now: datetime, style: int = TILE_STYLE) -> tuple[dict[str, Any], Path]:
    directory = root / "assets" / "basemap"
    directory.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".follow-tiles-tmp-", dir=directory))
    records: list[dict[str, Any]] = []
    try:
        for index, tile in enumerate(plan["tiles"]):
            x, y, z = tile["x"], tile["y"], tile["z"]
            body = _fetch_tile(z, x, y, index % 4 + 1, transport, timeout=timeout, style=style)
            image = _decode_tile(body, z, x, y)
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=90, optimize=True)
            content = buffer.getvalue()
            target = temporary / f"z{z}" / str(x) / f"{y}.jpg"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            records.append({
                "x": x, "y": y, "z": z, "sha256": hashlib.sha256(content).hexdigest(),
                "width": TILE_SIZE, "height": TILE_SIZE, "projected": tile["projected"],
            })
            if delay > 0:
                time.sleep(delay)
        manifest = layout_module.manifest_digest(plan["planDigest"], records)
        manifest_data = {
            "planDigest": plan["planDigest"],
            "manifestDigest": manifest,
            "zoom": plan["zoom"],
            "tileSize": plan["tileSize"],
            "request": plan["request"],
            "created": now.isoformat(timespec="seconds"),
            "tiles": [{"x": tile["x"], "y": tile["y"], "sha256": tile["sha256"]}
                      for tile in records],
        }
        (temporary / "manifest.json").write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        final = directory / f"follow-tiles-{manifest[:16]}"
        if final.exists() and _directory_tiles_valid(final, records, plan["zoom"]):
            shutil.rmtree(temporary, ignore_errors=True)
        else:
            if final.exists():
                # 同名内容目录已损坏：使用新后缀安装，绝不移动旧 route 正在引用的目录。
                final = directory / f"follow-tiles-{manifest[:16]}-{uuid.uuid4().hex[:8]}"
            temporary.rename(final)
        tiles = [{**record, "path": (final / f"z{plan['zoom']}" / str(record["x"]) /
                                     f"{record['y']}.jpg").relative_to(root).as_posix()}
                 for record in records]
        layer = {
            "zoom": plan["zoom"],
            "tileSize": plan["tileSize"],
            "tileCount": len(tiles),
            "planDigest": plan["planDigest"],
            "manifestDigest": manifest,
            "bbox": plan["bbox"],
            "request": plan["request"],
            "tiles": tiles,
        }
        return layer, final
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _image_references(route: dict[str, Any]) -> set[Path]:
    references: set[Path] = set()
    basemap = route.get("basemap")
    if not isinstance(basemap, dict):
        return references
    overview = basemap.get("overview")
    if isinstance(overview, dict) and isinstance(overview.get("image"), dict):
        path = overview["image"].get("path")
        if isinstance(path, str):
            references.add(Path(path))
    follow = basemap.get("followTiles")
    if isinstance(follow, dict) and isinstance(follow.get("tiles"), list):
        for tile in follow["tiles"]:
            path = tile.get("path") if isinstance(tile, dict) else None
            if isinstance(path, str):
                references.add(Path(path))
    return references


def _directory_references(route: dict[str, Any]) -> set[Path]:
    directories: set[Path] = set()
    for path in _image_references(route):
        for parent in path.parents:
            if parent.name.startswith(("follow-tiles-", "follow-z11-")):
                directories.add(parent)
                break
    return directories


def _overview_reusable(root: Path, existing: dict[str, Any], plan: tuple[Any, ...],
                       style: int) -> bool:
    overview = existing.get("overview")
    if not isinstance(overview, dict) or overview.get("zoom") != plan[0]:
        return False
    request = overview.get("request")
    if not isinstance(request, dict) or request.get("params", {}).get("style") != str(style):
        return False
    if overview.get("bbox") != [round(value, 6) for value in plan[5]]:
        return False
    image = overview.get("image")
    if not isinstance(image, dict) or not isinstance(image.get("path"), str):
        return False
    file = root / image["path"]
    return (file.is_file()
            and hashlib.sha256(file.read_bytes()).hexdigest() == image.get("sha256"))


def _follow_reusable(root: Path, existing: dict[str, Any], plan: dict[str, Any]) -> bool:
    follow = existing.get("followTiles")
    if not isinstance(follow, dict):
        return False
    if (follow.get("zoom") != plan["zoom"] or follow.get("tileSize") != plan["tileSize"]
            or follow.get("planDigest") != plan["planDigest"]
            or follow.get("tileCount") != plan["tileCount"]):
        return False
    if follow.get("bbox") != plan["bbox"]:
        return False
    stored = follow.get("tiles")
    if not isinstance(stored, list) or len(stored) != plan["tileCount"]:
        return False
    planned = {(tile["x"], tile["y"]) for tile in plan["tiles"]}
    if {(tile.get("x"), tile.get("y")) for tile in stored if isinstance(tile, dict)} != planned:
        return False
    records = []
    for tile in stored:
        path = tile.get("path") if isinstance(tile, dict) else None
        digest = tile.get("sha256") if isinstance(tile, dict) else None
        if not isinstance(path, str) or not isinstance(digest, str):
            return False
        file = root / path
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            return False
        records.append({"x": tile["x"], "y": tile["y"], "sha256": digest})
    return layout_module.manifest_digest(plan["planDigest"], records) == follow.get("manifestDigest")


def _cleanup_assets(root: Path, route: dict[str, Any]) -> None:
    directory = root / "assets" / "basemap"
    if not directory.is_dir():
        return
    keep_images = {root / path for path in _image_references(route)}
    for old in directory.glob("roadmap-*.jpg"):
        if old not in keep_images:
            old.unlink(missing_ok=True)
    keep_directories = {root / path for path in _directory_references(route)}
    for pattern in ("follow-tiles-*", "follow-z11-*"):
        for old in directory.glob(pattern):
            if old not in keep_directories:
                shutil.rmtree(old, ignore_errors=True)
    for pattern in (".follow-tiles-tmp-*", ".follow-tiles-old-*",
                    ".follow-z11-tmp-*", ".follow-z11-old-*"):
        for temporary in directory.glob(pattern):
            shutil.rmtree(temporary, ignore_errors=True)


def fetch_basemap(project_dir: str | Path, *, transport: TileTransport | None = None,
                  now: datetime | None = None, refresh: bool = False,
                  delay: float = DEFAULT_DELAY_SECONDS,
                  timeout: float = DEFAULT_TIMEOUT_SECONDS,
                  style: str = "road") -> dict[str, Any]:
    """取概览影像与跟随瓦片走廊并原子更新 route.json；失败保留旧材料与旧影像。"""
    if style not in {"road", "satellite"}:
        raise M2VError("底图样式必须为 road 或 satellite")
    tile_style = SATELLITE_STYLE if style == "satellite" else ROAD_STYLE
    service = STYLE_SERVICES[tile_style]
    root = Path(project_dir).expanduser().resolve()
    _, project = load_manifest(root)
    if project["type"] != "driving-route" or project.get("materials") != materials.MATERIALS:
        raise M2VError("m2v driving-route basemap 仅适用于 driving-route 作品")
    request = materials.load_request(root)
    if request["sourceUsage"].get("mapTiles") is not True:
        raise M2VError("道路底图使用未获授权：请在 request.json.sourceUsage.mapTiles 置 true 后重试")
    route_path = root / materials.MATERIALS["route"]
    route_snapshot = route_path.read_bytes()
    route = materials._load(route_path, 3)
    route_without_basemap = {key: value for key, value in route.items() if key != "basemap"}
    materials.validate_route_document(request, route_without_basemap)

    route_box = geometry.route_projected_bbox(route)
    projected_length = geometry.projected_length(route)
    envelope = layout_module.camera_envelope(route_box, projected_length,
                                              geometry.visual_distance_meters(route))
    overview_plan = layer_plan(route_box, half_x=envelope["overview_half_x"],
                               half_y=envelope["overview_half_y"],
                               scale=envelope["full_scale"], minimum_zoom=8)
    follow_zoom = layout_module.zoom_for_scale(envelope["follow_scale"], minimum=9)
    follow_plan = layout_module.corridor_plan(
        route, request["durationSeconds"], materials.FPS, follow_zoom,
        tile_style=tile_style)

    version = layout_module.layout_version()
    existing = route.get("basemap")
    if (isinstance(existing, dict) and not refresh and existing.get("layoutVersion") == version
            and existing.get("service") == service
            and _overview_reusable(root, existing, overview_plan, tile_style)
            and _follow_reusable(root, existing, follow_plan)):
        _cleanup_assets(root, route)
        return {"path": route_path, "reused": True,
                "zoom": (existing["overview"]["zoom"], existing["followTiles"]["zoom"]),
                "tileCount": existing["overview"]["tileCount"] + existing["followTiles"]["tileCount"]}

    timestamp = now or datetime.now().astimezone()
    if timestamp.tzinfo is None:
        timestamp = timestamp.astimezone()
    client = transport or default_transport
    old_images = {root / path for path in _image_references(route)}
    old_directories = {root / path for path in _directory_references(route)}
    created: list[Path] = []
    follow_directory: Path | None = None
    wrote_route = False
    try:
        overview_layer, overview_image, overview_created = _render_layer(
            root, "overview", overview_plan, client, timeout=timeout, delay=delay,
            style=tile_style)
        if overview_created:
            created.append(overview_image)
        follow_layer, follow_directory = _fetch_corridor(
            root, follow_plan, client, timeout=timeout, delay=delay, now=timestamp,
            style=tile_style)
        route["basemap"] = {
            "layoutVersion": version,
            "provider": "amap",
            "service": service,
            "attribution": request["sourceUsage"]["attribution"],
            "fetchedAt": timestamp.isoformat(timespec="seconds"),
            "overview": overview_layer,
            "followTiles": follow_layer,
        }
        if route_path.read_bytes() != route_snapshot:
            raise M2VError("取图期间 route.json 已变化；未保存底图，请重试")
        current_request = materials.load_request(root)
        if materials.request_digest(current_request) != route["requestDigest"]:
            raise M2VError("取图期间 request.json 已变化；未保存底图，请重新执行 fetch")
        _write_json_atomic(route_path, route)
        wrote_route = True
    finally:
        if not wrote_route:
            for image in created:
                if image not in old_images:
                    image.unlink(missing_ok=True)
            if follow_directory is not None and follow_directory not in old_directories:
                shutil.rmtree(follow_directory, ignore_errors=True)

    _cleanup_assets(root, route)
    return {"path": route_path, "reused": False,
            "zoom": (overview_layer["zoom"], follow_layer["zoom"]),
            "tileCount": overview_layer["tileCount"] + follow_layer["tileCount"],
            "images": [overview_layer["image"]["path"], f"{follow_layer['tileCount']} 张跟随瓦片"]}
