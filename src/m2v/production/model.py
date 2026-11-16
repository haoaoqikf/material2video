"""媒体评审的小型公共校验；不解析设计文档或画面断言。"""

from __future__ import annotations

import math
import re
import subprocess
from datetime import datetime, timezone

from imageio_ffmpeg import get_ffmpeg_exe
from m2v.core.errors import M2VError

VERSION = 4
ROUNDS = ("trial",)
PURPOSES = ("keyframe", "process")


def adoption(verdict):
    """证据不足明确不可采用；不以文字禁词代替审美判断。"""
    return "adopt" if verdict == "pass" else "reject"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fields(value, required, optional=()):
    if (
        not isinstance(value, dict)
        or set(required) - value.keys()
        or value.keys() - set(required) - set(optional)
    ):
        raise M2VError(f"评审字段缺失或未知；必需字段：{sorted(required)}")


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", value
    ):
        raise M2VError("ID 必须为字母、数字、下划线或连字符，最长 96 位")
    return value


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise M2VError("必须填写具体观察或依据")


def window(value):
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(x) is not int for x in value)
        or not 0 <= value[0] < value[1]
    ):
        raise M2VError("观察窗口必须为非负整数帧的 [start, end)")
    return value


def ffmpeg(args):
    try:
        result = subprocess.run(
            [get_ffmpeg_exe(), "-v", "error", "-nostdin", "-y", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M2VError(f"评审媒体处理无法完成：{exc}") from exc
    if result.returncode:
        raise M2VError("评审媒体处理失败：" + result.stderr[-1500:])


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0
