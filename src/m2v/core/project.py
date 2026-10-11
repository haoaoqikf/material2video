"""Versioned project manifests and content-addressed preparation records."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any

from .errors import M2VError

PROJECT_FILE = "project.json"
PROJECT_VERSION = 1
PREPARED_FILE = "outputs/prepared.json"
_TYPES = {"article-narrative", "financial-timeseries", "general"}


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_project(directory: str | Path) -> tuple[Path, dict[str, Any]]:
    root = Path(directory).expanduser().resolve()
    path = root / PROJECT_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M2VError(f"无法读取作品描述 {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schemaVersion") != PROJECT_VERSION:
        raise M2VError("project.json schemaVersion 必须为 1")
    if data.get("type") not in _TYPES:
        raise M2VError(f"未知视频类型：{data.get('type')!r}；可用类型：{', '.join(sorted(_TYPES))}")
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
    return root, data


def create_project(directory: str | Path, video_type: str) -> Path:
    if video_type not in _TYPES:
        raise M2VError(f"未知视频类型：{video_type}")
    root = Path(directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / PROJECT_FILE
    if path.exists():
        raise M2VError(f"作品描述已存在，未覆盖：{path}")
    defaults = {
        "article-narrative": {"storyboard": "storyboard.json"},
        "financial-timeseries": {"request": "request.json", "prices": "prices.json", "plan": "animation-plan.json"},
        "general": {"plan": "general-plan.json"},
    }
    slug = re.sub(r"[^a-z0-9-]+", "-", root.name.lower()).strip("-") or "video"
    # Keep a readable prefix while giving same-named works independent stable IDs.
    project_id = f"{slug[:50].rstrip('-') or 'video'}-{uuid.uuid4().hex[:8]}"
    _write_json(path, {"schemaVersion": PROJECT_VERSION, "id": project_id, "type": video_type,
                       "materials": defaults[video_type], "output": {"width": 1080, "height": 1920, "fps": 30, "audio": "optional"}})
    return path


def save_prepared(root: Path, *, project: dict[str, Any], composition_id: str,
                  props: dict[str, Any], width: int, height: int, fps: int,
                  duration_in_frames: int, inputs: dict[str, str], audio: dict[str, Any] | None = None,
                  subtitles: list[dict[str, Any]] | None = None, dependencies: list[dict[str, str]] | None = None) -> dict[str, Any]:
    material_hash = _fingerprint({"project": project, "inputs": inputs})
    prepared = {"contractVersion": 1, "projectId": project["id"], "type": project["type"],
                "compositionId": composition_id, "props": props, "width": width, "height": height,
                "fps": fps, "durationInFrames": duration_in_frames, "inputs": inputs,
                "materialFingerprint": material_hash, "audio": audio or {},
                "subtitles": subtitles or [], "dependencies": dependencies or []}
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
    for name, reference in project["materials"].items():
        file = (root / reference).resolve()
        if not file.is_file():
            raise M2VError(f"作品材料不存在：{name}={file}")
        if prepared.get("inputs", {}).get(name) != hashlib.sha256(file.read_bytes()).hexdigest():
            raise M2VError(f"作品材料已变化：{name}；请重新 prepare")
    for dependency in prepared.get("dependencies", []):
        dependency_root = (root / dependency["path"]).resolve()
        child_root, child_project = load_project(dependency_root)
        child = load_current_prepared(child_root, child_project)
        if child["preparedFingerprint"] != dependency["preparedFingerprint"]:
            raise M2VError(f"嵌入作品已重新准备：{dependency_root}；请重新 prepare 当前作品")
    return prepared


def file_inputs(root: Path, project: dict[str, Any]) -> dict[str, str]:
    inputs = {}
    for name, reference in project["materials"].items():
        file = (root / reference).resolve()
        if not file.is_file():
            raise M2VError(f"作品材料不存在：{name}={file}")
        inputs[name] = hashlib.sha256(file.read_bytes()).hexdigest()
    return inputs
