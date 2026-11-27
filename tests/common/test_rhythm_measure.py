"""节奏测量：区间并集/交集、逐场分配、字数口径与归因限制。"""
from __future__ import annotations

import subprocess

import pytest
from film_runtime.core.errors import VideoError
from film_runtime.engine import qa_inspection as inspect
from film_runtime.engine import rhythm_measure

# 这项走真实 ffmpeg 抽帧，属 media 层，默认排除。
pytestmark = pytest.mark.media



def scene(scene_id, start, end, *, segments=(), lead_in=0, reading=0, tail=0, transition=0):
    return {
        "id": scene_id, "startFrame": start, "endFrame": end, "transitionFrames": transition,
        "leadInFrames": lead_in, "readingHoldFrames": reading, "tailFrames": tail,
        "narrationSegments": [{"id": key, "text": text} for key, text, _, _ in segments],
        "segmentWindows": {key: {"startFrame": a, "endFrame": b} for key, _, a, b in segments},
    }


def prepared(*scenes, fps=60):
    return {"fps": fps, "props": {"compiledScenes": list(scenes)}}


def audio(*silences, duration=20.0):
    return {"status": "measured", "durationSeconds": duration,
            "candidates": [{"startSeconds": a, "endSeconds": b, "reason": "silence"}
                           for a, b in silences] + [{"startSeconds": 0, "endSeconds": 0.1,
                                                      "reason": "clipping-candidate"}]}


def test_interval_merge_clip_and_intersection_are_half_open():
    assert rhythm_measure.merge([(0, 1), (0.5, 2), (3, 4)]) == [(0, 2), (3, 4)]
    assert rhythm_measure.merge([(0, 1), (1, 2)]) == [(0, 2)]
    assert rhythm_measure.clip([(-1, 1), (2, 5), (4, 4)], 3) == [(0, 1), (2, 3)]
    assert rhythm_measure.intersect_seconds([(0, 5)], [(2, 3), (3, 4)]) == 2


def test_whole_film_union_and_per_scene_intersection_do_not_double_count():
    data = prepared(
        scene("s1", 0, 600, segments=[("a", "甲乙", 0, 120)], reading=60, tail=120),
        scene("s2", 600, 1200, segments=[("b", "丙丁戊", 660, 780)], lead_in=60, reading=60, tail=120),
    )
    report = rhythm_measure.build(data, audio((1.5, 2.5), (2.0, 2.2), (9.5, 10.5), (19.0, 21.0)))

    assert report["status"] == "measured"
    summary = report["summary"]
    assert summary["silenceCandidates"] == 4
    assert summary["silenceMerged"] == 3
    # 重叠候选先合并，跨场与片尾区间按有效音轨范围裁切。
    assert summary["silenceSeconds"] == pytest.approx(3.0)
    assert summary["silenceRatio"] == pytest.approx(0.15)
    # 逐场按交集分配：0.5+1.0 与 0.5+1.0，合计仍等于全片并集。
    assert [row["silenceSeconds"] for row in report["scenes"]] == pytest.approx([1.5, 1.5])
    assert report["scenes"][0]["startSeconds"] == 0 and report["scenes"][1]["endSeconds"] == 20


def test_characters_reuse_punctuation_whitespace_rule_and_cps_includes_window_pauses():
    data = prepared(scene("s", 0, 240, segments=[("a", "观察结果，修正做法。", 0, 120)]))
    report = rhythm_measure.build(data, audio((0.5, 1.0), duration=4))

    summary = report["summary"]
    assert summary["characters"] == 8
    assert summary["narrationSeconds"] == pytest.approx(2.0)
    # 平均字速按旁白窗口并集，窗口内停顿不额外扣除；与字幕阅读上限互不参与。
    assert summary["charactersPerSecond"] == pytest.approx(4.0)
    assert "limit" not in str(summary).lower()


def test_rhythm_cps_is_independent_of_subtitle_reading_cap():
    """窗口字速可以高于 9 字/秒：节奏测量不是字幕阅读上限，也不产生失败状态。"""
    data = prepared(scene("s", 0, 60, segments=[("a", "观察结果，修正做法。", 0, 30)]))
    report = rhythm_measure.build(data, audio(duration=1))

    assert report["summary"]["charactersPerSecond"] == pytest.approx(16.0)
    assert report["status"] == "measured"
    assert "fail" not in report


def test_silence_inside_narration_window_is_position_not_punctuation_cause():
    data = prepared(scene("s", 0, 240, segments=[("a", "甲乙丙丁", 0, 120)], reading=60, tail=60))
    report = rhythm_measure.build(data, audio((0.5, 0.8), (2.0, 2.5), duration=4))

    summary = report["summary"]
    assert summary["narrationSilenceSeconds"] == pytest.approx(0.3)
    assert summary["declaredSilenceSeconds"] == pytest.approx(0.5)
    assert summary["unknownSilenceSeconds"] == pytest.approx(0)
    assert any("不声称由标点造成" in item for item in report["limitations"])


