"""分阶段耗时与结构化性能报告。

对应 openspec 变更 `optimize-final-video-render` 的任务 1.2：
报告要**记录真实**阶段耗时、标明缓存命中与实际并发，未执行的阶段标记为跳过，
且总耗时不重复累计（渲染与编码在 Remotion 内部重叠，只记一段）。

这里用替身顶掉打包与渲染：真实渲染按分钟计，而本文件要验证的是记录的**口径**。
真实数字由基准入口产出，见 `tests/test_render_benchmark.py`。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import a2v.engine.perf as perf
import a2v.engine.remotion as remotion
import a2v.types.article.render as render_mod


def _storyboard(frames: int = 90):
    """渲染编排只需要这几个字段来做交叉校验。"""
    return SimpleNamespace(fps=30, width=1080, height=1920, total_frames=frames)


def _fake_bundle(*, status: str = "miss", build_seconds: float = 0.02, cache_seconds: float = 0.01):
    def fake_bundle(**kwargs):
        return remotion.BundleOutcome(
            path=Path(kwargs["out_dir"]),
            cache_status=status,
            cache_key="k" * 8,
            cache_detail="测试替身",
            cache_seconds=cache_seconds,
            build_seconds=build_seconds,
        )

    return fake_bundle


def _fake_session(*, metadata, ready_seconds: float = 0.01, render_seconds: float = 0.05):
    def fake_session(**kwargs):
        params = kwargs["on_metadata"](metadata)
        assert params is not None
        # 真正渲染会写出成片；收口阶段要按帧数/分辨率验收它
        Path(params["out"]).write_bytes(b"fake video")
        time.sleep(render_seconds)
        return {"readySeconds": ready_seconds, "browsersOpened": 1}

    return fake_session


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """顶掉打包与渲染进程，保留真实的收口、报告与溯源逻辑。"""
    monkeypatch.setattr(remotion, "require_environment", lambda: tmp_path)
    monkeypatch.setattr(render_mod, "_write_provenance", lambda *args, **kwargs: None)

    def install(*, bundle=None, session=None, mux=None, probe=None):
        monkeypatch.setattr(remotion, "bundle", bundle or _fake_bundle())
        metadata = remotion.CompositionMetadata(
            fps=30, width=1080, height=1920, duration_in_frames=90
        )
        monkeypatch.setattr(
            remotion, "render_session", session or _fake_session(metadata=metadata)
        )
        # 替身成片不是真码流：这里只验证计时与流程，真实解码验收由端到端用例覆盖
        monkeypatch.setattr(
            render_mod,
            "_verify_output",
            probe or (lambda *args, **kwargs: time.sleep(0.05)),
        )
        if mux is not None:
            monkeypatch.setattr(render_mod, "mux", mux)
        # 溯源指纹要按规范目录解析作品归属；本文件测的是计时与报告
        monkeypatch.setattr(
            remotion, "build_input_fingerprint", lambda **kwargs: {"files": {}, "digest": "x"}
        )
    return install


def _render(tmp_path, **kwargs):
    storyboard_path = tmp_path / "storyboard.json"
    if not storyboard_path.is_file():
        storyboard_path.write_text(
            json.dumps(
                {
                    "version": 4,
                    "schemaVersion": 4,
                    "fps": 30,
                    "width": 1080,
                    "height": 1920,
                    "stages": [{"id": "s", "durationInFrames": 90, "data": {}}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    options = {
        "output": tmp_path / "out" / "silent.mp4",
        "storyboard": _storyboard(),
        "storyboard_path": storyboard_path,
        "workspace_root": tmp_path,
        "content_root": tmp_path,
    }
    options.update(kwargs)
    return render_mod.render_with_remotion(**options)


def _read_report(output: Path) -> dict:
    return json.loads(perf.report_path_for(output).read_text(encoding="utf-8"))


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
        fps=30,
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


# ---------------------------------------------------------------- 渲染路径


def test_render_writes_report_with_cache_concurrency_and_skipped_mux(tmp_path, pipeline):
    pipeline()
    result = _render(tmp_path)
    assert result.performance_path == perf.report_path_for(result.output)
    report = _read_report(result.output)
    assert report["entry"] == "render"
    assert (report["frames"], report["fps"], report["width"], report["height"]) == (90, 30, 1080, 1920)
    assert report["concurrency"] == 1
    assert report["cache"]["status"] == "miss"
    assert report["cache"]["buildSeconds"] == pytest.approx(0.02)
    # 无声合成：音轨阶段不存在，必须标为跳过而不是 0 秒
    assert report["stages"]["mux"] is None and "mux" in report["skipped"]
    assert report["stages"]["bundle"] == pytest.approx(0.02)
    assert report["stages"]["cache"] == pytest.approx(0.01)
    assert report["stages"]["metadata"] == pytest.approx(0.01)
    assert report["stages"]["render"] > 0
    # 浏览器只开一次，且会话信息留在报告里
    assert report["session"]["browsersOpened"] == 1
    assert result.cache_status == "miss"
    assert result.stages["mux"] is None


def test_cache_hit_marks_bundle_skipped_and_reports_the_status(tmp_path, pipeline):
    pipeline(bundle=_fake_bundle(status="hit", build_seconds=0.0, cache_seconds=0.02))
    result = _render(tmp_path)
    report = _read_report(result.output)
    assert report["cache"]["status"] == "hit"
    assert report["stages"]["bundle"] is None and "bundle" in report["skipped"]
    assert "缓存命中" in result.summary()


def test_disabling_the_cache_is_reported_as_disabled(tmp_path, pipeline):
    pipeline(bundle=_fake_bundle(status="disabled", build_seconds=0.05, cache_seconds=0.0))
    result = _render(tmp_path, bundle_cache=False)
    report = _read_report(result.output)
    assert report["cache"]["status"] == "disabled"
    assert report["stages"]["cache"] is None and "cache" in report["skipped"]
    assert report["stages"]["bundle"] == pytest.approx(0.05)
    assert "禁用打包缓存" in result.summary()


def test_skipping_the_probe_is_recorded_as_skipped(tmp_path, pipeline, monkeypatch):
    pipeline()
    monkeypatch.setattr(render_mod, "_verify_output", lambda *a, **k: None)
    result = _render(tmp_path, probe=False)
    report = _read_report(result.output)
    assert report["stages"]["probe"] is None and "probe" in report["skipped"]


def test_concurrency_is_passed_to_the_session_and_reported(tmp_path, pipeline):
    captured: dict = {}
    metadata = remotion.CompositionMetadata(fps=30, width=1080, height=1920, duration_in_frames=90)

    def session(**kwargs):
        captured.update(kwargs["on_metadata"](metadata))
        Path(captured["out"]).write_bytes(b"fake video")
        return {"readySeconds": 0.0, "browsersOpened": 1}

    pipeline(session=session)
    result = _render(tmp_path, concurrency=4)
    assert captured["concurrency"] == 4
    assert captured["frames"] == "0-89"
    report = _read_report(result.output)
    assert report["concurrency"] == 4
    assert "并发 4" in result.summary()


def test_report_write_failure_does_not_fail_the_render(tmp_path, pipeline, monkeypatch):
    pipeline()

    def broken(*args, **kwargs):
        raise OSError("磁盘满")

    monkeypatch.setattr(perf, "write_report", broken)
    result = _render(tmp_path)
    assert result.output.is_file()
    assert result.performance_path is None


# ---------------------------------------------------------------- 收口阶段


def _timed_finalize(tmp_path, *, media, probe, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    temp = tmp_path / "temp"
    temp.mkdir()
    output = tmp_path / "final.mp4"
    if probe:
        # 真实解码验收由端到端用例覆盖，这里只验证计时发生
        monkeypatch.setattr(render_mod, "_verify_output", lambda *a, **k: time.sleep(0.06))
    timings = perf.StageTimings()
    render_mod._finalize_output(
        video_path=video,
        temp=temp,
        output_path=output,
        total_frames=30,
        fps=30,
        width=1080,
        height=1920,
        media=media,
        probe=probe,
        timings=timings,
    )
    return timings.as_dict()


def test_finalize_times_mux_only_when_there_is_audio(tmp_path, monkeypatch):
    def fake_mux(video, audio, target, duration, start=0.0):
        Path(target).write_bytes(b"muxed")
        time.sleep(0.05)

    monkeypatch.setattr(render_mod, "mux", fake_mux)
    media = SimpleNamespace(
        audio=tmp_path / "voice.wav",
        data={"cues": [{"start": 0.0, "end": 0.5, "text": "测试"}]},
    )
    values = _timed_finalize(tmp_path, media=media, probe=False, monkeypatch=monkeypatch)
    assert values["mux"] is not None and values["mux"] > 0
    assert values["probe"] is None


def test_finalize_times_probe_and_skips_mux_without_media(tmp_path, monkeypatch):
    values = _timed_finalize(tmp_path, media=None, probe=True, monkeypatch=monkeypatch)
    assert values["probe"] is not None and values["probe"] > 0
    assert values["mux"] is None
