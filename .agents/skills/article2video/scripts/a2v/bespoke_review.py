"""作品定制动画的逐幕人工动态评审。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DIMENSIONS = ("焦点清晰度", "动作解释力", "节奏变化", "转场连贯性", "结果可读性")
MIN_SCORE = 4


def uses_code_scenes(storyboard: dict[str, Any]) -> bool:
    return any(
        isinstance(scene, dict)
        and isinstance(scene.get("renderer"), dict)
        and scene["renderer"].get("kind") == "code"
        for scene in storyboard.get("scenes", [])
    )


def review(path: str | Path, storyboard: dict[str, Any]) -> dict[str, Any]:
    """解析动态评审表；只对使用作品级代码场景的分镜启用发布闸门。"""
    required = uses_code_scenes(storyboard)
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError:
        text = ""

    section = re.search(
        r"^\s*#{2,6}\s*定制动画动态评审\s*$([\s\S]*?)(?=^\s*#{2,6}\s|\Z)",
        text,
        re.MULTILINE,
    )
    body = section.group(1) if section else ""
    enabled = bool(re.search(r"^\s*状态\s*[:：]\s*启用\s*$", body, re.MULTILINE))
    rows: dict[str, list[str]] = {}
    for line in body.splitlines():
        if not line.lstrip().startswith("|") or line.lstrip().startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(DIMENSIONS) + 2 or cells[0] == "场景":
            continue
        rows[cells[0]] = cells[1:]

    scene_ids = [str(scene.get("id")) for scene in storyboard.get("scenes", []) if isinstance(scene, dict)]
    scores: dict[str, dict[str, int]] = {}
    missing: list[str] = []
    low: list[dict[str, Any]] = []
    for scene_id in scene_ids:
        values = rows.get(scene_id)
        parsed: dict[str, int] = {}
        if values is not None:
            for label, raw in zip(DIMENSIONS, values[:-1]):
                match = re.fullmatch(r"([1-5])(?:\s*/\s*5)?", raw)
                if match:
                    parsed[label] = int(match.group(1))
        if values is None or len(parsed) != len(DIMENSIONS) or not values[-1].strip():
            missing.append(scene_id)
            continue
        scores[scene_id] = parsed
        low.extend(
            {"scene": scene_id, "dimension": dimension, "score": score}
            for dimension, score in parsed.items()
            if score < MIN_SCORE
        )

    if not required:
        status = "不适用"
    elif not section or not enabled or missing:
        status = "待评审"
    elif low:
        status = "不通过"
    else:
        status = "通过"
    return {
        "required": required,
        "status": status,
        "minScore": MIN_SCORE,
        "dimensions": list(DIMENSIONS),
        "scenes": scores,
        "missingScenes": missing,
        "belowThreshold": low,
        "publishable": not required or status == "通过",
        "source": str(source) if text else f"未找到评审结论：{source}",
    }
