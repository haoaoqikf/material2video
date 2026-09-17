"""视觉评审的判定逻辑。

这里覆盖不依赖浏览器的部分：采样点、标注并集比对、帧量测与判定阈值。
浏览器那一半（真的去读 DOM）由 `scripts/review.py` 端到端跑，
它的核心价值是抓住「组件挂上了但标签全空」这类静默缺陷，
因此下面的并集比对用例是这一层的重点。
"""

from __future__ import annotations

from a2v import inspect as review
from a2v import keynote
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
        # 中部画一条深色横带，顶部与底部保持背景。
        # 带宽按量测分辨率折算，避免把「测试用的行数」当成契约。
        band = range(H // 2 - H // 10, H // 2 + H // 10)
        metrics = review.frame_metrics(_gray({row: 20 for row in band}))
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


class TestKeynoteMetrics:
    """观感闸门的量测口径：与「不是废片」的墨迹量测分开验证。"""

    def _rgb(self, accent_pixels: int = 0, size: int = 100) -> bytes:
        """构造一张纯背景图，并在开头写入指定数量的强调色像素。"""
        data = bytearray()
        for index in range(size):
            if index < accent_pixels:
                data.extend([50, 214, 255])
            else:
                data.extend([8, 9, 12])
        return bytes(data)

    def test_empty_ratio_counts_background(self):
        assert keynote.rgb_metrics(self._rgb())["empty"] == 1.0

    def test_accent_ratio_is_measured(self):
        assert keynote.accent_metrics(self._rgb(accent_pixels=10), (50, 214, 255))["accent"] == 0.1

    def test_accent_tolerance_accepts_blended_pixels(self):
        # 抗锯齿叠加后的强调色比纯色暗一截（约八成亮度），仍应被算作强调色
        data = bytearray()
        for index in range(100):
            data.extend([34, 186, 224] if index < 10 else [8, 9, 12])
        assert keynote.accent_metrics(bytes(data), (50, 214, 255))["accent"] == 0.1

    def test_accent_rejects_unrelated_colors(self):
        # 红与青在任一通道上都差得很远，不该被算成强调色
        data = bytearray()
        for index in range(100):
            data.extend([220, 60, 60] if index < 10 else [8, 9, 12])
        assert keynote.accent_metrics(bytes(data), (50, 214, 255))["accent"] == 0.0

    def test_contrast_ratio_matches_wcag_reference(self):
        # 白 / 黑 = 21:1，是 WCAG 的已知端点
        assert round(keynote.contrast_ratio((255, 255, 255), (0, 0, 0)), 1) == 21.0

    def test_parse_color_accepts_hex_and_rgb(self):
        assert keynote.parse_color("#32d6ff") == (50, 214, 255)
        assert keynote.parse_color("rgb(50, 214, 255)") == (50, 214, 255)
        assert keynote.parse_color("transparent") is None


class TestKeynoteGates:
    def test_whitespace_fails_below_budget(self):
        gate = keynote.gate_whitespace("s", "list", 0.12)
        assert gate.status == "fail"
        assert gate.value == 0.12

    def test_whitespace_passes_for_hero_scene(self):
        assert keynote.gate_whitespace("s", "title", 0.62).status == "pass"

    def test_accent_flags_both_extremes(self):
        # 用滥是硬错误：画面失去唯一焦点
        assert keynote.gate_accent("s", 0.4).status == "fail"
        assert keynote.gate_accent("s", 0.06).status == "pass"
        # 偏少只提醒：单个强调元素本来就只有千分之几
        assert keynote.gate_accent("s", 0.0015).status == "warn"
        assert keynote.gate_accent("s", 0.0).status == "warn"
        assert keynote.gate_accent("s", 0.2).status == "warn"

    def test_type_sizes_ignores_small_labels(self):
        # 图形标注与角标是小字，不该把图形画面判成层级失控
        gate = keynote.gate_type_sizes("s", [28, 30, 32, 36, 96, 140])
        assert gate.status == "pass"
        assert gate.value == [96.0, 140.0]

    def test_type_sizes_fails_when_too_many_levels(self):
        assert keynote.gate_type_sizes("s", [44, 52, 60, 70, 80, 90]).status == "fail"

    def test_alignment_accepts_centered_layout(self):
        texts = [
            {"fontSize": 96, "left": 400, "center": 540},
            {"fontSize": 60, "left": 460, "center": 540},
        ]
        assert keynote.gate_alignment("s", texts, center=540).status == "pass"

    def test_alignment_accepts_center_plus_left_column(self):
        # 居中标题 + 一条左对齐注释是常见的合法组合
        texts = [
            {"fontSize": 96, "left": 400, "center": 540},
            {"fontSize": 60, "left": 96, "center": 300},
        ]
        assert keynote.gate_alignment("s", texts, center=540).status == "pass"

    def test_alignment_fails_on_scattered_blocks(self):
        texts = [
            {"fontSize": 96, "left": 96, "center": 300},
            {"fontSize": 60, "left": 400, "center": 700},
            {"fontSize": 60, "left": 700, "center": 900},
            {"fontSize": 60, "left": 200, "center": 500},
        ]
        gate = keynote.gate_alignment("s", texts, center=540)
        assert gate.status == "fail"
        assert "对齐线" in gate.detail

    def test_alignment_ignores_small_labels(self):
        # 幕角标与图形标注字号小，不参与对齐判定
        texts = [{"fontSize": 28, "left": 96, "center": 143}]
        assert keynote.gate_alignment("s", texts, center=540).status == "skipped"

    def test_alignment_skips_without_enough_blocks(self):
        assert keynote.gate_alignment("s", [], center=540).status == "skipped"

    def test_contrast_reports_skipped_without_colors(self):
        assert keynote.gate_contrast("s", [{"color": "transparent"}]).status == "skipped"

    def test_contrast_skips_gradient_text(self):
        # 渐变裁切的标题前景色是透明的，不能当成「对比度 1.0」
        gate = keynote.gate_contrast(
            "s",
            [{"color": "rgba(0, 0, 0, 0)", "gradient": True, "fontSize": 124}],
        )
        assert gate.status == "skipped"

    def test_contrast_falls_back_to_page_background(self):
        gate = keynote.gate_contrast(
            "s",
            [{"color": "rgba(255, 255, 255, 0.72)", "background": "rgba(0, 0, 0, 0)", "fontSize": 40}],
            page_background=(8, 9, 12),
        )
        assert gate.status == "pass"
        assert gate.value > 7

    def test_contrast_fails_on_low_ratio(self):
        gate = keynote.gate_contrast(
            "s",
            [{"color": "rgba(255,255,255,0.10)", "background": "rgb(8,9,12)", "fontSize": 40}],
        )
        assert gate.status == "fail"

    def test_card_discipline_flags_flat_blocks(self):
        # 单个表面缺特征算提醒，多个才判失败
        assert keynote.gate_card_discipline("s", [{"traits": ["radius"]}]).status == "warn"
        assert (
            keynote.gate_card_discipline("s", [{"traits": ["radius"]}, {"traits": ["radius", "border"]}]).status
            == "fail"
        )
        assert (
            keynote.gate_card_discipline("s", [{"traits": ["radius", "border", "shadow"]}]).status == "pass"
        )

    def test_result_aggregates_by_gate_and_scene(self):
        result = keynote.KeynoteResult()
        result.render("s1", 10, [keynote.gate_accent("s1", 0.06)])
        result.render("s1", 20, [keynote.gate_accent("s1", 0.4)])
        assert len(result.gates) == 1
        assert result.gates[0].status == "fail"
        assert result.gates[0].value == 0.4
        assert len(result.frames) == 2
        assert result.summary()["fail"] == 1

    def test_result_takes_the_worst_status_per_scene(self):
        # 同一幕逐帧采样：取最严重的一条，避免把同一问题按帧重复计数
        result = keynote.KeynoteResult()
        result.render("s1", 10, [keynote.gate_accent("s1", 0.06)])
        result.render("s1", 20, [keynote.gate_accent("s1", 0.001)])
        assert result.gates[0].status == "warn"
        assert result.summary()["pass"] == 0


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
