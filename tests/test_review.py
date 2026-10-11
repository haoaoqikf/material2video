"""视觉评审的判定逻辑。

这里覆盖不依赖浏览器的部分：采样点、标注并集比对、帧量测与判定阈值。
浏览器那一半（真的去读 DOM）由 `scripts/review.py` 端到端跑，
它的核心价值是抓住「组件挂上了但标签全空」这类静默缺陷，
因此下面的并集比对用例是这一层的重点。
"""

from __future__ import annotations

import m2v.types.article.cli as cli
import m2v.types.article.inspect as review
import m2v.types.article.keynote as keynote
from m2v.types.article.storyboard import Report

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
    def test_scene_tree_is_the_declared_renderer(self):
        assert review.declared_kind({"sceneTree": {"id": "root", "type": "stack"}}) == "scene-tree"

    def test_unknown_type_has_no_kind(self):
        assert review.declared_kind({"type": "unknown", "data": {}}) == ""

    def test_labels_follow_scene_tree_content_refs(self):
        scene = {"data": {"text": "甲"}, "sceneTree": {"id": "root", "type": "stack", "children": [{"id": "copy", "type": "text", "contentRef": "data.text"}]}}
        assert review.scene_labels(scene) == {"copy": "甲"}


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

    def _rgb_of(self, color: tuple[int, int, int], hits: int = 10) -> bytes:
        data = bytearray()
        for index in range(100):
            data.extend(color if index < hits else (8, 9, 12))
        return bytes(data)

    def test_accent_family_members_are_all_visible(self):
        """设计系统登记的四个强调色成员都必须量得到。

        原先的判据是「与纯强调色逐通道相差 ≤ 46」的色盒，它只认最亮的那一个；
        另外三个成员（着重色、描边色、焦点面的填充）全被判成「没有强调色」，
        于是「用强调色着重色画的焦点」在闸门里等于不存在。
        """
        members = {
            "纯强调色 #32d6ff": (50, 214, 255),
            "着重色 #2f7fa8": (47, 127, 168),
            "焦点面填充 #16465f": (22, 70, 95),
            "描边色合成(alpha 0.55)": (32, 122, 146),
        }
        for name, color in members.items():
            share = keynote.accent_metrics(self._rgb_of(color), (50, 214, 255))["accent"]
            assert share == 0.1, f"{name} 应当被算作强调色，实际 {share}"

    def test_accent_family_excludes_neutral_surfaces_and_background(self):
        """反向断言：中性面与背景不能被算进族里，否则闸门等于失效。

        背景是一层青绿光晕，色相与强调色很近，所以判据必须有**色度下限**：
        这几位的色度只有 4–32，离中性轴太近，读者不会读成"焦点"。
        """
        neutrals = {
            "背景梯度": (11, 12, 15),
            "背景暗端": (8, 9, 12),
            "中性表面 --fig-surface": (23, 30, 43),
            "14% 染色 --m2v-accent-soft": (15, 39, 47),
            "白字": (244, 247, 251),
        }
        for name, color in neutrals.items():
            share = keynote.accent_metrics(self._rgb_of(color), (50, 214, 255))["accent"]
            assert share == 0.0, f"{name} 不该被算作强调色，实际 {share}"

    def test_pure_share_is_reported_alongside_the_family(self):
        """诊断值：能分辨焦点是用纯强调色画的，还是用族里的暗档画的。"""
        family = keynote.accent_metrics(self._rgb_of((22, 70, 95)), (50, 214, 255))
        assert family["accent"] == 0.1, "暗档属于族"
        assert family["accent_pure"] == 0.0, "但它不是纯色"

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


SAFE = {"left": 96.0, "right": 984.0, "top": 240.0, "bottom": 1600.0}


def _block(role, left, right, top, bottom):
    return {
        "role": role,
        "block": role,
        "left": left,
        "right": right,
        "top": top,
        "bottom": bottom,
    }


