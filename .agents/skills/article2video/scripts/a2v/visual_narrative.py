"""全片视觉叙事分析：区分文字幕与论证型图形，并执行版本化的预算规则。

本模块是「声明 + 结构反证」的确定性实现：

- 逐幕分类：场景声明了什么视觉模式（``visualIntent.mode``），场景树里有没有
  能承担论证的结构证据（图表、图片、连接关系、圆周关系布局）；
- 全片预算：文字幕占比、连续文字幕、非文字模式覆盖、声明与结构矛盾。

它只回答「结构上像不像文字幻灯片」：读场景树与导演声明，不读文章正文，
不调用模型，不对语义质量下结论——「图形是否真的承担论证」由 review 的
V6 人工结论兜底（:func:`review_v6` 解析 ``review.md``）。

分类口径（与 references/article-to-storyboard.md 的判据一一对应）：

- 论证型结构证据只有四类：``chart``、``image``、``connector``（连接关系）、
  ``radial``（≥2 个内容子节点的圆周关系布局）；
- 布局原语（stack/row/column/split/grid/overlay/group）、表面、形状、图标
  与单个数值都是「包装或文字」：把文字卡片换一层包装不改变其文字主导性质；
- 声明了非 ``typography`` 模式但拿不出结构证据的幕，判定为「声明与结构矛盾」。
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

#: 规则版本：预算阈值或分类口径变化时递增，测试据此固定行为。
RULE_VERSION = 1

#: 受控视觉模式。``typography`` 表示主要论点依赖文字成立，是唯一的文字模式。
VISUAL_MODES: tuple[str, ...] = (
    "metaphor",
    "process",
    "comparison",
    "cycle",
    "chart",
    "image",
    "typography",
)
TEXT_MODE = "typography"

#: 文字幕占比上限（对场景数 × 占比向上取整）。
TEXT_SCENE_RATIO = 0.30

#: 非文字模式覆盖下限：八幕及以上 3 种，少于八幕 2 种。
LONG_FILM_MIN_MODES = 3
SHORT_FILM_MIN_MODES = 2
LONG_FILM_SCENE_COUNT = 8

#: 结构证据类别。
EVIDENCE_CHART = "chart"
EVIDENCE_IMAGE = "image"
EVIDENCE_CONNECTOR = "connector"
EVIDENCE_RADIAL = "radial"

#: 中性布局原语：只负责摆放，不构成论证关系。
_NEUTRAL_LAYOUTS = frozenset({"stack", "row", "column", "split", "grid", "overlay", "group"})
#: 文字/数值/符号/装饰：内容即文字的节点类型。
_TEXT_LIKE = frozenset({"text", "number", "icon", "shape"})

#: 机械复述的动词前缀：「显示 X」「呈现 X」式复述不算视觉表达。
_RESTATE_PREFIXES = ("显示", "呈现", "展示", "表现", "表达")
_SENTENCE_PUNCT = "。．.！!？?，,；;：: "


def iter_nodes(tree: Any) -> list[dict[str, Any]]:
    """先序展开场景树的所有节点（含根）。非 dict 根返回空表。"""
    out: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        out.append(node)
        for child in node.get("children", []) or []:
            walk(child)

    walk(tree)
    return out


def _children(node: dict[str, Any]) -> list[dict[str, Any]]:
    kids = node.get("children", []) or []
    return [child for child in kids if isinstance(child, dict)]


def _has_content_descendant(node: dict[str, Any]) -> bool:
    """子树里是否有承载内容的节点（文字、数值、图片、图表或内容表面）。"""
    return any(
        child.get("type") in {"text", "number", "image", "chart", "surface"} or _has_content_descendant(child)
        for child in _children(node)
    )


def _carries_content(node: dict[str, Any]) -> bool:
    """作为关系布局的子节点时，算不算一个「语义对象」。"""
    node_type = node.get("type")
    if node_type in {"text", "number", "image", "chart", "surface"}:
        return True
    if isinstance(node_type, str) and (node_type in _NEUTRAL_LAYOUTS or node_type == "radial"):
        return _has_content_descendant(node)
    return False


def _is_plain_surface(node: dict[str, Any]) -> bool:
    """文字承载表面：子树只包含文本、数值、符号与装饰形状。"""
    return all(
        child.get("type") in _TEXT_LIKE or _is_plain_surface(child)
        for child in _children(node)
    )


def scene_evidence(scene: dict[str, Any]) -> list[str]:
    """收集一幕的论证型结构证据类别（去重、按固定顺序）。"""
    evidence: set[str] = set()
    for node in iter_nodes(scene.get("sceneTree")):
        node_type = node.get("type")
        if node_type == "chart":
            evidence.add(EVIDENCE_CHART)
        elif node_type == "image":
            evidence.add(EVIDENCE_IMAGE)
        elif node_type == "connector":
            evidence.add(EVIDENCE_CONNECTOR)
        elif node_type == "radial":
            content_children = [child for child in _children(node) if _carries_content(child)]
            if len(content_children) >= 2:
                evidence.add(EVIDENCE_RADIAL)
    return [kind for kind in (EVIDENCE_CHART, EVIDENCE_IMAGE, EVIDENCE_CONNECTOR, EVIDENCE_RADIAL) if kind in evidence]


def declared_mode(scene: dict[str, Any]) -> str | None:
    """逐幕声明的视觉模式；未声明（旧版分镜）返回 None。"""
    intent = scene.get("visualIntent")
    if not isinstance(intent, dict):
        return None
    mode = intent.get("mode")
    return mode if isinstance(mode, str) and mode in VISUAL_MODES else None


def analyze_scene(scene: dict[str, Any]) -> dict[str, Any]:
    """逐幕视觉叙事分类：声明、结构证据、文字主导判定与矛盾标记。

    - ``structuralClass``：``evidence``（有结构证据）/ ``text``（只有文字与包装）/
      ``code``（代码场景，结构不可静态核验）；
    - ``isTextScene``：声明为 ``typography``，或场景树被判为只有文字与包装；
      代码场景只按声明归类（结构无法核验，不得猜测）；
    - ``contradictsDeclaration``：声明了非文字模式却拿不出结构证据。
    """
    scene_id = str(scene.get("id"))
    mode = declared_mode(scene)
    renderer = scene.get("renderer")
    is_code = isinstance(renderer, dict) and renderer.get("kind") == "code"
    evidence = [] if is_code else scene_evidence(scene)
    if is_code:
        structural_class = "code"
    elif evidence:
        structural_class = "evidence"
    else:
        structural_class = "text"
    text_scene = (mode == TEXT_MODE) or (structural_class == "text")
    return {
        "id": scene_id,
        "declaredMode": mode,
        "structuralClass": structural_class,
        "evidence": evidence,
        "isTextScene": text_scene,
        "contradictsDeclaration": structural_class == "text" and mode is not None and mode != TEXT_MODE,
    }


def _text_scene_reason(scene: dict[str, Any], analysis: dict[str, Any]) -> str:
    """文字主导判据的人读描述：声明与结构证据各占一句。"""
    if analysis["structuralClass"] == "code":
        return "代码场景：结构不可静态核验，按声明归类"
    declared = analysis["declaredMode"]
    if analysis["structuralClass"] == "text":
        detail = "场景树只有文字、数值、符号图标、装饰形状或包裹它们的表面"
    else:
        detail = "场景树含结构证据：" + "、".join(analysis["evidence"])
    if declared is None:
        return f"未声明视觉模式；{detail}"
    if declared == TEXT_MODE:
        return f"声明为 {TEXT_MODE}（论点依赖文字成立）；{detail}"
    return f"声明为 {declared}；{detail}"


def _mode_coverage_required(scene_count: int) -> int:
    return LONG_FILM_MIN_MODES if scene_count >= LONG_FILM_SCENE_COUNT else SHORT_FILM_MIN_MODES


def analyze(data: dict[str, Any]) -> dict[str, Any]:
    """全片视觉叙事分析：逐幕分类 + 版本化预算结论。

    输出始终带 ``ruleVersion``；预算结论列出分子、分母、上限与场景 id，
    供严格校验与 review 的 V 系列共用同一口径。
    """
    scenes = [scene for scene in data.get("scenes", []) if isinstance(scene, dict)]
    analyses = [analyze_scene(scene) for scene in scenes]
    scene_count = len(analyses)
    text_ids = [item["id"] for item in analyses if item["isTextScene"]]
    adjacent_pairs = [
        [analyses[index - 1]["id"], analyses[index]["id"]]
        for index in range(1, len(analyses))
        if analyses[index - 1]["isTextScene"] and analyses[index]["isTextScene"]
    ]
    non_text_modes = sorted(
        {item["declaredMode"] for item in analyses if item["declaredMode"] and item["declaredMode"] != TEXT_MODE}
    )
    contradictions = [
        {"id": item["id"], "declaredMode": item["declaredMode"], "evidence": item["evidence"]}
        for item in analyses
        if item["contradictsDeclaration"]
    ]
    limit = math.ceil(scene_count * TEXT_SCENE_RATIO)
    required_modes = _mode_coverage_required(scene_count)
    findings: list[dict[str, Any]] = []
    if scene_count:
        if len(text_ids) > limit:
            findings.append(
                {
                    "rule": "text-scene-budget",
                    "scenes": text_ids,
                    "detail": {"actual": len(text_ids), "limit": limit, "sceneCount": scene_count},
                }
            )
        for pair in adjacent_pairs:
            findings.append({"rule": "adjacent-text-scenes", "scenes": pair, "detail": {}})
        if len(non_text_modes) < required_modes:
            findings.append(
                {
                    "rule": "non-text-mode-coverage",
                    "scenes": [],
                    "detail": {
                        "actual": len(non_text_modes),
                        "required": required_modes,
                        "modes": non_text_modes,
                        "sceneCount": scene_count,
                    },
                }
            )
        for item in contradictions:
            findings.append(
                {
                    "rule": "declaration-structure-conflict",
                    "scenes": [item["id"]],
                    "detail": {"declaredMode": item["declaredMode"], "evidence": item["evidence"]},
                }
            )
    return {
        "ruleVersion": RULE_VERSION,
        "sceneCount": scene_count,
        "scenes": [
            {**item, "reason": _text_scene_reason(scene, item)}
            for scene, item in zip(scenes, analyses)
        ],
        "textScenes": text_ids,
        "budget": {"actual": len(text_ids), "limit": limit, "sceneCount": scene_count},
        "adjacentTextPairs": adjacent_pairs,
        "nonTextModes": non_text_modes,
        "modeCoverage": {"actual": len(non_text_modes), "required": required_modes, "modes": non_text_modes},
        "contradictions": contradictions,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# review 的 V 系列（V1–V5 机检证据；V6 人工结论）
# ---------------------------------------------------------------------------


def review_gates(analysis: dict[str, Any]) -> dict[str, Any]:
    """把全片分析整理成体检报告的 V1–V5 闸门结构。

    V1–V4 是可判定的预算/覆盖/矛盾结论（与严格校验同一口径）；
    V5 是证据清单：列出全部结构判定的文字幕与判定依据，供人工在
    联系表上裁决，不参与退出码。
    """
    budget = analysis["budget"]
    coverage = analysis["modeCoverage"]
    v1_fail = budget["actual"] > budget["limit"]
    v2_fail = bool(analysis["adjacentTextPairs"])
    v3_fail = coverage["actual"] < coverage["required"]
    v4_fail = bool(analysis["contradictions"])
    return {
        "ruleVersion": RULE_VERSION,
        "v1": {
            "id": "V1",
            "title": "文字幕预算",
            "status": "fail" if v1_fail else "pass",
            "value": budget["actual"],
            "limit": budget["limit"],
            "sceneCount": budget["sceneCount"],
            "scenes": analysis["textScenes"],
        },
        "v2": {
            "id": "V2",
            "title": "连续文字幕",
            "status": "fail" if v2_fail else "pass",
            "pairs": analysis["adjacentTextPairs"],
        },
        "v3": {
            "id": "V3",
            "title": "非文字模式覆盖",
            "status": "fail" if v3_fail else "pass",
            "value": coverage["actual"],
            "required": coverage["required"],
            "modes": coverage["modes"],
        },
        "v4": {
            "id": "V4",
            "title": "声明与结构一致",
            "status": "fail" if v4_fail else "pass",
            "scenes": analysis["contradictions"],
        },
        "v5": {
            "id": "V5",
            "title": "文字主导候选",
            "status": "pass" if not analysis["textScenes"] else "candidates",
            "scenes": [
                {
                    "id": item["id"],
                    "declaredMode": item["declaredMode"],
                    "structuralClass": item["structuralClass"],
                    "evidence": item["evidence"],
                    "reason": item["reason"],
                }
                for item in analysis["scenes"]
                if item["isTextScene"]
            ],
        },
    }


#: V6 的人工结论必须达到的最低分（满分 5）。
V6_MIN_SCORE = 4


def review_v6(path: str | Path, candidates: list[str]) -> dict[str, Any]:
    """解析 ``review.md`` 里的人工「图形承担论证」结论（V6）。

    分数来自六项评分表的「图形论证」行，或 V6 小节里的 ``评分：N/5``；
    V5 候选场景在 ``候选裁决`` 小节逐条写 ``- <scene-id>：结论`` 视为已裁决。
    未填写结论时状态为「待评审」；评分低于 4/5 或存在未裁决候选时
    ``publishable`` 为 False——缺失或跳过永远不会被记成通过。
    """
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError:
        text = ""
    score: int | None = None
    resolved: set[str] = set()
    if text:
        row = re.search(r"^\s*\|\s*图形论证\s*\|\s*([0-5])\s*\|", text, re.MULTILINE)
        if row:
            score = int(row.group(1))
        else:
            inline = re.search(r"评分[:：]\s*([0-5])\s*(?:/\s*5)?(?!\d)", text)
            if not inline:
                inline = re.search(r"(?:图形承担论证|图形论证|V6)[^\n]*?([0-5])\s*/\s*5", text)
            if inline:
                score = int(inline.group(1))
        section = re.search(r"^\s*#{2,6}\s*(?:V5[^\n]*?)?候选裁决[^\n]*\n(.*?)(?=^\s*#{2,6}\s|\Z)", text, re.MULTILINE | re.DOTALL)
        if section:
            resolved = set(re.findall(r"^\s*[-*]\s*([A-Za-z0-9_-]+)\s*[:：]", section.group(1), re.MULTILINE))
    unresolved = [scene_id for scene_id in candidates if scene_id not in resolved]
    if score is None:
        status = "待评审"
    elif score < V6_MIN_SCORE:
        status = "不通过"
    elif unresolved:
        status = "候选未裁决"
    else:
        status = "通过"
    return {
        "id": "V6",
        "title": "图形承担论证（人工）",
        "status": status,
        "score": score,
        "minScore": V6_MIN_SCORE,
        "unresolvedCandidates": unresolved,
        "publishable": status == "通过",
        "source": str(source) if text else f"未找到评审结论：{source}",
    }


# ---------------------------------------------------------------------------
# 字段级检查：机械复述检测（供校验器复用）
# ---------------------------------------------------------------------------


def is_restatement(show_without_text: str, claim: str) -> bool:
    """「无正文视觉表达」是否只是复述论点。

    命中以下任一情形即为复述：与 ``claim`` 完全相同（忽略首尾标点空白），
    或是「显示/呈现/展示/表现/表达 + claim」式的机械包装。
    只检测明确的机械模式，不做通用自然语言相似度判断。
    """
    show = str(show_without_text).strip().strip(_SENTENCE_PUNCT)
    core = str(claim).strip().strip(_SENTENCE_PUNCT)
    if not show or not core:
        return False
    if show == core:
        return True
    for prefix in _RESTATE_PREFIXES:
        if show.startswith(prefix):
            rest = show[len(prefix):].lstrip(_SENTENCE_PUNCT).rstrip(_SENTENCE_PUNCT)
            if rest == core:
                return True
    return False
