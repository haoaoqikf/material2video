"""注册表与 `catalog.py` 的逐项对照。

`web/src/registry/index.ts` 是渲染层的组件选择面，`scripts/a2v/catalog.py` 是校验器
读的同一份目录。两边都描述「每个组件认识哪些标注键、能吃下多少条目、默认给哪种
场景类型」，因此它们**必须逐项相同**——这正是旧实现漂移过一次的地方（图节点只
允许 `{id}`），症状是整份分镜在一条路径上画不出来、另一条却判它合法。

这里把 TS 源码当文本解析，而不是跑一遍 TypeScript：注册表是**声明式**的常量，
解析规则窄而显式（见 `_parse_registry`），一旦写法变了就会失败并提示改这里，
不会静默漏检。对照的另一侧是权威真源 `FIGURE_CATALOG` / `DEFAULT_KINDS`。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "web" / "src" / "registry" / "index.ts"
SCRIPTS = ROOT / ".agents" / "skills" / "article2video" / "scripts"

import sys

sys.path.insert(0, str(SCRIPTS))

from a2v.catalog import DEFAULT_KINDS, FIGURE_CATALOG, known_kinds  # noqa: E402


# ---------------------------------------------------------------------------
# 解析 TS 注册表
# ---------------------------------------------------------------------------


def _block(text: str, start: int) -> tuple[str, int]:
    """从 `{` 开始取到配对的 `}`，返回 (块正文, 结束位置)。"""
    assert text[start] == "{", f"期望从 `{{` 开始，实际是 {text[start]!r}"
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index], index + 1
    raise AssertionError("括号没有闭合")


def _entries(body: str) -> dict[str, str]:
    """顶层条目：`key: { ... },` → key → 块正文。"""
    found: dict[str, str] = {}
    pattern = re.compile(r"([A-Za-z_][\w-]*)\s*:\s*\{")
    position = 0
    while True:
        match = pattern.search(body, position)
        if match is None:
            return found
        inner, end = _block(body, match.end() - 1)
        found[match.group(1)] = inner
        position = end


def _field(body: str, name: str) -> str | None:
    """取一个字段的原始值文本（不含尾随逗号）。

    值可能是字符串、数组或裸标识符，因此这里按括号/引号配对取，而不是切到第一个逗号
    （`['a', 'b']` 里的逗号属于值）。
    """
    match = re.search(rf"(?:^|[\s,]){name}\s*:\s*", body)
    if match is None:
        return None
    rest = body[match.end() :]
    if rest.startswith("["):
        depth = 0
        for index, char in enumerate(rest):
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    return rest[: index + 1]
        raise AssertionError(f"{name} 的数组没有闭合：{rest[:40]!r}")
    if rest[:1] in {"'", '"'}:
        quote = rest[0]
        end = rest.index(quote, 1)
        return rest[: end + 1]
    return re.split(r"[,\n]", rest, maxsplit=1)[0].strip()


def _string_list(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    assert raw.startswith("[") and raw.endswith("]"), f"不是数组字面量：{raw!r}"
    inner = raw[1:-1].strip()
    if not inner:
        return []
    return [item.strip().strip("'\"") for item in inner.split(",")]


def _parse_registry() -> tuple[dict[str, dict[str, object]], dict[str, str], set[str]]:
    """→ (kind → {labels, items, summary, component}, 默认映射, 被引用的组件名)。"""
    text = REGISTRY.read_text(encoding="utf-8")

    figures_start = text.index("export const FIGURES")
    figures_body, after = _block(text, text.index("{", figures_start))

    defaults_start = text.index("export const DEFAULT_KIND_BY_SCENE", after)
    defaults_body, _ = _block(text, text.index("{", defaults_start))

    figures: dict[str, dict[str, object]] = {}
    for key, body in _entries(figures_body).items():
        labels = _string_list(_field(body, "labels"))
        assert labels is not None, f"{key} 没有 labels 字段"
        raw_items = _field(body, "items")
        if raw_items == "null":
            items: tuple[int, int] | None = None
        else:
            numbers = _string_list(raw_items)
            assert numbers is not None and len(numbers) == 2, f"{key} 的 items 不是二元组：{raw_items}"
            items = (int(numbers[0]), int(numbers[1]))
        summary = _field(body, "summary")
        assert summary is not None, f"{key} 没有 summary 字段"
        component = _field(body, "Component")
        assert component is not None, f"{key} 没有 Component 字段"
        figures[key] = {
            "kind": (_field(body, "kind") or "").strip("'\""),
            "labels": labels,
            "items": items,
            "summary": summary.strip("'\""),
            "component": component,
        }

    defaults: dict[str, str] = {}
    for match in re.finditer(r"([A-Za-z_][\w-]*)\s*:\s*'([^']*)'", defaults_body):
        defaults[match.group(1)] = match.group(2)

    imported = set(re.findall(r"import\s*\{\s*([A-Za-z_][\w]*)\s*\}\s*from\s*'@/components/", text))
    return figures, defaults, imported


REGISTRY_FIGURES, REGISTRY_DEFAULTS, IMPORTED_COMPONENTS = _parse_registry()


# ---------------------------------------------------------------------------
# 对照
# ---------------------------------------------------------------------------


def test_registry_is_parseable_and_non_trivial() -> None:
    """解析规则一旦失效（写法变了），后面每条断言都会变成空转，这里先挡住。"""
    assert len(REGISTRY_FIGURES) >= 8, f"只解析出 {len(REGISTRY_FIGURES)} 个组件，解析规则可能失效了"
    assert len(REGISTRY_DEFAULTS) >= 8, f"只解析出 {len(REGISTRY_DEFAULTS)} 条默认映射"
    assert len(IMPORTED_COMPONENTS) >= 8, f"只解析出 {len(IMPORTED_COMPONENTS)} 个组件导入"


def test_kinds_match_the_server_catalog() -> None:
    assert sorted(REGISTRY_FIGURES) == known_kinds(), (
        "渲染层注册表的组件清单与 scripts/a2v/catalog.py 不一致：\n"
        f"  渲染层：{sorted(REGISTRY_FIGURES)}\n"
        f"  校验器：{known_kinds()}"
    )
    for key, entry in REGISTRY_FIGURES.items():
        assert entry["kind"] == key, f"{key} 的 kind 字段写成了 {entry['kind']!r}，两边必须同名"


@pytest.mark.parametrize("kind", sorted(FIGURE_CATALOG))
def test_labels_match_the_server_catalog(kind: str) -> None:
    """标注键不一致的后果是**静默**的：写了标签却没人画，或组件读一个没人认识的键。"""
    expected = FIGURE_CATALOG[kind]
    entry = REGISTRY_FIGURES[kind]
    assert set(entry["labels"]) == set(expected.labels), (
        f"{kind} 认识的标注键不一致：渲染层 {sorted(entry['labels'])}，"
        f"校验器 {sorted(expected.labels)}"
    )


@pytest.mark.parametrize("kind", sorted(FIGURE_CATALOG))
def test_items_and_summary_match_the_server_catalog(kind: str) -> None:
    expected = FIGURE_CATALOG[kind]
    entry = REGISTRY_FIGURES[kind]
    assert entry["items"] == expected.items, (
        f"{kind} 的条目区间不一致：渲染层 {entry['items']}，校验器 {expected.items}"
    )
    assert entry["summary"] == expected.summary, (
        f"{kind} 的说明文字不一致：\n  渲染层：{entry['summary']!r}\n  校验器：{expected.summary!r}"
    )


def test_default_kinds_match_the_server_catalog() -> None:
    """默认映射不一致会让同一份分镜在两条路径上画出不同的组件。"""
    assert REGISTRY_DEFAULTS == DEFAULT_KINDS, (
        "按场景类型的默认组件与 catalog.py 的 DEFAULT_KINDS 不一致：\n"
        f"  渲染层：{REGISTRY_DEFAULTS}\n"
        f"  校验器：{DEFAULT_KINDS}"
    )


def test_every_component_is_imported_and_every_kind_has_a_default() -> None:
    for key, entry in REGISTRY_FIGURES.items():
        assert entry["component"] in IMPORTED_COMPONENTS, (
            f"{key} 用了 {entry['component']}，但它不在文件顶部的导入里"
        )
    unknown = {kind for kind in REGISTRY_DEFAULTS.values() if kind not in REGISTRY_FIGURES}
    assert not unknown, f"默认映射指向了没有实现的组件：{sorted(unknown)}"
