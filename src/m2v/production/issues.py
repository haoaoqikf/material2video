"""唯一问题表；独立失败只能由当前、同范围的独立复查关闭。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from . import ledger
from .model import VERSION, fields, identifier, text
from .storage import atomic_text, read, local

FENCE = re.compile(r"^```m2v-issues-v2\s*\n(.*?)^```\s*$", re.M | re.S)
CAUSES = {"implementation", "design", "mixed", "undetermined"}


def save(root: Path, items: list):
    path = outputs(root) / "visual-notes.md"
    source = (
        path.read_text(encoding="utf-8") if path.exists() else "# 制作观察与问题\n\n"
    )
    block = (
        "```m2v-issues-v2\n"
        + json.dumps(
            {
                "version": VERSION,
                "cycleId": ledger.cycle(root)["cycleId"],
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n```\n"
    )
    if FENCE.search(source):
        source = FENCE.sub(lambda _: block, source)
    else:
        # 新周期保留的原文件已由 start 归档，当前只保留新问题块。
        source = "# 制作观察与问题\n\n" + block
    atomic_text(path, source)


def parse(source):
    matches = FENCE.findall(source)
    if len(matches) != 1:
        raise M2VError("问题记录须使用唯一 m2v-issues-v2 块；旧格式不兼容")
    try:
        value = json.loads(matches[0])
        fields(value, {"version", "cycleId", "items"})
        if value["version"] != VERSION or not isinstance(value["items"], list):
            raise ValueError("问题格式无效")
    except (ValueError, TypeError) as exc:
        raise M2VError(f"问题记录损坏：{exc}") from exc
    seen = set()
    for item in value["items"]:
        fields(
            item,
            {
                "id",
                "cycleId",
                "status",
                "required",
                "round",
                "scope",
                "reportId",
                "versionRefs",
                "cause",
                "observations",
            },
            {"closureReportId", "evidence"},
        )
        identifier(item["id"])
        if (
            item["id"] in seen
            or item["status"] not in ("open", "closed")
            or type(item["required"]) is not bool
            or item["cause"] not in CAUSES
            or item["round"] not in ("trial", "final", "internal")
            or not isinstance(item["versionRefs"], list)
            or any(not isinstance(v, str) for v in item["versionRefs"])
            or item["cycleId"] != value["cycleId"]
        ):
            raise M2VError("问题状态、周期、原因或引用无效")
        seen.add(item["id"])
        text(item["observations"])
    return value


def load(root: Path, *, required=False, check_closures=True, pending_report=None):
    path = outputs(root) / "visual-notes.md"
    if not path.exists() and not required:
        return []
    try:
        value = parse(
            local(outputs(root), "visual-notes.md").read_text(encoding="utf-8")
        )
    except OSError as exc:
        raise M2VError(f"问题记录不可读：{exc}") from exc
    if value["cycleId"] != ledger.cycle(root)["cycleId"]:
        raise M2VError("问题记录属于旧周期")
    events, errors = ledger.history(root)
    if errors:
        raise M2VError("; ".join(errors))
    by_report = {p["reportId"]: p for p in value["items"] if p["reportId"]}
    for event in events:
        if event["type"] != "review" or event["data"]["reportId"] == pending_report:
            continue
        if not ledger.evidence_valid(root, event["data"]["receipts"]):
            raise M2VError("问题引用的原评审记录损坏")
        report = read(local(outputs(root), event["data"]["reportPath"]))
        if report["verdict"] == "fail":
            item = by_report.get(report["id"])
            if (
                not item
                or not item["required"]
                or item["round"] != report["round"]
                or item["scope"] != scope(root, report)
            ):
                raise M2VError("独立失败问题缺失或原条件被改写")
    if check_closures:
        for item in value["items"]:
            if item["status"] == "closed":
                try:
                    validate_closure(root, item)
                except M2VError:
                    # 只读投影为重开；原关闭历史留在文件中，不悄悄改写。
                    item["status"] = "open"
    return value["items"]


def scope(root, report):
    from .samples import scope_sources
    private = read(
        ledger.directory(root)
        / "packages"
        / f"{read(local(outputs(root), report['packPath']))['reviewId']}.json"
    )
    request = private["request"]
    return {
        "focus": report["focus"],
        "displaySizes": sorted(request["displaySizes"]),
        "references": private["binding"]["references"],
        "conditions": request.get("conditions", []),
        "items": [
            {k: item[k] for k in ("id", "window", "dynamic")}
            for item in request["items"]
        ],
        "sources": scope_sources(root, request),
        "sceneIds": request["sceneIds"],
    }


def from_review(root, report):
    items = load(root, required=True, pending_report=report["id"])
    if any(p["reportId"] == report["id"] for p in items):
        return
    items.append(
        dict(
            id="REVIEW-" + report["id"],
            cycleId=report["cycleId"],
            status="open",
            required=True,
            round=report["round"],
            scope=scope(root, report),
            reportId=report["id"],
            versionRefs=["current"],
            cause="undetermined",
            observations=report["observations"],
        )
    )
    save(root, items)


def covers(original, current, round):
    """终审覆盖当前全片；局部复查须覆盖原窗口，目标与显示条件均不得降低。"""
    conditions = ("focus", "displaySizes", "references", "conditions")
    if any(original[key] != current[key] for key in conditions):
        return False
    if round == "final":
        return True  # 打包器已经强制当前完整候选；剪短或重排不要求保留旧全片帧数。
    if any(original[key] != current[key] for key in ("sources", "sceneIds")):
        return False
    selected = {item["id"]: item for item in current["items"]}
    return all(
        item["id"] in selected
        and selected[item["id"]]["dynamic"] == item["dynamic"]
        and selected[item["id"]]["window"][0] <= item["window"][0]
        and selected[item["id"]]["window"][1] >= item["window"][1]
        for item in original["items"]
    )


def validate_closure(root: Path, item: dict):
    from . import reviews
    from . import targets
    from m2v.core.project import load_project

    if item.get("status") == "closed":
        if item.get("cause") == "undetermined":
            raise M2VError("原因未定位不能关闭")
        if item.get("reportId"):
            expected_scope, target_position = targets.effective_scope(root, item)
            report = reviews.current_report(
                root, load_project(root)[1], identifier(item.get("closureReportId"))
            )
            if (
                report["isolation"] != "independent-subagent"
                or report["verdict"] != "pass"
                or report["round"] != item["round"]
                or report["reviewType"] != "blind"
                or not covers(expected_scope, scope(root, report), item["round"])
            ):
                raise M2VError("必须以当前对应范围的独立通过复查关闭")
            if report["requiresComparison"]:
                events, _ = ledger.history(root)
                pairs = []
                for event in events:
                    if (
                        event["type"] == "review"
                        and event["data"]["reportId"] != report["id"]
                    ):
                        try:
                            # 先按已封存报告的同轮身份筛选，避免为无关历史报告
                            # 重算整个媒体/源码绑定；匹配项仍执行完整有效性验证。
                            candidate = read(local(outputs(root), event["data"]["reportPath"]))
                            if candidate.get("blindId") != report["id"]:
                                continue
                            pairs.append(
                                reviews.current_report(
                                    root,
                                    load_project(root)[1],
                                    event["data"]["reportId"],
                                )
                            )
                        except M2VError:
                            continue  # 无关过期报告不能阻止当前有效复查。
                if not any(
                    p.get("blindId") == report["id"]
                    and p["verdict"] == "pass"
                    and p["isolation"] == "independent-subagent"
                    for p in pairs
                ):
                    raise M2VError("复查缺少同轮目标对照")
            events, _ = ledger.history(root)
            positions = {
                e["data"].get("reportId"): i
                for i, e in enumerate(events)
                if e["type"] == "review"
            }
            if positions[report["id"]] <= max(positions[item["reportId"]], target_position):
                raise M2VError("复查必须晚于原失败及用户目标变更")
            targets.validate_fresh_observation(root, report, positions[item['reportId']])
            targets.validate_fresh_observation(root, report, target_position)
        elif not ledger.evidence_valid(root, item.get("evidence", [])):
            raise M2VError("内部问题关闭需要实际复查证据")


def update(root: Path, item: dict):
    items = load(root, required=True, check_closures=False)
    previous = next((p for p in items if p["id"] == item.get("id")), None)
    if item.get("cycleId") != ledger.cycle(root)["cycleId"]:
        raise M2VError("跨周期报告不能关闭旧问题")
    if previous and any(
        previous[k] != item.get(k) for k in ("required", "round", "scope", "reportId")
    ):
        raise M2VError("不得改写原问题范围、独立失败身份或必改性质")
    if not previous and item.get("reportId"):
        raise M2VError("独立失败问题只能由导入评审产生")
    validate_closure(root, item)
    updated = [p for p in items if p["id"] != item["id"]] + [item]
    # 共用解析器核验写入内容，防止损坏记录破坏后续状态与清理。
    parse(
        "```m2v-issues-v2\n"
        + json.dumps(
            {
                "version": VERSION,
                "cycleId": ledger.cycle(root)["cycleId"],
                "items": updated,
            }
        )
        + "\n```\n"
    )
    save(root, updated)
