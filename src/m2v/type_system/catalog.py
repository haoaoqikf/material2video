"""视频类型目录：类型身份、材料入口与文档文案的单一来源。

目录以同目录下的 ``catalog.json`` 为唯一真源。此前同一份事实散落在四处代码
（注册表、作品契约的类型白名单与材料映射、命令行的初始化模板）和三份文档里，
且没有任何一致性检查；现在统一入口、作品初始化与文档都从这里派生。

规范作品位置只有 ``videos/<type>/<slug>/``，目录只接受五个当前类型，
不解析类别或旧类型。

本模块负责读取与校验类型目录；五类行为由统一适配器提供。

目录是数据而不是行为，因此允许不方便放进数据里的东西（正则、类）留在这里，
但**任何一个类型的名称、说明、材料文件名或文档文案都不允许在本模块之外再写
一遍**——那正是这次要消除的重复。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from m2v.core.errors import M2VError
from m2v.core.video_config import default_fps

#: 随包分发的目录文件。
CATALOG_PATH = Path(__file__).with_name("catalog.json")

#: 目录结构版本。字段含义变化时必须递增，并同步校验规则。
SCHEMA_VERSION = 3
FIVE_TYPES = frozenset({"text-motion", "data-evolution", "principle-metaphor", "spatial-3d", "documentary-edit"})

#: 类型名与作品 id 同规则：小写字母、数字与连字符。
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

#: 材料文件名：单层文件名，不允许路径分隔符或上跳段。
_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.json$")

#: 登记项必须提供的非空文本字段：目录中的字段名 → 登记项的属性名。
_TEXT_FIELDS = {
    "description": "description",
    "summary": "summary",
    "plan": "plan",
    "skillGuide": "skill_guide",
}


@dataclass(frozen=True)
class Material:
    """一个类型的一份材料：契约内的名称、默认文件名与初始化内容。"""

    name: str
    file: str
    template: dict[str, Any]


@dataclass(frozen=True)
class Entry:
    """一个视频类型在目录中的全部登记信息（不含行为）。"""

    name: str
    description: str
    summary: str
    plan: str
    skill_guide: str
    materials: tuple[Material, ...]

    def material_map(self) -> dict[str, str]:
        """作品契约使用的「材料名 → 默认文件名」映射。"""
        return {material.name: material.file for material in self.materials}

    def workspace_parts(self) -> tuple[str, ...]:
        """作品在 ``videos/`` 下只按五类身份分层。"""
        return (self.name,)

    def initial_dimensions(self) -> dict[str, int]:
        """从渲染材料的显式画幅派生项目默认值，避免创建器另存一套尺寸。"""
        for material in self.materials:
            canvas = material.template.get("canvas", material.template)
            if isinstance(canvas, dict) and all(type(canvas.get(k)) is int and canvas[k] > 0
                                                for k in ("width", "height")):
                return {k: canvas[k] for k in ("width", "height")}
        return {}


class Catalog:
    """已校验的类型目录。构造一律通过 :func:`load`。"""

    def __init__(self, entries: tuple[Entry, ...]) -> None:
        self._entries = entries
        self._by_name = {entry.name: entry for entry in entries}

    def entries(self) -> tuple[Entry, ...]:
        """按目录中的登记顺序返回全部登记项（文档生成依赖这一顺序）。"""
        return self._entries

    def names(self) -> tuple[str, ...]:
        return tuple(entry.name for entry in self._entries)

    def has(self, name: str) -> bool:
        return name in self._by_name

    def get(self, name: str) -> Entry:
        """按名取登记项；未登记时给出可照做的登记指引。"""
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise M2VError(
                f"类型目录缺少登记项：{name}；可在 {CATALOG_PATH.name} 中登记该类型的"
                f"说明与材料入口（当前已登记：{'、'.join(self.names()) or '无'}）"
            ) from exc


def _require_text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise M2VError(f"类型目录 {where} 必须是非空字符串")
    return value


def _parse_material(raw: Any, type_name: str, index: int) -> Material:
    where = f"types[{type_name}].materials[{index}]"
    if not isinstance(raw, dict):
        raise M2VError(f"类型目录 {where} 必须是对象")
    name = _require_text(raw.get("name"), f"{where}.name")
    if not _NAME_RE.match(name):
        raise M2VError(f"类型目录 {where}.name 必须是 1 至 63 位小写字母、数字或连字符：{name!r}")
    file = _require_text(raw.get("file"), f"{where}.file")
    if not _FILE_RE.match(file) or "/" in file or "\\" in file or ".." in file:
        raise M2VError(f"类型目录 {where}.file 必须是作品根下的单个 JSON 文件名：{file!r}")
    template = raw.get("template")
    if not isinstance(template, dict) or not template:
        raise M2VError(f"类型目录 {where}.template 必须是非空对象")
    expected_fps = default_fps(type_name)
    if "fps" in template and (type(template["fps"]) is not int or template["fps"] != expected_fps):
        raise M2VError(f"类型目录 {where}.template.fps 必须为 {expected_fps}")
    return Material(name=name, file=file, template=template)


def _parse_entry(raw: Any, index: int, seen: set[str]) -> Entry:
    where = f"types[{index}]"
    if not isinstance(raw, dict):
        raise M2VError(f"类型目录 {where} 必须是对象")
    name = _require_text(raw.get("name"), f"{where}.name")
    if not _NAME_RE.match(name):
        raise M2VError(f"类型目录 {where}.name 必须是 1 至 63 位小写字母、数字或连字符：{name!r}")
    if name in seen:
        raise M2VError(f"类型目录重复登记类型：{name}")
    seen.add(name)
    if "category" in raw:
        raise M2VError(f"类型目录 types[{name}] 不再支持类别字段")
    texts = {
        attribute: _require_text(raw.get(field), f"types[{name}].{field}")
        for field, attribute in _TEXT_FIELDS.items()
    }
    raw_materials = raw.get("materials")
    if not isinstance(raw_materials, list) or not raw_materials:
        raise M2VError(f"类型目录 types[{name}].materials 必须是非空数组")
    materials = tuple(_parse_material(item, name, position) for position, item in enumerate(raw_materials))
    material_names = [material.name for material in materials]
    if len(set(material_names)) != len(material_names):
        raise M2VError(f"类型目录 types[{name}].materials 的材料名重复：{'、'.join(material_names)}")
    files = [material.file for material in materials]
    if len(set(files)) != len(files):
        raise M2VError(f"类型目录 types[{name}].materials 的文件名重复：{'、'.join(files)}")
    return Entry(name=name, materials=materials, **texts)


def _parse(data: Any) -> Catalog:
    if not isinstance(data, dict):
        raise M2VError(f"类型目录 {CATALOG_PATH.name} 顶层必须是对象")
    if data.get("schemaVersion") != SCHEMA_VERSION:
        raise M2VError(f"类型目录 schemaVersion 必须为 {SCHEMA_VERSION}")
    raw_types = data.get("types")
    if not isinstance(raw_types, list) or not raw_types:
        raise M2VError("类型目录 types 必须是非空数组")
    if set(data) != {"schemaVersion", "types"}:
        raise M2VError("类型目录顶层只允许 schemaVersion 和 types")
    seen: set[str] = set()
    entries = tuple(_parse_entry(raw, index, seen) for index, raw in enumerate(raw_types))
    if {entry.name for entry in entries} != FIVE_TYPES:
        raise M2VError("类型目录必须恰好登记指定的五类视频")
    return Catalog(entries)


def load(path: str | Path | None = None) -> Catalog:
    """读取并严格校验目录；任何字段问题都在这里失败，不留给调用方。"""
    target = Path(path) if path is not None else CATALOG_PATH
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M2VError(f"无法读取类型目录 {target}: {exc}") from exc
    return _parse(data)


_cached: Catalog | None = None


def catalog() -> Catalog:
    """随包目录（进程内缓存一次）。测试需要替换时直接构造 :class:`Catalog`。"""
    global _cached
    if _cached is None:
        _cached = load()
    return _cached
