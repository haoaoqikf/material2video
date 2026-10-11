"""全片节奏人工评分解析与发布门槛。"""

from __future__ import annotations

import re


MIN_SCORE = 4
_TIMECODE = re.compile(r"(?<!\d)(?:[0-5]?\d):[0-5]\d(?:\.\d+)?(?!\d)")
_STAGE_REFERENCE = re.compile(r"阶段\s*[：:]\s*[\w\u4e00-\u9fff-]+")


def review(text: str) -> dict:
    """解析 ``review.md`` 的全片节奏评分。

    支持标准评分表的「节奏」行，或独立的「## 节奏」小节。发布证据必须
    定位到时间码或明确阶段；仅有总分、笼统评价或分镜声明不构成动态评审。
    """
    cleaned = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    score, evidence, issue = _table_score(cleaned)
    if issue:
        return _result("pending", None, evidence, issue)
    if score is None:
        score, evidence, issue = _section_score(cleaned)
        if issue:
            return _result("pending", None, evidence, issue)

    if score is None:
        return _result("pending", None, evidence, "缺少全片节奏单项评分")
    if not evidence.strip():
        return _result("pending", score, evidence, "节奏评分缺少有声预演的时间或阶段证据")
    if not (_TIMECODE.search(evidence) or _STAGE_REFERENCE.search(evidence)):
        return _result("pending", score, evidence, "节奏依据须定位到有声预演的时间码或明确阶段")
    if score < MIN_SCORE:
        return _result("fail", score, evidence, f"节奏评分 {score}/5 低于发布门槛 {MIN_SCORE}/5")
    return _result("pass", score, evidence, f"节奏评分 {score}/5 达到发布门槛")


def _table_score(text: str) -> tuple[int | None, str, str | None]:
    matches: list[tuple[int | None, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 3 or cells[0] not in {"节奏", "节奏变化"}:
            continue
        if not re.fullmatch(r"[0-5]", cells[1]):
            matches.append((None, ""))
            continue
        evidence = " | ".join(cell for cell in cells[2:] if cell)
        matches.append((int(cells[1]), evidence))
    if len(matches) > 1:
        return None, "", "发现多个节奏评分行，请保留唯一评分及其证据"
    if matches:
        score, evidence = matches[0]
        return score, evidence, None
    return None, "", None


def _section_score(text: str) -> tuple[int | None, str, str | None]:
    matches = list(re.finditer(
        r"^\s*#{1,6}\s*(?:全片)?节奏(?:评审)?[^\n]*\n(.*?)(?=^\s*#{1,6}\s|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    ))
    if len(matches) > 1:
        return None, "", "发现多个节奏评审小节，请保留唯一评分及其证据"
    if not matches:
        return None, "", None
    match = matches[0]
    body = match.group(1)
    score_match = re.search(r"(?:评分|分数)\s*[：:]\s*([0-5])\s*(?:/\s*5)?(?!\d)", body)
    evidence_match = re.search(r"(?:依据|证据)\s*[：:]\s*([^\n]+)", body)
    return (
        int(score_match.group(1)) if score_match else None,
        evidence_match.group(1).strip() if evidence_match else "",
        None,
    )


def _result(status: str, score: int | None, evidence: str, detail: str) -> dict:
    return {
        "id": "rhythm",
        "title": "全片节奏",
        "status": status,
        "score": score,
        "minScore": MIN_SCORE,
        "evidence": evidence,
        "detail": detail,
        "publishable": status == "pass",
    }
