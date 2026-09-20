"""不读取正文的场景树布局指纹与多样性检查。"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

RULE_VERSION = 1

def _node_shape(node: Any) -> Any:
    if not isinstance(node, dict): return "invalid"
    return {"type":node.get("type"),"ratio":node.get("ratio"),"columns":node.get("columns"),"align":node.get("align"),"children":[_node_shape(child) for child in node.get("children", [])]}

def fingerprint(scene: dict[str, Any]) -> str:
    intent=scene.get("visualIntent", {}); motions=scene.get("motions", [])
    payload={"ruleVersion":RULE_VERSION,"tree":_node_shape(scene.get("sceneTree")),"relation":intent.get("relation"),"focus":intent.get("focus"),"composition":intent.get("composition"),"density":intent.get("density"),"motions":[item.get("recipe") for item in motions if isinstance(item,dict)]}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",",":"))

def inspect(data: dict[str, Any], references: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    scenes=[scene for scene in data.get("scenes",[]) if isinstance(scene,dict)]; fps=[fingerprint(scene) for scene in scenes]; findings=[]
    for index in range(1,len(fps)):
        if fps[index] == fps[index-1]: findings.append({"rule":"adjacent-identical","scenes":[scenes[index-1].get("id"),scenes[index].get("id")],"features":json.loads(fps[index])})
    groups: dict[str,list[str]]={}
    for scene, value in zip(scenes,fps): groups.setdefault(value,[]).append(str(scene.get("id")))
    for value, ids in groups.items():
        if len(ids)>=3: findings.append({"rule":"intra-video-reuse","scenes":ids,"features":json.loads(value)})
    cross=[]
    for ref_index, reference in enumerate(references or []):
        ref_values={fingerprint(scene) for scene in reference.get("scenes",[]) if isinstance(scene,dict)}
        matches=[scenes[i].get("id") for i,value in enumerate(fps) if value in ref_values]
        if matches: cross.append({"reference":ref_index,"scenes":matches})
    return {"ruleVersion":RULE_VERSION,"findings":findings,"crossWork":{"status":"checked" if references is not None else "skipped","reason":None if references is not None else "未显式提供参考分镜集合","matches":cross}}

def load_references(paths: list[str]) -> list[dict[str, Any]]:
    return [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]
