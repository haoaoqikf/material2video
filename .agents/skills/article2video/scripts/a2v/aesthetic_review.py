"""导演层的确定性预检：检查母题覆盖、镜头声明和连续构图重复。

它不替代人工审美；联系表仍由现有 review 流程生成。这里只报告能从分镜
声明客观判断的问题，避免把主观评分伪装成自动结论。
"""

from __future__ import annotations

from collections import Counter
from typing import Any


def analyze(storyboard: dict[str, Any]) -> dict[str, Any]:
    scenes = storyboard.get("scenes") or []
    enabled = storyboard.get("directingVersion") == 1
    direction = storyboard.get("visualDirection") or {}
    motif = (direction.get("motif") or "").strip()
    findings: list[dict[str, Any]] = []
    signatures: list[tuple[Any, ...]] = []
    camera_missing: list[str] = []
    motif_missing: list[str] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("id"))
        camera = scene.get("camera") or {}
        if enabled and not camera:
            camera_missing.append(scene_id)
        intent = scene.get("visualIntent") or {}
        declared_motif = str(intent.get("motif") or intent.get("primaryObject") or "").strip()
        if enabled and not declared_motif:
            motif_missing.append(scene_id)
        signatures.append((
            camera.get("shot"), camera.get("composition"), camera.get("depth"),
            camera.get("movement"), intent.get("relation"), intent.get("mode"),
        ))
    if enabled and camera_missing:
        findings.append({"rule": "camera-declaration", "status": "fail", "scenes": camera_missing, "detail": "启用导演契约的场景必须声明 camera"})
    if enabled and motif_missing:
        findings.append({"rule": "motif-coverage", "status": "fail", "scenes": motif_missing, "detail": "每幕必须能从 primaryObject 或 visualIntent.motif 追踪视觉母题"})
    repeated = []
    for index in range(1, len(signatures)):
        if signatures[index] == signatures[index - 1] and signatures[index] != (None,) * 6:
            repeated.append([str(scenes[index - 1].get("id")), str(scenes[index].get("id"))])
    if repeated:
        findings.append({"rule": "adjacent-shot-reuse", "status": "warn", "scenes": repeated, "detail": "相邻场景镜头与视觉关系完全复用，需人工确认不是模板化重复"})
    return {
        "enabled": enabled,
        "motif": motif,
        "sceneCount": len(scenes),
        "signatures": [list(item) for item in signatures],
        "findings": findings,
        "publishable": not any(item["status"] == "fail" for item in findings),
    }
