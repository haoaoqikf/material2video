"""作品制作记录、版本依赖和正式渲染闸门。"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from . import article_text, paths, remotion
from .errors import A2VError
from .media import file_digest, fingerprint
from .media import load_media

RECORD_VERSION = 1
RECORD_NAME = "production.json"
STATUSES = {"pass", "fail", "pending"}
REVIEW_DIMENSIONS = {
    "content": ("opening_question", "explanation_chain", "spoken_naturalness", "closing_response", "boundary_accuracy"),
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
    result: dict[str, str | None] = {"storyboard": raw_storyboard, "assets": assets, "media": media_digest}
    article_source_dir = getattr(article, "source_dir", None)
    article_path = article_text.active_source(article_source_dir) if article_source_dir is not None else None
    if article_path is not None and article_path.is_file():
        _, result["input"] = article_text.read_source(article_path)
    return result


def template(storyboard: dict[str, Any], fingerprints: dict[str, str | None],
             input_review: dict[str, Any] | None = None) -> dict[str, Any]:
    scene_ids = [str(item.get("id", "")) for item in storyboard.get("scenes", [])]
    return {
        "version": RECORD_VERSION,
        "fingerprints": fingerprints,
        "inputReview": input_review or {
            "countingVersion": article_text.COUNTING_VERSION,
            "source": {"path": "article.md", "sha256": "0" * 64},
            "charCount": 0,
            "lengthStatus": "fail",
            "singleScene": {"status": "pending", "claim": "", "metaphor": "", "problemSpans": [], "rationale": ""},
            "status": "fail",
            "assessment": None,
        },
        "direction": {
            "keyScenes": {"opening": "", "core": "", "climax": ""},
            "pace": "",
            "scenePlans": {scene_id: {"start": "", "change": "", "result": ""} for scene_id in scene_ids},
        },
        "reviews": {
            "keyScenes": {},
            "full": {
                "content": {"status": "pending", "dimensions": _pending_dimensions("content"), "evidence": "", "assessment": None},
                "static": {"status": "pending", "dimensions": _pending_dimensions("static"), "evidence": "", "assessment": None},
                "dynamic": {"status": "pending", "dimensions": _pending_dimensions("dynamic"), "evidence": "", "assessment": None},
            },
        },
        "materials": {"keyframes": None, "samples": None, "rehearsal": None},
        "rework": [],
    }


def initialize_template(storyboard: dict[str, Any], fingerprints: dict[str, str | None],
                        input_review: dict[str, Any] | None = None) -> dict[str, Any]:
    result = template(storyboard, fingerprints, input_review)
    result["reviews"]["keyScenes"] = {
        scene_id: {
            "static": {"status": "pending", "dimensions": _pending_dimensions("static"), "evidence": "", "assessment": None},
            "dynamic": {"status": "pending", "dimensions": _pending_dimensions("dynamic"), "evidence": "", "assessment": None},
        }
        # Provide review slots for every scene so a creator can assign roles
        # after generating the template without making the record invalid.
        for scene_id in sorted(result["direction"]["scenePlans"])
    }
    return result


def _pending_dimensions(kind: str) -> dict[str, dict[str, str]]:
    return {name: {"status": "pending", "evidence": "", **({"score": None} if kind == "content" else {})} for name in REVIEW_DIMENSIONS[kind]}


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
    input_review = value.get("inputReview")
    if not isinstance(input_review, dict):
        fail("inputReview", "必须记录输入文章审查")
    source = input_review.get("source")
    if (not isinstance(source, dict) or not isinstance(source.get("path"), str) or not source["path"].strip()
            or not isinstance(source.get("sha256"), str) or len(source["sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in source["sha256"].lower())):
        fail("inputReview.source", "必须包含工作区相对路径及 SHA-256 摘要")
    source_path = Path(source["path"])
    if source_path.is_absolute() or ".." in source_path.parts:
        fail("inputReview.source.path", "必须是工作区内的相对路径")
    if type(input_review.get("charCount")) is not int or input_review["charCount"] < 0:
        fail("inputReview.charCount", "必须是非负整数")
    if input_review.get("countingVersion") != article_text.COUNTING_VERSION:
        fail("inputReview.countingVersion", "字数规则版本不匹配，须重新审查")
    expected_review_status = article_text.review_status(input_review, fingerprints.get("input"))
    if input_review.get("status") not in {"pass", "fail", "pending"}:
        fail("inputReview.status", "只接受 pass、fail 或 pending")
    if input_review["status"] != expected_review_status:
        fail("inputReview.status", f"与字数、语义结论或输入摘要不一致；应为 {expected_review_status}")
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
        if item is not None:
            digest = item.get("sha256")
            if digest is not None and not _valid_sha256(digest):
                fail(f"materials.{name}.sha256", "必须是 SHA-256 十六进制摘要")
            files = item.get("files", {})
            if not isinstance(files, dict) or any(not isinstance(key, str) or not _valid_sha256(value)
                                                   for key, value in files.items()):
                fail(f"materials.{name}.files", "必须是文件名到 SHA-256 摘要的映射")
    for scope_name, scope in [(f"reviews.keyScenes.{scene}", reviews["keyScenes"][scene])
                              for scene in set(roles.values())] + [("reviews.full", reviews["full"])]:
        for kind in ("static", "dynamic"):
            result = scope[kind]
            assessment = result.get("assessment") if isinstance(result, dict) else None
            if assessment is None:
                continue  # 旧记录继续可读，门禁会拒绝其无来源的通过结论。
            used = assessment.get("materials", {})
            if isinstance(used, dict):
                for material_name, digest in used.items():
                    item = materials.get(material_name)
                    if (material_name not in {"keyframes", "samples", "rehearsal"}
                            or not isinstance(item, dict) or not _valid_sha256(digest)):
                        fail(f"{scope_name}.{kind}.assessment.materials.{material_name}",
                             "引用材料类别无效，摘要必须是 SHA-256 十六进制值")
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
    kinds = ("static", "dynamic", "content") if where == "reviews.full" and "content" in review else ("static", "dynamic")
    for kind in kinds:
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
            if kind == "content" and item["status"] != "pending":
                score = item.get("score")
                if type(score) is not int or not 1 <= score <= 5:
                    fail(f"{where}.{kind}.dimensions.{name}.score", "完成评审必须填写 1–5 整数评分")
                if (score >= 4) != (item["status"] == "pass"):
                    fail(f"{where}.{kind}.dimensions.{name}.score", "至少 4/5 才能通过")
        expected = "pass" if all(dimensions[name]["status"] == "pass" for name in REVIEW_DIMENSIONS[kind]) else (
            "fail" if any(dimensions[name]["status"] == "fail" for name in REVIEW_DIMENSIONS[kind]) else "pending")
        if result["status"] != expected:
            fail(f"{where}.{kind}.status", f"应根据逐维结论填写 {expected}")
        if result["status"] != "pending" and not result["evidence"].strip():
            fail(f"{where}.{kind}.evidence", "完成的评审必须有整体依据")
        assessment = result.get("assessment")
        if assessment is not None:
            if not isinstance(assessment, dict) or assessment.get("reviewer") != "ai":
                fail(f"{where}.{kind}.assessment.reviewer", "只接受带来源声明的 ai 评审")
            for field in ("model", "session"):
                if not isinstance(assessment.get(field), str) or not assessment[field].strip():
                    fail(f"{where}.{kind}.assessment.{field}", "AI 评审来源必填")
            used = assessment.get("materials")
            if not isinstance(used, dict) or not used:
                fail(f"{where}.{kind}.assessment.materials", "必须引用实际查看的评审材料摘要")
            if result["status"] != "pending" and not _assessment_has_required_materials(assessment, where, kind, fail):
                return


def _assessment_has_required_materials(assessment: dict[str, Any], where: str, kind: str, fail: Any) -> bool:
    required = {"static": {"keyframes"}, "dynamic": {"rehearsal" if where == "reviews.full" else "samples"}, "content": {"rehearsal"}}[kind]
    used = assessment.get("materials", {})
    for material in required:
        digest = used.get(material)
        if not isinstance(digest, str) or not digest:
            fail(f"{where}.{kind}.assessment.materials.{material}", "已完成 AI 评审必须引用该类画面材料")
            return False
    return True


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def _material_root(record: dict[str, Any], record_file: str | Path | None) -> Path | None:
    relative = record.get("materialRoot")
    if not isinstance(relative, str) or record_file is None:
        return None
    return (Path(record_file).resolve().parent / relative).resolve()


def _input_review_issue(record: dict[str, Any], current: dict[str, str | None],
                        record_file: str | Path | None) -> str | None:
    review = record.get("inputReview")
    status = article_text.review_status(review, current.get("input"))
    if status == "fail":
        return "输入文章审查未通过；请保留原文、提供修改意见与候选稿，明确采用后重新审查"
    if status != "pass":
        return "输入文章审查缺失、待评审或已过期；先完成长度与单场景适配审查"
    if record_file is None:
        return None
    root = _material_root(record, record_file)
    if root is None:
        return "制作记录缺少 materialRoot，无法验证输入文章来源"
    relative = Path(review["source"]["path"])
    source = (root / relative).resolve()
    if not source.is_relative_to(root) or not source.is_file():
        return "输入文章来源路径无效或文件已缺失；请重新审查"
    try:
        text, digest = article_text.read_source(source)
    except (OSError, UnicodeError):
        return "输入文章无法读取；请修复原文后重新审查"
    if digest != review["source"]["sha256"] or article_text.count_characters(article_text.extract_body(text)) != review["charCount"]:
        return "输入文章已变化，原审查失效；请重新审查"
    authorization = review.get("authorization")
    if authorization is not None:
        if not isinstance(authorization, dict) or not isinstance(authorization.get("path"), str):
            return "候选稿采用授权记录无效；请重新采用并审查"
        candidate = (source.parent / authorization["path"]).resolve()
        if not candidate.is_relative_to(source.parent.resolve()) or not candidate.is_file():
            return "已采用候选稿或其授权来源缺失；请重新采用并审查"
        try:
            _, candidate_digest = article_text.read_source(candidate)
        except (OSError, UnicodeError):
            return "已采用候选稿授权来源不可读；请重新采用并审查"
        if candidate_digest != authorization.get("sha256"):
            return "候选稿在采用后发生变化，授权与审查失效；请重新采用并审查"
        original = source.parent / "article.md"
        if not original.is_file():
            return "采用候选稿所依据的原文已缺失；请重新审查"
        try:
            _, original_digest = article_text.read_source(original)
        except (OSError, UnicodeError):
            return "采用候选稿所依据的原文不可读；请重新审查"
        if original_digest != authorization.get("sourceSha256"):
            return "候选稿依据的原文已变化，授权与审查失效；请重新审查"
    return None


def _material_issue(review: dict[str, Any], kind: str, materials: dict[str, Any],
                    material_root: Path | None, current: dict[str, str | None], where: str) -> str | None:
    assessment = review.get("assessment")
    if review.get("status") != "pass":
        return None
    if not isinstance(assessment, dict) or assessment.get("reviewer") != "ai":
        return f"{where}缺少 AI 评审来源；请检查当前画面并补充 assessment"
    used = assessment.get("materials", {})
    required = {"keyframes"} if kind == "static" else {"samples"}
    if where in {"全片有声动态评审", "全片口播内容评审"}:
        required = {"rehearsal"}
    for name in required:
        entry = materials.get(name)
        if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
            return f"{where}缺少 {name} 评审材料摘要"
        if used.get(name) != entry["sha256"]:
            return f"{where}引用的 {name} 摘要与登记材料不一致"
        if material_root is not None:
            source = (material_root / str(entry.get("path", ""))).resolve()
            if not source.is_relative_to(material_root.resolve()):
                return f"{where}的 {name} 材料路径越出工作区"
            if not source.is_file() or _file_sha256(source) != entry["sha256"]:
                return f"{where}使用的 {name} 材料已缺失或摘要已变化"
            for filename, digest in entry.get("files", {}).items():
                member = (source.parent / filename).resolve()
                if not member.is_relative_to(source.parent.resolve()):
                    return f"{where}的 {name} 视频材料路径无效：{filename}"
                if not member.is_file() or _file_sha256(member) != digest:
                    return f"{where}引用的 {name} 视频材料已缺失或摘要已变化：{filename}"
        bound = entry.get("fingerprints", {})
        bound_keys = ("storyboard", "assets") if kind == "static" else ("storyboard", "assets", "media")
        if any(bound.get(key) != current.get(key) for key in bound_keys):
            return f"{where}的 {name} 材料输入版本已过期"
    return None


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
    item: dict[str, Any] = {"path": relative, "fingerprints": fingerprints, "sha256": _file_sha256(target)}
    if target.suffix.lower() == ".json":
        try:
            manifest = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            manifest = None
        files: dict[str, str] = {}
        outputs = manifest.get("outputs") if isinstance(manifest, dict) else None
        if isinstance(outputs, list):
            for output in outputs:
                filename = output.get("file") if isinstance(output, dict) else None
                candidate = target.parent / filename if isinstance(filename, str) else None
                if (candidate is not None and candidate.resolve().is_relative_to(target.parent.resolve())
                        and candidate.is_file()):
                    files[filename] = _file_sha256(candidate)
        if files:
            item["files"] = files
    record.setdefault("materials", {})[name] = item
    if not record.get("materialRoot"):
        record["materialRoot"] = os.path.relpath(article.workspace_root.resolve(), source.parent.resolve())
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
    changed = [key for key in ("storyboard", "assets", "input") if current.get(key) is not None and stored.get(key) != current.get(key)]
    if changed:
        return f"制作评审已过期（输入变化：{'、'.join(changed)}）；请重新审查输入、更新指纹并复评"
    issue = _input_review_issue(record, current, record_file)
    if issue:
        return issue
    material_root = _material_root(record, record_file)
    content = record["reviews"]["full"].get("content")
    if not isinstance(content, dict) or content.get("status") != "pass":
        return "全片口播内容评审缺失或未通过（五项均需至少 4/5）"
    if not review_current(record, current, "content"):
        return "全片口播内容评审已过期"
    issue = _material_issue(content, "content", record.get("materials", {}), material_root, current, "全片口播内容评审")
    if issue:
        return issue
    roles = set(record["direction"]["keyScenes"].values())
    for scene_id in roles:
        review = record["reviews"]["keyScenes"][scene_id]
        if review["static"]["status"] != "pass" or review["dynamic"]["status"] != "pass":
            return f"关键幕 {scene_id} 尚未通过静态和动态评审"
        if not review_current(record, current, "static") or not review_current(record, current, "dynamic"):
            return f"关键幕 {scene_id} 的评审已过期"
        for kind in ("static", "dynamic"):
            issue = _material_issue(review[kind], kind, record.get("materials", {}), material_root, current,
                                    f"关键幕 {scene_id} {kind} 评审")
            if issue:
                return issue
    if not review_current(record, current, "static") or record["reviews"]["full"]["static"]["status"] != "pass":
        return "全片静态评审缺失、未通过或已过期"
    if not review_current(record, current, "dynamic") or record["reviews"]["full"]["dynamic"]["status"] != "pass":
        return "全片有声动态评审缺失、未通过或已过期"
    for kind in ("static", "dynamic"):
        issue = _material_issue(record["reviews"]["full"][kind], kind, record.get("materials", {}),
                                material_root, current,
                                "全片有声动态评审" if kind == "dynamic" else "全片静态评审")
        if issue:
            return issue
    open_required = [item["id"] for item in record["rework"] if item["severity"] == "required" and item["status"] != "resolved"]
    if open_required:
        return "存在未解决的必改项：" + "、".join(open_required)
    return None


def status_rows(record: dict[str, Any] | None, storyboard: dict[str, Any], current: dict[str, str | None],
                record_file: str | Path | None = None) -> list[dict[str, str]]:
    if record is None:
        return [{"stage": "制作记录", "status": "blocked", "detail": "尚未创建 production.json",
                 "nextCommand": "production.py template --storyboard <分镜> [--media <媒体清单>] --out <作品目录>/production.json"},
                {"stage": "关键幕试制", "status": "pending", "detail": "指定开场、核心论证与高潮场景",
                 "nextCommand": "让 article2video AI 助手读取分镜与 motion-design.md 自动填写 direction"}]
    rows: list[dict[str, str]] = []
    if not isinstance(record, dict):
        return [{"stage": "制作记录", "status": "blocked", "detail": "production.json 必须是 JSON 对象",
                 "nextCommand": "重新生成 production.json 模板并恢复记录结构"}]
    input_status = article_text.review_status(record.get("inputReview"), current.get("input"))
    input_issue = _input_review_issue(record, current, record_file)
    if input_issue and input_status == "pass":
        input_status = "stale"
    input_detail = {
        "pass": "输入长度、语义审查与来源摘要有效",
        "fail": "输入不符合标准；保留原文并提供修改意见及候选，待明确采用",
        "pending": "待 AI 阅读原文并填写核心观点、视觉隐喻、依据和来源",
        "stale": input_issue or "输入原文变化，须重新审查",
    }[input_status]
    rows.append({"stage": "输入文章审查", "status": input_status, "detail": input_detail,
                 "nextCommand": "production.py input-review --storyboard <分镜>" if input_status != "pass" else "已通过"})
    plan = record.get("direction")
    known = {str(item.get("id", "")) for item in storyboard.get("scenes", [])}
    if not isinstance(plan, dict) or not isinstance(plan.get("keyScenes"), dict):
        rows.append({"stage": "制作记录", "status": "blocked", "detail": "direction.keyScenes 缺失",
                     "nextCommand": "重新生成 production.json 模板并填写导演规划"})
        return rows
    missing_roles = [role for role in ("opening", "core", "climax")
                     if not isinstance(plan["keyScenes"].get(role), str)
                     or not plan["keyScenes"].get(role)
                     or plan["keyScenes"].get(role) not in known]
    if missing_roles:
        rows.append({"stage": "导演规划", "status": "pending",
                     "detail": "待指定有效场景：" + "、".join(missing_roles),
                     "nextCommand": "让 article2video AI 助手根据分镜自动选择开场、核心与高潮场景"})
        return rows
    if not str(plan.get("pace", "")).strip():
        rows.append({"stage": "导演规划", "status": "pending", "detail": "缺少全片快慢安排",
                     "nextCommand": "让 article2video AI 助手根据 visualDirection 与 beats 填写全片节奏"})
        return rows
    scene_plans = plan.get("scenePlans") if isinstance(plan.get("scenePlans"), dict) else {}
    missing_plans = [scene for scene in known if not isinstance(scene_plans.get(scene), dict)
                     or any(not str(scene_plans[scene].get(key, "")).strip()
                            for key in ("start", "change", "result"))]
    if missing_plans:
        rows.append({"stage": "导演规划", "status": "pending",
                     "detail": "起始/变化/结果未完成：" + "、".join(sorted(missing_plans)),
                     "nextCommand": "让 article2video AI 助手根据 beats 与 motion-design.md 补齐逐幕计划"})
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
        detail = str(scene_id)
        if state == "passed":
            for kind in ("static", "dynamic"):
                problem = _material_issue(item[kind], kind, record.get("materials", {}),
                                          _material_root(record, record_file), current,
                                          f"关键幕 {scene_id} {kind} 评审")
                if problem:
                    state, detail = "stale", problem
                    break
        next_command = "已通过" if state == "passed" else "production.py samples --storyboard <分镜> --media <媒体清单>"
        rows.append({"stage": f"关键幕:{role}", "status": state, "detail": detail, "nextCommand": next_command})
    for kind, label in (("content", "全片口播内容评审"), ("static", "全片静态评审"), ("dynamic", "全片有声动态评审")):
        review = record.get("reviews", {}).get("full", {}).get(kind, {})
        state = review.get("status", "pending")
        if state == "pass" and not review_current(record, current, kind):
            state = "stale"
        detail = str(review.get("evidence", ""))
        if state == "pass":
            problem = _material_issue(review, kind, record.get("materials", {}), _material_root(record, record_file),
                                      current, label)
            if problem:
                state, detail = "stale", problem
        next_command = "已通过" if state == "pass" else (
            "production.py rehearsal --storyboard <分镜> --media <媒体清单>"
            if kind in {"dynamic", "content"} else "production.py keyframes --storyboard <分镜>")
        rows.append({"stage": label, "status": state, "detail": detail, "nextCommand": next_command})
    issues = record.get("rework", [])
    open_items = [item["id"] for item in issues if item.get("severity") == "required" and item.get("status") != "resolved"]
    rows.append({"stage": "定向返工", "status": "blocked" if open_items else "not-required", "detail": "、".join(open_items) if open_items else "无未解决必改项",
                 "nextCommand": "处理并复查 production.json 中的必改项" if open_items else "无需返工"})
    problem = gate_for_status(record, storyboard, current, record_file)
    rows.append({"stage": "正式渲染", "status": "passed" if problem is None else "blocked", "detail": problem or "评审记录有效",
                 "nextCommand": "render.py --storyboard <分镜> --media <媒体清单>" if problem is None else "完成上述阻塞项后复查状态"})
    return rows


#: 阶段状态里表示「这一步已经通过」的取值。关键幕与正式渲染行用 `passed`，
#: 全片评审行直接沿用记录里的 `pass`（记录字段就是 pass/fail/pending）；
#: 两者都是成功，退出码不能只认其中一个——否则填完所有评审的命令仍然报失败。
SUCCESS_STATES = frozenset({"passed", "pass", "not-required"})


def all_stages_pass(rows: list[dict[str, str]]) -> bool:
    """所有阶段都通过时才算成功；`pending`/`stale`/`blocked` 一律算未完成。"""
    return all(row.get("status") in SUCCESS_STATES for row in rows)


def gate_for_status(record: dict[str, Any], storyboard: dict[str, Any], current: dict[str, str | None],
                    record_file: str | Path | None = None) -> str | None:
    try:
        validate_record(record, {str(item.get("id", "")) for item in storyboard.get("scenes", [])})
    except A2VError as exc:
        return str(exc)
    # status uses the same checks as render without creating or mutating a file.
    stored = record.get("fingerprints", {})
    changed = [key for key in ("storyboard", "assets", "input") if current.get(key) is not None and stored.get(key) != current.get(key)]
    if changed:
        return f"评审已过期：{'、'.join(changed)}"
    issue = _input_review_issue(record, current, record_file)
    if issue:
        return issue
    for scene_id in set(record["direction"]["keyScenes"].values()):
        review = record["reviews"]["keyScenes"].get(scene_id, {})
        if any(review.get(kind, {}).get("status") != "pass" for kind in ("static", "dynamic")):
            return f"关键幕 {scene_id} 尚未通过静态和动态评审"
        if not review_current(record, current, "static") or not review_current(record, current, "dynamic"):
            return f"关键幕 {scene_id} 的评审已过期"
        material_root = _material_root(record, record_file)
        for kind in ("static", "dynamic"):
            issue = _material_issue(review[kind], kind, record.get("materials", {}), material_root, current,
                                    f"关键幕 {scene_id} {kind} 评审")
            if issue:
                return issue
    if any(record["reviews"]["full"][kind]["status"] != "pass" or not review_current(record, current, kind) for kind in ("static", "dynamic")):
        return "全片静态和有声动态评审需通过且仍有效"
    material_root = _material_root(record, record_file)
    for kind in ("static", "dynamic"):
        issue = _material_issue(record["reviews"]["full"][kind], kind, record.get("materials", {}), material_root,
                                current, "全片有声动态评审" if kind == "dynamic" else "全片静态评审")
        if issue:
            return issue
    if any(item["severity"] == "required" and item["status"] != "resolved" for item in record["rework"]):
        return "存在未解决的必改项"
    content = record["reviews"]["full"].get("content")
    if not isinstance(content, dict) or content.get("status") != "pass":
        return "全片口播内容评审缺失或未通过（五项均需至少 4/5）"
    if not review_current(record, current, "content"):
        return "全片口播内容评审已过期"
    issue = _material_issue(content, "content", record.get("materials", {}), material_root, current, "全片口播内容评审")
    if issue: return issue
    return None
