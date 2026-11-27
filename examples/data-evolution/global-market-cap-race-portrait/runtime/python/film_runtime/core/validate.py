"""类型材料校验的共享原语。

各类型适配器过去各写一份「必须是对象 / 未知字段 / 有限数字 / 非空文本」的判定：
这里提供唯一实现：调用方只传字段路径与边界，错误消息由这里统一给出。

路径参数 `path` 指向 JSON 内的层级位置（例如 `scenes[2].content`），便于按报错定位。
"""
from __future__ import annotations

import math
from typing import Any

from film_runtime.core.errors import VideoError


def fail(path: str, message: str) -> None:
    raise VideoError(f"{path}: {message}")


def obj(value: Any, path: str, allowed: set[str]) -> dict:
    if not isinstance(value, dict):
        fail(path, "必须是对象")
    unknown = set(value) - allowed
    if unknown:
        fail(path, f"未知字段：{'、'.join(sorted(unknown))}")
    return value


def number(value: Any, low: float, high: float, path: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        fail(path, f"必须为 {low}～{high} 的有限数字")
    return value


def integer(value: Any, low: int, high: int, path: str) -> int:
    if type(value) is not int or not low <= value <= high:
        fail(path, f"必须为 {low}～{high} 的整数")
    return value


def text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(path, "必须是非空文本")
    return value


def items(value: Any, path: str, maximum: int) -> list:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        fail(path, f"必须包含 1～{maximum} 项")
    return value
