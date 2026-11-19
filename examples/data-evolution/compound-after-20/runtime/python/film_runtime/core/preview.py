"""严格短于全片的检查窗口，半开帧区间。"""
import math
from .errors import VideoError


def window(total: int, fps: int, *, start_seconds: float = 0, end_seconds: float | None = None,
           limit_frames: int | None = None) -> tuple[int, int]:
    if not math.isfinite(start_seconds) or start_seconds < 0:
        raise VideoError("预览起始时间必须为非负有限秒数")
    if limit_frames is not None and (type(limit_frames) is not int or limit_frames < 1):
        raise VideoError("limit_frames 必须为正整数")
    if limit_frames is not None and end_seconds is not None:
        raise VideoError("--limit-frames 与 --end-seconds 不能同时使用")
    start = round(start_seconds * fps)
    if end_seconds is not None:
        if not math.isfinite(end_seconds):
            raise VideoError("预览结束时间必须为有限秒数")
        end = round(end_seconds * fps)
    elif limit_frames is not None:
        end = start + limit_frames
    else:
        end = min(total if start else total - 1, start + 10 * fps)
    if not 0 <= start < end <= total:
        raise VideoError("预览时间范围必须位于作品时长内且非空")
    if start == 0 and end == total:
        raise VideoError("预览不能覆盖全片；完整生成请使用 pnpm run render")
    return start, end
