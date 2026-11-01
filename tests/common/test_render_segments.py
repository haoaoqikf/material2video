"""进程级分段渲染的区间切分；真实渲染只在 slow 用例里做。"""
from __future__ import annotations

import pytest

from m2v.engine.remotion.process import RemotionError
from m2v.engine.remotion.segments import frame_ranges


def test_frame_ranges_split_without_gaps_or_overlap():
    assert frame_ranges(10, 3) == [(0, 3), (3, 7), (7, 10)]
    assert frame_ranges(7, 2) == [(0, 4), (4, 7)]
    # 进程数超过帧数时按帧数收敛，避免空段。
    assert frame_ranges(2, 4) == [(0, 1), (1, 2)]


@pytest.mark.parametrize("jobs", [0, -1])
def test_frame_ranges_rejects_invalid_jobs(jobs):
    with pytest.raises(RemotionError, match="正整数"):
        frame_ranges(10, jobs)


def test_frame_ranges_rejects_empty_composition():
    with pytest.raises(RemotionError, match="总帧数"):
        frame_ranges(0, 2)
