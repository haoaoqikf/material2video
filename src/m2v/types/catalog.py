"""视频类型目录：类型身份、材料入口与文档文案的单一来源。

目录以同目录下的 ``catalog.json`` 为唯一真源。此前同一份事实散落在四处代码
（注册表、作品契约的类型白名单与材料映射、命令行的初始化模板）和三份文档里，
且没有任何一致性检查；现在统一入口、作品初始化与文档都从这里派生。

目录同时支持两级的「类别 → 类型」登记：类别只提供组织信息（标识、标题、说明），
类型可以声明唯一一个所属类别；类别本身不可初始化或渲染。规范作品位置由类别
派生：分类类型为 ``videos/<category>/<type>/<slug>/``，未分类类型为
``videos/<type>/<slug>/``。

本模块只负责**读取与校验**目录，并回答「这个类型叫什么、说明是什么、属于哪个
类别、材料有哪些、初始内容是什么」。行为（校验/准备/预演/渲染）仍由各类型的
适配器实现，两者按名称对应：``registry`` 负责把它们对上。

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
SCHEMA_VERSION = 2

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
class Category:
    """一个类型类别。类别只组织类型，不提供行为、材料或初始化。"""

    id: str
    title: str
    description: str


@dataclass(frozen=True)
class Entry:
    """一个视频类型在目录中的全部登记信息（不含行为）。"""

    name: str
    description: str
    summary: str
    plan: str
    skill_guide: str
    materials: tuple[Material, ...]
    starters: tuple[str, ...] = ()
    category: str | None = None

    def material_map(self) -> dict[str, str]:
        """作品契约使用的「材料名 → 默认文件名」映射。"""
        return {material.name: material.file for material in self.materials}

    def workspace_parts(self) -> tuple[str, ...]:
        """作品在 ``videos/`` 下的规范层级：分类类型含类别，未分类类型只含类型。"""
        return (self.category, self.name) if self.category else (self.name,)

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

    def __init__(self, entries: tuple[Entry, ...], categories: tuple[Category, ...] = ()) -> None:
        self._entries = entries
        self._by_name = {entry.name: entry for entry in entries}
        self._categories = categories
        self._by_category = {category.id: category for category in categories}

    def entries(self) -> tuple[Entry, ...]:
        """按目录中的登记顺序返回全部登记项（文档生成依赖这一顺序）。"""
        return self._entries

    def names(self) -> tuple[str, ...]:
        return tuple(entry.name for entry in self._entries)

    def categories(self) -> tuple[Category, ...]:
        """按目录登记顺序返回全部类别。"""
        return self._categories

    def category(self, category_id: str) -> Category | None:
        return self._by_category.get(category_id)

    def types_in(self, category_id: str) -> tuple[Entry, ...]:
        """某类别下的类型，保持类型的登记顺序。"""
        return tuple(entry for entry in self._entries if entry.category == category_id)

    def uncategorized(self) -> tuple[Entry, ...]:
        return tuple(entry for entry in self._entries if entry.category is None)

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


def _parse_entry(raw: Any, index: int, seen: set[str], category_ids: set[str]) -> Entry:
    where = f"types[{index}]"
    if not isinstance(raw, dict):
        raise M2VError(f"类型目录 {where} 必须是对象")
    name = _require_text(raw.get("name"), f"{where}.name")
    if not _NAME_RE.match(name):
        raise M2VError(f"类型目录 {where}.name 必须是 1 至 63 位小写字母、数字或连字符：{name!r}")
    if name in seen:
        raise M2VError(f"类型目录重复登记类型：{name}")
    seen.add(name)
    category = raw.get("category")
    if category is not None:
        category = _require_text(category, f"types[{name}].category")
        if category not in category_ids:
            raise M2VError(f"类型目录 types[{name}].category 引用了未登记的类别：{category}")
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
    return Entry(name=name, materials=materials, starters=_parse_starters(raw.get("starters"), name),
                 category=category, **texts)


def _parse_categories(raw: Any) -> tuple[Category, ...]:
    """类别只组织类型：标识、标题与说明都必须显式给出，不接受空分类。"""
    if raw is None:
        return ()
    if not isinstance(raw, list) or not raw:
        raise M2VError("类型目录 categories 必须是非空数组")
    categories: list[Category] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        where = f"categories[{index}]"
        if not isinstance(item, dict):
            raise M2VError(f"类型目录 {where} 必须是对象")
        category_id = _require_text(item.get("id"), f"{where}.id")
        if not _NAME_RE.match(category_id):
            raise M2VError(f"类型目录 {where}.id 必须是 1 至 63 位小写字母、数字或连字符：{category_id!r}")
        if category_id in seen:
            raise M2VError(f"类型目录重复登记类别：{category_id}")
        seen.add(category_id)
        categories.append(Category(
            id=category_id,
            title=_require_text(item.get("title"), f"{where}.title"),
            description=_require_text(item.get("description"), f"{where}.description"),
        ))
    return tuple(categories)


def _parse_starters(raw: Any, type_name: str) -> tuple[str, ...]:
    """初始化时额外生成的起步文件（例如本地代码场景入口）。

    路径相对作品根，内容取自 ``types/<类型名>/starters/<同一路径>``。作品代码是
    可编辑材料而不是派生产物，因此只在 ``init`` 时写一次，之后不再覆盖。
    """
    if raw is None:
        return ()
    where = f"types[{type_name}].starters"
    if not isinstance(raw, list) or not raw:
        raise M2VError(f"类型目录 {where} 必须是非空数组")
    for index, item in enumerate(raw):
        if (not isinstance(item, str) or not item or "\\" in item or item.startswith("/")
                or ".." in item.split("/") or not item.endswith(".tsx")):
            raise M2VError(f"类型目录 {where}[{index}] 必须是作品内不含上跳段的相对 .tsx 路径：{item!r}")
    if len(set(raw)) != len(raw):
        raise M2VError(f"类型目录 {where} 存在重复路径")
    return tuple(raw)


def starters_dir(type_name: str) -> Path:
    """某类型的起步文件目录：``types/<类型名>/starters/``。"""
    return Path(__file__).parent / type_name / "starters"


def _parse(data: Any) -> Catalog:
    if not isinstance(data, dict):
        raise M2VError(f"类型目录 {CATALOG_PATH.name} 顶层必须是对象")
    if data.get("schemaVersion") != SCHEMA_VERSION:
        raise M2VError(f"类型目录 schemaVersion 必须为 {SCHEMA_VERSION}")
    raw_types = data.get("types")
    if not isinstance(raw_types, list) or not raw_types:
        raise M2VError("类型目录 types 必须是非空数组")
    categories = _parse_categories(data.get("categories"))
    category_ids = {category.id for category in categories}
    seen: set[str] = set()
    entries = tuple(_parse_entry(raw, index, seen, category_ids) for index, raw in enumerate(raw_types))
    overlap = category_ids & seen
    if overlap:
        raise M2VError(f"类型目录类别标识与类型名冲突：{'、'.join(sorted(overlap))}")
    used = {entry.category for entry in entries if entry.category}
    for category in categories:
        if category.id not in used:
            raise M2VError(f"类型目录类别没有任何类型成员：{category.id}")
    return Catalog(entries, categories)


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