class TestOverflowGate:
    """K7 是硬判定：文字被裁掉或压出安全区不是审美问题，是画面坏了。"""

    def test_passes_when_everything_is_inside(self):
        gate = keynote.gate_overflow("s", [_block("title-text", 200, 800, 400, 700)], SAFE)
        assert gate.status == "pass"
        assert gate.value == 0

    def test_tolerates_subpixel_and_entrance_offsets(self):
        # 入场动画会把文字整体位移，7px 的越界不该报错
        gate = keynote.gate_overflow("s", [_block("t", 96 - 7, 984 + 7, 240 - 7, 1600 + 7)], SAFE)
        assert gate.status == "pass"

    def test_fails_and_names_the_direction(self):
        gate = keynote.gate_overflow("s", [_block("title-text", 200, 800, 100, 700)], SAFE)
        assert gate.status == "fail"
        assert "上越界" in gate.detail
        assert "title-text" in gate.detail
        # 实测像素值必须写出来，否则人无法据此改分镜
        assert "140.0px" in gate.detail
        assert "硬判定" in gate.detail

    def test_merges_text_nodes_of_the_same_block(self):
        # 一段话会被拆成多个文本节点（强调词、逐字揭示），只该报一条
        texts = [
            _block("quote-text", 200, 800, 100, 700),
            _block("quote-text", 210, 810, 105, 705),
            _block("quote-text", 220, 820, 110, 710),
        ]
        gate = keynote.gate_overflow("s", texts, SAFE)
        assert gate.status == "fail"
        assert gate.value == 1
        assert gate.detail.count("quote-text") == 1
        # 取该方向上最大的越界量，而不是最后一条
        assert "140.0px" in gate.detail

    def test_reports_both_directions_of_one_block(self):
        gate = keynote.gate_overflow("s", [_block("t", 20, 1100, 400, 700)], SAFE)
        assert "左越界" in gate.detail and "右越界" in gate.detail

    def test_fails_when_the_engine_cannot_fit_the_copy(self):
        # 缩到正文下限仍放不下：比像素越界更早的预警，同样要报，并要求拆场景
        gate = keynote.gate_overflow(
            "s",
            [_block("quote-text", 200, 800, 400, 700)],
            SAFE,
            no_fit=[{"id": "copy-17", "role": "quote-text", "text": "一段怎么缩都放不下的长文案"}],
        )
        assert gate.status == "fail"
        assert "拆场景" in gate.detail
        assert "copy-17" in gate.detail

    def test_skips_without_safe_geometry(self):
        assert keynote.gate_overflow("s", [], None).status == "skipped"

    def test_the_gate_is_wired_into_the_frame_verdict(self):
        # 接上闸门与「写了一个没人调用的函数」是两回事：这里从帧结论入口验一次
        gates = review.keynote_gate(
            "frame-0001",
            "opening",
            "title",
            b"\x00" * (review._PROBE_W * review._PROBE_H * 3),
            {
                "sizes": [120.0],
                "texts": [_block("title-text", 200, 800, 100, 700)],
                "cards": [],
                "noFit": [],
                "safe": SAFE,
                "background": "#08090c",
            },
            (50, 214, 255),
        )
        ids = [gate.id for gate in gates]
        assert "K7" in ids
        overflow = next(gate for gate in gates if gate.id == "K7")
        assert overflow.status == "fail"


class TestHardGateReachesTheVerdict:
    """硬判定必须影响错误数与退出码。

    「打印一条失败」而结论仍是 0 个错误，等于把硬判定降级成了建议：
    流水线只看退出码，看不到那行字。
    """

    def _keynote(self, status: str, gate_id: str = "K7"):
        return {
            "gates": [
                {"id": gate_id, "title": "文字溢出", "status": status, "scene": "opening",
                 "detail": "硬判定：越出安全区：「title-text」上越界 285.2px"}
            ]
        }

    def test_overflow_failure_becomes_an_error(self):
        report = Report()
        cli._apply_hard_gates(report, self._keynote("fail"))
        assert len(report.errors) == 1
        assert not report.ok
        message = report.errors[0].message
        assert "文字溢出" in message and "上越界 285.2px" in message

    def test_passing_hard_gate_adds_nothing(self):
        report = Report()
        cli._apply_hard_gates(report, self._keynote("pass"))
        assert report.ok and not report.issues

    def test_soft_gates_still_do_not_block(self):
        # K2「强调色偏少」这类只提示：它不该让体检失败
        report = Report()
        cli._apply_hard_gates(report, self._keynote("fail", gate_id="K2"))
        assert report.ok and not report.issues

    def test_missing_keynote_section_is_tolerated(self):
        report = Report()
        cli._apply_hard_gates(report, {})
        assert report.ok


