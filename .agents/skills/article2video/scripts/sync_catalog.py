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
CATALOG = REPO_ROOT / ".agents/skills/article2video/scripts/a2v/catalog.py"
TYPES = REPO_ROOT / "web/src/schema/primitiveTypes.ts"
DOC = REPO_ROOT / ".agents/skills/article2video/references/primitive-catalog.md"
BEGIN, END = "# >>> generated:registry >>>", "# <<< generated:registry <<<"

def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))

def _block(text: str, content: str) -> str:
    start, stop = text.index(BEGIN), text.index(END)
    return text[:start + len(BEGIN)] + "\n" + content.rstrip() + "\n" + text[stop:]

def _catalog(registry: dict[str, Any]) -> str:
    lines = ["PRIMITIVE_CATALOG: dict[str, Primitive] = {"]
    for entry in sorted(registry["primitives"], key=lambda item: item["type"]):
        lines += [f"    {entry['type']!r}: Primitive(", f"        type={entry['type']!r},", f"        category={entry['category']!r},", f"        children=({entry['children'][0]}, {entry['children'][1]}),", f"        props=frozenset({entry['props']!r}),", f"        motions=frozenset({entry['motions']!r}),", f"        summary={entry['summary']!r},", "    ),"]
    return "\n".join(lines + ["}"])

def _types(registry: dict[str, Any]) -> str:
    kinds = sorted(item["type"] for item in registry["primitives"])
    props = ",\n".join(
        f"    {item['type']!r}: [{', '.join(repr(prop) for prop in item['props'])}]"
        for item in sorted(registry["primitives"], key=lambda entry: entry["type"])
    )
    motions = ",\n".join(
        f"    {item['type']!r}: [{', '.join(repr(motion) for motion in item['motions'])}]"
        for item in sorted(registry["primitives"], key=lambda entry: entry["type"])
    )
    return (
        "/* eslint-disable */\n/** 由 sync_catalog.py 从视觉原语注册表生成。 */\n"
        "export const PRIMITIVE_TYPES = [" + ", ".join(repr(kind) for kind in kinds) + "] as const;\n"
        "export type PrimitiveType = (typeof PRIMITIVE_TYPES)[number];\n"
        "/** 每个原语允许声明的属性（结构性字段 id/type/children 不在此列）。 */\n"
        "export const PRIMITIVE_PROPS: Readonly<Record<string, readonly string[]>> = {\n" + props + ",\n};\n"
        "/** 每个原语允许绑定的动效配方。 */\n"
        "export const PRIMITIVE_MOTIONS: Readonly<Record<string, readonly string[]>> = {\n" + motions + ",\n};\n"
    )

def _doc(registry: dict[str, Any]) -> str:
    lines = ["# 视觉原语目录", "", "本文件由 `web/src/registry/registry.json` 生成，不要手工维护表格。", "", "| 类型 | 类别 | 子节点容量 | 属性 | 动效 | 用途 |", "| --- | --- | --- | --- | --- | --- |"]
    for item in registry["primitives"]:
        lines.append(f"| `{item['type']}` | {item['category']} | {item['children'][0]}–{item['children'][1]} | {', '.join(f'`{x}`' for x in item['props']) or '无'} | {', '.join(f'`{x}`' for x in item['motions'])} | {item['summary']} |")
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
