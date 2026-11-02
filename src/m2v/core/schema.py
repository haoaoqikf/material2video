"""材料结构校验的共享 Pydantic 层。

这里只负责“文档形状”：必填字段、类型、数组/对象、未知字段与简单的边界。
路线连续性、价格覆盖、投资计算等业务语义仍留在各类型校验器里。
模型默认严格模式，保持现有契约「布尔不算数字、未知字段直接拒绝」。
"""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

from m2v.core.errors import M2VError

#: 非空文本；先去掉首尾空白再判长度，与 `core.validate.text` 的口径一致。
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

_MESSAGES = {
    "missing": "缺少必填字段",
    "extra_forbidden": "未知字段",
    "string_type": "必须是文本",
    "int_type": "必须是整数",
    "float_type": "必须是数字",
    "bool_type": "必须是布尔值",
    "list_type": "必须是数组",
    "dict_type": "必须是对象",
    "literal_error": "取值不在允许范围",
    "greater_than_equal": "不得小于 {ge}",
    "greater_than": "必须大于 {gt}",
    "less_than_equal": "不得大于 {le}",
    "less_than": "必须小于 {lt}",
    "string_too_short": "不能为空",
    "string_pattern_mismatch": "格式不符合要求",
    "too_long": "最多 {max_length} 项",
    "too_short": "至少 {min_length} 项",
    "finite_number": "必须是有限数字",
}


class StrictModel(BaseModel):
    """材料文档基类：拒绝未知字段，按严格类型判定。"""

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


def _describe(error: dict[str, Any]) -> str:
    kind = error.get("type", "")
    template = _MESSAGES.get(kind)
    if template:
        context = error.get("ctx") or {}
        try:
            return template.format(**context)
        except (KeyError, ValueError):
            return template
    message = str(error.get("msg") or "结构不符合要求")
    return message


def validate_document(model: type[BaseModel], value: Any, path: str) -> Any:
    """校验一份材料文档；成功时原样返回，失败时抛中文 `M2VError`。

    原样返回而不是模型的 `model_dump()`：材料里可能包含模型只声明为 `Any`
    的嵌套对象，重新序列化会改变键顺序或补出默认值，下游指纹会因此漂移。
    """
    try:
        model.model_validate(value)
    except ValidationError as exc:
        error = exc.errors()[0]
        location = ".".join(str(part) for part in error.get("loc", ()))
        where = f"{path}.{location}" if location else path
        raise M2VError(f"{where}: {_describe(error)}") from exc
    return value
