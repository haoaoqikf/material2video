"""两层框架住宅建筑材料的离线校验与渲染输入。"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from m2v.core.validate import fail, obj, text

WIDTH = 1920
HEIGHT = 1080
FPS = 30
MATERIALS = {
    "building": "building.json",
    "construction": "construction.json",
    "assets": "manifest.json",
}
_WALL_SIDES = {"front", "back", "left", "right"}
_ID = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        fail(path.name, f"无法读取有效 UTF-8 JSON：{exc}")
    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        fail(path.name, "schemaVersion 必须为 1")
    return data


def _number(value: Any, where: str, *, low: float | None = None) -> float:
    if type(value) not in (int, float):
        fail(where, "必须是数字")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        fail(where, "超出可表示范围")
    if not math.isfinite(number) or (low is not None and number < low):
        fail(where, "必须是有限数字" + (f"，且不小于 {low:g}" if low is not None else ""))
    return number


def _id(value: Any, where: str) -> str:
    result = text(value, where)
    if not _ID.fullmatch(result):
        fail(where, "必须是 1～63 位小写字母、数字或连字符，并以字母开头")
    return result


def _validate_building(building: dict[str, Any]) -> None:
    obj(building, "building.json", {"schemaVersion", "canvas", "house"})
    canvas = obj(building.get("canvas"), "building.json.canvas", {"width", "height"})
    if (canvas.get("width"), canvas.get("height")) != (WIDTH, HEIGHT):
        fail("building.json.canvas", f"固定为 {WIDTH}×{HEIGHT}")
    house = obj(building.get("house"), "building.json.house", {
        "width", "depth", "floors", "floorHeight", "bayCount", "roofHeight",
        "wallThickness", "foundationDepth", "sitePadding", "openings",
    })
    width = _number(house.get("width"), "building.json.house.width", low=4)
    depth = _number(house.get("depth"), "building.json.house.depth", low=4)
    floors = house.get("floors")
    if type(floors) is not int or not 1 <= floors <= 3:
        fail("building.json.house.floors", "必须是 1～3 的整数")
    floor_height = _number(house.get("floorHeight"), "building.json.house.floorHeight", low=2.2)
    bay_count = house.get("bayCount")
    if type(bay_count) is not int or not 2 <= bay_count <= 5:
        fail("building.json.house.bayCount", "必须是 2～5 的整数")
    for field in ("roofHeight", "wallThickness", "foundationDepth", "sitePadding"):
        _number(house.get(field), f"building.json.house.{field}", low=0.1)
    openings = house.get("openings")
    if not isinstance(openings, list) or len(openings) > 60:
        fail("building.json.house.openings", "必须是最多 60 项的数组")
    seen: set[str] = set()
    for index, raw in enumerate(openings):
        where = f"building.json.house.openings[{index}]"
        opening = obj(raw, where, {"id", "floor", "side", "offset", "width", "height"})
        opening_id = _id(opening.get("id"), f"{where}.id")
        if opening_id in seen:
            fail(f"{where}.id", "开口 ID 重复")
        seen.add(opening_id)
        floor = opening.get("floor")
        if type(floor) is not int or not 1 <= floor <= floors:
            fail(f"{where}.floor", "必须落在声明楼层内")
        side = opening.get("side")
        if side not in _WALL_SIDES:
            fail(f"{where}.side", "必须是 front/back/left/right")
        offset = _number(opening.get("offset"), f"{where}.offset", low=0)
        opening_width = _number(opening.get("width"), f"{where}.width", low=0.2)
        opening_height = _number(opening.get("height"), f"{where}.height", low=0.3)
        wall_length = width if side in {"front", "back"} else depth
        if offset + opening_width > wall_length - 0.2:
            fail(f"{where}", "开口超出所属墙面")
        if opening_height > floor_height - 0.3:
            fail(f"{where}.height", "开口高度超出层高")


def _validate_construction(construction: dict[str, Any]) -> None:
    obj(construction, "construction.json", {"schemaVersion", "durationSeconds", "fps",
                                             "stages", "camera"})
    duration = construction.get("durationSeconds")
    if type(duration) is not int or not 10 <= duration <= 120:
        fail("construction.json.durationSeconds", "必须是 10～120 的整数秒")
    if construction.get("fps") != FPS:
        fail("construction.json.fps", f"必须为 {FPS}")
    stages = construction.get("stages")
    if not isinstance(stages, list) or not 1 <= len(stages) <= 20:
        fail("construction.json.stages", "必须包含 1～20 个阶段")
    cursor = 0.0
    seen: set[str] = set()
    for index, raw in enumerate(stages):
        where = f"construction.json.stages[{index}]"
        stage = obj(raw, where, {"id", "label", "startSeconds", "endSeconds"})
        stage_id = _id(stage.get("id"), f"{where}.id")
        if stage_id in seen:
            fail(f"{where}.id", "阶段 ID 重复")
        seen.add(stage_id)
        text(stage.get("label"), f"{where}.label")
        start = _number(stage.get("startSeconds"), f"{where}.startSeconds", low=0)
        end = _number(stage.get("endSeconds"), f"{where}.endSeconds", low=0)
        if abs(start - cursor) > 1e-6 or end <= start:
            fail(where, "阶段必须从 0 开始、首尾相接且 end > start")
        cursor = end
    if abs(cursor - duration) > 1e-6:
        fail("construction.json.stages", "阶段必须完整覆盖声明时长")
    camera = obj(construction.get("camera"), "construction.json.camera",
                 {"startAzimuth", "endAzimuth", "elevation"})
    for field in ("startAzimuth", "endAzimuth", "elevation"):
        _number(camera.get(field), f"construction.json.camera.{field}")


def _validate_assets(manifest: dict[str, Any]) -> None:
    obj(manifest, "assets/manifest.json", {"schemaVersion", "assets"})
    assets = manifest.get("assets")
    if not isinstance(assets, list) or len(assets) > 50:
        fail("assets/manifest.json.assets", "必须是最多 50 项的数组")
    for index, raw in enumerate(assets):
        where = f"assets/manifest.json.assets[{index}]"
        item = obj(raw, where, {"path", "sha256", "source", "license"})
        path = text(item.get("path"), f"{where}.path")
        if Path(path).is_absolute() or ".." in Path(path).parts:
            fail(f"{where}.path", "必须是作品内相对路径")
        digest = text(item.get("sha256"), f"{where}.sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"{where}.sha256", "必须是 64 位十六进制 SHA-256")
        text(item.get("source"), f"{where}.source")
        text(item.get("license"), f"{where}.license")


def load_project(project_dir: str | Path) -> dict[str, Any]:
    root = Path(project_dir).resolve()
    if not root.is_dir():
        fail("作品目录", f"目录不存在：{root}")
    building = _load(root / MATERIALS["building"])
    construction = _load(root / MATERIALS["construction"])
    manifest = _load(root / MATERIALS["assets"])
    _validate_building(building)
    _validate_construction(construction)
    _validate_assets(manifest)
    for asset in manifest["assets"]:
        file = (root / asset["path"]).resolve()
        if not file.is_relative_to(root) or not file.is_file():
            fail("assets/manifest.json.assets", f"资产不存在：{asset['path']}")
        if hashlib.sha256(file.read_bytes()).hexdigest() != asset["sha256"]:
            fail("assets/manifest.json.assets", f"资产摘要不匹配：{asset['path']}")
    return {"building": building, "construction": construction, "assets": manifest}


def build_render_props(docs: dict[str, Any]) -> dict[str, Any]:
    construction = docs["construction"]
    return {
        "schemaVersion": 1,
        "durationInFrames": construction["durationSeconds"] * FPS,
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "building": docs["building"],
        "construction": construction,
        "assets": docs["assets"],
    }


def render_inputs_digest(project_dir: str | Path) -> str:
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
    manifest = _load(root / MATERIALS["assets"])
    for asset in manifest["assets"]:
        inputs.append((root, root / asset["path"]))
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
