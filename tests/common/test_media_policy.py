"""采用政策覆盖三条消费者共用的状态、依据和片段失败边界。"""
from __future__ import annotations

import pytest

from m2v.core.errors import M2VError
from m2v.core import media_policy


def reviewed(status="no-explicit-restriction", **extra):
    return {"status": status, "evidenceUrl": "https://example.com/terms", "checkedAt": "2026-11-05",
            "note": "用于产品介绍；检查素材页与条款未发现禁止此用途", **extra}


def test_unknown_and_unchecked_remain_distinct_from_permission():
    entry = {"license": "未知"}
    source, errors, warnings = media_policy.assess(entry)
    assert source["usage"] == {"status": "not-checked"}
    assert not errors
    assert {item["code"] for item in warnings} == {"usage-not-checked", "license-unknown"}
    assert "usage" not in entry


@pytest.mark.parametrize("status,conditions,blocked", [
    ("no-explicit-restriction", {}, False), ("explicit-allowed", {}, False),
    ("prohibited", {}, True), ("conditional", {"conditionsMet": False}, True),
    ("conditional", {"conditionsMet": True}, False),
])
def test_explicit_restrictions_override_license_labels(status, conditions, blocked):
    source, errors, _ = media_policy.assess({"license": "CC0", "usage": reviewed(status, **conditions)})
    assert bool(errors) is blocked
    assert source["usage"]["status"] == status


@pytest.mark.parametrize("usage", [
    None, {"status": "typo"}, {"status": "no-explicit-restriction"},
    reviewed(checkedAt="2026-02-30"), reviewed(checkedAt="20261105"),
    reviewed(evidenceUrl="file:///tmp/terms"), reviewed(evidenceUrl="https://user:secret@example.com/"),
    reviewed(evidenceUrl="https://[broken"), reviewed(note="  "),
    reviewed(evidenceUrl="https://:443"), reviewed(evidenceUrl="https://exa mple.com/terms"),
    reviewed(evidenceUrl="https://example.com:not-a-port/terms"),
    reviewed("conditional"), reviewed("conditional", conditionsMet="true"),
    reviewed(conditionsMet=True), reviewed(extraField="x"),
])
def test_invalid_usage_is_not_silently_downgraded(usage):
    with pytest.raises(M2VError):
        media_policy.assess({"usage": usage})


def test_prohibition_does_not_require_complete_evidence_to_block():
    _, errors, _ = media_policy.assess({"usage": {"status": "prohibited"}})
    assert errors[0]["code"] == "usage-prohibited"


@pytest.mark.parametrize("segment,kind,duration", [
    ({"startSeconds": 2, "endSeconds": 1}, "video", 4),
    ({"startSeconds": 0, "endSeconds": 5}, "video", 4),
    ({"startSeconds": -1, "endSeconds": 1}, "video", 4),
    ({"startSeconds": False, "endSeconds": 1}, "video", 4),
    ({"startSeconds": 0, "endSeconds": float("nan")}, "video", 4),
    ({"startSeconds": 0, "endSeconds": 1}, "image", None),
])
def test_invalid_usable_segment(segment, kind, duration):
    with pytest.raises(M2VError):
        media_policy.metadata({"kind": kind, "durationSeconds": duration, "usableSegment": segment})


def test_segment_and_official_source_are_retained():
    fields = {"sourceType": "official", "publisher": "公司甲", "description": "产品演示",
              "usableSegment": {"startSeconds": 1, "endSeconds": 4}, "usage": reviewed()}
    source = media_policy.metadata({"kind": "video", "durationSeconds": 4, **fields})
    assert source == fields
