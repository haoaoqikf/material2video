"""有界、确定性的全时间轴预算分配；不把排序靠前误当更重要。"""
from __future__ import annotations

from bisect import bisect_left
import heapq
from typing import Callable, TypeVar

T = TypeVar('T')
STRATEGY = 'timeline-spread-v1'


def spread(items: list[T], limit: int, *, time: Callable[[T], int] = lambda item: item) -> list[T]:
    """在整个时间范围选最近代表点；至少两点时保留两端，单点取中部。"""
    ordered = sorted(items, key=time)
    if len(ordered) <= limit:
        return ordered
    if limit < 1:
        raise ValueError('采样预算必须为正整数')
    times = [time(item) for item in ordered]
    if limit == 1:
        target = (times[0] + times[-1]) // 2
        return [ordered[min(range(len(times)), key=lambda i: (abs(times[i] - target), i))]]
    selected = {0, len(ordered) - 1}
    for step in range(1, limit - 1):
        target = times[0] + (times[-1] - times[0]) * step // (limit - 1)
        right = bisect_left(times, target)
        choices = [i for i in (right - 1, right) if 0 <= i < len(times) and i not in selected]
        if choices:
            selected.add(min(choices, key=lambda i: (abs(times[i] - target), i)))
    # 非均匀候选可能多个目标落在同一点附近；分裂最大可用间隔补足预算。
    gaps = []
    def add_gap(left, right):
        if right - left > 1:
            heapq.heappush(gaps, (-(times[right] - times[left]), -(right - left), left, right))
    positions = sorted(selected)
    for left, right in zip(positions, positions[1:]):
        add_gap(left, right)
    while len(selected) < limit:
        _, _, left, right = heapq.heappop(gaps)
        middle = min(right - 1, max(left + 1, bisect_left(times, (times[left] + times[right]) // 2)))
        selected.add(middle)
        add_gap(left, middle)
        add_gap(middle, right)
    return [ordered[i] for i in sorted(selected)]


def frame_time(record) -> int:
    return record.localRange.startUs if record.localRange else 0
