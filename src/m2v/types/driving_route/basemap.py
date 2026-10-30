"""高德普通道路瓦片采集、拼接与离线底图记录。

底图与路线同为 GCJ-02 Web Mercator；本模块只负责取图、拼接、计算投影矩形与
原子写入，画面只读取本地影像。瓦片请求不带任何凭据，来源参数写入材料时也
不记录 Key。
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from m2v.core.errors import M2VError
from m2v.core.project import load_project as load_manifest
from m2v.types.driving_route import geometry, layout as layout_module, materials

TILE_SIZE = 256
TILE_STYLE = 8
MAX_ZOOM = 18
MAX_TILES = 900
MAX_WIDTH = 10240
MAX_HEIGHT = 8192
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


def tile_url(x: int, y: int, z: int, subdomain: int = 1) -> str:
    return (f"https://webrd0{subdomain}.is.autonavi.com/appmaptile"
            f"?lang=zh_cn&size=1&scale=1&style={TILE_STYLE}&x={x}&y={y}&z={z}")


def zoom_for_scale(scale: float, minimum: int = 1) -> int:
    """按屏幕像素/投影米的清晰度目标选 zoom，再受上限约束。"""
    if scale <= 0:
        return minimum
    target = 0 if scale * geometry.WORLD / TILE_SIZE <= 1 else int(
        math.ceil(math.log2(scale * geometry.WORLD / TILE_SIZE)))
    return max(minimum, min(MAX_ZOOM, target))


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


def _fetch_tiles(z: int, x0: int, y0: int, x1: int, y1: int,
                 transport: TileTransport, *, timeout: float,
                 delay: float) -> dict[tuple[int, int], bytes]:
    tiles: dict[tuple[int, int], bytes] = {}
    index = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            url = tile_url(x, y, z, index % 4 + 1)
            index += 1
            try:
                status, body = transport(url, timeout)
            except Exception as exc:  # noqa: BLE001 - 传输失败只报类型，不回显 URL
                raise M2VError(f"高德道路瓦片请求失败（{type(exc).__name__}）；请检查网络后重试") from None
            if status != 200:
                raise M2VError(f"高德道路瓦片返回 HTTP {status}（z={z}, x={x}, y={y}）")
            if not body.startswith(b"\x89PNG\r\n\x1a\n"):
                raise M2VError(f"高德道路瓦片不是 PNG（z={z}, x={x}, y={y}）")
            tiles[(x, y)] = body
            if delay > 0:
                time.sleep(delay)
    return tiles


def stitch_tiles(tiles: dict[tuple[int, int], bytes], bbox: tuple[float, float, float, float],
                 z: int, x0: int, y0: int, x1: int, y1: int) -> tuple[Image.Image, dict[str, float]]:
    canvas = Image.new("RGB", ((x1 - x0 + 1) * TILE_SIZE, (y1 - y0 + 1) * TILE_SIZE), "white")
    for (x, y), body in tiles.items():
        try:
            with Image.open(io.BytesIO(body)) as tile:
                rgba = tile.convert("RGBA")
                if rgba.size != (TILE_SIZE, TILE_SIZE):
                    raise M2VError(f"高德道路瓦片尺寸不是 {TILE_SIZE}×{TILE_SIZE}（z={z}, x={x}, y={y}）")
                background = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (255, 255, 255, 255))
                background.alpha_composite(rgba)
                canvas.paste(background.convert("RGB"), ((x - x0) * TILE_SIZE, (y - y0) * TILE_SIZE))
        except M2VError:
            raise
        except Exception as exc:  # noqa: BLE001 - 解码失败按瓦片错误处理
            raise M2VError(f"高德道路瓦片无法解码（z={z}, x={x}, y={y}）：{exc}") from None
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
                  transport: TileTransport, *, timeout: float, delay: float
                  ) -> tuple[dict[str, Any], Path, bool]:
    zoom, x0, y0, x1, y1, bbox = plan
    tiles = _fetch_tiles(zoom, x0, y0, x1, y1, transport, timeout=timeout, delay=delay)
    image, projected = stitch_tiles(tiles, bbox, zoom, x0, y0, x1, y1)
    directory = root / "assets" / "basemap"
    directory.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90, optimize=True)
    content = buffer.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    target = directory / f"roadmap-{name}-z{zoom}-{digest[:8]}.jpg"
    created = not target.exists()
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
                    "params": {"style": str(TILE_STYLE), "lang": "zh_cn", "zoom": str(zoom)}},
    }
    return layer, target, created


def _image_references(route: dict[str, Any]) -> set[Path]:
    references: set[Path] = set()
    basemap = route.get("basemap")
    if isinstance(basemap, dict):
        for name in ("overview", "follow"):
            layer = basemap.get(name)
            if isinstance(layer, dict) and isinstance(layer.get("image"), dict):
                path = layer["image"].get("path")
                if isinstance(path, str):
                    references.add(Path(path))
    return references


def fetch_basemap(project_dir: str | Path, *, transport: TileTransport | None = None,
                  now: datetime | None = None, refresh: bool = False,
                  delay: float = DEFAULT_DELAY_SECONDS,
                  timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """取两级普通道路影像并原子更新 route.json；失败保留旧材料与旧影像。"""
    root = Path(project_dir).expanduser().resolve()
    _, project = load_manifest(root)
    if project["type"] != "driving-route" or project.get("materials") != materials.MATERIALS:
        raise M2VError("m2v driving-route basemap 仅适用于 driving-route 作品")
    request = materials.load_request(root)
    if request["sourceUsage"].get("mapTiles") is not True:
        raise M2VError("道路底图使用未获授权：请在 request.json.sourceUsage.mapTiles 置 true 后重试")
    route_path = root / materials.MATERIALS["route"]
    route_snapshot = route_path.read_bytes()
    route = materials._load(route_path)
    route_without_basemap = {key: value for key, value in route.items() if key != "basemap"}
    materials.validate_route_document(request, route_without_basemap)

    route_box = geometry.route_projected_bbox(route)
    projected_length = geometry.projected_length(route)
    envelope = layout_module.camera_envelope(route_box, projected_length,
                                              route["route"]["distanceMeters"])
    overview_plan = layer_plan(route_box, half_x=envelope["overview_half_x"],
                               half_y=envelope["overview_half_y"],
                               scale=envelope["full_scale"], minimum_zoom=8)
    follow_plan = layer_plan(route_box, half_x=envelope["follow_half_x"],
                             half_y=envelope["follow_half_y"],
                             scale=envelope["follow_scale"], minimum_zoom=9)

    version = layout_module.layout_version()
    existing = route.get("basemap")
    if existing and not refresh and existing.get("layoutVersion") == version:
        same = existing["overview"]["zoom"] == overview_plan[0] \
            and existing["follow"]["zoom"] == follow_plan[0] \
            and existing["overview"]["bbox"] == [round(v, 6) for v in overview_plan[5]] \
            and existing["follow"]["bbox"] == [round(v, 6) for v in follow_plan[5]]
        if same:
            images_ok = True
            for name in ("overview", "follow"):
                image = root / existing[name]["image"]["path"]
                images_ok = images_ok and image.is_file() and \
                    hashlib.sha256(image.read_bytes()).hexdigest() == existing[name]["image"]["sha256"]
            if images_ok:
                return {"path": route_path, "reused": True,
                        "zoom": (existing["overview"]["zoom"], existing["follow"]["zoom"]),
                        "tileCount": existing["overview"]["tileCount"] + existing["follow"]["tileCount"]}

    timestamp = now or datetime.now().astimezone()
    if timestamp.tzinfo is None:
        timestamp = timestamp.astimezone()
    client = transport or default_transport
    old_images = {root / path for path in _image_references(route)}
    created: list[Path] = []
    wrote_route = False
    try:
        overview_layer, overview_image, overview_created = _render_layer(
            root, "overview", overview_plan, client, timeout=timeout, delay=delay)
        if overview_created:
            created.append(overview_image)
        follow_layer, follow_image, follow_created = _render_layer(
            root, "follow", follow_plan, client, timeout=timeout, delay=delay)
        if follow_created:
            created.append(follow_image)
        route["basemap"] = {
            "layoutVersion": version,
            "provider": "amap",
            "service": "road-tiles",
            "attribution": request["sourceUsage"]["attribution"],
            "fetchedAt": timestamp.isoformat(timespec="seconds"),
            "overview": overview_layer,
            "follow": follow_layer,
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

    directory = root / "assets" / "basemap"
    for old in directory.glob("roadmap-*.jpg"):
        if old not in {overview_image, follow_image}:
            old.unlink(missing_ok=True)
    return {"path": route_path, "reused": False,
            "zoom": (overview_layer["zoom"], follow_layer["zoom"]),
            "tileCount": overview_layer["tileCount"] + follow_layer["tileCount"],
            "images": [layer["image"]["path"] for layer in (overview_layer, follow_layer)]}
