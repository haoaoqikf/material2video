"""文章与最终口播的标准字数统计。Python/TypeScript 行为由固定测试向量共同约束。"""
from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

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


def review_template(text: str, source_path: str, source_sha256: str) -> dict[str, Any]:
    body = extract_body(text)
    length = standard_length_result(body)
    return {
        "countingVersion": COUNTING_VERSION,
        "source": {"path": source_path, "sha256": source_sha256},
        "charCount": length["count"],
        "lengthStatus": "pass" if length["pass"] else "fail",
        "singleScene": {"status": "pending", "claim": "", "metaphor": "", "problemSpans": [], "rationale": ""},
        "status": "fail" if not length["pass"] else "pending",
        "assessment": None,
    }


def review_status(review: Any, current_sha256: str | None = None) -> str:
    if not isinstance(review, dict) or review.get("countingVersion") != COUNTING_VERSION:
        return "pending"
    source = review.get("source")
    if (not isinstance(source, dict) or not isinstance(source.get("path"), str)
            or not isinstance(source.get("sha256"), str) or not source["sha256"]):
        return "pending"
    if current_sha256 is not None and source["sha256"] != current_sha256:
        return "pending"
    if type(review.get("charCount")) is not int:
        return "pending"
    length_status = review.get("lengthStatus")
    expected_length = "pass" if MIN_STANDARD_CHARS <= review["charCount"] <= MAX_STANDARD_CHARS else "fail"
    if length_status != expected_length:
        return "pending"
    semantic = review.get("singleScene")
    if not isinstance(semantic, dict) or semantic.get("status") not in {"pass", "fail", "pending"}:
        return "pending"
    if not isinstance(semantic.get("problemSpans"), list):
        return "pending"
    assessment = review.get("assessment")
    semantic_complete = all(isinstance(semantic.get(key), str) and semantic[key].strip()
                            for key in ("claim", "metaphor", "rationale"))
    if semantic["status"] != "pending":
        if not semantic_complete or not isinstance(assessment, dict) or assessment.get("reviewer") != "ai":
            return "pending"
        if any(not isinstance(assessment.get(key), str) or not assessment[key].strip()
               for key in ("model", "session")):
            return "pending"
    if length_status == "fail" or semantic["status"] == "fail":
        return "fail"
    if length_status == "pass" and semantic["status"] == "pass" and semantic_complete:
        return "pass"
    return "pending"


def read_source(path: str | Path) -> tuple[str, str]:
    """Read UTF-8 source and return text plus digest of original bytes."""
    import hashlib

    source = Path(path)
    raw = source.read_bytes()
    return raw.decode("utf-8-sig"), hashlib.sha256(raw).hexdigest()


def review_for_file(path: str | Path, workspace_root: str | Path) -> dict[str, Any]:
    source = Path(path).resolve()
    workspace = Path(workspace_root).resolve()
    if not source.is_relative_to(workspace):
        raise ValueError(f"文章输入必须位于工作区内：{source}")
    text, digest = read_source(source)
    return review_template(text, source.relative_to(workspace).as_posix(), digest)


def active_source(article_dir: str | Path) -> Path:
    """采用稿存在时作为当前制作输入；原始 article.md 始终保留。"""
    root = Path(article_dir)
    adopted = root / "article.accepted.md"
    return adopted if adopted.is_file() else root / "article.md"


def save_candidate(article_dir: str | Path, text: str, source_sha256: str) -> dict[str, Any]:
    """只保存合规候选；调用方负责证明其对应的审查原文仍有效。"""
    count = count_characters(extract_body(text))
    if not MIN_STANDARD_CHARS <= count <= MAX_STANDARD_CHARS:
        raise ValueError(f"候选稿正文为 {count} 字，须在 {MIN_STANDARD_CHARS}～{MAX_STANDARD_CHARS} 字")
    root = Path(article_dir)
    root.mkdir(parents=True, exist_ok=True)
    target = root / "article.candidate.md"
    target.write_text(text.rstrip() + "\n", encoding="utf-8")
    _, digest = read_source(target)
    return {"path": target.name, "sha256": digest, "basedOn": source_sha256, "charCount": count}
