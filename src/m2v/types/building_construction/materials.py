"""两层框架住宅建筑材料的离线校验与渲染输入（v2）。"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from m2v.core.schema import validate_document
from m2v.core.validate import fail, text
from .components import build_components, expand_selector
from .schema import Building, Construction, Manifest

WIDTH = 1920
HEIGHT = 1080
FPS = 30
MATERIALS = {
    "building": "building.json",
    "construction": "construction.json",
    "assets": "manifest.json",
}
_ID = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
_ACTIONS = {"excavate", "pour", "grow", "slide", "lift", "rotate", "insert", "spread"}


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        fail(path.name, f"无法读取有效 UTF-8 JSON：{exc}")
    if not isinstance(data, dict):
        fail(path.name, "顶层必须是对象")
    version = data.get("schemaVersion")
    if version == 1:
        fail(path.name, "schemaVersion 1 已停用：请按 v2 重写本材料（新版需要 roof/stairs/sill、"
                        "shots 与 steps），不提供迁移工具")
    if version != 2:
        fail(path.name, "schemaVersion 必须为 2")
    return data


def _number(value: Any, where: str, *, low: float | None = None,
            high: float | None = None) -> float:
    if type(value) not in (int, float):
        fail(where, "必须是数字")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        fail(where, "超出可表示范围")
    if not math.isfinite(number) or (low is not None and number < low) \
            or (high is not None and number > high):
        bounds = ""
        if low is not None and high is not None:
            bounds = f"，范围 {low:g}～{high:g}"
        elif low is not None:
            bounds = f"，且不小于 {low:g}"
        elif high is not None:
            bounds = f"，且不大于 {high:g}"
        fail(where, "必须是有限数字" + bounds)
    return number


def _id(value: Any, where: str) -> str:
    result = text(value, where)
    if not _ID.fullmatch(result):
        fail(where, "必须是 1～63 位小写字母、数字或连字符，并以字母开头")
    return result


def _validate_building(building: dict[str, Any]) -> None:
    canvas = building["canvas"]
    if (canvas["width"], canvas["height"]) != (WIDTH, HEIGHT):
        fail("building.json.canvas", f"固定为 {WIDTH}×{HEIGHT}")
    house = building["house"]
    width = _number(house.get("width"), "building.json.house.width", low=4, high=40)
    depth = _number(house.get("depth"), "building.json.house.depth", low=4, high=40)
    floors = house.get("floors")
    if not isinstance(floors, int) or not 1 <= floors <= 3:
        fail("building.json.house.floors", "必须是 1～3 的整数")
    floor_height = _number(house.get("floorHeight"), "building.json.house.floorHeight",
                           low=2.2, high=6)
    bay_count = house.get("bayCount")
    if not isinstance(bay_count, int) or not 2 <= bay_count <= 5:
        fail("building.json.house.bayCount", "必须是 2～5 的整数")
    roof = house["roof"]
    roof_type = roof.get("type")
    if roof_type not in {"gable", "flat"}:
        fail("building.json.house.roof.type", "必须是 gable 或 flat")
    roof_height = _number(roof.get("height"), "building.json.house.roof.height", low=0.3, high=6)
    _number(roof.get("overhang"), "building.json.house.roof.overhang", low=0, high=1.5)
    if roof_type == "flat" and roof_height > 1.5:
        fail("building.json.house.roof.height", "平屋顶女儿墙高度不得超过 1.5")
    _number(house.get("wallThickness"), "building.json.house.wallThickness", low=0.1, high=0.6)
    _number(house.get("foundationDepth"), "building.json.house.foundationDepth",
            low=0.3, high=4)
    _number(house.get("sitePadding"), "building.json.house.sitePadding", low=1, high=12)
    stairs = house["stairs"]
    stair_side = stairs.get("side")
    if stair_side not in {"front", "back", "left", "right"}:
        fail("building.json.house.stairs.side", "必须是 front、back、left 或 right")
    stair_offset = _number(stairs.get("offset"), "building.json.house.stairs.offset", low=0)
    stair_width = _number(stairs.get("width"), "building.json.house.stairs.width", low=0.8, high=4)
    stair_wall = width if stair_side in {"front", "back"} else depth
    if stair_offset + stair_width > stair_wall - 0.2:
        fail("building.json.house.stairs", "楼梯超出所属墙面")
    openings = house["openings"]
    seen: set[str] = set()
    for index, opening in enumerate(openings):
        where = f"building.json.house.openings[{index}]"
        opening_id = _id(opening.get("id"), f"{where}.id")
        if opening_id in seen:
            fail(f"{where}.id", "开口 ID 重复")
        seen.add(opening_id)
        floor = opening.get("floor")
        if not isinstance(floor, int) or not 1 <= floor <= floors:
            fail(f"{where}.floor", "必须落在声明楼层内")
        side = opening.get("side")
        if side not in {"front", "back", "left", "right"}:
            fail(f"{where}.side", "必须是 front、back、left 或 right")
        offset = _number(opening.get("offset"), f"{where}.offset", low=0)
        opening_width = _number(opening.get("width"), f"{where}.width", low=0.4, high=6)
        opening_height = _number(opening.get("height"), f"{where}.height", low=0.4)
        sill = _number(opening.get("sill"), f"{where}.sill", low=0)
        wall_length = width if side in {"front", "back"} else depth
        if offset + opening_width > wall_length - 0.2:
            fail(where, "开口超出所属墙面")
        if sill + opening_height > floor_height - 0.1:
            fail(f"{where}", "窗台加洞高超出层高")


def _validate_construction(construction: dict[str, Any], components: list[Any]) -> None:
    duration = construction.get("durationSeconds")
    if not isinstance(duration, int) or not 10 <= duration <= 120:
        fail("construction.json.durationSeconds", "必须是 10～120 的整数秒")
    if construction.get("fps") != FPS:
        fail("construction.json.fps", f"必须为 {FPS}")
    stages = construction["stages"]
    cursor = 0.0
    stage_ids: dict[str, tuple[float, float]] = {}
    seen: set[str] = set()
    for index, stage in enumerate(stages):
        where = f"construction.json.stages[{index}]"
        stage_id = _id(stage.get("id"), f"{where}.id")
        if stage_id in seen:
            fail(f"{where}.id", "阶段 ID 重复")
        seen.add(stage_id)
        start = _number(stage.get("startSeconds"), f"{where}.startSeconds", low=0)
        end = _number(stage.get("endSeconds"), f"{where}.endSeconds", low=0)
        if abs(start - cursor) > 1e-6 or end <= start:
            fail(where, "阶段必须从 0 开始、首尾相接且 end > start")
        stage_ids[stage_id] = (start, end)
        cursor = end
    if abs(cursor - duration) > 1e-6:
        fail("construction.json.stages", "阶段必须完整覆盖声明时长")

    shots = construction["shots"]
    shot_ids: set[str] = set()
    cursor = 0.0
    known = {item.id for item in components}
    for index, shot in enumerate(shots):
        where = f"construction.json.shots[{index}]"
        shot_id = _id(shot.get("id"), f"{where}.id")
        if shot_id in shot_ids:
            fail(f"{where}.id", "镜头 ID 重复")
        shot_ids.add(shot_id)
        start = _number(shot.get("startSeconds"), f"{where}.startSeconds", low=0)
        end = _number(shot.get("endSeconds"), f"{where}.endSeconds", low=0)
        if abs(start - cursor) > 1e-6 or end <= start:
            fail(where, "镜头必须从 0 开始、首尾相接且不重叠")
        cursor = end
        for camera_key in ("camera", "to"):
            camera = shot.get(camera_key)
            if camera is None:
                continue
            for field in ("position", "target"):
                values = camera.get(field)
                if not isinstance(values, list) or len(values) != 3:
                    fail(f"{where}.{camera_key}.{field}", "必须是三个数字的数组")
                for axis, value in enumerate(values):
                    _number(value, f"{where}.{camera_key}.{field}[{axis}]")
            fov = _number(camera.get("fov"), f"{where}.{camera_key}.fov", low=20, high=90)
            if camera.get("position") == camera.get("target"):
                fail(f"{where}.{camera_key}", "position 与 target 不能相同")
            if fov <= 0:
                fail(f"{where}.{camera_key}.fov", "必须为正")
        for selector in shot.get("hide", []):
            _selector(selector, where + ".hide", components, allow_empty=False)
    if abs(cursor - duration) > 1e-6:
        fail("construction.json.shots", "镜头必须完整覆盖声明时长")

    initial = construction.get("initial", [])
    initial_set: set[str] = set()
    for index, identity in enumerate(initial):
        where = f"construction.json.initial[{index}]"
        identity = _id(identity, where)
        if identity not in known:
            fail(where, f"未知构件：{identity}")
        if identity in initial_set:
            fail(where, f"初始构件重复：{identity}")
        initial_set.add(identity)

    steps = construction["steps"]
    step_ids: dict[str, Any] = {}
    for index, step in enumerate(steps):
        where = f"construction.json.steps[{index}]"
        step_id = _id(step.get("id"), f"{where}.id")
        if step_id in step_ids:
            fail(f"{where}.id", "步骤 ID 重复")
        step_ids[step_id] = step
    for step_id, step in step_ids.items():
        for dependency in step.get("after", []):
            dependency = _id(dependency, f"construction.json.steps[{step_id}].after")
            if dependency not in step_ids:
                fail(f"construction.json.steps[{step_id}].after",
                     f"未知依赖步骤：{dependency}")
    _check_cycles(step_ids)
    owners: dict[str, str] = {}
    for step_id, step in step_ids.items():
        where = f"construction.json.steps[{step_id}]"
        stage = stage_ids.get(step.get("stage"))
        if stage is None:
            fail(f"{where}.stage", f"未知阶段：{step.get('stage')}")
        action = step.get("action")
        if action not in _ACTIONS:
            fail(f"{where}.action", f"未知动作：{action}")
        start = _number(step.get("startSeconds"), f"{where}.startSeconds", low=0)
        end = _number(step.get("endSeconds"), f"{where}.endSeconds", low=0)
        if end <= start:
            fail(where, "步骤 endSeconds 必须大于 startSeconds")
        if start < stage[0] - 1e-6 or end > stage[1] + 1e-6:
            fail(where, "步骤必须落在所属阶段内")
        if not step.get("select"):
            fail(f"{where}.select", "步骤必须选择至少一个构件")
        matches: list[str] = []
        for selector in step["select"]:
            found = _selector(selector, f"{where}.select", components, allow_empty=False)
            if set(found) & set(matches):
                fail(where, "同一步骤的选择器重叠")
            matches.extend(found)
        for identity in matches:
            if identity in initial_set:
                fail(where, f"初始构件不得被步骤再次建成：{identity}")
            if identity in owners:
                fail(where, f"构件被重复建成：{identity}（已由 {owners[identity]} 建成）")
            owners[identity] = step_id
        for dependency in step.get("after", []):
            dependency = _id(dependency, f"{where}.after")
            if dependency not in step_ids:
                fail(f"{where}.after", f"未知依赖步骤：{dependency}")
            if dependency == step_id:
                fail(f"{where}.after", "步骤不能依赖自身")
            dependency_end = _number(step_ids[dependency].get("endSeconds"),
                                     f"{where}.after.{dependency}.endSeconds", low=0)
            if start < dependency_end - 1e-6:
                fail(where, f"步骤不能早于依赖 {dependency} 结束")
    missing = [item.id for item in components if item.id not in initial_set
               and item.id not in owners]
    if missing:
        fail("construction.json.steps", "以下构件没有被任何步骤建成：" + "、".join(missing[:8]))
    extra = sorted(set(owners) - known)
    if extra:
        fail("construction.json.steps", "步骤引用了未知构件：" + "、".join(extra[:8]))


def _selector(value: Any, where: str, components: list[Any], *, allow_empty: bool) -> list[str]:
    selector = text(value, where)
    try:
        found = expand_selector(components, selector)
    except ValueError as exc:
        fail(where, str(exc))
    if not found and not allow_empty:
        fail(where, f"选择器没有匹配任何构件：{selector}")
    return found


def _check_cycles(steps: dict[str, Any]) -> None:
    graph = {step_id: list(step.get("after", [])) for step_id, step in steps.items()}
    state: dict[str, int] = {}

    def visit(node: str, trail: list[str]) -> None:
        if state.get(node) == 1:
            fail("construction.json.steps", "依赖环：" + " → ".join([*trail, node]))
        if state.get(node) == 2:
            return
        state[node] = 1
        for dependency in graph.get(node, []):
            visit(dependency, [*trail, node])
        state[node] = 2

    for step_id in graph:
        visit(step_id, [])


def _validate_assets(manifest: dict[str, Any]) -> None:
    for index, item in enumerate(manifest["assets"]):
        where = f"assets/manifest.json.assets[{index}]"
        path = item["path"]
        if Path(path).is_absolute() or ".." in Path(path).parts:
            fail(f"{where}.path", "必须是作品内相对路径")
        digest = item["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"{where}.sha256", "必须是 64 位十六进制 SHA-256")


def load_project(project_dir: str | Path, *, files: dict[str, str] | None = None) -> dict[str, Any]:
    root = Path(project_dir).resolve()
    if not root.is_dir():
        fail("作品目录", f"目录不存在：{root}")
    names = files or MATERIALS
    building = validate_document(Building, _load(root / names["building"]), "building.json")
    construction = validate_document(
        Construction, _load(root / names["construction"]), "construction.json")
    manifest = validate_document(
        Manifest, _load(root / names["assets"]), "assets/manifest.json")
    _validate_building(building)
    components = build_components(building["house"])
    _validate_construction(construction, components)
    _validate_assets(manifest)
    for asset in manifest["assets"]:
        file = (root / asset["path"]).resolve()
        if not file.is_relative_to(root) or not file.is_file():
            fail("assets/manifest.json.assets", f"资产不存在：{asset['path']}")
        if hashlib.sha256(file.read_bytes()).hexdigest() != asset["sha256"]:
            fail("assets/manifest.json.assets", f"资产摘要不匹配：{asset['path']}")
    return {
        "building": building,
        "construction": construction,
        "assets": manifest,
        "components": [item.__dict__ for item in components],
    }


def build_render_props(docs: dict[str, Any]) -> dict[str, Any]:
    construction = docs["construction"]
    return {
        "schemaVersion": 2,
        "durationInFrames": construction["durationSeconds"] * FPS,
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "building": docs["building"],
        "construction": construction,
        "assets": docs["assets"],
        "components": docs["components"],
    }
