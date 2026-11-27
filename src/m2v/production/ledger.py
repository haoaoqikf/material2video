"""显式周期与媒体评审的只读状态投影；不推断创作阶段。"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path

from m2v.core.delivery import outputs
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
    if query_active():
        yield
        return
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
    if value.get("version") != VERSION:
        raise M2VError("旧制作记录不兼容；请显式执行 m2v review start，新周期不继承旧通过")
    fields(value, {"version", "cycleId", "projectId", "createdAt"})
    identifier(value["cycleId"])
    original = read(local(outputs(root), f"production/{value['cycleId']}/cycle.json"))
    if original != value:
        raise M2VError("周期身份已被改写")
    return value


def directory(root: Path) -> Path:
    return outputs(root) / "production" / cycle(root)["cycleId"]


def start(root: Path, manifest: dict) -> dict:
    from . import issues, legacy

    identifier(manifest["id"])
    base = outputs(root)
    workflow = local(base, "production/workflow.json", exists=False)
    previous = local(base, "visual-notes.md", exists=False)
    identity = uuid.uuid4().hex
    value = dict(version=VERSION, cycleId=identity, projectId=manifest["id"], createdAt=now())
    carried = []
    if not workflow.exists() and any((base / "production").glob("*/cycle.json")):
        raise M2VError("制作账本存在但当前周期指针缺失，不能通过开始新周期绕过")
    if workflow.exists():
        old = read(workflow)
        old_id = identifier(old.get("cycleId"))
        if old.get("projectId") != manifest["id"] or old != read(local(base, f"production/{old_id}/cycle.json")):
            raise M2VError("旧周期身份或原始记录损坏，不能借版本升级重开周期")
        if old.get("version") == VERSION:
            _, errors = history(root)
            if errors or any(item["required"] and item["status"] != "closed"
                             for item in issues.load(root, required=True, active_only=True)):
                raise M2VError("当前制作周期仍有未关闭必改项或历史无法核验，不能重开周期绕过")
        else:
            carried = legacy.unresolved(root, old, previous)
        archive = local(base, f"production/history-notes/{old_id}-{identity}.md", exists=False)
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(previous, archive)
        if carried:
            carried = legacy.carry(carried, identity, receipt(base, archive))
    write(local(base, f"production/{identity}/cycle.json", exists=False), value)
    write(workflow, value)
    issues.save(root, carried, replace=True)
    append(root, manifest, "started", data={"carriedIssues": carried} if carried else None)
    logger.info("开启媒体评审周期 %s；承接 %d 条历史必改", identity, len(carried))
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
    from .review_blobs import recorded_file

    try:
        return bool(entries) and all(
            dependencies.digest(recorded_file(outputs(root), entry["path"])) == entry["sha256"]
            for entry in entries
        )
    except (M2VError, OSError, KeyError, TypeError):
        return False


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
    # 正式窗口已绑定实际画幅、字幕及音频，按局部输入核验。试制还需要显式绑定工程设置。
    if not request.get("film") and (root / "project.json").exists():
        project = read(root / "project.json")
        global_inputs = {key: project.get(key) for key in ("type", "output", "tts")}
    return {
        "globals": global_inputs,
        "files": {p: dependencies.digest(local(root, p)) for p in paths},
        "scenes": selected,
    }


def binding(root: Path, manifest: dict, request: dict, *, sealed=None) -> dict:
    base = outputs(root)

    def media_receipt(name):
        path = local(base, name)
        return {"path": path.relative_to(base).as_posix(), "sha256": dependencies.digest(path)}

    value = {
        "conditions": request.get("conditions", []),
        "sources": sources(root, request),
        "media": [media_receipt(item["path"]) for item in request["items"]],
        "references": [media_receipt(p) for p in request.get("references", [])],
    }
    if request.get("film"):
        from .film_review import composition_binding
        value["film"] = composition_binding(root, manifest, request, value["media"], sealed=sealed)
    return value


def status(root: Path, manifest: dict, *, full_history=False) -> dict:
    from . import film_review, issues, media_evidence, reuse, reviews

    result = {
        "version": VERSION,
        "complete": False,
        "trial": [],
        "keyframes": {"status": "missing"},
        "keySamples": {"status": "undetermined"},
        "technicalQA": {"status": "unverified"},
        "wholeFilmReview": {"status": "missing"},
        "diagnostics": [],
        "issues": [],
    }
    with query(), dependencies.snapshot(), media_evidence.snapshot():
        try:
            data = film_review.prepared(root, manifest)
        except (M2VError, OSError, ValueError, KeyError, TypeError) as exc:
            data = None
            result["keySamples"]["detail"] = str(exc)
        try:
            result["technicalQA"] = {"status": "pass", **film_review.qa_binding(root, manifest)}
        except (M2VError, OSError, ValueError, KeyError, TypeError) as exc:
            result["technicalQA"]["detail"] = str(exc)
        if data is not None:
            result["keySamples"] = film_review.sample_state(data, [], [])
        try:
            c = cycle(root)
            if c["projectId"] != manifest["id"]:
                raise M2VError("周期不属于当前作品")
            events, errors = history(root)
            result.update(cycleId=c["cycleId"], diagnostics=errors,
                          history=events if full_history else events[-5:])
            result["issues"] = [p for p in issues.load(root, required=True, active_only=True) if p["status"] != "closed"]
            verified = {}
            partial = {}
            for event in events:
                if event["type"] != "review":
                    continue
                record = event["data"]
                row = {"id": record["reportId"], "round": record["round"],
                       "focus": record["focus"], "reviewerId": record["reviewerId"],
                       "status": "stale", "adoption": "reject", "detail": ""}
                try:
                    report = reviews.current_report(root, manifest, row["id"])
                    independent = report["isolation"] == "independent-subagent"
                    row.update(status=report["verdict"] if independent else "degraded",
                               reviewType=report["reviewType"], blindId=report.get("blindId"),
                               purpose=report["purpose"], hasVisualTarget=report["hasVisualTarget"],
                               adoption=report["adoption"] if independent else "reject")
                    if reuse.has_record(root, report["id"]):
                        row["visualReuse"] = reuse.resolve(root, manifest, report["id"])[3]
                    verified[row["id"]] = report
                except (M2VError, OSError, ValueError, KeyError, TypeError) as exc:
                    row.update(status="stale", adoption="reject", detail=str(exc))
                    if data is not None:
                        try:
                            retained = reviews.still_current_film_items(root, manifest, row["id"])
                            if retained:
                                partial[row["id"]] = retained
                                row["currentWindowIds"] = list(retained[1])
                        except (M2VError, OSError, ValueError, KeyError, TypeError):
                            # 原诊断继续说明整包失效原因，封存材料无法核对时不保留局部。
                            pass
                result["trial"].append(row)

            contrasts = {row["blindId"] for row in result["trial"]
                         if row["status"] == "pass" and row["reviewType"] == "consistency"}
            film_contrasts = {}
            film_passes = list(partial.values())
            for row in result["trial"]:
                if row["status"] != "pass" or not row["hasVisualTarget"]:
                    continue
                _, _, private, _ = reuse.evidence(root, manifest, row["id"])
                binding = private["binding"]
                if binding.get("film"):
                    film_passes.append((verified[row["id"]], binding["film"], binding["conditions"]))
            for report, film, _ in film_passes:
                if report["reviewType"] == "consistency":
                    film_contrasts.setdefault(report["blindId"], set()).update(film)

            formal_stills, approved = [], []
            subtitles_covered = False
            for row in result["trial"]:
                if row["status"] != "pass" or row["reviewType"] == "consistency":
                    continue
                if verified[row["id"]]["requiresComparison"] and row["id"] not in contrasts:
                    row.update(status="insufficient", adoption="reject", detail="缺少当前同轮目标对照")
            for report, film, conditions in film_passes:
                if report["reviewType"] == "consistency":
                    continue
                if report["requiresComparison"]:
                    paired = film_contrasts.get(report["id"], set())
                    film = {identity: item for identity, item in film.items() if identity in paired}
                    if not film:
                        continue
                if report["purpose"] == "keyframe":
                    formal_stills.append(report["id"])
                    subtitles_covered |= any(item["hasSubtitles"] for item in film.values())
                else:
                    approved.append((film, conditions))

            static_pass = bool(formal_stills) and (
                subtitles_covered or not data["props"]["subtitleCues"]
            )
            result["keyframes"] = {"status": "pass" if static_pass else "missing",
                                   "reportIds": formal_stills}
            if formal_stills and not static_pass:
                result["keyframes"]["detail"] = "缺少包含真实字幕的合成关键帧"
            result["keySamples"] = film_review.sample_state(data, events, approved)
            result["wholeFilmReview"] = film_review.whole_film_state(events, result["technicalQA"])
            result["complete"] = (
                static_pass
                and result["keySamples"]["status"] in ("exempt", "pass")
                and result["technicalQA"]["status"] == "pass"
                and result["wholeFilmReview"]["status"] == "pass"
                and not errors
                and not any(item["required"] for item in result["issues"])
            )
        except (M2VError, OSError, ValueError, KeyError, TypeError) as exc:
            result["diagnostics"].append(str(exc))
    return result
