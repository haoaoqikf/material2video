"""Versioned project manifests and content-addressed preparation records."""
from __future__ import annotations

from m2v.core.video_config import project_fps, validate_fps

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import M2VError

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
        raise M2VError("output 必须为对象")
    if "subtitle" not in output:
        return None
    subtitle = output["subtitle"]
    if not isinstance(subtitle, dict):
        raise M2VError("output.subtitle 必须为仅含 fontSize 的对象")
    unknown = sorted(set(subtitle) - {"fontSize"})
    if unknown:
        raise M2VError(f"output.subtitle 含未知字段：{'、'.join(unknown)}")
    size = subtitle.get("fontSize")
    if type(size) is not int or not 24 <= size <= 56:
        raise M2VError("output.subtitle.fontSize 必须为 24 至 56 的整数")
    return size


def _local_reference(root: Path, reference: str) -> Path:
    if (not isinstance(reference, str) or not reference or '\0' in reference
            or Path(reference).anchor or ':' in reference or '\\' in reference
            or '..' in Path(reference).parts):
        raise M2VError('作品文件必须为目录内相对路径，不能越过作品目录')
    path = (root / reference).resolve()
    if not path.is_relative_to(root.resolve()):
        raise M2VError('作品文件链接越过作品目录')
    return path


def load_project(directory: str | Path) -> tuple[Path, dict[str, Any]]:
    """读取作品描述。

    类型身份取自唯一类型目录；可选制作工具委托作品自己的执行入口。
    """
    root = Path(directory).expanduser().resolve()
    path = root / PROJECT_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M2VError(f"无法读取作品描述 {path}: {exc}") from exc
    if isinstance(data, dict) and "productionProfile" in data:
        raise M2VError("productionProfile 制作档位已移除；请删除并重新 prepare")
    if (not isinstance(data, dict) or type(data.get("schemaVersion")) is not int
            or data["schemaVersion"] != PROJECT_VERSION):
        raise M2VError("project.json schemaVersion 必须为 3；旧作品须重新编排")
    if "style" in data:
        raise M2VError("project.style 已移除；请用新版场景组件重新编排")
    if "category" in data:
        raise M2VError("project.category 类别层已移除；请只保留三类 type")
    if not isinstance(data.get("type"), str) or not data["type"].strip():
        raise M2VError("project.json 必须声明非空的视频类型 type")
    from m2v.type_system.catalog import catalog
    if not catalog().has(data["type"]):
        raise M2VError(f"未知视频类型：{data['type']}；运行 m2v types 查看三类视频")
    if not isinstance(data.get("id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", data["id"]):
        raise M2VError("作品 id 必须为 1 至 63 位小写字母、数字或连字符")
    materials = data.get("materials")
    if not isinstance(materials, dict) or set(materials) != {"storyboard"} or not isinstance(materials["storyboard"], str) or not materials["storyboard"]:
        raise M2VError("materials 仅允许 storyboard 本地分镜入口")
    for name, reference in materials.items():
        _local_reference(root, reference)
    output = data.get("output", {})
    if not isinstance(output, dict):
        raise M2VError("output 必须为对象")
    subtitle_font_size(data)
    for field in ("width", "height", "fps"):
        if field in output and (type(output[field]) is not int or output[field] < 1):
            raise M2VError(f"output.{field} 必须是正整数")
    if "fps" in output:
        validate_fps(output["fps"], "output.fps")
    from m2v.standalone.protocol import command
    command(root, data)
    return root, data


def create_project(directory: str | Path, video_type: str, materials: Mapping[str, str], *,
                   output: Mapping[str, Any] | None = None) -> Path:
    """生成完整独立工程；材料映射仍从类型目录核对，拒绝部分旧工程。"""
    from m2v.type_system.catalog import catalog
    from m2v.standalone.scaffold import create
    if dict(materials) != catalog().get(video_type).material_map():
        raise M2VError('作品材料入口必须使用当前类型的storyboard')
    return create(directory, video_type, output=dict(output or {}))


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
        raise M2VError(f"缺少有效准备记录；请先执行 m2v prepare：{exc}") from exc
    if not isinstance(prepared, dict) or not isinstance(prepared.get("inputs"), dict):
        raise M2VError("准备记录结构损坏；请重新prepare")
    if (any(not isinstance(k, str) or not k or not isinstance(v, str)
            for k, v in prepared['inputs'].items())
            or not isinstance(prepared.get('compositionId'), str)
            or not prepared['compositionId']
            or not isinstance(prepared.get('props'), dict)
            or not isinstance(prepared.get('audio'), dict)
            or not isinstance(prepared.get('subtitles'), list)
            or any(type(prepared.get(k)) is not int or prepared[k] <= 0
                   for k in ('width', 'height', 'fps', 'durationInFrames'))):
        raise M2VError('准备记录字段类型或画幅／时长无效；请重新prepare')
    expected = prepared.pop("preparedFingerprint", None)
    try:
        actual = _fingerprint(prepared)
    except (ValueError, TypeError) as exc:
        raise M2VError('准备记录包含无效JSON数值') from exc
    if not isinstance(expected, str) or actual != expected:
        raise M2VError("准备记录损坏或被修改；请重新 prepare")
    prepared["preparedFingerprint"] = expected
    if type(prepared.get("contractVersion")) is not int or prepared["contractVersion"] != 3 or "style" in prepared:
        raise M2VError("旧准备记录不能用于三类视频；请重新 prepare")
    if prepared.get("projectId") != project["id"] or prepared.get("type") != project["type"]:
        raise M2VError("准备记录与当前作品不匹配；请重新 prepare")
    expected_fps = project_fps(root, project)
    if type(prepared.get("fps")) is not int or prepared["fps"] != expected_fps:
        raise M2VError(f"准备记录帧率与当前 {expected_fps} fps 不匹配；请重新 prepare")
    for name, reference in project["materials"].items():
        file = _local_reference(root, reference)
        if not file.is_file():
            raise M2VError(f"作品材料不存在：{name}={file}")
        if prepared.get("inputs", {}).get(name) != hashlib.sha256(file.read_bytes()).hexdigest():
            raise M2VError(f"作品材料已变化：{name}；请重新 prepare")
    # 显式引用的附属输入也属于版本绑定：源文、图片、语义审查及准备音轨。
    for name, digest in prepared.get("inputs", {}).items():
        # 可选登记表的「尚不存在」也是输入状态；首次导入不能复用旧的无登记准备。
        if name.startswith("absent-file:"):
            file = _local_reference(root, name[len('absent-file:'):])
            if not file.is_relative_to(root.resolve()) or file.exists():
                raise M2VError(f"准备引用文件已变化：{name}；请重新 prepare")
            continue
        if not name.startswith("file:"):
            continue
        file = _local_reference(root, name[5:])
        if (not file.is_relative_to(root.resolve()) or not file.is_file()
                or hashlib.sha256(file.read_bytes()).hexdigest() != digest):
            raise M2VError(f"准备引用文件已变化或缺失：{name[5:]}；请重新 prepare 并评审")
    # project 包含音色等作品属性；仅检查材料文件无法发现这些配置变化。
    if prepared.get("materialFingerprint") != _fingerprint({"project": project, "inputs": prepared["inputs"]}):
        raise M2VError("作品描述已变化；请重新 prepare 并生成当前候选")
    if load_project(root)[1] != project:
        raise M2VError('执行期间磁盘作品描述已变化；请重新prepare')
    return prepared


def file_inputs(root: Path, project: dict[str, Any]) -> dict[str, str]:
    inputs = {}
    for name, reference in project["materials"].items():
        file = _local_reference(root, reference)
        if not file.is_file():
            raise M2VError(f"作品材料不存在：{name}={file}")
        inputs[name] = hashlib.sha256(file.read_bytes()).hexdigest()
    return inputs
