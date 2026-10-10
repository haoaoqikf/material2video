"""基准与验收的判定逻辑。

真正跑渲染的矩阵按分钟计（见任务 4.1/4.2 的实测报告），这里验证的是
**把数字变成结论**的那部分：中位数、目标判定、跨并发 PSNR、字幕时间轴与内存采样。
判定逻辑错了，跑再多次也只能得到一份读不出结论的报告。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from a2v import benchmark, perf


def _sample_run(
    example: str,
    scenario: str,
    *,
    total: float,
    bundle: float | None,
    concurrency: int = 1,
    peak: int | None = 100,
    status: str = "miss",
    cache_stage: float = 0.05,
) -> dict:
    return {
        "example": example,
        "scenario": scenario,
        "concurrency": concurrency,
        "frames": 90,
        "totalSeconds": total,
        "captureSeconds": total / 2,
        "stages": {
            "cache": cache_stage,
            "bundle": bundle,
            "metadata": 1.0,
            "render": total - 1.5,
            "mux": None,
            "probe": 0.5,
        },
        "cache": {"status": status, "key": "k", "detail": "", "prepareSeconds": cache_stage, "buildSeconds": bundle},
        "session": {"browsersOpened": 1},
        "peakRssBytes": peak,
        "outputBytes": 1000,
        "output": "out.mp4",
        "startedAt": "2026-01-01T00:00:00+00:00",
        "failure": None,
    }


def test_summarize_series_reports_medians_and_peak_memory():
    runs = [
        _sample_run("demo", "cold", total=value, bundle=value / 2, peak=peak)
        for value, peak in ((30.0, 100), (20.0, 300), (25.0, 200))
    ]
    summary = benchmark.summarize_series(runs)
    assert summary["runs"] == 3
    assert summary["totalSecondsMedian"] == 25.0
    assert summary["totalSecondsMin"] == 20.0
    assert summary["stagesMedian"]["bundle"] == 12.5
    assert summary["peakRssBytesMax"] == 300
    # 未执行的阶段仍然是 None，不参与中位数
    assert summary["stagesMedian"]["mux"] is None


def test_evaluate_targets_checks_the_three_declared_goals():
    series = {}
    for example in benchmark.EXAMPLES:
        series[f"{example}/baseline/c1"] = benchmark.summarize_series(
            [_sample_run(example, "baseline", total=100.0, bundle=40.0, status="disabled")]
        )
        series[f"{example}/cold/c1"] = benchmark.summarize_series(
            [_sample_run(example, "cold", total=102.0, bundle=41.0)]
        )
        series[f"{example}/hot/c1"] = benchmark.summarize_series(
            [_sample_run(example, "hot", total=80.0, bundle=2.0, status="hit")]
        )
    report = benchmark.evaluate_targets(series, representative=benchmark.EXAMPLES[1])
    checks = {check["name"]: check for check in report["checks"]}
    bundle_check = checks[f"{benchmark.EXAMPLES[0]}: 热缓存打包相关阶段下降"]
    # 打包相关 = cache + bundle：冷 0.05+41，热 0.05+2
    assert bundle_check["pass"] and bundle_check["value"] == pytest.approx(1 - 2.05 / 41.05, abs=1e-4)
    regression = checks[f"{benchmark.EXAMPLES[0]}: 冷路径回退（缓存机制可归因开销）"]
    # 回退量读缓存机制自身耗时（0.05 秒）÷ 基线中位数（100 秒）
    assert regression["pass"] and regression["value"] == pytest.approx(0.0005, abs=1e-6)
    assert regression["endToEndDeltaSeconds"] == pytest.approx(2.0, abs=1e-6)
    hot = checks[f"{benchmark.EXAMPLES[1]}: 热缓存端到端下降"]
    assert hot["pass"] and hot["value"] == pytest.approx(1 - 80 / 102, abs=1e-4)
    assert report["pass"]


def test_evaluate_targets_fails_when_a_goal_is_missed():
    series = {}
    for example in benchmark.EXAMPLES:
        series[f"{example}/baseline/c1"] = benchmark.summarize_series(
            [_sample_run(example, "baseline", total=100.0, bundle=40.0, status="disabled")]
        )
        # 冷路径的缓存机制开销取 6 秒（基线的 6%），越界
        series[f"{example}/cold/c1"] = benchmark.summarize_series(
            [_sample_run(example, "cold", total=110.0, bundle=41.0, cache_stage=6.0)]
        )
        series[f"{example}/hot/c1"] = benchmark.summarize_series(
            [_sample_run(example, "hot", total=105.0, bundle=20.0, status="hit")]
        )
    report = benchmark.evaluate_targets(series, representative=benchmark.EXAMPLES[0])
    assert not report["pass"]
    failed = [check["name"] for check in report["checks"] if not check["pass"]]
    assert any("打包相关" in name for name in failed)
    assert any("端到端" in name for name in failed)
    assert any("冷路径回退" in name for name in failed)
    regression = next(c for c in report["checks"] if "冷路径回退" in c["name"])
    # 报告里同时给出端到端差值与观测带宽，便于区分「确实慢」与「这次本来就慢」
    assert regression["value"] == pytest.approx(0.06, abs=1e-6)
    assert regression["attributableSeconds"] == 6.0
    assert regression["endToEndDeltaSeconds"] == pytest.approx(10.0, abs=1e-6)
    assert "noiseSeconds" in regression


def test_evaluate_targets_reports_missing_series_instead_of_passing():
    report = benchmark.evaluate_targets({}, representative=benchmark.EXAMPLES[0])
    assert not report["pass"]
    assert all(check["value"] is None for check in report["checks"])


def _jpeg(directory: Path, name: str, color: str) -> Path:
    target = directory / name
    completed = subprocess.run(
        [get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c={color}:s=32x32",
         "-frames:v", "1", str(target)],
        capture_output=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr[-500:]
    return target


def test_psnr_between_identical_frames_is_infinite_and_changed_frames_fail(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    changed = tmp_path / "changed"
    for directory in (left, right, changed):
        directory.mkdir()
        _jpeg(directory, "frame-0.jpg", "black")
        _jpeg(directory, "frame-1.jpg", "white")
    shutil.copy(left / "frame-0.jpg", right / "frame-0.jpg")
    shutil.copy(left / "frame-1.jpg", right / "frame-1.jpg")

    same = benchmark.psnr_between(left, right)
    assert same["pass"], same
    assert same["identicalFrames"] == 2
    assert same["minimumDb"] is None, "完全一致的帧不产生有限 PSNR"

    _jpeg(changed, "frame-0.jpg", "black")
    _jpeg(changed, "frame-1.jpg", "red")
    different = benchmark.psnr_between(left, changed)
    assert not different["pass"]
    assert different["worstDb"] is not None and different["worstDb"] < benchmark.PSNR_FLOOR_DB
    assert different["worstFrame"] == "frame-1.jpg"


def test_psnr_rejects_mismatched_frame_counts(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    _jpeg(left, "frame-0.jpg", "black")
    _jpeg(left, "frame-1.jpg", "black")
    _jpeg(right, "frame-0.jpg", "black")
    with pytest.raises(Exception, match="截图数量不一致"):
        benchmark.psnr_between(left, right)


# ---------------------------------------------------------------- 字幕时间轴


def _srt(*spans: tuple[str, str]) -> str:
    blocks = []
    for index, (start, end) in enumerate(spans, start=1):
        blocks.append(f"{index}\n{start} --> {end}\n第 {index} 句\n")
    return "\n".join(blocks)


def test_subtitle_timeline_accepts_monotonic_cues(tmp_path):
    path = tmp_path / "voiced.srt"
    path.write_text(_srt(("00:00:00,000", "00:00:02,000"), ("00:00:02,500", "00:00:05,000")), encoding="utf-8")
    report = benchmark.verify_subtitles(path, duration=5.0)
    assert report["cues"] == 2 and report["lastEnd"] == 5.0


def test_subtitle_timeline_rejects_overlap_and_overrun(tmp_path):
    overlap = tmp_path / "overlap.srt"
    overlap.write_text(_srt(("00:00:00,000", "00:00:03,000"), ("00:00:02,000", "00:00:04,000")), encoding="utf-8")
    with pytest.raises(Exception, match="重叠或倒序"):
        benchmark.verify_subtitles(overlap, duration=5.0)

    overrun = tmp_path / "overrun.srt"
    overrun.write_text(_srt(("00:00:00,000", "00:00:09,000")), encoding="utf-8")
    with pytest.raises(Exception, match="超出成片时长"):
        benchmark.verify_subtitles(overrun, duration=5.0)


def test_subtitle_timeline_requires_the_file(tmp_path):
    with pytest.raises(Exception, match="没有生成字幕文件"):
        benchmark.verify_subtitles(tmp_path / "missing.srt", duration=1.0)


# ---------------------------------------------------------------- 内存采样


def test_memory_sampler_reports_the_peak_of_its_probe():
    values = iter([10, 40, 20, 30, 30, 30])
    sampler = perf.ProcessTreeMemorySampler(
        1234, interval_s=0.001, probe=lambda pid: next(values, 30)
    )
    sampler.start()
    time.sleep(0.05)
    peak = sampler.stop()
    assert peak == 40
    assert sampler.samples >= 2


def test_memory_sampler_tolerates_a_probe_that_fails():
    sampler = perf.ProcessTreeMemorySampler(1234, interval_s=0.001, probe=lambda pid: None)
    sampler.start()
    time.sleep(0.02)
    assert sampler.stop() is None
    assert sampler.samples == 0


@pytest.mark.skipif(os.name != "nt", reason="Windows 的 CIM 进程树采样")
def test_tree_memory_probe_reads_this_process():
    """采样器要真能读数：只验证「返回正整数」这一件事，不比对具体数值。"""
    value = perf.tree_memory_bytes(os.getpid())
    assert isinstance(value, int) and value > 0
