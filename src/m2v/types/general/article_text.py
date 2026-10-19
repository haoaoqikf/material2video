"""文章正文提取与非空计数。

这里只保留仍被生产路径使用的两件事：剥掉首个 Markdown 一级标题取正文，以及按
Unicode 标点/空白规则数非空字符。候选稿保存与输入审查记录分别由
`explainer_cli._candidate` 与 `explainer_review` 负责，本模块不再承担字数门禁。
"""
from __future__ import annotations

import unicodedata
from pathlib import Path


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


def active_source(article_dir: str | Path) -> Path:
    """采用稿存在时作为当前制作输入；原始 article.md 始终保留。"""
    root = Path(article_dir)
    adopted = root / "article.accepted.md"
    return adopted if adopted.is_file() else root / "article.md"
