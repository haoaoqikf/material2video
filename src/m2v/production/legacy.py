"""只在开启新版周期时承接历史必改。旧报告不会进入当前评审协议。"""
from __future__ import annotations

import json

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.core.project import load_project
from . import ledger
from .model import fields, identifier
from .storage import local, read


def unresolved(root, cycle, notes):
    from .issues import parse

    fields(cycle, {"version", "cycleId", "projectId", "createdAt", "finalFocuses", "basis"})
    version = cycle["version"]
    if type(version) is not int or version not in (2, 3):
        raise M2VError("无法识别历史评审版本")
    base = outputs(root)
    history = local(base, f"production/{cycle['cycleId']}/history.jsonl")
    value = parse(notes.read_text(encoding="utf-8"), version=version)
    if value["cycleId"] != cycle["cycleId"]:
        raise M2VError("历史问题周期身份不一致")
    reports, packages, seen = {}, {}, set()
    for position, line in enumerate(history.read_text(encoding="utf-8").splitlines()):
        event = json.loads(line)
        fields(event, {"id", "version", "type", "time", "cycleId", "projectId", "data"})
        if (event["id"] in seen or any(event[key] != cycle[key]
                                      for key in ("version", "cycleId", "projectId"))):
            raise M2VError("历史制作账本身份损坏")
        seen.add(identifier(event["id"]))
        if event["type"] == "package":
            packages[event["data"]["reviewId"]] = event["data"]["receipt"]
        elif event["type"] == "review":
            data = event["data"]
            if not ledger.evidence_valid(root, data["receipts"]):
                raise M2VError("历史评审记录摘要失配")
            report = read(local(base, data["reportPath"]))
            if report["id"] != data["reportId"] or report["id"] in reports:
                raise M2VError("历史报告身份不一致")
            reports[report["id"]] = (report, data["receipts"], position)
    registered = {item["reportId"]: item for item in value["items"] if item["reportId"]}
    if any(report["verdict"] == "fail"
           and (report_id not in registered or not registered[report_id]["required"])
           for report_id, (report, _, _) in reports.items()):
        raise M2VError("历史独立失败缺少关联必改，无法承接")
    carried = []
    for item in value["items"]:
        if not item["required"]:
            continue
        report_id = item["reportId"]
        if report_id and report_id not in reports:
            raise M2VError("历史必改引用未知报告")
        if item["status"] == "closed":
            if report_id:
                if _known_closure(root, item, reports, packages):
                    continue
            elif ledger.evidence_valid(root, item.get("evidence", [])):
                continue
        carried.append((item, reports[report_id][1] if report_id else []))
    return carried


def _known_closure(root, item, reports, packages):
    """只承认仍可核验的历史关闭。旧封存证据不参与新版通过。"""
    base = outputs(root)
    pair = reports.get(item.get("closureReportId"))
    if not pair:
        return False
    closed, _, position = pair
    if (closed["verdict"] != "pass" or closed["round"] != item["round"]
            or closed["isolation"] != "independent-subagent"
            or position <= reports[item["reportId"]][2]):
        return False
    try:
        pack = read(local(base, closed["packPath"]))
        sealed = packages[pack["reviewId"]]
        if not ledger.evidence_valid(root, [sealed, {"path": closed["packPath"], "sha256": closed["packSha256"]}]):
            return False
        private = read(local(base, sealed["path"]))
        binding = private["binding"]
        if (any(not ledger.evidence_valid(root, entries)
                for key in ("media", "references") if (entries := binding[key]))
                or ledger.sources(root, private["request"]) != binding["sources"]):
            return False
        if closed.get("requiresComparison") and not any(
            report.get("blindId") == closed["id"] and report["verdict"] == "pass"
            and report["isolation"] == "independent-subagent" and pos > position
            for report, _, pos in reports.values()
        ):
            return False
        if item["round"] == "final":
            from .film_review import qa_binding
            current = qa_binding(root, load_project(root)[1])
            return all(current[key] == binding["final"][key] for key in current)
        return True
    except (M2VError, OSError, ValueError, KeyError, TypeError):
        return False


def carry(items, cycle_id, archive):
    return [
        {
            "id": item["id"], "cycleId": cycle_id, "status": "open", "required": True,
            "round": "internal", "reportId": None, "versionRefs": item["versionRefs"],
            "cause": item["cause"], "observations": item["observations"],
            "scope": {"legacy": {"round": item["round"], "scope": item["scope"],
                                 "reportId": item["reportId"], "notes": archive, "receipts": refs}},
        }
        for item, refs in items
    ]


def validate_carried(root, items, events):
    by_id = {item["id"]: item for item in items}
    for event in events:
        if event["type"] != "started":
            continue
        for original in event["data"].get("carriedIssues", []):
            record = by_id.get(original["id"])
            if not record or any(record[key] != original[key] for key in ("round", "scope", "required", "reportId")):
                raise M2VError("新版问题表缺少承接的历史必改或范围已改写")
            scope = original["scope"]["legacy"]
            if not ledger.evidence_valid(root, [scope["notes"], *scope["receipts"]]):
                raise M2VError("承接的历史必改原件缺失或摘要失配")


def validate_resolution(root, item):
    from . import film_review, issues, reviews

    project = load_project(root)[1]
    old = item["scope"]["legacy"]
    if not ledger.evidence_valid(root, item.get("evidence", [])):
        raise M2VError("承接的历史问题须提供当前修复及对应窗口的实际复查证据")
    if old["round"] == "final":
        events, errors = ledger.history(root)
        if errors:
            raise M2VError("制作账本损坏")
        qa = {"status": "pass", **film_review.qa_binding(root, project)}
        if film_review.whole_film_state(events, qa)["status"] != "pass":
            raise M2VError("历史整片问题须由当前整片证据复核确认修复")
    elif old["reportId"]:
        report = reviews.current_report(root, project, identifier(item.get("closureReportId")))
        if (report["verdict"] != "pass" or report["isolation"] != "independent-subagent"
                or not issues.covers(old["scope"], issues.scope(root, report))
                or (report["requiresComparison"] and report["reviewType"] != "consistency")):
            raise M2VError("历史独立必改须以同范围的当前独立观察通过关闭")
        if report["reviewType"] == "consistency":
            blind = reviews.current_report(root, project, report["blindId"])
            if blind["verdict"] != "pass" or blind["isolation"] != "independent-subagent":
                raise M2VError("历史独立问题复查缺少同轮盲审通过")
