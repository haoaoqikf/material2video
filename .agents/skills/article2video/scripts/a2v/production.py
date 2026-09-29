"""作品制作记录、版本依赖和正式渲染闸门。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from . import paths, remotion
from .errors import A2VError
from .media import file_digest, fingerprint
from .media import load_media

RECORD_VERSION = 1
RECORD_NAME = "production.json"
STATUSES = {"pass", "fail", "pending"}
REVIEW_DIMENSIONS = {
    "static": ("subject_scale", "composition_repetition", "information_density", "visual_motif", "climax_weight"),
    "dynamic": ("motion_meaning", "narration_sync", "rhythm", "result_hold"),
}


def record_path(article: paths.ArticlePaths) -> Path:
    root = article.output_dir.parent if article.kind == "example" else article.source_dir
    return root / RECORD_NAME


def current_fingerprints(storyboard_path: str | Path, media_path: str | Path | None,
                         article: paths.ArticlePaths) -> dict[str, str | None]:
    source = Path(storyboard_path).resolve()
    raw_storyboard = file_digest(source)
    assets = remotion.build_input_fingerprint(
        storyboard_path=source, content_root=article.workspace_root,
        workspace_root=article.workspace_root,
    )["digest"]
    media_digest = None
    if media_path is not None:
        manifest = Path(media_path).resolve()
        if not manifest.is_file():
            raise A2VError(f"媒体清单不存在：{manifest}")
        media = load_media(manifest, source)
        media_digest = fingerprint({"manifest": file_digest(manifest), "audio": file_digest(media.audio)})
    return {"storyboard": raw_storyboard, "assets": assets, "media": media_digest}


def template(storyboard: dict[str, Any], fingerprints: dict[str, str | None]) -> dict[str, Any]:
    scene_ids = [str(item.get("id", "")) for item in storyboard.get("scenes", [])]
    return {
        "version": RECORD_VERSION,
        "fingerprints": fingerprints,
        "direction": {
            "keyScenes": {"opening": "", "core": "", "climax": ""},
            "pace": "",
            "scenePlans": {scene_id: {"start": "", "change": "", "result": ""} for scene_id in scene_ids},
        },
        "reviews": {
            "keyScenes": {},
            "full": {
                "static": {"status": "pending", "dimensions": _pending_dimensions("static"), "evidence": ""},
                "dynamic": {"status": "pending", "dimensions": _pending_dimensions("dynamic"), "evidence": ""},
            },
        },
        "materials": {"keyframes": None, "samples": None, "rehearsal": None},
        "rework": [],
    }


def initialize_template(storyboard: dict[str, Any], fingerprints: dict[str, str | None]) -> dict[str, Any]:
    result = template(storyboard, fingerprints)
    result["reviews"]["keyScenes"] = {
        scene_id: {
            "static": {"status": "pending", "dimensions": _pending_dimensions("static"), "evidence": ""},
            "dynamic": {"status": "pending", "dimensions": _pending_dimensions("dynamic"), "evidence": ""},
        }
        # Provide review slots for every scene so a creator can assign roles
        # after generating the template without making the record invalid.
        for scene_id in sorted(result["direction"]["scenePlans"])
    }
    return result


def _pending_dimensions(kind: str) -> dict[str, dict[str, str]]:
    return {name: {"status": "pending", "evidence": ""} for name in REVIEW_DIMENSIONS[kind]}


def key_scene_ranges(scenes: Iterable[Any], roles: dict[str, str], fps: int, total_frames: int) -> list[tuple[int, int, list[str], list[str]]]:
    """按全局帧号生成带半秒相邻上下文的关键幕区间，并合并重叠片段。"""
    scene_roles: dict[str, list[str]] = {}
    for role, scene_id in roles.items():
        scene_roles.setdefault(scene_id, []).append(role)
    margin = round(fps * 0.5)
    raw: list[tuple[int, int, str]] = []
    cursor = 0
    for scene in scenes:
        end = cursor + scene.duration_in_frames - 1
        if scene.id in scene_roles:
            raw.append((max(0, cursor - margin), min(total_frames - 1, end + margin), scene.id))
        cursor = end + 1
    raw.sort()
    merged: list[tuple[int, int, list[str], list[str]]] = []
    for first, last, scene_id in raw:
        if merged and first <= merged[-1][1] + 1:
            old_first, old_last, ids, labels = merged[-1]
            merged[-1] = (old_first, max(old_last, last), ids + [scene_id], labels + scene_roles[scene_id])
        else:
            merged.append((first, last, [scene_id], list(scene_roles[scene_id])))
    return merged


def load_record(path: str | Path, scene_ids: set[str]) -> dict[str, Any]:
    record_file = Path(path)
    try:
        value = json.loads(record_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise A2VError(f"无法读取制作记录 {record_file}: {exc}") from exc
    validate_record(value, scene_ids)
    return value


def validate_record(value: Any, scene_ids: set[str]) -> None:
    def fail(where: str, message: str) -> None:
        raise A2VError(f"制作记录字段 {where}: {message}")

    if not isinstance(value, dict):
        fail("$", "必须是 JSON 对象")
    if value.get("version") != RECORD_VERSION:
        fail("version", f"只接受版本 {RECORD_VERSION}")
    fingerprints = value.get("fingerprints")
    if not isinstance(fingerprints, dict) or any(not isinstance(fingerprints.get(key), str) or not fingerprints[key]
                                                 for key in ("storyboard", "assets")):
        fail("fingerprints", "必须包含非空 storyboard 与 assets 指纹")
    direction = value.get("direction")
    if not isinstance(direction, dict):
        fail("direction", "必须是对象")
    roles = direction.get("keyScenes")
    if not isinstance(roles, dict):
        fail("direction.keyScenes", "必须声明开场、核心论证与高潮场景")
    for role in ("opening", "core", "climax"):
        scene_id = roles.get(role)
        if not isinstance(scene_id, str) or not scene_id:
            fail(f"direction.keyScenes.{role}", "必须指定场景 ID")
        if scene_id not in scene_ids:
            fail(f"direction.keyScenes.{role}", f"未知场景 ID {scene_id!r}")
    if not isinstance(direction.get("pace"), str) or not direction["pace"].strip():
        fail("direction.pace", "必须描述全片快慢安排")
    plans = direction.get("scenePlans")
    if not isinstance(plans, dict):
        fail("direction.scenePlans", "必须按场景 ID 描述起始、变化和结果")
    for scene_id in scene_ids:
        plan = plans.get(scene_id)
        if not isinstance(plan, dict):
            fail(f"direction.scenePlans.{scene_id}", "缺少该场景的导演计划")
        for key in ("start", "change", "result"):
            if not isinstance(plan.get(key), str) or not plan[key].strip():
                fail(f"direction.scenePlans.{scene_id}.{key}", "必须填写可观察的内容")
    reviews = value.get("reviews")
    if not isinstance(reviews, dict) or not isinstance(reviews.get("keyScenes"), dict):
        fail("reviews.keyScenes", "必须记录关键幕静态与动态评审")
    if not isinstance(reviews.get("full"), dict):
        fail("reviews.full", "必须记录全片静态与动态评审")
    for scene_id in set(roles.values()):
        item = reviews["keyScenes"].get(scene_id)
        if not isinstance(item, dict):
            fail(f"reviews.keyScenes.{scene_id}", "关键幕尚未评审")
        _validate_review(item, f"reviews.keyScenes.{scene_id}", fail)
    _validate_review(reviews["full"], "reviews.full", fail)
    issues = value.get("rework")
    materials = value.get("materials")
    if not isinstance(materials, dict):
        fail("materials", "必须记录评审材料出处")
    for name, item in materials.items():
        if name not in {"keyframes", "samples", "rehearsal"}:
            fail(f"materials.{name}", "未知材料类型")
        if item is not None and (not isinstance(item, dict) or not isinstance(item.get("path"), str)
                                 or not isinstance(item.get("fingerprints"), dict)):
            fail(f"materials.{name}", "必须包含材料路径和生成时的指纹")
    if not isinstance(issues, list):
        fail("rework", "必须是返工项数组")
    seen: set[str] = set()
    for index, issue in enumerate(issues):
        where = f"rework[{index}]"
        if not isinstance(issue, dict):
            fail(where, "必须是对象")
        issue_id = issue.get("id")
        if not isinstance(issue_id, str) or not issue_id or issue_id in seen:
            fail(f"{where}.id", "必须是唯一的非空 ID")
        seen.add(issue_id)
        for key in ("dimension", "problem", "direction", "returnStage"):
            if not isinstance(issue.get(key), str) or not issue[key].strip():
                fail(f"{where}.{key}", "必填")
        if issue.get("severity") not in {"required", "optional"}:
            fail(f"{where}.severity", "只接受 required 或 optional")
        if issue.get("status") not in {"open", "resolved"}:
            fail(f"{where}.status", "只接受 open 或 resolved")
        targets = issue.get("sceneIds")
        if not isinstance(targets, list) or any(scene not in scene_ids for scene in targets):
            fail(f"{where}.sceneIds", "必须是有效场景 ID 数组（全片问题可为空）")
        if issue["status"] == "resolved":
            review = issue.get("recheck")
            if not isinstance(review, dict) or review.get("status") != "pass" or not str(review.get("evidence", "")).strip():
                fail(f"{where}.recheck", "关闭前必须有当前版本的通过结论和依据")
            if review.get("fingerprints") != fingerprints:
                fail(f"{where}.recheck.fingerprints", "必须绑定当前分镜、媒体与资产指纹")


def _validate_review(review: dict[str, Any], where: str, fail: Any) -> None:
    for kind in ("static", "dynamic"):
        result = review.get(kind)
        if not isinstance(result, dict):
            fail(f"{where}.{kind}", "缺少评审结论")
        if result.get("status") not in STATUSES:
            fail(f"{where}.{kind}.status", "只接受 pass、fail 或 pending")
        if not isinstance(result.get("evidence"), str):
            fail(f"{where}.{kind}.evidence", "必须是字符串")
        dimensions = result.get("dimensions")
        if not isinstance(dimensions, dict):
            fail(f"{where}.{kind}.dimensions", "必须逐维记录结论")
        for name in REVIEW_DIMENSIONS[kind]:
            item = dimensions.get(name)
            if not isinstance(item, dict) or item.get("status") not in STATUSES:
                fail(f"{where}.{kind}.dimensions.{name}.status", "缺少有效结论")
            if not isinstance(item.get("evidence"), str):
                fail(f"{where}.{kind}.dimensions.{name}.evidence", "必须是字符串")
            if item["status"] != "pending" and not item["evidence"].strip():
                fail(f"{where}.{kind}.dimensions.{name}.evidence", "通过或失败结论必须说明依据")
        expected = "pass" if all(dimensions[name]["status"] == "pass" for name in REVIEW_DIMENSIONS[kind]) else (
            "fail" if any(dimensions[name]["status"] == "fail" for name in REVIEW_DIMENSIONS[kind]) else "pending")
        if result["status"] != expected:
            fail(f"{where}.{kind}.status", f"应根据逐维结论填写 {expected}")
        if result["status"] != "pending" and not result["evidence"].strip():
            fail(f"{where}.{kind}.evidence", "完成的评审必须有整体依据")


def review_current(record: dict[str, Any], current: dict[str, str | None], kind: str) -> bool:
    stored = record.get("fingerprints", {})
    required = ("storyboard", "assets") if kind == "static" else ("storyboard", "assets", "media")
    return all(stored.get(key) and stored.get(key) == current.get(key) for key in required)


def attach_material(record_file: str | Path, article: paths.ArticlePaths, name: str,
                    material_path: str | Path, fingerprints: dict[str, str | None]) -> None:
    """记录新生成材料的相对出处和输入指纹，不改变任何评审结论。"""
    source = Path(record_file)
    if not source.is_file():
        return
    try:
        record = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise A2VError(f"无法更新制作记录 {source}: {exc}") from exc
    target = Path(material_path).resolve()
    try:
        relative = target.relative_to(article.workspace_root.resolve()).as_posix()
    except ValueError as exc:
        raise A2VError(f"评审材料不在工作区内：{target}") from exc
    record.setdefault("materials", {})[name] = {"path": relative, "fingerprints": fingerprints}
    temporary = source.with_suffix(source.suffix + ".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(source)


def gate(path: str | Path, storyboard: dict[str, Any], current: dict[str, str | None]) -> str | None:
    scene_ids = {str(item.get("id", "")) for item in storyboard.get("scenes", [])}
    record_file = Path(path)
    if not record_file.is_file():
        return f"缺少制作记录 {record_file}；请复制 production.template.json 并填写导演计划与评审结论"
    try:
        record = load_record(record_file, scene_ids)
    except A2VError as exc:
        return str(exc)
    stored = record["fingerprints"]
    changed = [key for key in ("storyboard", "assets") if current.get(key) is not None and stored.get(key) != current.get(key)]
    if changed:
        return f"制作评审已过期（输入变化：{'、'.join(changed)}）；请更新指纹、重新生成材料并复评"
    roles = set(record["direction"]["keyScenes"].values())
    for scene_id in roles:
        review = record["reviews"]["keyScenes"][scene_id]
        if review["static"]["status"] != "pass" or review["dynamic"]["status"] != "pass":
            return f"关键幕 {scene_id} 尚未通过静态和动态评审"
        if not review_current(record, current, "static") or not review_current(record, current, "dynamic"):
            return f"关键幕 {scene_id} 的评审已过期"
    if not review_current(record, current, "static") or record["reviews"]["full"]["static"]["status"] != "pass":
        return "全片静态评审缺失、未通过或已过期"
    if not review_current(record, current, "dynamic") or record["reviews"]["full"]["dynamic"]["status"] != "pass":
        return "全片有声动态评审缺失、未通过或已过期"
    open_required = [item["id"] for item in record["rework"] if item["severity"] == "required" and item["status"] != "resolved"]
    if open_required:
        return "存在未解决的必改项：" + "、".join(open_required)
    return None


def status_rows(record: dict[str, Any] | None, storyboard: dict[str, Any], current: dict[str, str | None]) -> list[dict[str, str]]:
    if record is None:
        return [{"stage": "制作记录", "status": "blocked", "detail": "尚未创建 production.json",
                 "nextCommand": "production.py template --storyboard <分镜> [--media <媒体清单>] --out <作品目录>/production.json"},
                {"stage": "关键幕试制", "status": "pending", "detail": "指定开场、核心论证与高潮场景",
                 "nextCommand": "编辑 production.json 的 direction.keyScenes 与 direction.scenePlans"}]
    rows: list[dict[str, str]] = []
    if not isinstance(record, dict):
        return [{"stage": "制作记录", "status": "blocked", "detail": "production.json 必须是 JSON 对象",
                 "nextCommand": "重新生成 production.json 模板并恢复记录结构"}]
    plan = record.get("direction")
    known = {str(item.get("id", "")) for item in storyboard.get("scenes", [])}
    if not isinstance(plan, dict) or not isinstance(plan.get("keyScenes"), dict):
        return [{"stage": "制作记录", "status": "blocked", "detail": "direction.keyScenes 缺失",
                 "nextCommand": "重新生成 production.json 模板并填写导演规划"}]
    missing_roles = [role for role in ("opening", "core", "climax")
                     if not isinstance(plan["keyScenes"].get(role), str)
                     or not plan["keyScenes"].get(role)
                     or plan["keyScenes"].get(role) not in known]
    if missing_roles:
        rows.append({"stage": "导演规划", "status": "pending",
                     "detail": "待指定有效场景：" + "、".join(missing_roles),
                     "nextCommand": "编辑 production.json 的 direction.keyScenes"})
        return rows
    if not str(plan.get("pace", "")).strip():
        rows.append({"stage": "导演规划", "status": "pending", "detail": "缺少全片快慢安排",
                     "nextCommand": "填写 production.json 的 direction.pace"})
        return rows
    scene_plans = plan.get("scenePlans") if isinstance(plan.get("scenePlans"), dict) else {}
    missing_plans = [scene for scene in known if not isinstance(scene_plans.get(scene), dict)
                     or any(not str(scene_plans[scene].get(key, "")).strip()
                            for key in ("start", "change", "result"))]
    if missing_plans:
        rows.append({"stage": "导演规划", "status": "pending",
                     "detail": "起始/变化/结果未完成：" + "、".join(sorted(missing_plans)),
                     "nextCommand": "编辑 production.json 的 direction.scenePlans"})
        return rows
    roles = plan.get("keyScenes", {})
    for role, scene_id in roles.items():
        reviews = record.get("reviews") if isinstance(record.get("reviews"), dict) else {}
        key_reviews = reviews.get("keyScenes") if isinstance(reviews.get("keyScenes"), dict) else {}
        item = key_reviews.get(scene_id, {}) if isinstance(scene_id, str) else {}
        if not isinstance(scene_id, str) or not scene_id or scene_id not in known:
            rows.append({"stage": f"关键幕:{role}", "status": "blocked", "detail": f"场景 ID 无效：{scene_id}",
                         "nextCommand": "修正 production.json 的 direction.keyScenes"})
            continue
        state = "passed" if isinstance(item, dict) and all(
            isinstance(item.get(kind), dict) and item[kind].get("status") == "pass"
            for kind in ("static", "dynamic")
        ) else "pending"
        if state == "passed" and not all(review_current(record, current, kind) for kind in ("static", "dynamic")):
            state = "stale"
        next_command = "已通过" if state == "passed" else "production.py samples --storyboard <分镜> --media <媒体清单>"
        rows.append({"stage": f"关键幕:{role}", "status": state, "detail": str(scene_id), "nextCommand": next_command})
    for kind, label in (("static", "全片静态评审"), ("dynamic", "全片有声动态评审")):
        review = record.get("reviews", {}).get("full", {}).get(kind, {})
        state = review.get("status", "pending")
        if state == "pass" and not review_current(record, current, kind):
            state = "stale"
        next_command = "已通过" if state == "pass" else (
            "production.py rehearsal --storyboard <分镜> --media <媒体清单>"
            if kind == "dynamic" else "production.py keyframes --storyboard <分镜>")
        rows.append({"stage": label, "status": state, "detail": str(review.get("evidence", "")), "nextCommand": next_command})
    issues = record.get("rework", [])
    open_items = [item["id"] for item in issues if item.get("severity") == "required" and item.get("status") != "resolved"]
    rows.append({"stage": "定向返工", "status": "blocked" if open_items else "not-required", "detail": "、".join(open_items) if open_items else "无未解决必改项",
                 "nextCommand": "处理并复查 production.json 中的必改项" if open_items else "无需返工"})
    problem = gate_for_status(record, storyboard, current)
    rows.append({"stage": "正式渲染", "status": "passed" if problem is None else "blocked", "detail": problem or "评审记录有效",
                 "nextCommand": "render.py --storyboard <分镜> --media <媒体清单>" if problem is None else "完成上述阻塞项后复查状态"})
    return rows


def gate_for_status(record: dict[str, Any], storyboard: dict[str, Any], current: dict[str, str | None]) -> str | None:
    try:
        validate_record(record, {str(item.get("id", "")) for item in storyboard.get("scenes", [])})
    except A2VError as exc:
        return str(exc)
    # status uses the same checks as render without creating or mutating a file.
    stored = record.get("fingerprints", {})
    changed = [key for key in ("storyboard", "assets") if current.get(key) is not None and stored.get(key) != current.get(key)]
    if changed:
        return f"评审已过期：{'、'.join(changed)}"
    for scene_id in set(record["direction"]["keyScenes"].values()):
        review = record["reviews"]["keyScenes"].get(scene_id, {})
        if any(review.get(kind, {}).get("status") != "pass" for kind in ("static", "dynamic")):
            return f"关键幕 {scene_id} 尚未通过静态和动态评审"
        if not review_current(record, current, "static") or not review_current(record, current, "dynamic"):
            return f"关键幕 {scene_id} 的评审已过期"
    if any(record["reviews"]["full"][kind]["status"] != "pass" or not review_current(record, current, kind) for kind in ("static", "dynamic")):
        return "全片静态和有声动态评审需通过且仍有效"
    if any(item["severity"] == "required" and item["status"] != "resolved" for item in record["rework"]):
        return "存在未解决的必改项"
    return None
