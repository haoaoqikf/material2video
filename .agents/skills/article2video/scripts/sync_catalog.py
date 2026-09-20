#!/usr/bin/env python3
"""由组件注册表生成全部派生文件（openspec 能力 react-component-registry）。

**唯一真源**：`web/src/registry/registry.json`。它声明组件集合、每个组件认识的
标注键、容量、适用场景类型与默认映射；本脚本把它投到三个消费方各自的形态：

1. `scripts/a2v/catalog.py` 的生成区——校验器读的镜像（Python dataclass）；
2. `references/figure-catalog.md` 的组件表——给上游 AI 选组件看的文档；
3. `web/src/schema/figureKinds.ts`——分镜 schema 的 `kind` 取值枚举。

为什么是「生成」而不是「各抄一份」：注册表机制建立之前，catalog.py 与
浏览器端注册表各写一份、靠测试对照，漂移只能等测试失败才暴露；
组件文档的表格还要第三份。三个消费方现在都由同一份 JSON 推导，
**手改任何一份派生文件都会被 `--check` 判为落后并指名该文件**。

用法::

    uv run python .agents/skills/article2video/scripts/sync_catalog.py           # 生成
    uv run python .agents/skills/article2video/scripts/sync_catalog.py --check   # 只校验

`tests/test_web_registry.py` 在 `uv run pytest` 里跑的就是 `--check`，
所以「改了注册表忘了重新生成」会在提交前失败。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]

REGISTRY_RELATIVE = Path("web/src/registry/registry.json")
CATALOG_RELATIVE = Path(".agents/skills/article2video/scripts/a2v/catalog.py")
DOC_RELATIVE = Path(".agents/skills/article2video/references/figure-catalog.md")
KINDS_RELATIVE = Path("web/src/schema/figureKinds.ts")

# 派生文件的边界。catalog.py 与文档只在边界**内**生成，其余内容（docstring、
# 组件契约说明等）是手工维护的；figureKinds.ts 整个文件都是生成物。
CATALOG_BEGIN = "# >>> generated:registry >>>"
CATALOG_END = "# <<< generated:registry <<<"
TABLE_BEGIN = "<!-- >>> generated:figures-table >>> -->"
TABLE_END = "<!-- <<< generated:figures-table <<< -->"

_CANVAS_NOTE = """\
# 画面主体由 canvas 绘制的组件：它们内部的文字量不到，
# 观感闸门（K7 文字溢出 / K8 容器内溢出）对图形内部**不适用**，
# 体检报告必须写明这一判定范围并说明原因（见 inspect.py / keynote.py）。"""

_SCHEMATIC_NOTE = """\
# 会把 figure.schematic 自动画成「示意」标的组件。
# 其它组件声明了该标记时，校验器要求文案里自己出现「示意」二字，
# 否则「标记为示意」只存在于数据里，观众看不到。"""


def load_registry() -> dict[str, Any]:
    """读注册表。JSON 解析失败直接崩：真源坏了，一切派生都不该发生。"""
    path = REPO_ROOT / REGISTRY_RELATIVE
    return json.loads(path.read_text(encoding="utf-8"))


def _python_string(value: str) -> str:
    """Python 字符串字面量。summary 里可能出现引号，用 repr 保证转义正确。"""
    return repr(value)


def _labels_literal(labels: list[str]) -> str:
    if not labels:
        return "frozenset()"
    inner = ", ".join(_python_string(label) for label in sorted(labels))
    return "frozenset({" + inner + "})"


def generate_catalog_module(registry: dict[str, Any]) -> str:
    """catalog.py 生成区的内容（不带边界标记）。"""
    lines: list[str] = []
    lines.append("FIGURE_CATALOG: dict[str, Component] = {")
    for entry in sorted(registry["figures"], key=lambda item: item["kind"]):
        lines.append(f"    {_python_string(entry['kind'])}: Component(")
        lines.append(f"        kind={_python_string(entry['kind'])},")
        lines.append(f"        labels={_labels_literal(entry['labels'])},")
        items = entry.get("items")
        if items is not None:
            lines.append(f"        items=({items[0]}, {items[1]}),")
        lines.append(f"        summary={_python_string(entry['summary'])},")
        lines.append("    ),")
    lines.append("}")
    lines.append("")
    lines.append(
        "# 分镜没有声明 figure.kind 时，按场景类型取用的默认组件。"
    )
    lines.append("DEFAULT_KINDS: dict[str, str] = {")
    for scene_type in sorted(registry["defaultKindByScene"]):
        lines.append(
            f"    {_python_string(scene_type)}: "
            f"{_python_string(registry['defaultKindByScene'][scene_type])},"
        )
    lines.append("}")
    lines.append("")
    lines.append(_CANVAS_NOTE)
    canvas = sorted(
        entry["kind"] for entry in registry["figures"] if entry.get("canvasDrawn")
    )
    lines.append(f"CANVAS_KINDS: frozenset[str] = frozenset({{{', '.join(map(_python_string, canvas))}}})")
    lines.append("")
    lines.append(_SCHEMATIC_NOTE)
    schematic = sorted(
        entry["kind"] for entry in registry["figures"] if entry.get("schematicMark")
    )
    lines.append(
        f"SCHEMATIC_KINDS: frozenset[str] = frozenset({{{', '.join(map(_python_string, schematic))}}})"
    )
    return "\n".join(lines) + "\n"


