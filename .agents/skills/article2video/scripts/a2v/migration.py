"""旧整页组件分镜到 v2 场景树的显式单文件迁移。"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from typing import Any

LEGACY_DEFAULTS = {"title":"balance","quote":"gap","comparison":"versus","list":"iceberg","diagram":"loop","timeline":"stairs","conclusion":"exchange","number":"number","chart":"chart"}
DIRECT = {"number", "chart", "flow"}

def _content_nodes(data: dict[str, Any], schematic: bool) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for key, role in (("title","title"),("text","headline"),("subtitle","body"),("left","headline"),("right","headline"),("value","hero"),("label","label"),("caption","caption"),("action","title"),("items","body"),("nodes","body"),("values","body")):
        if key not in data:
            continue
        node_type = "number" if key == "value" else "chart" if key == "values" else "text"
        node: dict[str, Any] = {"id": f"content-{key}", "type": node_type, "contentRef": f"data.{key}"}
        # role 只对 text/number 注册；chart 没有这个属性
        if node_type != "chart":
            node["role"] = role
        else:
            node["chart"] = data.get("chart", "bar")
        if schematic and node_type in {"number", "chart"}: node["schematic"] = True
        nodes.append(node)
    return nodes or [{"id":"content-fallback","type":"text","contentRef":"data.text","role":"body"}]

def migrate_document(source: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if source.get("version") != 1:
        raise ValueError("迁移输入必须是 version=1 的旧分镜")
    result = copy.deepcopy(source); result["version"] = 2; result["schemaVersion"] = 2
    result["visualDirection"] = {"motif":"legacy-migration","compositionBias":"mixed","density":"balanced","rhythm":"steady","avoid":["repeated-center"]}
    report: dict[str, Any] = {"sourceVersion":1,"targetVersion":2,"pixelEquivalent":False,"accepted":False,"scenes":[]}
    compositions = ["offset", "split", "radial", "center", "full"]
    for index, scene in enumerate(result.get("scenes", [])):
        data = scene.setdefault("data", {}); figure = data.pop("figure", {}) if isinstance(data, dict) else {}
        kind = figure.get("kind") if isinstance(figure, dict) else None; kind = kind or LEGACY_DEFAULTS.get(scene.get("type"), "unknown")
        schematic = isinstance(figure, dict) and figure.get("schematic") is True
        children = _content_nodes(data, schematic)
        layout = "split" if len(children) == 2 else "radial" if kind in {"loop","flow"} and len(children) > 1 else "stack"
        scene["visualIntent"] = {"relation":"contrast" if kind in {"balance","gap","versus"} else "sequence" if kind in {"stairs","flow"} else "cycle" if kind == "loop" else "focus", "focus":"chart" if kind == "chart" else "number" if kind == "number" else "text", "composition":compositions[index % len(compositions)], "density":"balanced", "tone":"neutral"}
        scene["sceneTree"] = {"id":"root","type":layout,"children":children}
        scene["motions"] = [{"target":node["id"],"recipe":"count" if node["type"] == "number" else "reveal","startFrame":min(12 + i * 8, max(0, scene.get("durationInFrames", 30) - 24)),"durationFrames":min(24, scene.get("durationInFrames", 30))} for i, node in enumerate(children)]
        if isinstance(scene.get("visual"), dict): scene["visual"].pop("layout", None)
        report["scenes"].append({"id":scene.get("id"),"legacyKind":kind,"mapping":"direct" if kind in DIRECT else "semantic-fallback","manualReview":kind not in DIRECT,"preservedFields":["id","type","durationInFrames","narration","data"]})
    return result, report

def migrate_file(source: Path, output: Path, *, force: bool = False) -> Path:
    if output.exists() and not force: raise FileExistsError(f"目标已存在：{output}")
    if source.resolve() == output.resolve(): raise ValueError("迁移输出不能覆盖输入；请指定新的输出路径")
    data = json.loads(source.read_text(encoding="utf-8")); migrated, report = migrate_document(data)
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = output.with_suffix(".migration.json"); report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path
