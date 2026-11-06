"""文章正文提取与非空计数。

这里只保留仍被生产路径使用的两件事：剥掉首个 Markdown 一级标题取正文，以及按
Unicode 标点/空白规则数非空字符。候选稿保存与输入审查记录分别由
`explainer_cli._candidate` 与 `explainer_review` 负责，本模块不再承担字数门禁。
"""
from __future__ import annotations

from pathlib import Path

from m2v.core.text import count_characters


def extract_body(text: str) -> str:
    """移除第一个非空行上的 Markdown 一级标题；不猜测普通文本首行是标题。"""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip():
            if line.startswith("# ") and line[2:].strip():
                return "\n".join(lines[index + 1 :])
            break
    return text


def active_source(article_dir: str | Path) -> Path:
    """采用稿存在时作为当前制作输入；原始 article.md 始终保留。"""
    root = Path(article_dir)
    adopted = root / "article.accepted.md"
    return adopted if adopted.is_file() else root / "article.md"
