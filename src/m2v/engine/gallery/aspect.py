"""素材长宽比契约：把「素材比例是否必须与画布一致」收敛成一份可复用的判定规则。

通用 v8 取消了按画布比例约束素材：裁切与摆位由作品代码决定，因此检索与导入都以
``aspectRatio: "any"`` 运行，本模块的 ``target_ratio`` 返回 ``None``。保留这套判定
是为了让「要不要约束比例」仍然是一处显式声明，而不是散落在各调用点的分支。

本模块不 import ``provider``，以免与它的依赖方向形成循环。
"""
from __future__ import annotations

from typing import Any, Mapping

#: 历史画布尺寸：仅在显式要求按画布比例匹配时使用（当前通用类型不启用）。
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

#: 长宽比契约的两种取值：按画布比例匹配，或不约束比例。
MODE_CANVAS = "canvas"
MODE_ANY = "any"
MODES = (MODE_CANVAS, MODE_ANY)

#: 默认容差：覆盖图库缩放取整带来的 ±1 像素级误差，同时让裁切落在不可见范围。
DEFAULT_TOLERANCE = 0.02


def canvas_ratio() -> float:
    """画布宽高比（宽 / 高）。"""
    return CANVAS_WIDTH / CANVAS_HEIGHT


def effective_mode(config: Mapping[str, Any], scene: Mapping[str, Any] | None = None) -> str:
    """该幕生效的长宽比契约：幕级声明优先，其次 provider，最后默认按画布匹配。"""
    if scene is not None and scene.get("aspectRatio") is not None:
        return str(scene["aspectRatio"])
    return str(config.get("aspectRatio") or MODE_CANVAS)


def target_ratio(config: Mapping[str, Any]) -> float | None:
    """需要匹配的目标比例；契约为 ``any`` 时返回 ``None``（表示不约束）。"""
    return canvas_ratio() if effective_mode(config) == MODE_CANVAS else None


def tolerance_of(config: Mapping[str, Any]) -> float:
    """声明的容差；缺省时使用默认值。"""
    value = config.get("aspectRatioTolerance")
    return DEFAULT_TOLERANCE if value is None else float(value)


def ratio_matches(width: Any, height: Any, ratio: float, tolerance: float) -> bool:
    """像素尺寸与目标比例的相对偏差是否落在容差内；尺寸非法一律视为不匹配。"""
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        return False
    if ratio <= 0 or tolerance < 0:
        return False
    return abs((width / height) / ratio - 1.0) <= tolerance


def describe_ratio(width: Any, height: Any) -> str:
    """把像素尺寸写成可读的「宽×高（约 W:H）」证据串，用于报错与留证。"""
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        return f"{width}×{height}"
    return f"{width}×{height}（约 {_simple_ratio(width, height)}）"


def _simple_ratio(width: int, height: int) -> str:
    """用最大公约数把比例化简成 ``16:9`` 这样的整数比；化简后过大时退回小数。"""
    divisor = _gcd(width, height)
    left, right = width // divisor, height // divisor
    if max(left, right) > 100:
        return f"{width / height:.3f}:1"
    return f"{left}:{right}"


def _gcd(left: int, right: int) -> int:
    while right:
        left, right = right, left % right
    return left or 1
