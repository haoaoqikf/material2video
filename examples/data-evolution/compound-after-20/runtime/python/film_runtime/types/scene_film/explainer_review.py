"""讲解源文的人工语义审查；不对审美或忠实程度自动判定通过。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from film_runtime.core.errors import VideoError
from film_runtime.core.project import _write_json
from . import explainer
from .article_text import extract_body, count_characters


def template(root: Path, project: dict) -> dict:
    source = explainer.source_file(root, project)
    return {"schemaVersion": 5, "source": {"path": source.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
            "charCount": count_characters(extract_body(source.read_text(encoding="utf-8-sig"))),
            "status": "pending", "claim": "", "rationale": "", "problemSpans": [], "reviewer": ""}


def require_input(root: Path, project: dict) -> None:
    if explainer.topic_input(explainer.load(root, project)):
        return
    current = template(root, project)
    try:
        review = json.loads((root / "outputs/input-review.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise VideoError("请完成本作品outputs/input-review.json的源文语义审查；格式由本地explainer_review.template提供") from exc
    if (review.get("schemaVersion") != 5 or review.get("source") != current["source"]
            or review.get("charCount") != current["charCount"] or review.get("status") != "pass"
            or any(not isinstance(review.get(key), str) or not review[key].strip() for key in ("claim", "rationale", "reviewer"))
            or review.get("problemSpans") != []):
        raise VideoError("当前源文未通过讲解语义审查或审查已过期；请重新审查")


def create_input(root: Path, project: dict) -> Path:
    target = root / "outputs/input-review.json"
    _write_json(target, template(root, project))
    return target