class TestDeterminismAcceptance:
    """任务 6.4：同帧重复截图 + 随机寻帧验收进入评审结论。"""

    def _png(self, tmp_path, name: str, value: int) -> bytes:
        """用 ffmpeg 编码一张纯色灰度 PNG（逐像素可比较的真实图像）。"""
        import subprocess

        from imageio_ffmpeg import get_ffmpeg_exe

        target = tmp_path / name
        raw = bytes([value]) * (64 * 64)
        completed = subprocess.run(
            [
                get_ffmpeg_exe(), "-v", "error", "-y",
                "-f", "rawvideo", "-pix_fmt", "gray", "-s", "64x64",
                "-i", "pipe:0", "-frames:v", "1", str(target),
            ],
            input=raw, capture_output=True,
        )
        assert completed.returncode == 0, completed.stderr
        return target.read_bytes()

    class _FlakyPage:
        """同帧两次求值给出不同画面的页面：非确定性失败夹具。"""

        def __init__(self, images):
            self._images = images
            self._calls = 0

        def evaluate(self, *args, **kwargs):
            return None

        def seek(self, frame):
            pass

        def capture(self, image_format="jpeg", quality=98):
            image = self._images[self._calls % len(self._images)]
            self._calls += 1
            return image

    def _scenes(self):
        return [{"id": "s0", "durationInFrames": 30, "startFrame": 0}]

    def test_画面漂移被判定为失败(self, tmp_path):
        import m2v.core.determinism as determinism_mod

        dark = self._png(tmp_path, "dark.png", 20)
        light = self._png(tmp_path, "light.png", 220)
        page = self._FlakyPage([dark, light])
        verdicts = cli._determinism_acceptance(page, self._scenes())
        assert verdicts, "验收没有产生任何判定"
        assert any(not verdict.ok for verdict in verdicts)
        assert any(verdict.psnr < determinism_mod.DEFAULT_PSNR_DB for verdict in verdicts)

    def test_稳定页面通过验收(self, tmp_path):
        stable = self._png(tmp_path, "stable.png", 90)
        page = self._FlakyPage([stable, stable])
        verdicts = cli._determinism_acceptance(page, self._scenes())
        assert verdicts and all(verdict.ok for verdict in verdicts)

    def test_失败结论进入错误并影响退出码(self):
        from m2v.core.determinism import FrameVerdict

        report = Report()
        verdicts = [FrameVerdict(frame=29, psnr=18.4, threshold=60.0)]
        payload = cli._apply_determinism_verdicts(report, verdicts)
        assert len(report.errors) == 1
        assert not report.ok
        assert "第 29 帧" in report.errors[0].message and "PSNR" in report.errors[0].message.replace("dB", "PSNR") or "18.4" in report.errors[0].message
        assert payload == [verdicts[0].describe()]

    def test_未开启验收时不写字段也不报错(self):
        report = Report()
        assert cli._apply_determinism_verdicts(report, None) is None
        assert report.ok


class TestDeterminismEndToEnd:
    """任务 6.4 端到端：真实作品上跑 `review.py --check-determinism`。

    入口只接受分镜 v4，仓库内的旧示例不再能被体检；这里用 ``valid_script_v4``
    （tree renderer）在 tmp_path 搭一个内容根作品，驱动同一条检查。用例依赖
    浏览器：没有可用的 Chromium 时按 ``conftest.chromium_ready`` 的约定跳过。
    """

    def test_review_with_determinism_check_passes_on_example(
        self, tmp_path, valid_script_v4, chromium_ready
    ):
        import json

        # 分镜放在仓库外的内容根里：归属靠 --content-root，共享契约页仍在仓库中
        content = tmp_path / "content"
        article = content / "videos" / "demo"
        article.mkdir(parents=True)
        (article / "index.html").write_text("<!doctype html><html></html>", encoding="utf-8")
        storyboard = article / "storyboard.json"
        storyboard.write_text(json.dumps(valid_script_v4, ensure_ascii=False), encoding="utf-8")
        argv = [
            "--storyboard", str(storyboard),
            "--content-root", str(content),
            "--out-dir", str(tmp_path / "inspect"),
            "--check-determinism",
        ]
        cli.main_review(argv)
        payload = json.loads((tmp_path / "inspect" / "report.json").read_text(encoding="utf-8"))
        # 确定性验收在真实作品上跑过并全部通过：三个阶段各取收尾帧
        assert payload.get("determinism"), "report.json 应记录确定性验收结论"
        assert len(payload["determinism"]) == 3
        assert all("通过" in line and "未通过" not in line for line in payload["determinism"])
        # 确定性层面零错误（画面本身的墨迹提示与确定性无关）
        assert not any(error.startswith("确定性") for error in payload["errors"])


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
