"""画面素材的来源记录与采用政策；不推断法律授权，不执行网络请求。

原始许可和本次用途的检查结果是两件事。缺少检查记录只提示，绝不能被规范化成
「未发现明确禁止」；明确禁止或未满足的条件则在所有采用检查路径阻断。
"""
from __future__ import annotations

from datetime import date
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, Field

from film_runtime.core.errors import VideoError
from film_runtime.core.schema import NonEmptyText, StrictModel, validate_document

UNKNOWN_LICENSES = ("", "未知", "unknown", "n/a", "none", "null")


class Usage(StrictModel):
    status: Literal["explicit-allowed", "no-explicit-restriction", "conditional", "prohibited", "not-checked"]
    evidenceUrl: AnyHttpUrl | None = None
    checkedAt: NonEmptyText | None = None
    note: NonEmptyText | None = None
    conditionsMet: bool | None = None


class Segment(StrictModel):
    startSeconds: float = Field(ge=0, allow_inf_nan=False)
    endSeconds: float = Field(gt=0, allow_inf_nan=False)


class SourceMetadata(StrictModel):
    sourceType: Literal["official", "official-account", "archive", "research", "news", "industry",
                        "open-library", "stock", "other"] = "other"
    publisher: NonEmptyText = "未知"
    description: str = ""
    usableSegment: Segment | None = None
    usage: Usage = Field(default_factory=lambda: Usage(status="not-checked"))


FIELDS = frozenset(SourceMetadata.model_fields)


def metadata(entry: dict) -> dict:
    """校验清单或登记项的可选元数据；缺省不意味着检查已经完成。"""
    values = {key: entry[key] for key in FIELDS if key in entry}
    validate_document(SourceMetadata, values, "素材来源")
    result = SourceMetadata.model_validate(values).model_dump(mode="json", exclude_none=True)
    usage = result["usage"]
    checked = usage["status"] in {"explicit-allowed", "no-explicit-restriction", "conditional"}
    if checked and any(not usage.get(key) for key in ("evidenceUrl", "checkedAt", "note")):
        raise VideoError("usage 已检查状态必须提供 evidenceUrl、checkedAt 和 note（用途与检查结论）")
    if "evidenceUrl" in usage:
        try:
            url = urlsplit(usage["evidenceUrl"])
        except ValueError as exc:
            raise VideoError("usage.evidenceUrl 必须是有效的 HTTP(S) 依据页") from exc
        if url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password:
            raise VideoError("usage.evidenceUrl 必须是无凭据的 HTTP(S) 依据页")
    if "checkedAt" in usage:
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", usage["checkedAt"]):
                raise ValueError("日期格式")
            date.fromisoformat(usage["checkedAt"])
        except ValueError as exc:
            raise VideoError("usage.checkedAt 必须是 YYYY-MM-DD 有效日期") from exc
    if usage["status"] == "conditional" and "conditionsMet" not in usage:
        raise VideoError("usage 条件使用必须提供布尔 conditionsMet")
    if "conditionsMet" in usage and usage["status"] != "conditional":
        raise VideoError("usage.conditionsMet 仅用于 conditional 状态")
    segment = result.get("usableSegment")
    if segment:
        duration = entry.get("durationSeconds")
        if (entry.get("kind") != "video" or not isinstance(duration, (int, float))
                or isinstance(duration, bool) or not segment["startSeconds"] < segment["endSeconds"] <= duration):
            raise VideoError("usableSegment 必须是实际视频时长内的有效起止窗口")
    return result


def assess(entry: dict) -> tuple[dict, list[dict], list[dict]]:
    """返回规范元数据、阻断原因、提示；结构错误由调用方按素材 ID 定位。"""
    source = metadata(entry)
    usage = source["usage"]
    problems, warnings = [], []
    if usage["status"] == "prohibited":
        problems.append({"code": "usage-prohibited", "message": "明确禁止当前用途，请更换素材"})
    elif usage["status"] == "conditional" and not usage["conditionsMet"]:
        problems.append({"code": "usage-conditions-unmet", "message": "使用条件未满足，请满足条件或更换素材"})
    elif usage["status"] == "not-checked":
        warnings.append({"code": "usage-not-checked", "message": "采用依据未核实；继续检查来源页和适用条款，不代表已获授权"})
    elif usage["status"] == "no-explicit-restriction":
        warnings.append({"code": "usage-no-explicit-restriction", "message": "按未发现明确禁止的制作政策采用，不代表已获授权"})
    if str(entry.get("license") or "未知").strip().lower() in UNKNOWN_LICENSES:
        warnings.append({"code": "license-unknown", "message": "原始许可未知，保留原值并记录本次采用依据"})
    return source, problems, warnings

# 本作品登记媒体的用途，与许可审计共用同一组语义。
MEDIA_ROLES = ("color", "normal", "roughness", "emissive", "ring", "alpha", "other")
