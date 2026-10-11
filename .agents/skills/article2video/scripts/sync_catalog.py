#!/usr/bin/env python3
"""从视觉原语注册表生成 Python 镜像、TypeScript 枚举与原语目录。"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
REGISTRY = REPO_ROOT / "web/src/registry/registry.json"
CATALOG = REPO_ROOT / "src/a2v/core/catalog.py"
TYPES = REPO_ROOT / "web/src/schema/primitiveTypes.ts"
DOC = REPO_ROOT / ".agents/skills/article2video/references/primitive-catalog.md"
BEGIN, END = "# >>> generated:registry >>>", "# <<< generated:registry <<<"

def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))

def _block(text: str, content: str) -> str:
    start, stop = text.index(BEGIN), text.index(END)
    return text[:start + len(BEGIN)] + "\n" + content.rstrip() + "\n" + text[stop:]

def _vocabulary(registry: dict[str, Any]) -> str:
    """受控语义动作词汇：动作全集、中性动作、改变类动作与人读说明。"""
    actions = registry["actions"]
    neutral = registry["neutralActions"]
    change = [item for item in actions if item not in neutral]
    labels = ",\n".join(f"    {key!r}: {value!r}" for key, value in registry["actionLabels"].items())
    return "\n".join([
        "#: 受控语义动作全集：beat.action 只能取这些值。",
        "SEMANTIC_ACTIONS: tuple[str, ...] = (",
        *[f"    {item!r}," for item in actions],
        ")",
        "#: 中性动作：只让对象出现或更醒目，不改变状态与关系（A3 闸门据此判定）。",
        "NEUTRAL_ACTIONS: frozenset[str] = frozenset(" + repr(tuple(neutral)) + ")",
        "#: 改变对象状态或关系的动作，与 NEUTRAL_ACTIONS 互补。",
        "CHANGE_ACTIONS: frozenset[str] = frozenset(" + repr(tuple(change)) + ")",
        "#: 动作的中文人读说明：错误信息、报告与文档共用同一份措辞。",
        "ACTION_LABELS: dict[str, str] = {",
        labels,
        "}",
    ])


def _icons(registry: dict[str, Any]) -> str:
    """受控图标白名单：`icon` 与 `pictogram` 只能引用这里列出的名字。"""
    return "\n".join([
        "#: 受控图标名白名单：icon/pictogram 只能引用这些名字，未知名字在校验阶段失败。",
        "ICON_NAMES: tuple[str, ...] = (",
        *[f"    {item!r}," for item in registry["icons"]],
        ")",
    ])


def _catalog(registry: dict[str, Any]) -> str:
    transforms = tuple(tuple(pair) for pair in registry["continuityTransforms"])
    continuity = "\n".join([
        "#: 注册表允许的有限跨幕原语变形；同类原语始终允许。",
        f"CONTINUITY_TRANSFORMS: frozenset[tuple[str, str]] = frozenset({transforms!r})",
    ])
    lines = [_vocabulary(registry), _icons(registry), continuity, "", "PRIMITIVE_CATALOG: dict[str, Primitive] = {"]
    for entry in sorted(registry["primitives"], key=lambda item: item["type"]):
        lines += [f"    {entry['type']!r}: Primitive(", f"        type={entry['type']!r},", f"        category={entry['category']!r},", f"        children=({entry['children'][0]}, {entry['children'][1]}),", f"        props=frozenset({entry['props']!r}),", f"        motions=frozenset({entry['motions']!r}),", f"        actions=frozenset({entry['actions']!r}),", f"        summary={entry['summary']!r},", "    ),"]
    return "\n".join(lines + ["}"])

def _types(registry: dict[str, Any]) -> str:
    kinds = sorted(item["type"] for item in registry["primitives"])
    ordered = sorted(registry["primitives"], key=lambda entry: entry["type"])
    actions = registry["actions"]
    neutral = registry["neutralActions"]
    change = [item for item in actions if item not in neutral]
    labels = ",\n".join(f"    {key!r}: {value!r}" for key, value in registry["actionLabels"].items())

    def mapping(field: str) -> str:
        return ",\n".join(
            f"    {item['type']!r}: [{', '.join(repr(value) for value in item[field])}]"
            for item in ordered
        )

    return (
        "/* eslint-disable */\n/** 由 sync_catalog.py 从视觉原语注册表生成。 */\n"
        "/** 受控语义动作全集：beat.action 只能取这些值。 */\n"
        "export const SEMANTIC_ACTIONS = [" + ", ".join(repr(item) for item in actions) + "] as const;\n"
        "export type SemanticAction = (typeof SEMANTIC_ACTIONS)[number];\n"
        "/** 中性动作：只让对象出现或更醒目，不改变状态与关系。 */\n"
        "export const NEUTRAL_ACTIONS: readonly string[] = [" + ", ".join(repr(item) for item in neutral) + "];\n"
        "/** 改变对象状态或关系的动作，与 NEUTRAL_ACTIONS 互补。 */\n"
        "export const CHANGE_ACTIONS: readonly string[] = [" + ", ".join(repr(item) for item in change) + "];\n"
        "/** 动作的中文人读说明：报告与文档共用同一份措辞。 */\n"
        "export const ACTION_LABELS: Readonly<Record<string, string>> = {\n" + labels + ",\n};\n"
        "/** 受控图标名白名单：icon/pictogram 只能引用这些名字。 */\n"
        "export const ICON_NAMES = [" + ", ".join(repr(item) for item in registry["icons"]) + "] as const;\n"
        "export type IconName = (typeof ICON_NAMES)[number];\n"
        "export const PRIMITIVE_TYPES = [" + ", ".join(repr(kind) for kind in kinds) + "] as const;\n"
        "export type PrimitiveType = (typeof PRIMITIVE_TYPES)[number];\n"
        "/** 注册表允许的有限跨幕原语变形；同类原语始终允许。 */\n"
        "export const CONTINUITY_TRANSFORMS = " + repr(registry["continuityTransforms"]).replace("'", '"') + " as const;\n"
        "/** 每个原语允许声明的属性（结构性字段 id/type/children 不在此列）。 */\n"
        "export const PRIMITIVE_PROPS: Readonly<Record<string, readonly string[]>> = {\n" + mapping("props") + ",\n};\n"
        "/** 每个原语允许绑定的动效配方。 */\n"
        "export const PRIMITIVE_MOTIONS: Readonly<Record<string, readonly string[]>> = {\n" + mapping("motions") + ",\n};\n"
        "/** 每个原语支持的受控语义动作（beat 的 action 必须落在目标原语的清单里）。 */\n"
        "export const PRIMITIVE_ACTIONS: Readonly<Record<string, readonly string[]>> = {\n" + mapping("actions") + ",\n};\n"
    )

def _doc(registry: dict[str, Any]) -> str:
    lines = [
        "# 视觉原语目录",
        "",
        "本文件由 `web/src/registry/registry.json` 生成，不要手工维护表格。",
        "",
        "## 语义动作词汇",
        "",
        "beat 的 `action` 只能取下表的值；`建立` 类动作只让对象出现或更醒目，",
        "不改变对象状态与关系，因此 A3 闸门（动画论证评审）不把它算作一次推理。",
        "",
        "| 动作 | 含义 | 是否改变状态或关系 |",
        "| --- | --- | --- |",
    ]
    for item in registry["actions"]:
        neutral = "否（中性动作）" if item in registry["neutralActions"] else "是"
        lines.append(f"| `{item}` | {registry['actionLabels'][item]} | {neutral} |")
    lines += [
        "",
        "## 受控图标白名单",
        "",
        "`icon` 与 `pictogram` 的 `icon` 属性只能引用下表的名字：",
        "未知名字在**校验阶段**失败，运行期不做动态解析，也不发起网络请求。",
        "",
        "| 图标名 |",
        "| --- |",
    ]
    lines += [f"| `{item}` |" for item in registry["icons"]]
    lines += [
        "",
        "## 原语清单",
        "",
        "「语义动作」列是该原语**支持**的动作子集：beat 的目标原语不支持某个动作时校验失败。",
        "",
        "| 类型 | 类别 | 子节点容量 | 属性 | 动效 | 语义动作 | 用途 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in registry["primitives"]:
        lines.append(f"| `{item['type']}` | {item['category']} | {item['children'][0]}–{item['children'][1]} | {', '.join(f'`{x}`' for x in item['props']) or '无'} | {', '.join(f'`{x}`' for x in item['motions'])} | {', '.join(f'`{x}`' for x in item['actions'])} | {item['summary']} |")
    return "\n".join(lines) + "\n"

def build_outputs(registry: dict[str, Any]) -> dict[Path, str]:
    return {CATALOG: _block(CATALOG.read_text(encoding="utf-8"), _catalog(registry)), TYPES: _types(registry), DOC: _doc(registry)}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--check", action="store_true"); args = parser.parse_args(argv)
    outputs = build_outputs(load_registry()); drifted = [path for path, expected in outputs.items() if not path.is_file() or path.read_text(encoding="utf-8") != expected]
    if args.check:
        if drifted:
            print("以下派生文件与原语注册表不一致："); [print(f"  - {path.relative_to(REPO_ROOT)}") for path in drifted]; return 1
        print("原语注册表生成物一致。"); return 0
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8"); print(f"已生成：{path.relative_to(REPO_ROOT)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
