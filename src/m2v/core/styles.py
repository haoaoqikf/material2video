"""可选风格包：唯一清单解释器，绑定准备依赖并为场景提供受限入口。"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .assets import REPOSITORY_ROOT
from .errors import M2VError

STYLES_ROOT = REPOSITORY_ROOT / "styles"
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")
_VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".woff2", ".ttf", ".otf"}


def _json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"不允许非有限数值：{value}")
    def unique_object(pairs: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"重复 JSON 字段：{key}")
            result[key] = value
        return result
    try:
        value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant, object_pairs_hook=unique_object)
        json.dumps(value, allow_nan=False)
        return value
    except (OSError, UnicodeError, ValueError) as exc:
        raise M2VError(f"风格 JSON 无效：{path}: {exc}") from exc


def _file(root: Path, value: Any) -> Path:
    if (not isinstance(value, str) or not value or "\\" in value
            or Path(value).is_absolute() or ".." in Path(value).parts):
        raise M2VError(f"风格入口必须是包内相对路径：{value!r}")
    target = (root / value).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        if Path(value).suffix in {".ttf", ".otf", ".woff2"}:
            raise M2VError(f"风格字体缺失或越界：{value}；请运行 uv run python fonts/fetch.py 恢复")
        raise M2VError(f"风格入口缺失或越界：{value}")
    return target


def load_style(style_id: str) -> dict:
    if not isinstance(style_id, str) or not _ID.fullmatch(style_id):
        raise M2VError("风格 id 必须是 1 至 63 位小写字母、数字或连字符")
    base = STYLES_ROOT.resolve()
    root = (base / style_id).resolve()
    if root.parent != base or not (root / "style.json").is_file():
        raise M2VError(f"未知风格或风格目录越界：{style_id}")
    manifest = _json(_file(root, "style.json"))
    allowed = {"schemaVersion", "id", "version", "description", "types", "frames", "guide", "tokens", "components", "assets", "requires"}
    if (not isinstance(manifest, dict) or set(manifest) - allowed
            or type(manifest.get("schemaVersion")) is not int or manifest["schemaVersion"] != 1
            or manifest.get("id") != style_id):
        raise M2VError(f"风格 {style_id} 清单字段、schemaVersion 或 id 无效")
    if not isinstance(manifest.get("version"), str) or not _VERSION.fullmatch(manifest["version"]):
        raise M2VError(f"风格 {style_id} version 必须是 major.minor.patch")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        raise M2VError(f"风格 {style_id} 必须有非空 description")
    types, frames = manifest.get("types"), manifest.get("frames")
    if (not isinstance(types, list) or not types
            or any(not isinstance(item, str) or not _ID.fullmatch(item) for item in types)
            or len(set(types)) != len(types)):
        raise M2VError(f"风格 {style_id} types 必须是非空且不重复的类型名列表")
    if (not isinstance(frames, list) or not frames
            or any(not isinstance(item, dict) or set(item) != {"width", "height"}
                   or any(type(item[k]) is not int or item[k] < 1 for k in ("width", "height")) for item in frames)
            or len({(item['width'], item['height']) for item in frames}) != len(frames)):
        raise M2VError(f"风格 {style_id} frames 必须是非空且不重复的宽高对象列表")
    guide = _file(root, manifest.get("guide"))
    if guide.suffix != ".md" or not guide.read_text(encoding="utf-8").strip():
        raise M2VError(f"风格 {style_id} guide 必须是非空 Markdown")
    requires = manifest.get("requires", {})
    if (not isinstance(requires, dict) or set(requires) - {"narration"}
            or requires.get("narration", "any") not in ("none", "any")):
        raise M2VError(f"风格 {style_id} requires 只允许 narration 取 none/any")
    tokens = _json(_file(root, manifest["tokens"])) if "tokens" in manifest else {}
    if not isinstance(tokens, dict):
        raise M2VError(f"风格 {style_id} tokens 必须为 JSON 对象")
    components, assets = {}, {}
    for field, resolved in (("components", components), ("assets", assets)):
        entries = manifest.get(field, {})
        if not isinstance(entries, dict):
            raise M2VError(f"风格 {style_id} {field} 必须为命名对象")
        for name, entry in entries.items():
            if not _ID.fullmatch(name):
                raise M2VError(f"风格资源名无效：{name}")
            if field == "assets":
                if (not isinstance(entry, dict) or set(entry) != {"path", "source", "license"}
                        or any(not isinstance(entry[k], str) or not entry[k].strip() for k in entry)):
                    raise M2VError(f"风格资产 {name} 必须声明 path/source/license")
                entry = entry["path"]
            file = _file(root, entry)
            suffixes = {".tsx", ".ts", ".jsx", ".js"} if field == "components" else ASSET_SUFFIXES
            if file.suffix not in suffixes:
                raise M2VError(f"风格 {field} 不支持文件类型：{file.name}")
            resolved[name] = str(file)
    # 所有包文件纳入依赖，包括指导与尚未被组件引用的资源；禁止目录链接隐藏包外依赖。
    hashes = {}
    for file in sorted(root.rglob("*")):
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise M2VError(f"风格包不允许符号链接或越界文件：{file}")
        if file.is_file():
            hashes[file.relative_to(root).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    return {"manifest": manifest, "root": str(root), "guide": str(guide), "tokens": tokens,
            "components": components, "assets": assets,
            "identity": {"id": style_id, "version": manifest["version"], "fingerprint": digest}}


def list_styles() -> list[dict]:
    if not STYLES_ROOT.exists():
        return []
    result = []
    for entry in sorted(STYLES_ROOT.iterdir()):
        if entry.is_dir():
            package = load_style(entry.name)
            result.append({key: package["manifest"][key] for key in ("id", "version", "description", "types", "frames")})
    return result


def selected_style(project: dict, *, width: int | None = None, height: int | None = None) -> dict | None:
    if "style" not in project:
        return None
    selection = project["style"]
    if not isinstance(selection, dict) or set(selection) != {"id"}:
        raise M2VError("project.style 必须为仅包含 id 的对象")
    package = load_style(selection["id"])
    if project["type"] not in package["manifest"]["types"]:
        raise M2VError(f"风格 {selection['id']} 不支持视频类型 {project['type']}")
    if width is not None and height is not None and {"width": width, "height": height} not in package["manifest"]["frames"]:
        raise M2VError(f"风格 {selection['id']} 不支持画幅 {width}×{height}")
    return package


def check_requirements(package: dict | None, *, has_narration: bool) -> None:
    """作品级硬约束：类型与画幅之外，清单只能声明旁白要求。"""
    if package is None:
        return
    requires = package["manifest"].get("requires") or {}
    if requires.get("narration") == "none" and has_narration:
        raise M2VError(f"风格 {package['manifest']['id']} 要求无旁白作品；当前分镜包含旁白")
