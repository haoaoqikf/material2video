"""统一分镜的结构化来源：先验证文件边界，再复用已有计算与几何。"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from m2v.core.errors import M2VError

_ID = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
_ROLES = {
    "financial-series": {"request", "prices", "plan"},
    "construction": {"building", "construction", "assets"},
    "vehicle-model": {"showcase", "assets"},
}
_TYPES = {"financial-series": "data-evolution", "construction": "spatial-3d",
          "vehicle-model": "spatial-3d"}


def _local_file(root: Path, reference: str, *, allow_missing: bool = False) -> Path:
    if not isinstance(reference, str) or not reference or "\\" in reference:
        raise M2VError(f"结构化来源文件路径无效：{reference!r}")
    relative = Path(reference)
    path = (root / relative).resolve()
    if (relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(root.resolve())
            or (not allow_missing and not path.is_file())):
        raise M2VError(f"结构化来源文件缺失或越界：{reference}")
    return path


def validate(root: Path, storyboard: dict, video_type: str, *, allow_missing_financial_plan: bool = False) -> dict[str, dict]:
    declared = storyboard.get("sources", {})
    if not isinstance(declared, dict):
        raise M2VError("storyboard.sources 必须为 ID 到来源的对象")
    for identity, source in declared.items():
        if not isinstance(identity, str) or not _ID.fullmatch(identity):
            raise M2VError(f"结构化来源 ID 无效：{identity!r}")
        if not isinstance(source, dict) or set(source) != {"kind", "files"}:
            raise M2VError(f"结构化来源 {identity} 只允许 kind、files")
        kind = source["kind"]
        if kind not in _ROLES or _TYPES[kind] != video_type:
            raise M2VError(f"结构化来源 {identity} 的种类 {kind!r} 不适用于 {video_type}")
        files = source["files"]
        if not isinstance(files, dict) or set(files) != _ROLES[kind]:
            raise M2VError(f"结构化来源 {identity} 的 files 必须含：{'、'.join(sorted(_ROLES[kind]))}")
        for role, reference in files.items():
            _local_file(root, reference, allow_missing=allow_missing_financial_plan and kind == "financial-series" and role == "plan")
    for scene in storyboard["scenes"]:
        ids = scene["content"].get("sourceIds", [])
        if (not isinstance(ids, list) or any(not isinstance(x, str) or x not in declared for x in ids)
                or len(ids) != len(set(ids))):
            raise M2VError(f"场景 {scene['id']} 的 content.sourceIds 必须为已声明且不重复的来源 ID")
    return declared


def prepare(root: Path, storyboard: dict, video_type: str) -> tuple[dict[str, Any], dict[str, str]]:
    declared = validate(root, storyboard, video_type)
    resolved: dict[str, Any] = {}
    inputs: dict[str, str] = {}
    for identity, source in declared.items():
        files = source["files"]
        for reference in files.values():
            path = _local_file(root, reference)
            inputs["file:" + path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        kind = source["kind"]
        if kind == "financial-series":
            from m2v.types.financial import materials as financial
            docs = financial.load_project(root, files=files)
            payload = financial.build_render_props(docs)
            prices = docs["prices"]
            nested = [*prices.get("rawSnapshots", []),
                      *((prices.get("fx") or {}).get("rawSnapshots", []))]
            extra = [item["path"] for item in nested]
        elif kind == "construction":
            from m2v.types.building_construction import materials as building
            docs = building.load_project(root, files=files)
            payload = building.build_render_props(docs)
            extra = [item["path"] for item in docs["assets"]["assets"]]
        else:
            from m2v.types.vehicle_showcase import materials as vehicle
            docs = vehicle.load_project(root, files=files)
            payload = vehicle.build_render_props(docs)
            extra = [item["path"] for item in docs["manifest"]["assets"]]
        for reference in extra:
            path = _local_file(root, reference)
            inputs["file:" + path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        resolved[identity] = {"kind": kind, "data": payload}
        inputs["source:" + identity] = hashlib.sha256(
            json.dumps(resolved[identity], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    return resolved, inputs
