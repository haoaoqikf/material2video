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

from m2v.core.errors import M2VError
from m2v.core.schema import NonEmptyText, StrictModel, validate_document

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


class QuotedWork(StrictModel):
    title: NonEmptyText | None = None
    author: NonEmptyText | None = None
    platform: NonEmptyText | None = None
    url: AnyHttpUrl | None = None
    durationSeconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class SourceMetadata(StrictModel):
    sourceType: Literal["official", "official-account", "archive", "research", "news", "industry",
                        "open-library", "stock", "social-screenshot", "quoted-media", "other"] = "other"
    publisher: NonEmptyText = "未知"
    description: str = ""
    usableSegment: Segment | None = None
    usage: Usage = Field(default_factory=lambda: Usage(status="no-explicit-restriction"))
    platform: NonEmptyText | None = None
    postUrl: AnyHttpUrl | None = None
    postedAt: NonEmptyText | None = None
    capturedAt: NonEmptyText | None = None
    risk: Literal["low", "medium", "high"] | None = None
    riskNotes: NonEmptyText | None = None
    quotedWork: QuotedWork | None = None


FIELDS = frozenset(SourceMetadata.model_fields)


def _check_date(value: str, label: str) -> None:
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("日期格式")
        date.fromisoformat(value)
    except ValueError as exc:
        raise M2VError(f"{label} 必须是 YYYY-MM-DD 有效日期") from exc


def metadata(entry: dict) -> dict:
    """校验清单或登记项的可选元数据；缺省按从宽政策采用。"""
    values = {key: entry[key] for key in FIELDS if key in entry}
    validate_document(SourceMetadata, values, "素材来源")
    result = SourceMetadata.model_validate(values).model_dump(mode="json", exclude_none=True)
    usage = result["usage"]
    if "evidenceUrl" in usage:
        try:
            url = urlsplit(usage["evidenceUrl"])
        except ValueError as exc:
            raise M2VError("usage.evidenceUrl 必须是有效的 HTTP(S) 依据页") from exc
        if url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password:
            raise M2VError("usage.evidenceUrl 必须是无凭据的 HTTP(S) 依据页")
    if "checkedAt" in usage:
        _check_date(usage["checkedAt"], "usage.checkedAt")
    for key in ("postedAt", "capturedAt"):
        if key in result:
            _check_date(result[key], f"素材 {key}")
    if usage["status"] == "conditional" and "conditionsMet" not in usage:
        raise M2VError("usage 条件使用必须提供布尔 conditionsMet")
    if "conditionsMet" in usage and usage["status"] != "conditional":
        raise M2VError("usage.conditionsMet 仅用于 conditional 状态")
    segment = result.get("usableSegment")
    if segment:
        duration = entry.get("durationSeconds")
        if (entry.get("kind") != "video" or not isinstance(duration, (int, float))
                or isinstance(duration, bool) or not segment["startSeconds"] < segment["endSeconds"] <= duration):
            raise M2VError("usableSegment 必须是实际视频时长内的有效起止窗口")
    return result


def assess(entry: dict) -> tuple[dict, list[dict], list[dict]]:
    """返回规范元数据、阻断原因、提示；结构错误由调用方按素材 ID 定位。"""
    source = metadata(entry)
    usage = source["usage"]
    problems, warnings = [], []
    if usage["status"] == "prohibited":
        problems.append({"code": "usage-prohibited", "message": "权利人明确禁止当前用途，请更换素材"})
    elif usage["status"] == "conditional" and not usage["conditionsMet"]:
        warnings.append({"code": "usage-conditions-unmet",
                         "message": "使用条件未满足，按从宽政策记录风险后继续采用"})
    elif usage["status"] == "not-checked":
        warnings.append({"code": "usage-not-checked", "message": "采用依据未核实，按从宽政策继续采用"})
    elif usage["status"] == "no-explicit-restriction":
        warnings.append({"code": "usage-no-explicit-restriction",
                         "message": "按未发现明确禁止的从宽政策采用，不代表已获授权"})
    if str(entry.get("license") or "未知").strip().lower() in UNKNOWN_LICENSES:
        warnings.append({"code": "license-unknown", "message": "原始许可未知，保留原值并记录本次采用依据"})
    return source, problems, warnings
