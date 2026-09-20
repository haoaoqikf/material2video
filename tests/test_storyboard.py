"""分镜脚本校验与时间换算的单元测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2v import storyboard as sb


def error_paths(report: sb.Report) -> list[str]:
    return [issue.path for issue in report.errors]


def warning_paths(report: sb.Report) -> list[str]:
    return [issue.path for issue in report.warnings]


class TestDeclarativeValidation:
    def test_optional_visual_fields_keep_legacy_valid(self, valid_script):
        assert sb.validate(valid_script).ok
        assert sb.validate(valid_script, declarative=True).ok
        valid_script["visual"] = {"theme": "light"}
        valid_script["scenes"][0]["visual"] = {"layout": "lower"}
        assert sb.validate(valid_script, declarative=True).ok

    def test_visual_errors_have_field_paths(self, valid_script):
        valid_script["visual"] = {"theme": "neon"}
        valid_script["scenes"][0]["visual"] = {"layout": "floating"}
        assert {"visual.theme", "scenes[0].visual.layout"} <= set(
            error_paths(sb.validate(valid_script, declarative=True))
        )

    def test_kicker_is_accepted_on_a_scene(self, valid_script):
        valid_script["scenes"][0]["visual"] = {"layout": "center", "kicker": "问题"}
        assert sb.validate(valid_script, declarative=True).ok

    def test_kicker_is_rejected_at_the_top_level(self, valid_script):
        """角标是**幕**的定位词，顶层 visual 描述整片（主题、预设）。

        顶层没有"第几幕"可言，所以那里不该有角标。
        """
        valid_script["visual"] = {"theme": "dark", "kicker": "问题"}
        assert "visual.kicker" in error_paths(sb.validate(valid_script, declarative=True))

    @pytest.mark.parametrize("value", ["", "   ", "两\n行", 5, "这是一个很长的角标句子不该出现在画面上"])
    def test_kicker_must_be_a_short_single_line_word(self, valid_script, value):
        """角标是读者第一眼看到的定位词：一个词、单行、非空。

        它原先直接取 `scene.type`，所以这条校验顺带挡住了"把类型名当文案"，
        也挡住了"把一句话塞进角标"——要说得更多请放进 title 或 subtitle。
        """
        valid_script["scenes"][0]["visual"] = {"kicker": value}
        assert "scenes[0].visual.kicker" in error_paths(sb.validate(valid_script, declarative=True))

    def test_kicker_equal_to_the_scene_type_is_rejected(self, valid_script):
        """用类型名当角标就是被修掉的那个缺陷本身，所以它是错误而不是提醒。"""
        scene_type = valid_script["scenes"][0]["type"]
        valid_script["scenes"][0]["visual"] = {"kicker": scene_type.upper()}
        errors = sb.validate(valid_script, declarative=True)
        assert "scenes[0].visual.kicker" in error_paths(errors)
        assert any("schema 字段" in issue.message for issue in errors.issues)

    def test_every_example_scene_authors_its_own_kicker(self):
        """示例分镜的每一幕都自己写了角标，且没有一个角标就是它的类型名。

        角标是给读者看的文案，不是 schema 字段的回显——`TITLE`、`LIST`、
        `TIMELINE` 这类内部类型名出现在画面上就是这个缺陷本身。
        """
        from conftest import EXAMPLES_DIR

        data = json.loads(
            (EXAMPLES_DIR.parent / "keynote-baseline" / "storyboard.json").read_text(encoding="utf-8")
        )
        assert len(data["scenes"]) >= 8
        for scene in data["scenes"]:
            kicker = (scene.get("visual") or {}).get("kicker")
            assert kicker, f"{scene['id']} 缺 visual.kicker"
            assert kicker.strip(), f"{scene['id']} 的角标是空白"
            assert len(kicker) <= 8, f"{scene['id']} 的角标太长：{kicker}"
            assert kicker.lower() != scene["type"], (
                f"{scene['id']} 的角标就是它的类型名 {scene['type']!r}——"
                "那是 schema 字段，不是文案"
            )
        kickers = [(scene.get("visual") or {}).get("kicker") for scene in data["scenes"]]
        assert len(set(kickers)) == len(kickers), f"角标重复：{kickers}"

    @pytest.mark.parametrize("key,value,path", [
        ("figure", {"kind": "not-registered"}, "scenes[0].data.figure.kind"),
        ("figure", {"kind": "balance", "params": {"size": 4}}, "scenes[0].data.figure.params"),
        ("figure", {"kind": "balance", "motion": "spin"}, "scenes[0].data.figure.motion"),
        ("html", "<script>alert(1)</script>", "scenes[0].data.html"),
        ("package", "gsap", "scenes[0].data.package"),
    ])
    def test_rejects_uncontrolled_fields(self, valid_script, key, value, path):
        valid_script["scenes"][0]["data"][key] = value
        assert path in error_paths(sb.validate(valid_script, declarative=True))


class TestStructuralValidation:
    def test_accepts_valid_script(self, valid_script):
        report = sb.validate(valid_script)
        assert report.ok, report.issues
        assert report.errors == []

    def test_rejects_non_object_root(self):
        report = sb.validate(["not", "an", "object"])
        assert error_paths(report) == ["$"]

    def test_requires_supported_version(self, valid_script):
        valid_script["version"] = 99
        report = sb.validate(valid_script)
        assert "version" in error_paths(report)

    def test_rejects_missing_version(self, valid_script):
        del valid_script["version"]
        assert "version" in error_paths(sb.validate(valid_script))

    def test_rejects_non_integer_fps(self, valid_script):
        valid_script["fps"] = 30.5
        assert "fps" in error_paths(sb.validate(valid_script))

    def test_rejects_out_of_range_fps(self, valid_script):
        valid_script["fps"] = 0
        assert "fps" in error_paths(sb.validate(valid_script))

    def test_warns_uncommon_fps(self, valid_script):
        valid_script["fps"] = 29
        report = sb.validate(valid_script)
        assert report.ok
        assert "fps" in warning_paths(report)

    @pytest.mark.parametrize("key", ["width", "height"])
    def test_rejects_odd_dimension(self, valid_script, key):
        # H.264 yuv420p 要求宽高为偶数，奇数必须在开渲前拦下
        valid_script[key] = 1081
        assert key in error_paths(sb.validate(valid_script))

    def test_rejects_empty_scenes(self, valid_script):
        valid_script["scenes"] = []
        assert "scenes" in error_paths(sb.validate(valid_script))

    def test_warns_landscape_orientation(self, valid_script):
        valid_script["width"] = 1920
        valid_script["height"] = 1080
        assert "width" in warning_paths(sb.validate(valid_script))

    @pytest.mark.parametrize("value", ["1080", None, [], {}, True])
    def test_rejects_non_integer_width_without_crashing(self, valid_script, value):
        # 校验器本身不能因为字段类型异常而抛 TypeError，
        # 否则用户看到的是一堆栈而不是可修正的错误清单。
        valid_script["width"] = value
        report = sb.validate(valid_script)
        assert "width" in error_paths(report)

    @pytest.mark.parametrize("value", ["30", "abc", None, [], {}, True])
    def test_rejects_non_integer_fps_without_crashing(self, valid_script, value):
        # fps 非法时仍要继续统计总时长，不能因 int() 转换失败而中断
        valid_script["fps"] = value
        report = sb.validate(valid_script)
        assert "fps" in error_paths(report)


class TestSceneValidation:
    def test_rejects_duplicate_ids(self, valid_script):
        valid_script["scenes"][1]["id"] = "opening"
        report = sb.validate(valid_script)
        assert "scenes[1].id" in error_paths(report)

    @pytest.mark.parametrize("scene_id", ["", "有 空格", "斜杠/", "点.号"])
    def test_rejects_invalid_ids(self, valid_script, scene_id):
        valid_script["scenes"][0]["id"] = scene_id
        assert "scenes[0].id" in error_paths(sb.validate(valid_script))

    @pytest.mark.parametrize("duration", [0, -5, "30", 1.5, None])
    def test_rejects_invalid_duration(self, valid_script, duration):
        valid_script["scenes"][0]["durationInFrames"] = duration
        assert "scenes[0].durationInFrames" in error_paths(sb.validate(valid_script))

    def test_warns_unknown_type_but_passes(self, valid_script):
        valid_script["scenes"][0]["type"] = "hologram"
        valid_script["scenes"][0]["data"] = {"anything": 1}
        report = sb.validate(valid_script)
        assert report.ok
        assert "scenes[0].type" in warning_paths(report)

    def test_errors_when_known_type_lacks_data(self, valid_script):
        del valid_script["scenes"][0]["data"]
        assert "scenes[0].data" in error_paths(sb.validate(valid_script))

    def test_errors_on_missing_required_field(self, valid_script):
        del valid_script["scenes"][0]["data"]["text"]
        assert "scenes[0].data.text" in error_paths(sb.validate(valid_script))

    def test_warns_on_undefined_field(self, valid_script):
        valid_script["scenes"][0]["data"]["color"] = "#fff"
        assert "scenes[0].data.color" in warning_paths(sb.validate(valid_script))

    def test_rejects_empty_items(self, valid_script):
        valid_script["scenes"][0] = {
            "id": "steps",
            "type": "list",
            "durationInFrames": 30,
            "data": {"items": []},
        }
        assert "scenes[0].data.items" in error_paths(sb.validate(valid_script))

    def test_rejects_blank_item_text(self, valid_script):
        valid_script["scenes"][0] = {
            "id": "steps",
            "type": "list",
            "durationInFrames": 30,
            "data": {"items": ["有效", "   "]},
        }
        assert "scenes[0].data.items[1]" in error_paths(sb.validate(valid_script))

    def test_warns_when_total_duration_is_long(self, valid_script):
        valid_script["scenes"][0]["durationInFrames"] = 30 * 200
        assert "scenes" in warning_paths(sb.validate(valid_script))


class TestEmphasisValidation:
    def test_accepts_emphasis_phrases(self, valid_script):
        valid_script["scenes"][0]["data"]["emphasis"] = ["努力"]
        assert sb.validate(valid_script).ok

    def test_rejects_empty_emphasis(self, valid_script):
        valid_script["scenes"][0]["data"]["emphasis"] = []
        assert "scenes[0].data.emphasis" in error_paths(sb.validate(valid_script))

    def test_rejects_non_array_emphasis(self, valid_script):
        valid_script["scenes"][0]["data"]["emphasis"] = "努力"
        assert "scenes[0].data.emphasis" in error_paths(sb.validate(valid_script))

    @pytest.mark.parametrize("phrase", ["", "   ", 42, None])
    def test_rejects_invalid_emphasis_item(self, valid_script, phrase):
        valid_script["scenes"][0]["data"]["emphasis"] = ["方向", phrase]
        assert "scenes[0].data.emphasis[1]" in error_paths(sb.validate(valid_script))

    def test_emphasis_is_not_flagged_as_undefined_field(self, valid_script):
        # 短语必须在画面文本里原样出现，否则会被「强调色不生效」的警告拦下
        valid_script["scenes"][0]["data"]["text"] = "开场命题"
        valid_script["scenes"][0]["data"]["emphasis"] = ["命题"]
        assert warning_paths(sb.validate(valid_script)) == []


class TestAnnotationValidation:
    """图形标注：比喻画面上的短标签，键名由各视频的构图约定。"""

    def test_accepts_annotations(self, valid_script):
        valid_script["scenes"][0]["data"]["annotations"] = {"leftPan": "命运的考试"}
        assert sb.validate(valid_script).ok

    def test_is_not_flagged_as_undefined_field(self, valid_script):
        valid_script["scenes"][0]["data"]["annotations"] = {"leftPan": "命运的考试"}
        assert warning_paths(sb.validate(valid_script)) == []

    @pytest.mark.parametrize("value", [[], "命运的考试", {}, None])
    def test_rejects_non_mapping_or_empty(self, valid_script, value):
        valid_script["scenes"][0]["data"]["annotations"] = value
        assert "scenes[0].data.annotations" in error_paths(sb.validate(valid_script))

    @pytest.mark.parametrize("label", ["", "   ", 42, None])
    def test_rejects_invalid_label(self, valid_script, label):
        valid_script["scenes"][0]["data"]["annotations"] = {"leftPan": label}
        assert "scenes[0].data.annotations.leftPan" in error_paths(sb.validate(valid_script))

    def test_warns_on_overlong_label(self, valid_script):
        # 标注是要挤在图形旁边的，太长会挤压构图，因此只警告不阻断
        valid_script["scenes"][0]["data"]["annotations"] = {"leftPan": "这一条图形标注写得实在太长了"}
        report = sb.validate(valid_script)
        assert report.ok
        assert "scenes[0].data.annotations.leftPan" in warning_paths(report)


class TestFigureDeclaration:
    """选组件的声明：figure.kind 决定这一幕用哪个视觉组件。"""

    def test_accepts_minimal_figure(self, valid_script):
        valid_script["scenes"][0]["data"]["figure"] = {"kind": "balance"}
        assert sb.validate(valid_script).ok

    def test_is_not_flagged_as_undefined_field(self, valid_script):
        valid_script["scenes"][0]["data"]["figure"] = {"kind": "balance"}
        assert warning_paths(sb.validate(valid_script)) == []

    def test_accepts_labels_motion_and_params(self, valid_script):
        valid_script["scenes"][0]["data"]["figure"] = {
            "kind": "balance",
            "motion": "impact",
            "labels": {"leftPan": "命运的考试"},
            "params": {"arm": 320},
        }
        assert sb.validate(valid_script).ok

    @pytest.mark.parametrize("value", [[], "balance", None])
    def test_rejects_non_object(self, valid_script, value):
        valid_script["scenes"][0]["data"]["figure"] = value
        assert "scenes[0].data.figure" in error_paths(sb.validate(valid_script))

    @pytest.mark.parametrize("kind", ["", "   ", 42, None])
    def test_rejects_invalid_kind(self, valid_script, kind):
        valid_script["scenes"][0]["data"]["figure"] = {"kind": kind}
        assert "scenes[0].data.figure.kind" in error_paths(sb.validate(valid_script))

    def test_rejects_unknown_motion(self, valid_script):
        valid_script["scenes"][0]["data"]["figure"] = {"kind": "balance", "motion": "dramatic"}
        assert "scenes[0].data.figure.motion" in error_paths(sb.validate(valid_script))

    def test_rejects_non_object_labels(self, valid_script):
        valid_script["scenes"][0]["data"]["figure"] = {"kind": "balance", "labels": ["左侧"]}
        assert "scenes[0].data.figure.labels" in error_paths(sb.validate(valid_script))

    def test_labels_follow_the_annotation_rules(self, valid_script):
        valid_script["scenes"][0]["data"]["figure"] = {"kind": "balance", "labels": {"leftPan": ""}}
        assert "scenes[0].data.figure.labels.leftPan" in error_paths(sb.validate(valid_script))

    def test_warns_on_unknown_figure_field(self, valid_script):
        valid_script["scenes"][0]["data"]["figure"] = {"kind": "balance", "tempo": "fast"}
        report = sb.validate(valid_script)
        assert report.ok
        assert "scenes[0].data.figure.tempo" in warning_paths(report)

    def test_warns_that_params_is_not_consumed_yet(self, valid_script):
        # 机制接通了但还没有组件读它，与其让人以为写了就生效，不如明说
        valid_script["scenes"][0]["data"]["figure"] = {"kind": "balance", "params": {"arm": 320}}
        report = sb.validate(valid_script)
        assert report.ok
        assert "scenes[0].data.figure.params" in warning_paths(report)

    def test_warns_on_kind_outside_the_catalog(self, valid_script):
        valid_script["scenes"][0]["data"]["figure"] = {"kind": "hourglass"}
        report = sb.validate(valid_script)
        assert report.ok
        warnings = warning_paths(report)
        assert "scenes[0].data.figure.kind" in warnings

    def test_warns_on_label_key_the_component_does_not_know(self, valid_script):
        # 拼错的标签不会报错，只会让画面上的标签空着，因此在开渲前提醒
        valid_script["scenes"][0]["data"]["figure"] = {
            "kind": "balance",
            "labels": {"leftPan": "命运的考试", "middlePan": "写错了"},
        }
        report = sb.validate(valid_script)
        assert report.ok
        assert "scenes[0].data.figure.labels.middlePan" in warning_paths(report)

    def test_accepts_labels_the_component_knows(self, valid_script):
        valid_script["scenes"][0]["data"]["figure"] = {
            "kind": "balance",
            "labels": {"leftPan": "命运的考试", "rightPan": "一次上场"},
        }
        assert warning_paths(sb.validate(valid_script)) == []


class TestComponentCapacity:
    """组件能吃下多少条目：超了不会崩，但会挤在一起读不出来。"""

    def test_warns_when_nodes_exceed_the_component(self, valid_script):
        valid_script["scenes"][0] = {
            "id": "loop",
            "type": "diagram",
            "durationInFrames": 120,
            "data": {"nodes": ["一", "二", "三", "四", "五", "六", "七"]},
        }
        assert "scenes[0].data.nodes" in warning_paths(sb.validate(valid_script))

    def test_accepts_nodes_within_capacity(self, valid_script):
        valid_script["scenes"][0] = {
            "id": "loop",
            "type": "diagram",
            "durationInFrames": 120,
            "data": {"nodes": ["一", "二", "三"]},
        }
        assert warning_paths(sb.validate(valid_script)) == []

    def test_capacity_follows_the_declared_kind(self, valid_script):
        # 台阶适合 2–5 级；声明成 stairs 后，6 项就应该被提醒
        valid_script["scenes"][0] = {
            "id": "steps",
            "type": "timeline",
            "durationInFrames": 120,
            "data": {
                "figure": {"kind": "stairs"},
                "items": ["一", "二", "三", "四", "五", "六"],
            },
        }
        assert "scenes[0].data.items" in warning_paths(sb.validate(valid_script))


class TestVisualWarnings:
    """排版与动效相关的警告：默认放行，--strict 时视为失败。"""

    def test_warns_on_overlong_line(self, valid_script):
        valid_script["scenes"][0]["data"]["text"] = "这一行故意写得很长很长很长很长很长很长的文案"
        assert "scenes[0].data.text" in warning_paths(sb.validate(valid_script))

    def test_accepts_manual_line_breaks(self, valid_script):
        valid_script["scenes"][0]["data"]["text"] = "第一行不足二十字\n第二行也不超限"
        assert warning_paths(sb.validate(valid_script)) == []

    def test_warns_on_long_list_item(self, valid_script):
        valid_script["scenes"][0] = {
            "id": "steps",
            "type": "list",
            "durationInFrames": 30,
            "data": {"items": ["这一条要点写得实在太长了会超出单行上限"]},
        }
        assert "scenes[0].data.items[0]" in warning_paths(sb.validate(valid_script))

    def test_warns_on_short_scene(self, valid_script):
        valid_script["scenes"][0]["durationInFrames"] = 12
        assert "scenes[0].durationInFrames" in warning_paths(sb.validate(valid_script))

    def test_warns_on_unmatched_emphasis(self, valid_script):
        valid_script["scenes"][0]["data"]["emphasis"] = ["方向"]
        assert "scenes[0].data.emphasis[0]" in warning_paths(sb.validate(valid_script))

    def test_emphasis_may_appear_in_any_checked_field(self, valid_script):
        valid_script["scenes"][0]["data"]["subtitle"] = "问题不在努力"
        valid_script["scenes"][0]["data"]["emphasis"] = ["努力"]
        assert warning_paths(sb.validate(valid_script)) == []


class TestDiagramValidation:
    def make_diagram(self, valid_script, nodes, edges=None):
        data = {"nodes": nodes}
        if edges is not None:
            data["edges"] = edges
        valid_script["scenes"][0] = {
            "id": "loop",
            "type": "diagram",
            "durationInFrames": 30,
            "data": data,
        }

    def test_accepts_string_nodes(self, valid_script):
        self.make_diagram(valid_script, ["问题", "约束"], [["问题", "约束"]])
        assert sb.validate(valid_script).ok

    def test_accepts_object_edges(self, valid_script):
        self.make_diagram(valid_script, ["A", "B"], [{"from": "A", "to": "B"}])
        assert sb.validate(valid_script).ok

    def test_accepts_object_nodes(self, valid_script):
        self.make_diagram(valid_script, [{"id": "a", "label": "A"}, "b"], [["a", "b"]])
        assert sb.validate(valid_script).ok

    def test_rejects_empty_nodes(self, valid_script):
        self.make_diagram(valid_script, [])
        assert "scenes[0].data.nodes" in error_paths(sb.validate(valid_script))

    def test_rejects_edge_with_unknown_node(self, valid_script):
        self.make_diagram(valid_script, ["A", "B"], [["A", "不存在"]])
        assert "scenes[0].data.edges[0]" in error_paths(sb.validate(valid_script))

    def test_rejects_malformed_edge(self, valid_script):
        self.make_diagram(valid_script, ["A", "B"], [["A"]])
        assert "scenes[0].data.edges[0]" in error_paths(sb.validate(valid_script))


class TestLoadingAndTimeline:
    def write(self, tmp_path: Path, data) -> Path:
        path = tmp_path / "storyboard.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_load_accumulates_start_frames(self, tmp_path, valid_script):
        model, report = sb.load(self.write(tmp_path, valid_script))
        assert report.ok
        assert model is not None
        assert [scene.start_frame for scene in model.scenes] == [0, 30]
        assert [scene.end_frame for scene in model.scenes] == [30, 90]
        assert model.total_frames == 90

    def test_load_reports_missing_file(self, tmp_path):
        model, report = sb.load(tmp_path / "absent.json")
        assert model is None
        assert not report.ok

    def test_load_reports_invalid_json(self, tmp_path):
        path = tmp_path / "broken.json"
        path.write_text("{ not json", encoding="utf-8")
        model, report = sb.load(path)
        assert model is None
        assert not report.ok
        assert "JSON" in report.errors[0].message

    def test_load_returns_none_when_validation_fails(self, tmp_path, valid_script):
        valid_script["scenes"] = []
        model, report = sb.load(self.write(tmp_path, valid_script))
        assert model is None
        assert not report.ok

    def test_scene_at_covers_boundaries(self, tmp_path, valid_script):
        model, _ = sb.load(self.write(tmp_path, valid_script))
        assert model is not None
        # 首帧属于第一个场景，末帧属于最后一个场景，边界不重叠
        assert model.scene_at(0).id == "opening"
        assert model.scene_at(29).id == "opening"
        assert model.scene_at(30).id == "closing"
        assert model.scene_at(89).id == "closing"

    def test_scene_at_clamps_out_of_range(self, tmp_path, valid_script):
        model, _ = sb.load(self.write(tmp_path, valid_script))
        assert model is not None
        # 越界时钳制到首末场景，保证 seek 结果稳定而不是抛错
        assert model.scene_at(-10).id == "opening"
        assert model.scene_at(9999).id == "closing"

    def test_narration_is_optional_and_preserved(self, tmp_path, valid_script):
        valid_script["scenes"][0]["narration"] = "口播文案"
        model, _ = sb.load(self.write(tmp_path, valid_script))
        assert model is not None
        assert model.scenes[0].narration == "口播文案"
        assert model.scenes[1].narration is None

    def test_example_storyboard_is_valid(self):
        """仓库自带示例必须始终通过校验，避免文档与实现漂移。"""
        from conftest import EXAMPLES_DIR

        model, report = sb.load(EXAMPLES_DIR / "storyboard.json")
        assert report.ok, [issue.format() for issue in report.issues]
        assert model is not None
        assert model.total_frames == 1350  # 45 秒 @ 30fps
        assert [scene.id for scene in model.scenes] == [
            "opening",
            "thesis",
            "choice",
            "loop",
            "closing",
        ]


def chart_scene(values=None, **extra) -> dict:
    """构造一个最小的图表幕，测试中按需局部改动。"""
    data: dict = {
        "title": "每月投入",
        "values": values if values is not None else [
            {"label": "四月", "value": 12},
            {"label": "五月", "value": 30},
        ],
    }
    data.update(extra)
    return {
        "id": "chart",
        "type": "chart",
        "durationInFrames": 120,
        "data": data,
    }


class TestChartScene:
    """图表场景（任务 7.2）：数据必须全部来自分镜，且画不出来要报错。"""

    def test_accepts_a_valid_chart_scene(self, valid_script):
        valid_script["scenes"][0] = chart_scene(
            figure={"labels": {"unit": " 小时", "note": "数据来源：团队周报"}}
        )
        report = sb.validate(valid_script)
        assert report.ok, [issue.format() for issue in report.issues]
        assert warning_paths(report) == []

    def test_values_are_required(self, valid_script):
        valid_script["scenes"][0] = chart_scene()
        del valid_script["scenes"][0]["data"]["values"]
        assert "scenes[0].data.values" in error_paths(sb.validate(valid_script))

    @pytest.mark.parametrize("values", [
        [],
        ["四月"],
        [{"label": "", "value": 1}],
        [{"label": "四月"}],
        [{"label": "四月", "value": "12"}],
        [{"label": "四月", "value": True}],
        [{"label": "四月", "value": float("nan")}],
    ])
    def test_rejects_invalid_values(self, valid_script, values):
        valid_script["scenes"][0] = chart_scene(values=values)
        assert any(
            path.startswith("scenes[0].data.values")
            for path in error_paths(sb.validate(valid_script))
        )

    def test_rejects_unknown_chart_type(self, valid_script):
        valid_script["scenes"][0] = chart_scene(chart="area")
        assert "scenes[0].data.chart" in error_paths(sb.validate(valid_script))

    def test_accepts_declared_chart_types(self, valid_script):
        for chart in ("bar", "line", "pie"):
            valid_script["scenes"][0] = chart_scene(chart=chart)
            assert sb.validate(valid_script).ok

    def test_warns_when_points_exceed_capacity(self, valid_script):
        # 图表条目上限是 6：7 个点会被提醒
        valid_script["scenes"][0] = chart_scene(
            values=[{"label": f"第{i}月", "value": i} for i in range(7)]
        )
        assert "scenes[0].data.values" in warning_paths(sb.validate(valid_script))

    def test_warns_on_duplicate_labels(self, valid_script):
        valid_script["scenes"][0] = chart_scene(
            values=[{"label": "四月", "value": 1}, {"label": "四月", "value": 2}]
        )
        assert "scenes[0].data.values[1].label" in warning_paths(sb.validate(valid_script))

    def test_warns_on_overlong_labels(self, valid_script):
        valid_script["scenes"][0] = chart_scene(
            values=[{"label": "这个数据点标签实在太长了一点", "value": 1}]
        )
        assert "scenes[0].data.values[0].label" in warning_paths(sb.validate(valid_script))

    def test_rejects_unknown_data_point_field_when_declarative(self, valid_script):
        valid_script["scenes"][0] = chart_scene(
            values=[{"label": "四月", "value": 1, "color": "red"}]
        )
        report = sb.validate(valid_script, declarative=True)
        assert not report.ok
        assert "scenes[0].data.values[0].color" in error_paths(report)


class TestSchematicMarker:
    """示意标记（任务 7.5）：标记被接受，且必须真的落到画面上。"""

    def test_schematic_is_accepted_and_silent_for_charts(self, valid_script):
        # 图表组件会自动画「示意」标：标记 + 文案双保险，不该有任何提醒
        valid_script["scenes"][0] = chart_scene(figure={"schematic": True})
        report = sb.validate(valid_script)
        assert report.ok
        assert warning_paths(report) == []

    def test_schematic_must_be_a_boolean(self, valid_script):
        valid_script["scenes"][0] = chart_scene(figure={"schematic": "yes"})
        assert "scenes[0].data.figure.schematic" in error_paths(sb.validate(valid_script))

    def test_marker_without_a_word_warns_for_kinds_that_cannot_draw_the_tag(self, valid_script):
        # 冰山不会自动画「示意」标：声明了标记就得让「示意」二字出现在文案里
        valid_script["scenes"][0] = {
            "id": "list",
            "type": "list",
            "durationInFrames": 120,
            "data": {
                "figure": {"kind": "iceberg", "schematic": True},
                "items": ["看得见的需求", "看不见的维护"],
            },
        }
        report = sb.validate(valid_script)
        assert report.ok
        assert "scenes[0].data.figure.schematic" in warning_paths(report)

    def test_marker_with_the_word_in_text_is_silent_for_other_kinds(self, valid_script):
        valid_script["scenes"][0] = {
            "id": "list",
            "type": "list",
            "durationInFrames": 120,
            "data": {
                "figure": {"kind": "iceberg", "schematic": True},
                "items": ["看得见的需求", "看不见的维护（示意）"],
            },
        }
        assert warning_paths(sb.validate(valid_script)) == []

    def test_chart_without_marker_or_word_gets_a_sourcing_reminder(self, valid_script):
        # 既没标记也没写明来源：提醒作者对「这些数字哪来的」给出交代
        valid_script["scenes"][0] = chart_scene()
        report = sb.validate(valid_script)
        assert report.ok
        assert "scenes[0].data.values" in warning_paths(report)

    def test_sourced_chart_note_silences_the_reminder(self, valid_script):
        valid_script["scenes"][0] = chart_scene(
            figure={"labels": {"unit": " 小时", "note": "数据来源：团队周报"}}
        )
        assert warning_paths(sb.validate(valid_script)) == []

    def test_data_point_labels_count_as_visible_text(self, valid_script):
        # 「示意」写进数据点标签同样算落到画面上
        valid_script["scenes"][0] = chart_scene(
            values=[{"label": "四月（示意）", "value": 12}, {"label": "五月", "value": 30}]
        )
        assert warning_paths(sb.validate(valid_script)) == []
