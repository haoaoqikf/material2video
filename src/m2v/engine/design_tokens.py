"""设计令牌的读取入口：解析 `web/src/styles/tokens.css` 的 `@theme static` 块。

令牌层是画面取值的唯一真源。浏览器量测过去把正文分区、字幕盒边界抄成自己的
Python 常量，于是「改一个令牌」只会改到画面那一半，判据那一半留在常量里不动，
两边静默漂移。这里让量测与画面读同一份取值。

只认 `@theme static` 那一个块：别的规则（例如 `:root { color-scheme }`）不提供
令牌，混进来会让「抽到了什么」变成取决于文件顺序的事。
"""
from __future__ import annotations

import re
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.engine.contract_page import web_dir

#: 只吸 `--m2v-*` 与 `--fig-*`，与令牌层的命名约定一致。
_TOKEN_DECLARATION = re.compile(r"(--[a-z0-9-]+):\s*([^;]+);")


def tokens_css_path(repo_root: Path | None = None) -> Path:
    """设计令牌文件。"""
    return web_dir(repo_root) / "src/styles/tokens.css"


def theme_block(source: str) -> dict[str, str]:
    """从 `tokens.css` 文本抽出 `@theme static` 块里的全部令牌取值。"""
    start = source.find("@theme static")
    if start == -1:
        raise M2VError("`tokens.css` 里找不到 `@theme static` 块")
    depth, index, end = 0, source.find("{", start), -1
    if index == -1:
        raise M2VError("`@theme static` 块没有起始大括号")
    while index < len(source):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
        index += 1
    if end == -1:
        raise M2VError("`@theme static` 块没有闭合")
    segment = source[source.find("{", start) : end]
    return {
        match.group(1): match.group(2).strip()
        for match in _TOKEN_DECLARATION.finditer(segment)
    }


def tokens(repo_root: Path | None = None) -> dict[str, str]:
    """当前令牌表。取值保持 CSS 原文（含 `px` 等单位）。"""
    path = tokens_css_path(repo_root)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise M2VError(f"无法读取设计令牌 {path}: {exc}") from exc
    table = theme_block(source)
    if not table:
        raise M2VError(f"{path} 的 `@theme static` 块里没有抽出任何令牌")
    return table


def px(name: str, repo_root: Path | None = None) -> float:
    """取一个长度令牌的像素值。

    要求取值确实带 `px`：令牌写错单位时应当在这里失败，
    而不是被当成一个没有单位的数字继续算下去。
    """
    value = _value(name, repo_root)
    if not value.endswith("px"):
        raise M2VError(f"令牌 {name} 应为 px 长度，实际是 {value}")
    try:
        return float(value[: -len("px")])
    except ValueError as exc:
        raise M2VError(f"令牌 {name} 的 px 取值无法解析：{value}") from exc


def number(name: str, repo_root: Path | None = None) -> float:
    """取一个无单位数值令牌（例如行高）。"""
    value = _value(name, repo_root)
    try:
        return float(value)
    except ValueError as exc:
        raise M2VError(f"令牌 {name} 应为无单位数值，实际是 {value}") from exc


def _value(name: str, repo_root: Path | None) -> str:
    table = tokens(repo_root)
    if name not in table:
        raise M2VError(f"设计令牌里没有 {name}")
    return table[name]
