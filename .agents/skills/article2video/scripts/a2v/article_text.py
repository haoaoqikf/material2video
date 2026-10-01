"""文章与最终口播的标准字数统计。Python/TypeScript 行为由固定测试向量共同约束。"""
from __future__ import annotations

import unicodedata

MIN_STANDARD_CHARS = 130
MAX_STANDARD_CHARS = 170
COUNTING_VERSION = 1


def extract_body(text: str) -> str:
    """移除第一个非空行上的 Markdown 一级标题；不猜测普通文本首行是标题。"""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip():
            if line.startswith("# ") and line[2:].strip():
                return "\n".join(lines[index + 1 :])
            break
    return text


def count_characters(text: str) -> int:
    """排除 Unicode 标点和 White_Space，其余 Unicode 码点逐个计数。"""
    return sum(
        1
        for char in text
        if not unicodedata.category(char).startswith("P") and not _is_white_space(char)
    )


def _is_white_space(char: str) -> bool:
    r"""Unicode White_Space 属性；与 JS `\p{White_Space}` 使用相同码点集。"""
    codepoint = ord(char)
    return (
        0x0009 <= codepoint <= 0x000D
        or codepoint in {0x0020, 0x0085, 0x00A0, 0x1680, 0x2028, 0x2029, 0x202F, 0x205F, 0x3000}
        or 0x2000 <= codepoint <= 0x200A
    )


def standard_length_result(text: str) -> dict[str, int | bool]:
    count = count_characters(text)
    return {"count": count, "pass": MIN_STANDARD_CHARS <= count <= MAX_STANDARD_CHARS}
