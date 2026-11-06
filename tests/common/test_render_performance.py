"""分阶段耗时与结构化性能报告。

报告要**记录真实**阶段耗时、标明缓存命中，未执行的阶段标记为跳过，
且总耗时不重复累计（渲染与编码在 Remotion 内部重叠，只记一段）。

直接测 `m2v.engine.perf` 的阶段计时与报告口径。
"""

from __future__ import annotations

import os
import time

import pytest

import m2v.engine.perf as perf



# ---------------------------------------------------------------- 口径


def test_stage_timings_marks_skipped_stages_as_none():
    timings = perf.StageTimings()
    with timings.measure("bundle"):
        time.sleep(0.06)
    timings.skip("mux", "probe")
    values = timings.as_dict()
    assert values["bundle"] is not None and values["bundle"] > 0
    assert values["mux"] is None and values["probe"] is None
    # 固定形状：报告里每个阶段都在，没跑的为 null，而不是缺键或写 0
    assert set(values) == set(perf.STAGES)
    assert set(timings.skipped()) == {"cache", "metadata", "render", "mux", "probe"}


def test_report_covers_every_stage_once_and_total_is_not_double_counted():
    """渲染与编码重叠执行，因此报告里只有一段合并耗时，总耗时也不重复累计。"""
    timings = perf.StageTimings()
    started = time.monotonic()
    with timings.measure("bundle"):
        time.sleep(0.02)
    with timings.measure("metadata"):
        time.sleep(0.01)
    with timings.measure("render"):
        time.sleep(0.02)
    timings.skip("mux")
    timings.skip("probe")
    timings.record("cache", 0.005)
    total = time.monotonic() - started
    report = perf.build_report(
        entry="test",
        output="out.mp4",
        storyboard="storyboard.json",
        frames=90,
        fps=60,
        width=1080,
        height=1920,
        concurrency=1,
        timings=timings,
        total_seconds=total,
    )
    assert "encode" not in report["stages"], "渲染与编码重叠，不得拆成两段相加"
    assert set(report["stages"]) == set(perf.STAGES)
    executed = sum(value for value in report["stages"].values() if value is not None)
    assert report["executedSeconds"] == pytest.approx(executed, abs=1e-6)
    # 每一段都发生在整段之内：总耗时不可能小于各段之和
    assert report["totalSeconds"] >= executed - 0.01
    assert report["skipped"] == ["mux", "probe"]
    # 环境信息随报告一起留下，否则两次数字没有可比性
    assert report["environment"]["python"]


def test_tree_memory_reads_the_current_process():
    value = perf.tree_memory_bytes(os.getpid())
    assert value and value > 0


# ---------------------------------------------------------------- 落盘
