"""视觉评审的判定逻辑。

这里覆盖不依赖浏览器的部分：采样点、标注并集比对、帧量测与判定阈值。
浏览器那一半（真的去读 DOM）由 `scripts/review.py` 端到端跑，
它的核心价值是抓住「组件挂上了但标签全空」这类静默缺陷，
因此下面的并集比对用例是这一层的重点。
"""

from __future__ import annotations

from a2v import inspect as review
from a2v.storyboard import Report

W, H = review._PROBE_W, review._PROBE_H


def _gray(rows: dict[int, int], background: int = 200) -> bytes:
    """造一帧灰度图：默认背景值，指定行填另一个值。"""
    data = bytearray([background]) * (W * H)
    for row, value in rows.items():
        for column in range(W):
            data[row * W + column] = value
    return bytes(data)


class TestWindows:
    def test_uses_declared_start_frames(self):
        scenes = [
            {"id": "a", "startFrame": 0, "durationInFrames": 30},
            {"id": "b", "startFrame": 30, "durationInFrames": 60},
        ]
        assert review.scene_windows(scenes) == [("a", 0, 30), ("b", 30, 90)]

    def test_falls_back_to_accumulation(self):
        scenes = [{"id": "a", "durationInFrames": 30}, {"id": "b", "durationInFrames": 60}]
        assert review.scene_windows(scenes) == [("a", 0, 30), ("b", 30, 90)]

    def test_samples_stay_inside_the_scene(self):
        for frame in review.sample_frames(100, 130):
            assert 100 <= frame < 130

    def test_short_scene_still_samples(self):
        frames = review.sample_frames(0, 2)
        assert len(frames) == 3
        assert all(0 <= frame < 2 for frame in frames)


class TestLabelUnion:
    """标注比对必须按整幕取并集。"""

    def test_finds_missing_label(self):
        missing = review.collect_labels({"a": "命运的考试"}, {"一次上场"})
        assert missing == ["a=命运的考试"]

    def test_accepts_label_seen_at_any_moment(self):
        # 翻转牌：before 与 after 写进同一个元素，任何一帧只能看到其中一个
        seen = {"公司在挑你", "你在挑公司"}
        assert review.collect_labels({"before": "公司在挑你", "after": "你在挑公司"}, seen) == []

    def test_ignores_empty_and_non_string_values(self):
        assert review.collect_labels({"a": "", "b": None, "c": 3}, set()) == []

    def test_accepts_label_embedded_in_longer_text(self):
        assert review.collect_labels({"gauge": "准备度"}, {"准备度 62%"}) == []


class TestSceneFields:
    def test_kind_prefers_the_declaration(self):
        scene = {"type": "list", "data": {"figure": {"kind": "gap"}}}
        assert review.declared_kind(scene) == "gap"

    def test_kind_falls_back_to_defaults(self):
        assert review.declared_kind({"type": "list", "data": {}}) == "iceberg"

    def test_unknown_type_has_no_kind(self):
        assert review.declared_kind({"type": "unknown", "data": {}}) == ""

    def test_labels_prefer_figure_over_annotations(self):
        scene = {"data": {"figure": {"labels": {"a": "新"}}, "annotations": {"a": "旧"}}}
        assert review.scene_labels(scene) == {"a": "新"}

    def test_labels_fall_back_to_annotations(self):
        assert review.scene_labels({"data": {"annotations": {"a": "旧"}}}) == {"a": "旧"}


class TestFrameMetrics:
    def test_blank_frame_has_no_ink(self):
        metrics = review.frame_metrics(_gray({}))
        assert metrics["ink"] == 0

    def test_detects_content(self):
        # 中部画一条深色横带，顶部与底部保持背景
        metrics = review.frame_metrics(_gray({row: 20 for row in range(80, 100)}))
        assert metrics["ink"] > 0.05
        assert metrics["band_top"] == 0
        assert metrics["band_bottom"] == 0

    def test_separates_the_top_band(self):
        rows = {row: 20 for row in range(0, 10)}
        assert review.frame_metrics(_gray(rows))["band_top"] > 0

    def test_separates_the_bottom_band(self):
        rows = {row: 20 for row in range(H - 10, H)}
        assert review.frame_metrics(_gray(rows))["band_bottom"] > 0

    def test_subtle_gradient_is_not_ink(self):
        # 背景渐变只有十几级的浮动，不该被算成内容
        data = bytearray()
        for row in range(H):
            data.extend([200 - (row % 12)] * W)
        assert review.frame_metrics(bytes(data))["ink"] == 0


class TestJudgement:
    def test_blank_frame_is_an_error(self):
        report = Report()
        review.judge_frame("x.png", {"ink": 0.0, "band_top": 0.0, "band_bottom": 0.0}, report)
        assert not report.ok
        assert "x.png#画面" in [issue.path for issue in report.issues]

    def test_normal_frame_is_silent(self):
        report = Report()
        review.judge_frame("x.png", {"ink": 0.05, "band_top": 0.001, "band_bottom": 0.0}, report)
        assert report.issues == []

    def test_crowded_safe_area_warns_but_passes(self):
        report = Report()
        review.judge_frame("x.png", {"ink": 0.05, "band_top": 0.2, "band_bottom": 0.3}, report)
        assert report.ok
        assert len(report.warnings) == 2

    def test_missing_label_is_an_error(self):
        probe = review.SceneProbe("s", 10, "gap", "gap", missing_labels=["assumption=假设"])
        report = Report()
        review.judge_scene(probe, {"assumption": "假设"}, report)
        assert not report.ok

    def test_wrong_component_is_an_error(self):
        probe = review.SceneProbe("s", 10, "gap", "iceberg")
        report = Report()
        review.judge_scene(probe, {}, report)
        assert not report.ok

    def test_unmounted_scene_is_an_error(self):
        probe = review.SceneProbe("s", 10, "", "iceberg")
        report = Report()
        review.judge_scene(probe, {}, report)
        assert not report.ok

    def test_silent_component_is_an_error(self):
        probe = review.SceneProbe("s", 10, "gap", "gap", has_any_text=False)
        report = Report()
        review.judge_scene(probe, {}, report)
        assert not report.ok

    def test_clean_scene_passes(self):
        probe = review.SceneProbe("s", 10, "gap", "gap")
        report = Report()
        review.judge_scene(probe, {"assumption": "假设"}, report)
        assert report.ok


def test_report_is_written_for_both_humans_and_tools(tmp_path):
    report = Report()
    report.error("x#C1", "缺少舞台")
    report.warn("y#C3", "用了模糊")
    target = tmp_path / "report.json"
    payload = review.write_report(report, {"frameCount": 18}, target)
    assert target.is_file()
    assert payload["ok"] is False
    assert payload["summary"] == {"errors": 1, "warnings": 1}
    assert payload["frameCount"] == 18
    assert payload["errors"] == ["[error] x#C1: 缺少舞台"]
