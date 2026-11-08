"""Versioned project manifests and content-addressed preparation records."""
from __future__ import annotations

from film_runtime.core.video_config import default_fps, project_fps, validate_fps

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .errors import VideoError

PROJECT_FILE = "project.json"
PROJECT_VERSION = 3
PREPARED_FILE = "outputs/prepared.json"


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def subtitle_font_size(project: dict[str, Any]) -> int | None:
    """校验作品级字幕覆盖；省略时由画幅清单提供完整默认样式。"""
    output = project.get("output", {})
    if not isinstance(output, dict):
        raise VideoError("output 必须为对象")
    if "subtitle" not in output:
        return None
    subtitle = output["subtitle"]
    if not isinstance(subtitle, dict):
        raise VideoError("output.subtitle 必须为仅含 fontSize 的对象")
    unknown = sorted(set(subtitle) - {"fontSize"})
    if unknown:
        raise VideoError(f"output.subtitle 含未知字段：{'、'.join(unknown)}")
    size = subtitle.get("fontSize")
    if type(size) is not int or not 24 <= size <= 56:
        raise VideoError("output.subtitle.fontSize 必须为 24 至 56 的整数")
    return size


def load_project(directory: str | Path) -> tuple[Path, dict[str, Any]]:
    """读取作品描述。

    类型身份来自作品自身保存的目录；可选执行协议只声明本地入口。
    """
    root = Path(directory).expanduser().resolve()
    path = root / PROJECT_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VideoError(f"无法读取作品描述 {path}: {exc}") from exc
    if isinstance(data, dict) and "productionProfile" in data:
        raise VideoError("productionProfile 制作档位已移除；请删除并重新 prepare")
    if (not isinstance(data, dict) or type(data.get("schemaVersion")) is not int
            or data["schemaVersion"] != PROJECT_VERSION):
        raise VideoError("project.json schemaVersion 必须为 3；旧作品须重新编排")
    if "style" in data:
        raise VideoError("project.style 已移除；请用新版场景组件重新编排")
    if "category" in data:
        raise VideoError("project.category 类别层已移除；请只保留五类 type")
    if not isinstance(data.get("type"), str) or not data["type"].strip():
        raise VideoError("project.json 必须声明非空的视频类型 type")
    from film_runtime.catalog import catalog
    if not catalog().has(data["type"]):
        raise VideoError(f"未知视频类型：{data['type']}；查看本作品video-types.json中的类型身份")
    if not isinstance(data.get("id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", data["id"]):
        raise VideoError("作品 id 必须为 1 至 63 位小写字母、数字或连字符")
    materials = data.get("materials")
    if not isinstance(materials, dict) or set(materials) != {"storyboard"} or not isinstance(materials["storyboard"], str) or not materials["storyboard"]:
        raise VideoError("materials 仅允许 storyboard 本地分镜入口")
    for name, reference in materials.items():
        candidate = (root / reference).resolve()
        if candidate != root and root not in candidate.parents:
            raise VideoError(f"材料 {name} 越过作品目录：{reference}")
    output = data.get("output", {})
    if not isinstance(output, dict):
        raise VideoError("output 必须为对象")
    subtitle_font_size(data)
    for field in ("width", "height", "fps"):
        if field in output and (type(output[field]) is not int or output[field] < 1):
            raise VideoError(f"output.{field} 必须是正整数")
    if "fps" in output:
        validate_fps(output["fps"], "output.fps")
    from .execution import command
    command(root, data)
    return root, data


def save_prepared(root: Path, *, project: dict[str, Any], composition_id: str,
                  props: dict[str, Any], width: int, height: int, fps: int,
                  duration_in_frames: int, inputs: dict[str, str], audio: dict[str, Any] | None = None,
                  subtitles: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    material_hash = _fingerprint({"project": project, "inputs": inputs})
    prepared = {"contractVersion": 3, "projectId": project["id"], "type": project["type"],
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
        raise VideoError(f"缺少有效准备记录；请先执行 pnpm run video:prepare：{exc}") from exc
    expected = prepared.pop("preparedFingerprint", None)
    if not isinstance(expected, str) or _fingerprint(prepared) != expected:
        raise VideoError("准备记录损坏或被修改；请重新 prepare")
    prepared["preparedFingerprint"] = expected
    if prepared.get("contractVersion") != 3 or "style" in prepared:
        raise VideoError("旧准备记录不能用于五类视频；请重新 prepare")
    if prepared.get("projectId") != project["id"] or prepared.get("type") != project["type"]:
        raise VideoError("准备记录与当前作品不匹配；请重新 prepare")
    expected_fps = project_fps(root, project)
    if type(prepared.get("fps")) is not int or prepared["fps"] != expected_fps:
        raise VideoError(f"准备记录帧率与当前 {expected_fps} fps 不匹配；请重新 prepare")
    for name, reference in project["materials"].items():
        file = (root / reference).resolve()
        if not file.is_file():
            raise VideoError(f"作品材料不存在：{name}={file}")
        if prepared.get("inputs", {}).get(name) != hashlib.sha256(file.read_bytes()).hexdigest():
            raise VideoError(f"作品材料已变化：{name}；请重新 prepare")
    # 显式引用的附属输入也属于版本绑定：源文、图片、语义审查及准备音轨。
    for name, digest in prepared.get("inputs", {}).items():
        # 可选登记表的「尚不存在」也是输入状态；首次导入不能复用旧的无登记准备。
        if name.startswith("absent-file:"):
            file = (root / name[len("absent-file:"):]).resolve()
            if not file.is_relative_to(root.resolve()) or file.exists():
                raise VideoError(f"准备引用文件已变化：{name}；请重新 prepare")
            continue
        if not name.startswith("file:"):
            continue
        file = (root / name[5:]).resolve()
        if (not file.is_relative_to(root.resolve()) or not file.is_file()
                or hashlib.sha256(file.read_bytes()).hexdigest() != digest):
            raise VideoError(f"准备引用文件已变化或缺失：{name[5:]}；请重新 prepare 并评审")
    # project 包含音色等作品属性；仅检查材料文件无法发现这些配置变化。
    if prepared.get("materialFingerprint") != _fingerprint({"project": project, "inputs": prepared["inputs"]}):
        raise VideoError("作品描述已变化；请重新 prepare 并生成当前候选")
    return prepared


def file_inputs(root: Path, project: dict[str, Any]) -> dict[str, str]:
    inputs = {}
    for name, reference in project["materials"].items():
        file = (root / reference).resolve()
        if not file.is_file():
            raise VideoError(f"作品材料不存在：{name}={file}")
        inputs[name] = hashlib.sha256(file.read_bytes()).hexdigest()
    return inputs
