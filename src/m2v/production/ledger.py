"""显式周期与媒体评审的只读状态投影；不推断创作阶段。"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path

from m2v.core.delivery import outputs, candidate
from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from . import dependencies
from .model import VERSION, fields, identifier, now
from .storage import local, read, receipt, write

logger = logging.getLogger(__name__)
_query = ContextVar("media_review_query", default=None)


def query_active() -> bool:
    """让嵌套只读校验沿用同一查询，不把缓存延伸到后续写入。"""
    return _query.get() is not None


@contextmanager
def query():
    """仅在一次只读查询内复用历史、包与报告验证，下一次查询立即重验。"""
    token = _query.set({})
    try:
        yield
    finally:
        _query.reset(token)


def query_value(key, compute):
    cache = _query.get()
    if cache is None:
        return compute()
    if key not in cache:
        try:
            cache[key] = compute()
        except M2VError as exc:
            cache[key] = exc
    if isinstance(cache[key], M2VError):
        raise M2VError(str(cache[key]))
    return cache[key]


def cycle(root: Path) -> dict:
    return query_value(("cycle", root), lambda: _cycle(root))


def _cycle(root: Path) -> dict:
    value = read(outputs(root) / "production/workflow.json")
    fields(
        value, {"version", "cycleId", "projectId", "createdAt", "finalFocuses", "basis"}
    )
    if value["version"] != VERSION:
        raise M2VError(
            "旧制作记录不兼容；请显式执行 m2v review start，新周期不继承旧通过"
        )
    identifier(value["cycleId"])
    original = read(local(outputs(root), f"production/{value['cycleId']}/cycle.json"))
    if original != value:
        raise M2VError("周期身份或终审要求已被改写；须显式开启新周期")
    if value["finalFocuses"] not in (["comprehensive"], ["structure", "visual-copy"]):
        raise M2VError("终审职责无效")
    return value


def directory(root: Path) -> Path:
    return outputs(root) / "production" / cycle(root)["cycleId"]


def start(
    root: Path, manifest: dict, *, split_final=False, basis="常规综合终审"
) -> dict:
    from .model import text

    text(basis)
    identifier(manifest["id"])
    if (outputs(root) / 'production/workflow.json').exists():
        events, errors = history(root)
        if (any(event['type'] == 'sample-captured' for event in events)
                or any((outputs(root) / 'samples').glob('*/capture.json'))):
            from . import issues
            if errors or any(item['required'] and item['status'] != 'closed'
                             for item in issues.load(root, required=True)):
                raise M2VError('原生样品周期仍有未关闭必改项或历史无法核验，不能重开周期绕过')
    value = dict(
        version=VERSION,
        cycleId=uuid.uuid4().hex,
        projectId=manifest["id"],
        createdAt=now(),
        finalFocuses=["structure", "visual-copy"] if split_final else ["comprehensive"],
        basis=basis,
    )
    previous = outputs(root) / "visual-notes.md"
    if previous.exists():
        archive = (
            outputs(root) / "production" / "history-notes" / (uuid.uuid4().hex + ".md")
        )
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local(outputs(root), "visual-notes.md"), archive)
    write(outputs(root) / "production" / value["cycleId"] / "cycle.json", value)
    write(outputs(root) / "production/workflow.json", value)
    from . import issues

    issues.save(root, [])
    append(root, manifest, "started")
    logger.info("开启媒体评审周期 %s；旧记录不继承通过", value["cycleId"])
    return value


def history(root: Path) -> tuple[list[dict], list[str]]:
    return query_value(("history", root), lambda: _history(root))


def _history(root: Path) -> tuple[list[dict], list[str]]:
    current = cycle(root)
    signature = fingerprint(current)
    path = outputs(root) / "production" / current["cycleId"] / "history.jsonl"
    events, errors, seen = [], [], set()
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for number, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
            fields(
                event, {"version", "id", "cycleId", "projectId", "type", "time", "data"}
            )
            if (
                event["version"] != VERSION
                or event["cycleId"] != current["cycleId"]
                or event["projectId"] != current["projectId"]
                or event["id"] in seen
                or not isinstance(event["data"], dict)
            ):
                raise M2VError("事件版本、周期、身份或 ID 无效")
            identifier(event["id"])
            events.append(event)
            seen.add(event["id"])
        except (ValueError, KeyError, TypeError, M2VError) as exc:
            errors.append(f"历史第 {number} 行损坏：{exc}")
            break
    # 周期在单次扫描内不变，避免每行重复读盘；结束仍绕过查询缓存重新核验完整身份。
    # 只读查询也可能遇到外部编辑，不能以已缓存的周期替代这个边界检查。
    try:
        if fingerprint(_cycle(root)) != signature:
            errors.append("制作历史校验期间周期已变化，请重新核验")
    except M2VError as exc:
        errors.append(f"制作历史周期复查失败：{exc}")
    return events, errors


def append(root: Path, manifest: dict, kind: str, *, data=None) -> dict:
    c = cycle(root)
    _, errors = history(root)
    if errors or manifest["id"] != c["projectId"]:
        raise M2VError("; ".join(errors) or "周期不属于当前作品")
    event = dict(
        version=VERSION,
        id=uuid.uuid4().hex,
        cycleId=c["cycleId"],
        projectId=manifest["id"],
        type=kind,
        time=now(),
        data=data or {},
    )
    path = directory(root) / "history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = ""
    if path.exists() and path.stat().st_size:
        with path.open("rb") as existing:
            existing.seek(-1, 2)
            prefix = "" if existing.read(1) == b"\n" else "\n"
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        import os

        stream.write(
            prefix + json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())
    return event


def evidence_valid_at(base: Path, entries: list) -> bool:
    try:
        return bool(entries) and all(
            dependencies.digest(local(base, e["path"])) == e["sha256"] for e in entries
        )
    except (M2VError, OSError, KeyError, TypeError):
        return False


def evidence_valid(root: Path, entries: list) -> bool:
    return evidence_valid_at(outputs(root), entries)


def sources(root: Path, request: dict) -> dict:
    """只绑定请求涉及的场景与文件；不把未制作场景作为试制前置。"""
    paths, scene_ids = request.get("sources", []), request.get("sceneIds", [])
    if (
        not isinstance(paths, list)
        or not isinstance(scene_ids, list)
        or any(not isinstance(x, str) for x in paths + scene_ids)
    ):
        raise M2VError("sources/sceneIds 必须为字符串列表")
    selected = {}
    if scene_ids:
        board = read(root / "storyboard.json")
        scenes = {s["id"]: s for s in board["scenes"]}
        if not set(scene_ids) <= scenes.keys():
            raise M2VError("评审引用未知场景")
        selected = {
            sid: {
                "scene": scenes[sid],
                "dependencies": dependencies.scene_sources(root, scenes[sid]),
            }
            for sid in scene_ids
        }
    global_inputs = {}
    if (root / "project.json").exists():
        project = read(root / "project.json")
        global_inputs = {key: project.get(key) for key in ("type", "output", "tts")}
    return {
        "globals": global_inputs,
        "files": {p: dependencies.digest(local(root, p)) for p in paths},
        "scenes": selected,
    }


def final_binding(root: Path, manifest: dict) -> dict:
    return query_value(("final-binding", root), lambda: _final_binding(root, manifest))


def _final_binding(root: Path, manifest: dict) -> dict:
    from m2v.commands import _prepared

    prepared = _prepared(root, manifest)
    record = candidate(root, prepared)
    if record.get("status") not in ("ready", "delivered"):
        raise M2VError("当前完整候选技术验收尚未通过")
    qa_path = outputs(root) / "qa.json"
    qa = read(qa_path)
    if (
        qa.get("status") != "pass"
        or qa.get("preparedFingerprint") != prepared["preparedFingerprint"]
        or qa.get("videoSha256") != record["sha256"]
    ):
        raise M2VError("终审需要绑定当前完整候选的有效技术 QA")
    board = read(
        root / manifest.get("materials", {}).get("storyboard", "storyboard.json")
    )
    return {
        "candidateSha256": record["sha256"],
        "preparedFingerprint": prepared["preparedFingerprint"],
        "durationFrames": prepared["durationInFrames"],
        "fps": prepared["fps"],
        "qa": receipt(outputs(root), qa_path),
        "storyboard": fingerprint(board),
        "sources": sources(root, {"sceneIds": [s["id"] for s in board["scenes"]]}),
    }


def binding(root: Path, manifest: dict, request: dict) -> dict:
    value = {
        "conditions": request.get("conditions", []),
        "sources": sources(root, request),
        "media": [
            receipt(outputs(root), local(outputs(root), item["path"]))
            for item in request["items"]
        ],
        "references": [
            receipt(outputs(root), local(outputs(root), p))
            for p in request.get("references", [])
        ],
    }
    if request["round"] == "final":
        value["final"] = final_binding(root, manifest)
    return value


def status(root: Path, manifest: dict, *, full_history=False) -> dict:
    from . import reviews, issues, media_evidence

    result = {
        "version": VERSION,
        "complete": False,
        "trial": [],
        "final": [],
        "diagnostics": [],
        "issues": [],
    }
    with query(), dependencies.snapshot(), media_evidence.snapshot():
        try:
            c = cycle(root)
            if c["projectId"] != manifest["id"]:
                raise M2VError("周期不属于当前作品")
            events, errors = history(root)
            result.update(
                cycleId=c["cycleId"],
                diagnostics=errors,
                history=events if full_history else events[-5:],
            )
            result["issues"] = [
                p for p in issues.load(root, required=True) if p["status"] != "closed"
            ]
            for event in events:
                if event["type"] != "review":
                    continue
                data = event["data"]
                row = {
                    "id": data["reportId"],
                    "round": data["round"],
                    "focus": data["focus"],
                    "reviewerId": data["reviewerId"],
                    "status": "stale",
                    "detail": "",
                }
                try:
                    report = reviews.current_report(root, manifest, data["reportId"])
                    row.update(
                        status=report["verdict"]
                        if report["isolation"] == "independent-subagent"
                        else "degraded",
                        reviewType=report["reviewType"],
                        blindId=report.get("blindId"),
                    )
                    from . import reuse
                    if reuse.has_record(root, report['id']):
                        row['visualReuse'] = reuse.resolve(root, manifest, report['id'])[3]
                except (M2VError, OSError, ValueError, KeyError, TypeError) as exc:
                    row["detail"] = str(exc)
                result[data["round"]].append(row)
            for name in ("trial", "final"):
                for row in result[name]:
                    if row["status"] == "pass" and row.get("reviewType") == "blind":
                        report = reviews.current_report(root, manifest, row["id"])
                        if report["requiresComparison"] and not any(
                            r["status"] == "pass" and r.get("blindId") == row["id"]
                            for r in result[name]
                        ):
                            row.update(
                                status="insufficient", detail="缺少当前同轮目标对照"
                            )
            try:
                result["technicalQA"] = {
                    "status": "pass",
                    **final_binding(root, manifest),
                }
            except (M2VError, OSError, KeyError, TypeError) as exc:
                result["technicalQA"] = {"status": "unverified", "detail": str(exc)}
            trial = any(
                r["status"] == "pass" and r.get("reviewType") == "blind"
                for r in result["trial"]
            )
            technical_qa = result["technicalQA"]
            technical_pass = technical_qa["status"] == "pass"
            # Use the QA-bound duration. targetSeconds only budgets the storyboard.
            short_film = (
                technical_pass
                and technical_qa["durationFrames"] <= 60 * technical_qa["fps"]
            )
            focuses = {
                r["focus"]
                for r in result["final"]
                if r["status"] == "pass" and r.get("reviewType") == "blind"
            }
            result["complete"] = (
                (short_film or trial)
                and set(c["finalFocuses"]) <= focuses
                and not errors
                and not result["issues"]
                and technical_pass
            )
        except (M2VError, OSError, ValueError, KeyError, TypeError) as exc:
            result["diagnostics"].append(str(exc))
    return result
