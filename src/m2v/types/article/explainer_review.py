"""讲解源文的人工语义审查；不对审美或忠实程度自动判定通过。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from m2v.core.errors import M2VError
from m2v.core.project import _write_json
from . import explainer
from .article_text import extract_body, count_characters


def template(root: Path, project: dict) -> dict:
    source = explainer.source_file(root, project)
    return {"schemaVersion": 5, "source": {"path": source.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
            "charCount": count_characters(extract_body(source.read_text(encoding="utf-8-sig"))),
            "status": "pending", "claim": "", "rationale": "", "problemSpans": [], "reviewer": ""}


def require_input(root: Path, project: dict) -> None:
    current = template(root, project)
    try:
        review = json.loads((root / "outputs/input-review.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise M2VError("请先运行 m2v article input-review --storyboard <路径>，完成 outputs/input-review.json 语义审查") from exc
    if (review.get("schemaVersion") != 5 or review.get("source") != current["source"]
            or review.get("charCount") != current["charCount"] or review.get("status") != "pass"
            or any(not isinstance(review.get(key), str) or not review[key].strip() for key in ("claim", "rationale", "reviewer"))
            or review.get("problemSpans") != []):
        raise M2VError("当前源文未通过讲解语义审查或审查已过期；请重新审查")


def create_input(root: Path, project: dict) -> Path:
    target = root / "outputs/input-review.json"
    _write_json(target, template(root, project))
    return target


def criteria(_root: Path, _project: dict, _prepared: dict) -> dict[str, str]:
    return {"informationClarity": "观点与摘要清晰，旁白忠实于当前源文",
            "templateLayout": "五模板排版与手机可读性，文字无溢出或字幕遮挡",
            "graphicRelation": "对比、步骤、因果与图片确实帮助说明观点",
            "narrationSync": "逐项出现与当前旁白同步，字幕和音频完整",
            "readingRhythm": "每幕阅读停留足够，转场连贯，全片不超过一分钟"}
