"""`m2v road-trip basemap`：全局概览、每日概览与每日跟随走廊。

底图是离线材料：一次取图后，validate / prepare / preview / render 都不再访问
网络。走廊只依赖路线与静态布局，改旁白或时长不会重新取图。索引与每日清单
原子更新；失败保留旧底图，不发布半份材料。
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from m2v.core.errors import M2VError
from m2v.core.project import load_project as load_manifest
from m2v.types.driving_route import geometry
from m2v.types.driving_route import layout as driving_layout
from m2v.types.driving_route import basemap as driving_basemap
from m2v.types.road_trip import layout as layout_module
from m2v.types.road_trip import materials

TileTransport = Callable[[str, float], tuple[int, bytes]]

DIRECTORY = materials.BASEMAP_DIR
INDEX = materials.BASEMAP_INDEX
ROAD_STYLE = driving_basemap.ROAD_STYLE
SATELLITE_STYLE = driving_basemap.SATELLITE_STYLE
SERVICE_BY_STYLE = driving_basemap.STYLE_SERVICES
DEFAULT_DELAY_SECONDS = driving_basemap.DEFAULT_DELAY_SECONDS
DEFAULT_TIMEOUT_SECONDS = driving_basemap.DEFAULT_TIMEOUT_SECONDS


def _style_for(day: dict[str, Any], override: str | None) -> str:
    style = override or day["basemapStyle"]
    if style not in materials.BASEMAP_STYLES:
        raise M2VError("底图样式必须为 road 或 satellite")
    return style


def _tile_style(style: str) -> int:
    return SATELLITE_STYLE if style == "satellite" else ROAD_STYLE


def _layer_plan_from_bbox(bbox: list[float], scale: float, *, minimum_zoom: int,
                          pixels: int) -> tuple[int, int, int, int, int,
                                              tuple[float, float, float, float]]:
    """按经纬度 bbox 选 zoom，并保证单图拼接在上限内（复用自驾路线的限制）。"""
    zoom = driving_basemap.zoom_for_scale(scale, minimum_zoom)
    while zoom > 1:
        x0, y0, x1, y1 = geometry.tile_range(tuple(bbox), zoom)
        columns, rows = x1 - x0 + 1, y1 - y0 + 1
        if (columns * rows <= driving_basemap.MAX_TILES
                and columns * pixels <= driving_basemap.MAX_WIDTH
                and rows * pixels <= driving_basemap.MAX_HEIGHT):
            return zoom, x0, y0, x1, y1, tuple(bbox)
        zoom -= 1
    raise M2VError("概览包围盒过大，无法在限制内拼接底图")


def _render_overview(root: Path, name: str, bbox: list[float], scale: float,
                     style: str, transport: TileTransport, *, timeout: float,
                     delay: float) -> tuple[dict[str, Any], Path, bool]:
    tile_style = _tile_style(style)
    pixels = driving_basemap.tile_pixels(tile_style)
    plan = _layer_plan_from_bbox(bbox, scale, minimum_zoom=8, pixels=pixels)
    zoom, x0, y0, x1, y1, planned_bbox = plan
    tiles = driving_basemap._fetch_tiles(zoom, x0, y0, x1, y1, transport,
                                         timeout=timeout, delay=delay, style=tile_style)
    image, projected = driving_basemap.stitch_tiles(tiles, planned_bbox, zoom, x0, y0, x1, y1,
                                                    pixels=pixels)
    directory = root / DIRECTORY
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
        "bbox": [round(value, 6) for value in planned_bbox],
        "image": {"path": target.relative_to(root).as_posix(), "sha256": digest,
                  "width": image.width, "height": image.height},
        "projected": {key: round(value, 3) for key, value in projected.items()},
        "tileCount": len(tiles),
        "request": {"path": "/appmaptile",
                    "params": {"style": str(tile_style), "lang": "zh_cn", "zoom": str(zoom),
                               **({"scl": driving_basemap.tile_scl(tile_style)}
                                  if driving_basemap.tile_scl(tile_style) else {})}},
    }
    return layer, target, created


def _reuse_directory(root: Path, plan: dict[str, Any],
                     pixels: int) -> tuple[dict[str, Any], Path] | None:
    """已有内容寻址目录覆盖同一走廊计划时不重复下载瓦片。"""
    directory = root / DIRECTORY
    if not directory.is_dir():
        return None
    planned = {(tile["x"], tile["y"]): tile for tile in plan["tiles"]}
    for final in sorted(directory.glob("road-trip-follow-*")):
        manifest_path = final / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if manifest.get("planDigest") != plan["planDigest"]:
            continue
        records = manifest.get("tiles")
        if not isinstance(records, list) or len(records) != plan["tileCount"]:
            continue
        if {(record.get("x"), record.get("y")) for record in records} != set(planned):
            continue
        tiles = []
        valid = True
        for record in records:
            x, y = record["x"], record["y"]
            file = final / f"z{plan['zoom']}" / str(x) / f"{y}.jpg"
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != record["sha256"]:
                valid = False
                break
            tiles.append({"x": x, "y": y, "z": plan["zoom"], "sha256": record["sha256"],
                          "width": pixels, "height": pixels,
                          "projected": planned[(x, y)]["projected"],
                          "path": (final / f"z{plan['zoom']}" / str(x) / f"{y}.jpg")
                          .relative_to(root).as_posix()})
        if not valid:
            continue
        layer = {
            "zoom": plan["zoom"], "tileSize": plan["tileSize"],
            "tileCount": len(tiles), "planDigest": plan["planDigest"],
            "manifestDigest": manifest["manifestDigest"], "bbox": plan["bbox"],
            "request": plan["request"],
            "manifest": manifest_path.relative_to(root).as_posix(),
            "tiles": tiles,
        }
        return layer, final
    return None


def _fetch_corridor(root: Path, plan: dict[str, Any], style: str,
                    transport: TileTransport, *, timeout: float, delay: float,
                    now: datetime) -> tuple[dict[str, Any], Path]:
    tile_style = _tile_style(style)
    pixels = driving_basemap.tile_pixels(tile_style)
    directory = root / DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    existing = _reuse_directory(root, plan, pixels)
    if existing is not None:
        return existing
    temporary = Path(tempfile.mkdtemp(prefix=".road-trip-follow-tmp-", dir=directory))
    records: list[dict[str, Any]] = []
    try:
        for index, tile in enumerate(plan["tiles"]):
            x, y, z = tile["x"], tile["y"], tile["z"]
            body = driving_basemap._fetch_tile(z, x, y, index % 4 + 1, transport,
                                               timeout=timeout, style=tile_style)
            image = driving_basemap._decode_tile(body, z, x, y, pixels)
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=90, optimize=True)
            content = buffer.getvalue()
            target = temporary / f"z{z}" / str(x) / f"{y}.jpg"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            records.append({"x": x, "y": y, "z": z,
                            "sha256": hashlib.sha256(content).hexdigest(),
                            "width": pixels, "height": pixels,
                            "projected": tile["projected"]})
            if delay > 0:
                time.sleep(delay)
        manifest = driving_layout.manifest_digest(plan["planDigest"], records)
        (temporary / "manifest.json").write_text(json.dumps({
            "planDigest": plan["planDigest"], "manifestDigest": manifest,
            "zoom": plan["zoom"], "tileSize": plan["tileSize"],
            "request": plan["request"], "created": now.isoformat(timespec="seconds"),
            "tiles": [{"x": tile["x"], "y": tile["y"], "sha256": tile["sha256"]}
                      for tile in records],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        final = directory / f"road-trip-follow-{manifest[:16]}"
        if final.exists() and _directory_tiles_valid(final, records, plan["zoom"]):
            shutil.rmtree(temporary, ignore_errors=True)
        else:
            if final.exists():
                final = directory / f"road-trip-follow-{manifest[:16]}-{uuid.uuid4().hex[:8]}"
            try:
                temporary.rename(final)
            except (FileExistsError, PermissionError):
                # Windows 防病毒/索引器可能短暂占用新目录；内容一致就复用，
                # 否则逐文件复制安装，绝不覆盖正在被引用的目录。
                if final.exists() and _directory_tiles_valid(final, records, plan["zoom"]):
                    shutil.rmtree(temporary, ignore_errors=True)
                else:
                    if final.exists():
                        final = directory / (f"road-trip-follow-{manifest[:16]}-"
                                             f"{uuid.uuid4().hex[:8]}")
                    final.mkdir(parents=True, exist_ok=False)
                    shutil.copytree(temporary, final, dirs_exist_ok=True)
                    shutil.rmtree(temporary, ignore_errors=True)
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
            "manifest": (final / "manifest.json").relative_to(root).as_posix(),
            "tiles": tiles,
        }
        return layer, final
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _directory_tiles_valid(final: Path, records: list[dict[str, Any]], zoom: int) -> bool:
    for record in records:
        file = final / f"z{zoom}" / str(record["x"]) / f"{record['y']}.jpg"
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != record["sha256"]:
            return False
    return True


def _overview_reusable(root: Path, existing: dict[str, Any], plan_bbox: list[float],
                       scale: float, style: str) -> bool:
    overview = existing.get("overview")
    if not isinstance(overview, dict):
        return False
    expected = _layer_plan_from_bbox(
        plan_bbox, scale, minimum_zoom=8,
        pixels=driving_basemap.tile_pixels(_tile_style(style)))
    if overview.get("zoom") != expected[0]:
        return False
    if overview.get("bbox") != [round(value, 6) for value in expected[5]]:
        return False
    request = overview.get("request")
    params = request.get("params", {}) if isinstance(request, dict) else {}
    if params.get("style") != str(_tile_style(style)):
        return False
    image = overview.get("image")
    if not isinstance(image, dict) or not isinstance(image.get("path"), str):
        return False
    file = root / image["path"]
    return file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest() == image.get("sha256")


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
    return driving_layout.manifest_digest(plan["planDigest"], records) == follow.get("manifestDigest")


def _references(index_data: dict[str, Any] | None) -> tuple[set[Path], set[Path]]:
    images: set[Path] = set()
    directories: set[Path] = set()
    if not isinstance(index_data, dict):
        return images, directories
    global_layer = index_data.get("global")
    if isinstance(global_layer, dict):
        path = global_layer.get("image", {}).get("path")
        if isinstance(path, str):
            images.add(Path(path))
    for entry in (index_data.get("days") or {}).values():
        if not isinstance(entry, dict):
            continue
        overview = entry.get("overview")
        if isinstance(overview, dict):
            path = overview.get("image", {}).get("path")
            if isinstance(path, str):
                images.add(Path(path))
        follow = entry.get("followTiles")
        if isinstance(follow, dict):
            for tile in follow.get("tiles", []):
                path = tile.get("path") if isinstance(tile, dict) else None
                if isinstance(path, str):
                    images.add(Path(path))
                    for parent in Path(path).parents:
                        if parent.name.startswith("road-trip-follow-"):
                            directories.add(parent)
                            break
    return images, directories


def _cleanup(root: Path, index_data: dict[str, Any] | None) -> None:
    directory = root / DIRECTORY
    if not directory.is_dir():
        return
    keep_images, keep_directories = _references(index_data)
    for pattern in ("roadmap-*.jpg",):
        for old in directory.glob(pattern):
            if old.relative_to(root) not in keep_images:
                old.unlink(missing_ok=True)
    for old in directory.glob("road-trip-follow-*"):
        if old.relative_to(root) not in keep_directories:
            shutil.rmtree(old, ignore_errors=True)
    for temporary in directory.glob(".road-trip-follow-tmp-*"):
        shutil.rmtree(temporary, ignore_errors=True)


def _read_index(root: Path) -> dict[str, Any] | None:
    path = root / INDEX
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_index(root: Path, value: dict[str, Any]) -> None:
    path = root / INDEX
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix="index.json.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _total_bytes(root: Path, index_data: dict[str, Any]) -> int:
    total = (root / index_data["global"]["image"]["path"]).stat().st_size
    for entry in index_data["days"].values():
        total += (root / entry["overview"]["image"]["path"]).stat().st_size
        for tile in entry["followTiles"]["tiles"]:
            total += (root / tile["path"]).stat().st_size
    return total


def fetch_basemap(project_dir: str | Path, *, transport: TileTransport | None = None,
                  now: datetime | None = None, refresh: bool = False,
                  delay: float = DEFAULT_DELAY_SECONDS,
                  timeout: float = DEFAULT_TIMEOUT_SECONDS,
                  style: str | None = None) -> dict[str, Any]:
    """生成或复用全局与每日底图并原子更新索引；失败保留旧索引。"""
    root = Path(project_dir).expanduser().resolve()
    _, manifest = load_manifest(root)
    if manifest["type"] != "road-trip" or manifest.get("materials") != materials.MATERIALS:
        raise M2VError("m2v road-trip basemap 仅适用于 road-trip 作品")
    docs = materials.load_project(root, require_basemap=False)
    trip = docs["trip"]
    if trip["sourceUsage"].get("mapTiles") is not True:
        raise M2VError("道路底图使用未获授权：请将 trip.json.sourceUsage.mapTiles 置 true 后重试")
    styles = {day["id"]: _style_for(day, style) for day in docs["days"]}
    trip_geom = layout_module.trip_geometry([docs["routes"][day["id"]] for day in docs["days"]])
    global_bbox, global_scale = layout_module.trip_overview_bbox(trip_geom, materials.WIDTH,
                                                                  materials.HEIGHT)
    day_plans: list[dict[str, Any]] = []
    total_tiles = 0
    for index, day in enumerate(docs["days"]):
        route = docs["routes"][day["id"]]
        geom = layout_module.day_geometry(route, trim_origin=index == 0)
        bbox, scale = layout_module.day_overview_bbox(geom, materials.WIDTH, materials.HEIGHT)
        tile_style = _tile_style(styles[day["id"]])
        zoom = layout_module.follow_zoom(route, day["id"], index, tile_style=tile_style)
        plan = layout_module.corridor_plan(route, day["id"], zoom, day_index=index,
                                           tile_style=tile_style)
        total_tiles += plan["tileCount"]
        day_plans.append({"day": day, "index": index, "bbox": bbox, "scale": scale,
                          "plan": plan, "style": styles[day["id"]]})
    if total_tiles > layout_module.MAX_TRIP_TILES:
        raise M2VError(f"全片走廊需要 {total_tiles} 块瓦片，超过上限 "
                       f"{layout_module.MAX_TRIP_TILES}；未发起取图")

    existing = _read_index(root)
    version = layout_module.layout_version()
    if isinstance(existing, dict) and not refresh and existing.get("layoutVersion") == version:
        reusable = (
            _overview_reusable(root, {"overview": existing.get("global")}, global_bbox,
                               global_scale, "road")
            and all(
                entry.get("style") == plan["style"]
                and entry.get("service") == SERVICE_BY_STYLE[_tile_style(plan["style"])]
                and _overview_reusable(root, entry, plan["bbox"], plan["scale"], plan["style"])
                and _follow_reusable(root, entry, plan["plan"])
                for entry, plan in zip(
                    (existing.get("days", {}).get(item["day"]["id"], {}) for item in day_plans),
                    day_plans)
            )
        )
        if reusable:
            _cleanup(root, existing)
            return {"path": root / INDEX, "reused": True,
                    "tileCount": total_tiles,
                    "zoom": (existing["global"]["zoom"],
                             {day_id: entry["followTiles"]["zoom"]
                              for day_id, entry in existing["days"].items()})}

    timestamp = now or datetime.now().astimezone()
    if timestamp.tzinfo is None:
        timestamp = timestamp.astimezone()
    client = transport or driving_basemap.default_transport
    old_images, old_directories = _references(existing)
    created_images: list[Path] = []
    created_directories: list[Path] = []
    wrote = False
    try:
        global_layer, global_image, global_created = _render_overview(
            root, "global", global_bbox, global_scale, "road",
            client, timeout=timeout, delay=delay)
        if global_created:
            created_images.append(global_image)
        days_data: dict[str, Any] = {}
        for item in day_plans:
            day = item["day"]
            style_name = item["style"]
            overview, image, created = _render_overview(
                root, day["id"], item["bbox"], item["scale"], style_name, client,
                timeout=timeout, delay=delay)
            if created:
                created_images.append(image)
            follow, directory = _fetch_corridor(root, item["plan"], style_name, client,
                                                timeout=timeout, delay=delay, now=timestamp)
            created_directories.append(directory)
            days_data[day["id"]] = {
                "style": style_name,
                "service": SERVICE_BY_STYLE[_tile_style(style_name)],
                "overview": overview,
                "followTiles": follow,
            }
        index_data = {
            "schemaVersion": 1,
            "layoutVersion": version,
            "provider": "amap",
            "attribution": trip["sourceUsage"]["attribution"],
            "fetchedAt": timestamp.isoformat(timespec="seconds"),
            "global": global_layer,
            "days": days_data,
        }
        size = _total_bytes(root, index_data)
        if size > layout_module.MAX_TRIP_BYTES:
            raise M2VError(f"底图共 {size / 1024 / 1024:.1f} MB，超过上限 "
                           f"{layout_module.MAX_TRIP_BYTES / 1024 / 1024:.0f} MB；未保存索引")
        _write_index(root, index_data)
        wrote = True
    finally:
        if not wrote:
            for image in created_images:
                if image.relative_to(root) not in old_images:
                    image.unlink(missing_ok=True)
            for directory in created_directories:
                if directory.relative_to(root) not in old_directories:
                    shutil.rmtree(directory, ignore_errors=True)
    _cleanup(root, index_data)
    return {"path": root / INDEX, "reused": False, "tileCount": total_tiles,
            "bytes": _total_bytes(root, index_data),
            "zoom": (global_layer["zoom"],
                     {day_id: entry["followTiles"]["zoom"]
                      for day_id, entry in days_data.items()})}
