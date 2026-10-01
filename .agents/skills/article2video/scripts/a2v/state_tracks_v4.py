"""V4 全局状态轨道编译与逐帧纯函数求值。"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from .timeline_v4 import V4Timeline


@dataclass(frozen=True)
class CompiledTrack:
    id: str
    target: str
    property: str
    start_frame: int
    end_frame: int
    start_value: Any
    end_value: Any
    interpolation: str


def _lookup(root: Any, reference: str) -> Any:
    value = root
    for key in reference.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _baseline(storyboard: dict[str, Any], target: str, prop: str) -> Any:
    world = storyboard["world"]
    if world["renderer"]["kind"] == "tree":
        nodes: dict[str, dict[str, Any]] = {}
        def visit(node: dict[str, Any]) -> None:
            nodes[node["id"]] = node
            for child in node.get("children", []):
                visit(child)
        visit(world["sceneTree"])
        node = nodes.get(target, {})
    else:
        objects = world.get("data", {}).get("objects", {})
        node = objects.get(target, {}) if isinstance(objects, dict) else {}
    if prop == "visible":
        return node.get("visible", True)
    value = node.get(prop)
    if value is None and prop == "value" and world["renderer"]["kind"] == "tree":
        ref = node.get("contentRef")
        if isinstance(ref, str):
            return _lookup(world.get("data", {}), ref)
    return value


def _phase_range(timeline: V4Timeline, stage_id: str, phase: str) -> tuple[int, int]:
    item = next((item for item in timeline.phases if item["stageId"] == stage_id and item["phase"] == phase), None)
    if item is None:
        raise ValueError(f"未知阶段 phase 绑定：{stage_id}:{phase}")
    return item["startFrame"], item["endFrame"]


def compile_state_tracks(storyboard: dict[str, Any], timeline: V4Timeline) -> tuple[CompiledTrack, ...]:
    """解析 binding 并按对象属性建立串行轨道；重叠区间会失败。"""
    beat_ranges = {item["id"]: (item["startFrame"], item["endFrame"]) for item in timeline.beats}
    pending: list[tuple[int, int, dict[str, Any], int, int]] = []
    for index, track in enumerate(storyboard["world"].get("stateTracks", [])):
        binding = track["binding"]
        if "beatId" in binding:
            if binding["beatId"] not in beat_ranges:
                raise ValueError(f"轨道 {track['id']} 引用未知 beat {binding['beatId']!r}")
            start, end = beat_ranges[binding["beatId"]]
        else:
            start, end = _phase_range(timeline, binding["stageId"], binding["phase"])
        pending.append((start, index, track, start, end))
    pending.sort(key=lambda item: (item[0], item[1]))
    previous: dict[tuple[str, str], CompiledTrack] = {}
    compiled: list[CompiledTrack] = []
    for _, _, track, start, end in pending:
        lane = (track["target"], track["property"])
        prior = previous.get(lane)
        if prior and start < prior.end_frame:
            raise ValueError(f"对象 {lane[0]} 的属性 {lane[1]} 轨道 {prior.id} 与 {track['id']} 时间重叠")
        start_value = copy.deepcopy(prior.end_value if prior else _baseline(storyboard, *lane))
        if start_value is None:
            raise ValueError(f"对象 {lane[0]} 的属性 {lane[1]} 缺少基础值")
        item = CompiledTrack(track["id"], lane[0], lane[1], start, end, start_value,
                             copy.deepcopy(track["to"]), track["interpolation"])
        compiled.append(item)
        previous[lane] = item
    return tuple(compiled)


def _ease(value: float, name: str) -> float:
    value = min(1.0, max(0.0, value))
    if name == "linear": return value
    if name == "ease-in": return value * value
    if name == "ease-out": return 1 - (1 - value) * (1 - value)
    if name == "ease-in-out": return 2 * value * value if value < .5 else 1 - ((-2 * value + 2) ** 2) / 2
    return value


def _interpolate(start: Any, end: Any, progress: float) -> Any:
    if isinstance(start, bool) or isinstance(end, bool):
        return copy.deepcopy(start)
    if isinstance(start, (int, float)) and isinstance(end, (int, float)):
        value = start + (end - start) * progress
        return int(value) if isinstance(start, int) and isinstance(end, int) and value.is_integer() else value
    if isinstance(start, list) and isinstance(end, list) and len(start) == len(end):
        return [_interpolate(a, b, progress) for a, b in zip(start, end)]
    if isinstance(start, dict) and isinstance(end, dict) and start.keys() == end.keys():
        return {key: _interpolate(start[key], end[key], progress) for key in start}
    return copy.deepcopy(start)


def state_at(tracks: tuple[CompiledTrack, ...], frame: int) -> dict[str, dict[str, Any]]:
    """以全局帧号求当前值；不缓存、不变更轨道输入，支持任意顺序寻帧。"""
    result: dict[str, dict[str, Any]] = {}
    for track in tracks:
        lane = result.setdefault(track.target, {})
        if frame < track.start_frame:
            lane.setdefault(track.property, copy.deepcopy(track.start_value))
            continue
        if frame >= track.end_frame:
            value = track.end_value
        elif track.interpolation == "step-end":
            value = track.start_value
        else:
            progress = _ease((frame - track.start_frame) / max(1, track.end_frame - track.start_frame), track.interpolation)
            value = _interpolate(track.start_value, track.end_value, progress)
        lane[track.property] = copy.deepcopy(value)
    return result