def _capacity_text(entry: dict[str, Any]) -> str:
    items = entry.get("items")
    if items is None:
        return "不限"
    return f"{items[0]}–{items[1]} {entry['capacityUnit']}"


def _labels_text(entry: dict[str, Any]) -> str:
    labels = entry.get("labels") or []
    if not labels:
        return "无"
    return ", ".join(f"`{label}`" for label in labels)


def _defaults_text(entry: dict[str, Any], defaults: dict[str, str]) -> str:
    scenes = sorted(scene for scene, kind in defaults.items() if kind == entry["kind"])
    if not scenes:
        return "—"
    return ", ".join(f"`{scene}`" for scene in scenes)


def generate_figures_table(registry: dict[str, Any]) -> str:
    """figure-catalog.md 组件表的内容（不带边界标记）。"""
    lines = [
        "| `kind` | 状态 | 适合表达 | 默认给 | 标注键 | 容量 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    defaults = registry["defaultKindByScene"]
    for entry in registry["figures"]:
        status = "已实现" if entry.get("implemented") else "规划中"
        lines.append(
            f"| `{entry['kind']}` | {status} | {entry['summary']} "
            f"| {_defaults_text(entry, defaults)} "
            f"| {_labels_text(entry)} "
            f"| {_capacity_text(entry)} |"
        )
    return "\n".join(lines)


def generate_figure_kinds(registry: dict[str, Any]) -> str:
    """figureKinds.ts 的完整内容（整个文件都是生成物）。"""
    kinds = sorted(entry["kind"] for entry in registry["figures"])
    lines = [
        "/* eslint-disable */",
        "/**",
        " * 分镜 `figure.kind` 的取值枚举——**生成物，不要手改**。",
        " *",
        " * 由 `scripts/sync_catalog.py` 从 `web/src/registry/registry.json` 生成；",
        " * 消费方是 `web/src/schema/storyboard.ts` 的 `figureSchema`：kind 写了",
        " * 但不在这份清单里时，解析报错并列出已知组件。重新生成：",
        " *",
        " *     uv run python .agents/skills/article2video/scripts/sync_catalog.py",
        " *",
        " * 手改后运行同一命令加 `--check` 会被判为落后并指名本文件。",
        " */",
        "export const FIGURE_KINDS = [",
    ]
    lines.extend(f"  '{kind}'," for kind in kinds)
    lines.extend(
        [
            "] as const;",
            "",
            "export type FigureKind = (typeof FIGURE_KINDS)[number];",
        ]
    )
    return "\n".join(lines) + "\n"


def replace_block(text: str, begin: str, end: str, content: str, target: Path) -> str:
    """替换 begin/end 标记之间的内容。标记缺失时报错并指名文件。"""
    start = text.find(begin)
    if start < 0:
        raise SystemExit(f"{target}: 缺少生成区开始标记 {begin!r}，无法生成")
    stop = text.find(end, start)
    if stop < 0:
        raise SystemExit(f"{target}: 缺少生成区结束标记 {end}，无法生成")
    return text[: start + len(begin)] + "\n" + content + text[stop:]


def build_outputs(registry: dict[str, Any]) -> dict[Path, str]:
    """路径 → 该文件应有的完整内容。"""
    catalog_path = REPO_ROOT / CATALOG_RELATIVE
    doc_path = REPO_ROOT / DOC_RELATIVE
    kinds_path = REPO_ROOT / KINDS_RELATIVE
    catalog_text = replace_block(
        catalog_path.read_text(encoding="utf-8"),
        CATALOG_BEGIN,
        CATALOG_END,
        generate_catalog_module(registry),
        catalog_path,
    )
    doc_text = replace_block(
        doc_path.read_text(encoding="utf-8"),
        TABLE_BEGIN,
        TABLE_END,
        generate_figures_table(registry),
        doc_path,
    )
    return {
        catalog_path: catalog_text,
        doc_path: doc_text,
        kinds_path: generate_figure_kinds(registry),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="只校验派生文件是否与注册表一致，不一致时列出落后文件并以非零退出",
    )
    args = parser.parse_args(argv)

    registry = load_registry()
    outputs = build_outputs(registry)

    drifted: list[tuple[Path, str]] = []
    for path, expected in outputs.items():
        actual = path.read_text(encoding="utf-8") if path.is_file() else None
        if actual != expected:
            label = path.relative_to(REPO_ROOT)
            drifted.append((path, str(label)))

    if args.check:
        if drifted:
            print("以下派生文件与注册表不一致（先运行生成命令，或补上注册表改动）：")
            for _, label in drifted:
                print(f"  - {label}")
            return 1
        print("生成物与注册表一致。")
        return 0

    for path, expected in outputs.items():
        path.write_text(expected, encoding="utf-8")
        print(f"已生成：{path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