def test_declared_holds_are_reported_separately_and_unknown_remainder_is_kept():
    data = prepared(scene("s", 0, 1200,
                          segments=[("a", "甲乙", 60, 180), ("b", "丙丁", 300, 420)],
                          lead_in=60, reading=120, tail=180))
    report = rhythm_measure.build(data, audio((1.2, 1.6), (2.0, 2.6), (9.5, 11.5), duration=20))

    holds = report["summary"]["declaredHoldSeconds"]
    assert holds == {"leadIn": pytest.approx(1.0), "segmentHold": pytest.approx(2.0),
                     "readingHold": pytest.approx(2.0), "tail": pytest.approx(3.0),
                     "total": pytest.approx(8.0)}
    # 9.5–11.5 秒静音不在旁白窗口或声明留白内，必须保留为未知归因。
    assert report["summary"]["unknownSilenceSeconds"] == pytest.approx(2.0)
    assert report["intervals"][-1]["unknownSeconds"] == pytest.approx(2.0)
    assert report["intervals"][-1]["declaredHolds"] == []


def test_overlapping_scene_silence_is_assigned_once():
    """淡化重叠时边界静音只归后一幕，逐场合计等于全片并集。"""
    data = prepared(
        scene("s1", 0, 600, segments=[("a", "甲", 0, 60)]),
        scene("s2", 540, 1200, segments=[("b", "乙", 600, 660)]),
    )
    report = rhythm_measure.build(data, audio((550 / 60, 560 / 60), duration=20))

    assert report["summary"]["silenceSeconds"] == pytest.approx(10 / 60, abs=1e-5)
    assert report["scenes"][0]["silenceSeconds"] == pytest.approx(0)
    assert report["scenes"][1]["silenceSeconds"] == pytest.approx(10 / 60, abs=1e-5)
    assert sum(row["silenceSeconds"] for row in report["scenes"]) == pytest.approx(
        report["summary"]["silenceSeconds"], abs=1e-5)


def test_missing_reading_hold_uses_contract_default_for_declaration():
    data = prepared(scene("s", 0, 240, segments=[("a", "甲", 0, 60)]))
    del data["props"]["compiledScenes"][0]["readingHoldFrames"]
    report = rhythm_measure.build(data, audio(duration=4))
    assert report["summary"]["storyboardHoldSeconds"]["readingHold"] == pytest.approx(0.4)
    assert report["summary"]["declaredHoldSeconds"]["readingHold"] == pytest.approx(0.4)


def test_truncated_audio_marks_cps_not_applicable():
    data = prepared(scene("s", 0, 240, segments=[("a", "甲乙", 0, 120)]))
    report = rhythm_measure.build(data, audio(duration=1.5))

    assert report["summary"]["truncated"] is True
    assert report["summary"]["charactersPerSecond"] is None
    assert "短于旁白窗口" in report["summary"]["charactersPerSecondReason"]
    assert report["scenes"][0]["truncated"] is True
    assert report["scenes"][0]["charactersPerSecond"] is None


def test_no_narration_marks_cps_not_applicable_but_still_reports_silence():
    data = prepared(scene("s", 0, 600, tail=120))
    report = rhythm_measure.build(data, audio((8.0, 9.0), duration=10))

    assert report["status"] == "measured"
    assert report["summary"]["characters"] == 0
    assert report["summary"]["charactersPerSecond"] is None
    assert "没有旁白窗口" in report["summary"]["charactersPerSecondReason"]
    assert report["summary"]["silenceSeconds"] == pytest.approx(1.0)
    assert report["scenes"][0]["charactersPerSecond"] is None


def test_zero_duration_and_missing_timeline_are_explicitly_not_applicable():
    data = prepared(scene("s", 0, 60))
    assert rhythm_measure.build(data, audio(duration=0))["status"] == "not-applicable"
    assert rhythm_measure.build({"fps": 60, "props": {}}, audio((1, 2)))["status"] == "not-applicable"
    assert rhythm_measure.build(data, {"status": "not-applicable"})["status"] == "not-applicable"


def test_narration_without_window_is_explicitly_not_applicable():
    data = prepared(scene("s", 0, 240, segments=[("a", "甲乙", 0, 120)]))
    del data["props"]["compiledScenes"][0]["segmentWindows"]["a"]
    assert rhythm_measure.build(data, audio(duration=4))["status"] == "not-applicable"


def test_measurement_is_pure_and_never_decodes_audio_again(monkeypatch):
    data = prepared(scene("s", 0, 240, segments=[("a", "甲乙", 0, 120)]), )

    def refuse(*_args, **_kwargs):
        raise AssertionError("节奏测量不应再次解码音轨")

    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)
    report = rhythm_measure.build(data, audio((1.0, 2.0), duration=4))
    assert report["status"] == "measured" and report["summary"]["silenceSeconds"] == pytest.approx(1.0)


def test_audio_detection_failure_is_not_reported_as_zero_silence(tmp_path):
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"broken")
    with pytest.raises(VideoError, match="缺少音轨"):
        inspect.audio_signals(broken, prepared(), required=True)


def test_inspection_embeds_rhythm_and_keeps_technical_scope(tmp_path):
    from test_qa_inspection import clip

    video = clip(tmp_path / "clip.mp4", silent=True)
    data = prepared(scene("s", 0, 120, segments=[("a", "甲乙", 30, 90)]))
    data["durationInFrames"] = 120
    data["preparedFingerprint"] = "x" * 8
    data["props"]["subtitle"] = {"textColor": "#ffffff", "plateColor": "#0b0d12"}
    result = inspect.inspect(video, data, tmp_path / "qa", audio_required=True)

    assert result["rhythm"]["kind"] == "measurement"
    assert result["rhythm"]["status"] == "measured"
    assert result["rhythm"]["summary"]["silenceMerged"] >= 1
    assert result["observation"] == "not-evaluated"
