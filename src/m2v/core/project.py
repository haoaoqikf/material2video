"""Versioned project manifests and content-addressed preparation records."""
from __future__ import annotations

from m2v.core.video_config import FPS

import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import M2VError

PROJECT_FILE = "project.json"
PROJECT_VERSION = 1
PREPARED_FILE = "outputs/prepared.json"


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_project(directory: str | Path) -> tuple[Path, dict[str, Any]]:
    """读取作品描述。

    这里**不判定类型是否可用**：类型清单的唯一来源是 ``m2v.types.catalog``，
    而底层不能反向依赖业务类型层。类型名是否为已知类型、是否有行为实现，
    由统一入口经 ``m2v.types.registry`` 判定，同样在渲染前失败。
    """
    root = Path(directory).expanduser().resolve()
    path = root / PROJECT_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M2VError(f"无法读取作品描述 {path}: {exc}") from exc
    if isinstance(data, dict) and "productionProfile" in data:
        raise M2VError("productionProfile 制作档位已移除；请删除并重新 prepare")
    if not isinstance(data, dict) or data.get("schemaVersion") != PROJECT_VERSION:
        raise M2VError("project.json schemaVersion 必须为 1")
    if not isinstance(data.get("type"), str) or not data["type"].strip():
        raise M2VError("project.json 必须声明非空的视频类型 type")
    if not isinstance(data.get("id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", data["id"]):
        raise M2VError("作品 id 必须为 1 至 63 位小写字母、数字或连字符")
    materials = data.get("materials")
    if not isinstance(materials, dict) or not materials or any(not isinstance(v, str) or not v for v in materials.values()):
        raise M2VError("materials 必须是非空的命名相对路径对象")
    for name, reference in materials.items():
        candidate = (root / reference).resolve()
        if candidate != root and root not in candidate.parents:
            raise M2VError(f"材料 {name} 越过作品目录：{reference}")
    output = data.get("output", {})
    if not isinstance(output, dict):
        raise M2VError("output 必须为对象")
    for field in ("width", "height", "fps"):
        if field in output and (type(output[field]) is not int or output[field] < 1):
            raise M2VError(f"output.{field} 必须是正整数")
    if output.get("fps", FPS) != FPS:
        raise M2VError(f"output.fps 必须为 {FPS}；旧帧率材料请重新编排")
    return root, data


def create_project(directory: str | Path, video_type: str, materials: Mapping[str, str]) -> Path:
    """创建作品描述。

    材料入口由调用方（统一入口，取自类型目录）传入。作品契约此前自带一份类型
    白名单与材料映射，那是同一份事实的第二处副本；现在它只要求调用方把材料说清楚。
    """
    if not isinstance(video_type, str) or not video_type.strip():
        raise M2VError("作品类型必须是非空字符串")
    if not isinstance(materials, Mapping) or not materials:
        raise M2VError("作品材料入口必须是非空映射")
    for name, reference in materials.items():
        if not isinstance(name, str) or not name or not isinstance(reference, str) or not reference:
            raise M2VError("作品材料入口必须是「材料名 → 非空相对路径」的映射")
    root = Path(directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / PROJECT_FILE
    if path.exists():
        raise M2VError(f"作品描述已存在，未覆盖：{path}")
    slug = re.sub(r"[^a-z0-9-]+", "-", root.name.lower()).strip("-") or "video"
    # Keep a readable prefix while giving same-named works independent stable IDs.
    project_id = f"{slug[:50].rstrip('-') or 'video'}-{uuid.uuid4().hex[:8]}"
    _write_json(path, {"schemaVersion": PROJECT_VERSION, "id": project_id, "type": video_type,
                       "materials": dict(materials), "output": {"width": 1080, "height": 1920, "fps": FPS, "audio": "optional"}})
    return path


def save_prepared(root: Path, *, project: dict[str, Any], composition_id: str,
                  props: dict[str, Any], width: int, height: int, fps: int,
                  duration_in_frames: int, inputs: dict[str, str], audio: dict[str, Any] | None = None,
                  subtitles: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    material_hash = _fingerprint({"project": project, "inputs": inputs})
    prepared = {"contractVersion": 1, "projectId": project["id"], "type": project["type"],
                "compositionId": composition_id, "props": props, "width": width, "height": height,
                "fps": fps, "durationInFrames": duration_in_frames, "inputs": inputs,
                "materialFingerprint": material_hash, "audio": audio or {},
                "subtitles": subtitles or []}
    prepared["preparedFingerprint"] = _fingerprint(prepared)
    _write_json(root / PREPARED_FILE, prepared)
    return prepared


def load_current_prepared(root: Path, project: dict[str, Any]) -> dict[str, Any]:
    path = root / PREPARED_FILE
    try:
        prepared = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M2VError(f"缺少有效准备记录；请先执行 m2v prepare：{exc}") from exc
    expected = prepared.pop("preparedFingerprint", None)
    if not isinstance(expected, str) or _fingerprint(prepared) != expected:
        raise M2VError("准备记录损坏或被修改；请重新 prepare")
    prepared["preparedFingerprint"] = expected
    if prepared.get("projectId") != project["id"] or prepared.get("type") != project["type"]:
        raise M2VError("准备记录与当前作品不匹配；请重新 prepare")
    if prepared.get("fps") != FPS:
        raise M2VError(f"旧帧率准备记录不能用于 {FPS} fps；请重新 prepare")
    for name, reference in project["materials"].items():
        file = (root / reference).resolve()
        if not file.is_file():
            raise M2VError(f"作品材料不存在：{name}={file}")
        if prepared.get("inputs", {}).get(name) != hashlib.sha256(file.read_bytes()).hexdigest():
            raise M2VError(f"作品材料已变化：{name}；请重新 prepare")
    # 显式引用的附属输入也属于版本绑定：源文、图片、语义审查及准备音轨。
    for name, digest in prepared.get("inputs", {}).items():
        if not name.startswith("file:"):
            continue
        file = (root / name[5:]).resolve()
        if (not file.is_relative_to(root.resolve()) or not file.is_file()
                or hashlib.sha256(file.read_bytes()).hexdigest() != digest):
            raise M2VError(f"准备引用文件已变化或缺失：{name[5:]}；请重新 prepare 并评审")
    # project 包含音色等作品属性；仅检查材料文件无法发现这些配置变化。
    if prepared.get("materialFingerprint") != _fingerprint({"project": project, "inputs": prepared["inputs"]}):
        raise M2VError("作品描述已变化；请重新 prepare 并生成当前候选")
    return prepared


def file_inputs(root: Path, project: dict[str, Any]) -> dict[str, str]:
    inputs = {}
    for name, reference in project["materials"].items():
        file = (root / reference).resolve()
        if not file.is_file():
            raise M2VError(f"作品材料不存在：{name}={file}")
        inputs[name] = hashlib.sha256(file.read_bytes()).hexdigest()
    return inputs
