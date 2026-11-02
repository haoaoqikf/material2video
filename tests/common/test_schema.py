"""材料结构层的严格语义：未知字段、类型与中文路径。"""
from __future__ import annotations

import pytest

from m2v.core.errors import M2VError
from m2v.core.schema import NonEmptyText, StrictModel, validate_document


class Sample(StrictModel):
    name: NonEmptyText
    count: int


def test_unknown_field_is_rejected_with_path():
    with pytest.raises(M2VError, match=r"sample\.extra: 未知字段"):
        validate_document(Sample, {"name": "a", "count": 1, "extra": True}, "sample")


def test_boolean_is_not_an_integer():
    with pytest.raises(M2VError, match="必须是整数"):
        validate_document(Sample, {"name": "a", "count": True}, "sample")


def test_empty_text_is_rejected():
    with pytest.raises(M2VError, match="不能为空"):
        validate_document(Sample, {"name": "  ", "count": 1}, "sample")


def test_missing_field_names_the_field():
    with pytest.raises(M2VError, match=r"sample\.count: 缺少必填字段"):
        validate_document(Sample, {"name": "a"}, "sample")


def test_success_returns_the_original_document():
    value = {"name": "a", "count": 1}
    assert validate_document(Sample, value, "sample") is value
