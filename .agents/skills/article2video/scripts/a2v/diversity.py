"""不读取正文的视觉结构指纹与叙事推进证据检查。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# v3：指纹扩展到持续世界、对象职责及受控状态推进；不含文章文本。
RULE_VERSION = 3
_ARGUMENT_ACTIONS = frozenset({
    "connect", "transfer", "accumulate", "deplete", "transform", "compare", "loop", "break", "restore",
})
_NON_TEXT_PROPERTIES = frozenset({"visible", "state", "value", "sourceRef"})


def _node_shape(node: Any) -> Any:
    """归一化树结构，只保留布局与原语信息。"""
    if not isinstance(node, dict):
        return "invalid"
    return {
        "type": node.get("type"),
        "ratio": node.get("ratio"),
        "columns": node.get("columns"),
        "align": node.get("align"),
        "children": [_node_shape(child) for child in node.get("children", [])],
    }


def _legacy_fingerprint(scene: dict[str, Any]) -> dict[str, Any]:
    intent = scene.get("visualIntent", {})
    motions = scene.get("motions", [])
    return {
        "tree": _node_shape(scene.get("sceneTree")),
        "relation": intent.get("relation"),
        "focus": intent.get("focus"),
        "composition": intent.get("composition"),
        "density": intent.get("density"),
        "mode": intent.get("mode"),
        "motions": [item.get("recipe") for item in motions if isinstance(item, dict)],
    }


def _world_signature(world: dict[str, Any]) -> dict[str, Any]:
    objects = world.get("objects", [])
    role_by_id = {
        item.get("id"): item.get("role")
        for item in objects if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    tracks = world.get("stateTracks", [])
    track_shapes = []
    for track in tracks if isinstance(tracks, list) else []:
        if not isinstance(track, dict):
            continue
        prop = track.get("property")
        # contentRef 只会令文案变化；不得把它算作画面结构或论证变化。
        if prop == "contentRef":
            continue
        track_shapes.append({
            "role": role_by_id.get(track.get("target")),
            "property": prop,
            "interpolation": track.get("interpolation"),
            "targetValueType": _value_type(track.get("to")) if prop in _NON_TEXT_PROPERTIES else None,
        })
    motions = world.get("motions", [])
    motion_shapes = []
    for motion in motions if isinstance(motions, list) else []:
        if isinstance(motion, dict):
            targets = motion.get("targets", [motion.get("target")])
            motion_shapes.append({
                "roles": sorted(role_by_id.get(target, "unknown") for target in targets if isinstance(target, str)),
                "recipe": motion.get("recipe"),
                "stagger": motion.get("stagger"),
            })
    renderer = world.get("renderer", {})
    camera = world.get("camera", {})
    return {
        "renderer": renderer.get("kind") if isinstance(renderer, dict) else None,
        "module": renderer.get("module") if isinstance(renderer, dict) else None,
        "tree": _node_shape(world.get("sceneTree")),
        "objectRoles": sorted(role_by_id.values()),
        "tracks": sorted(track_shapes, key=_canonical),
        "motions": sorted(motion_shapes, key=_canonical),
        "camera": {
            key: camera.get(key) for key in ("shot", "composition", "depth")
        } if isinstance(camera, dict) else None,
    }


def _value_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "null"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: dict[str, Any]) -> str:
    """生成稳定、不含文章正文的 v3 视觉指纹。"""
    if value.get("version") == 4 and isinstance(value.get("world"), dict):
        payload = {"ruleVersion": RULE_VERSION, "world": _world_signature(value["world"])}
    else:
        payload = {"ruleVersion": RULE_VERSION, **_legacy_fingerprint(value)}
    return _canonical(payload)


def _stage_progression(world: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    beats = stage.get("beats", [])
    beat_by_id = {beat.get("id"): beat for beat in beats if isinstance(beat, dict)}
    beat_ids = set(beat_by_id)
    tracks = world.get("stateTracks", [])
    evidence = []
    for track in tracks if isinstance(tracks, list) else []:
        if not isinstance(track, dict) or track.get("property") not in _NON_TEXT_PROPERTIES:
            continue
        binding = track.get("binding", {})
        beat_id = binding.get("beatId") if isinstance(binding, dict) else None
        stage_id = binding.get("stageId") if isinstance(binding, dict) else None
        bound_here = beat_id in beat_ids or stage_id == stage.get("id")
        if not bound_here:
            continue
        beat = beat_by_id.get(beat_id)
        if beat_id and (not isinstance(beat, dict) or beat.get("action") not in _ARGUMENT_ACTIONS):
            continue
        evidence.append({"target": track.get("target"), "property": track.get("property"), "binding": binding})
    return {"status": "pass" if evidence else "fail", "evidence": evidence}


def _inspect_v4(data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    world = data.get("world")
    stages = [item for item in data.get("stages", []) if isinstance(item, dict)]
    if not isinstance(world, dict):
        return [], {"status": "pending", "reason": "缺少 world，无法计算持续场景指纹"}
    findings: list[dict[str, Any]] = []
    progressions = [_stage_progression(world, stage) for stage in stages]
    for index in range(1, len(stages)):
        current_progress = progressions[index]
        previous_progress = progressions[index - 1]
        if current_progress["status"] == "fail" and previous_progress["status"] == "fail":
            findings.append({
                "rule": "adjacent-identical",
                "scenes": [stages[index - 1].get("id"), stages[index].get("id")],
                "features": {"world": _world_signature(world), "reason": "连续阶段没有受控的非文字状态推进"},
            })
    renderer = world.get("renderer")
    if isinstance(renderer, dict) and renderer.get("kind") == "code":
        progression = {
            "status": "pending",
            "reason": "code 画面推进需由实际运行探针与动态评审确认",
            "stages": [{"stageId": stage.get("id"), **progress} for stage, progress in zip(stages, progressions)],
        }
    else:
        progression = {
            "status": "fail" if findings else "pass",
            "reason": None if not findings else "存在仅文字变化或缺少受控状态推进的连续阶段",
            "stages": [{"stageId": stage.get("id"), **progress} for stage, progress in zip(stages, progressions)],
        }
    return findings, progression


def inspect(data: dict[str, Any], references: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """执行片内复用检查；没有参考集合时明确标记跨作品检查未运行。"""
    if data.get("version") == 4:
        findings, progression = _inspect_v4(data)
        cross = []
        if references is not None:
            own = fingerprint(data)
            cross = [
                {"reference": index, "matches": True}
                for index, reference in enumerate(references)
                if isinstance(reference, dict) and fingerprint(reference) == own
            ]
        return {
            "ruleVersion": RULE_VERSION,
            "status": "pending" if progression["status"] == "pending" else ("fail" if findings else "pass"),
            "findings": findings,
            "progression": progression,
            "crossWork": {"status": "checked" if references is not None else "skipped",
                          "reason": None if references is not None else "未显式提供参考分镜集合", "matches": cross},
        }

    scenes = [scene for scene in data.get("scenes", []) if isinstance(scene, dict)]
    values = [fingerprint(scene) for scene in scenes]
    findings = []
    for index in range(1, len(values)):
        if values[index] == values[index - 1]:
            findings.append({"rule": "adjacent-identical", "scenes": [scenes[index - 1].get("id"), scenes[index].get("id")],
                             "features": json.loads(values[index])})
    groups: dict[str, list[str]] = {}
    for scene, value in zip(scenes, values):
        groups.setdefault(value, []).append(str(scene.get("id")))
    for value, ids in groups.items():
        if len(ids) >= 3:
            findings.append({"rule": "intra-video-reuse", "scenes": ids, "features": json.loads(value)})
    cross = []
    for ref_index, reference in enumerate(references or []):
        ref_values = {fingerprint(scene) for scene in reference.get("scenes", []) if isinstance(scene, dict)}
        matches = [scenes[i].get("id") for i, value in enumerate(values) if value in ref_values]
        if matches:
            cross.append({"reference": ref_index, "scenes": matches})
    return {"ruleVersion": RULE_VERSION, "findings": findings,
            "crossWork": {"status": "checked" if references is not None else "skipped",
                          "reason": None if references is not None else "未显式提供参考分镜集合", "matches": cross}}


def load_references(paths: list[str]) -> list[dict[str, Any]]:
    return [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]
