"""分阶段耗时与结构化性能报告。

报告要**记录真实**阶段耗时、标明缓存命中，未执行的阶段标记为跳过，
且总耗时不重复累计（渲染与编码在 Remotion 内部重叠，只记一段）。

口径部分直接测 `m2v.engine.perf`；落盘部分用金融导出路径做集成验证——
它是最短的「打包 → 会话 → 收口 → 报告」全链路，替身顶掉打包与渲染进程，
保留真实的计时与报告逻辑。
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import m2v.engine.output_validation as output_validation
import m2v.engine.perf as perf
import m2v.engine.remotion as remotion
import m2v.engine.render_pipeline as render_pipeline
import m2v.types.financial.financial as financial
import m2v.types.financial.financial_render as financial_render

from helpers.financial import project


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


def test_financial_render_writes_the_performance_report(tmp_path, monkeypatch):
    root = project(tmp_path)
    docs = financial.load_project(root)
    destination = root / "outputs" / "previews" / "perf.mp4"
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    total_frames = docs["plan"]["durationSeconds"] * financial.FPS

    monkeypatch.setattr(remotion, "web_dir", lambda: tmp_path)
    monkeypatch.setattr(remotion, "bundle", lambda **kwargs: SimpleNamespace(
        path=bundle, build_seconds=0.02, cache_seconds=0.01,
        cache_status="hit", cache_key="perf-test", cache_detail="测试替身"))
    monkeypatch.setattr(output_validation, "verify_output", lambda *args, **kwargs: None)
    monkeypatch.setattr(render_pipeline, "assert_no_audio", lambda video: None)
    monkeypatch.setattr(render_pipeline.security, "grant_inherited_access", lambda path: True)

    def fake_session(**kwargs):
        params = kwargs["on_metadata"](remotion.CompositionMetadata(
            fps=financial.FPS, width=financial.WIDTH, height=financial.HEIGHT,
            duration_in_frames=total_frames))
        Path(params["out"]).write_bytes(b"fake video")
        return {"readySeconds": 0.03, "browsersOpened": 1}

    monkeypatch.setattr(remotion, "render_session", fake_session)

    output = financial_render.render(root, docs, preview=True, limit_frames=2, output=destination)
    assert output == destination
    report = json.loads(perf.report_path_for(output).read_text(encoding="utf-8"))
    assert report["entry"] == "preview"
    assert (report["frames"], report["fps"], report["width"], report["height"]) == (
        2, financial.FPS, financial.WIDTH, financial.HEIGHT)
    assert report["cache"]["status"] == "hit"
    assert report["stages"]["bundle"] == pytest.approx(0.02)
    assert report["stages"]["cache"] == pytest.approx(0.01)
    assert report["stages"]["metadata"] == pytest.approx(0.03)
    # 无声合成：音轨阶段不存在，必须标为跳过而不是 0 秒
    assert report["stages"]["mux"] is None and "mux" in report["skipped"]
    # 浏览器只开一次，且会话信息留在报告里（`extra` 的键并入报告根）
    assert report["session"]["browsersOpened"] == 1