"""跨类型共享的文本计数口径。

字数只数 Unicode 非标点、非空白码点；准备校验、阅读速度报告与节奏测量共用这一份实现，
避免「同一个字怎么算」出现第二套规则。
"""
from __future__ import annotations

import unicodedata


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
