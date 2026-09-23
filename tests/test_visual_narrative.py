"""视觉叙事契约：字段校验、结构分类、全片预算与 V 系列报告。

覆盖 openspec 变更 ``enforce-visual-storytelling`` 的四层确定性判定：

1. 逐幕 ``visualIntent`` 新字段的存在、枚举、空值与机械复述检查；
2. 场景树视觉叙事分类：文字卡片包装（surface+text、图标、布局换壳）
   不会被误算成论证型图形；
3. 版本化全片预算：30% 文字幕上限的向上取整、相邻文字幕、长短片
   非文字模式覆盖、声明/结构矛盾，以及普通校验与严格校验的兼容策略；
4. review 的 V1–V6 闸门结构与 ``review.md`` 人工结论解析。

夹具一律使用抽象文案，不包含任何作品原文。
"""

from __future__ import annotations

import json

import pytest

from a2v import cli
from a2v import storyboard as sb
from a2v import visual_narrative as vn


# ---------------------------------------------------------------------------
# 夹具构造
# ---------------------------------------------------------------------------


def _visual_direction() -> dict:
    return {"motif": "测试", "compositionBias": "mixed", "density": "balanced", "rhythm": "steady", "avoid": []}


def _text_tree(scene_id: str) -> dict:
    """最普通的文字卡片：一根文字原语。"""
    return {
        "id": "root",
        "type": "stack",
        "children": [{"id": f"{scene_id}-copy", "type": "text", "contentRef": "data.text", "role": "headline"}],
    }


def _motion(scene_id: str) -> list[dict]:
    return [{"target": f"{scene_id}-copy", "recipe": "reveal", "phase": "establish", "durationFrames": 24}]


def _intent(**overrides) -> dict:
    """完整的新契约 visualIntent：五个论证字段齐全。"""
    intent = {
        "relation": "focus",
        "focus": "text",
        "composition": "center",
        "density": "sparse",
        "tone": "neutral",
        "mode": "typography",
        "claim": "场景论点",
        "showWithoutText": "移除文字后只剩单个焦点块",
        "primaryObject": "标题文字块",
        "motionMeaning": "入场揭示论点",
    }
    intent.update(overrides)
    return intent


def _scene(scene_id: str, *, mode: str | None = "typography", tree: dict | None = None, data: dict | None = None, intent_extra: dict | None = None) -> dict:
    scene = {
        "id": scene_id,
        "type": "title",
        "durationInFrames": 90,
        "data": data if data is not None else {"text": f"{scene_id}的论点"},
        "visualIntent": _intent(**(intent_extra or {})),
        "sceneTree": tree if tree is not None else _text_tree(scene_id),
        "motions": [],
        "renderer": {"kind": "tree"},
        "camera": {"focus": "root", "shot": "medium", "composition": "center", "depth": "flat", "segments": [{"phase": "establish", "kind": "hold", "focus": "root"}]},
        "visual": {"kicker": "测试"},
    }
    if mode is None:
        # 旧版分镜：没有 visualIntent 论证字段（relation 等既有字段仍在）
        scene["visualIntent"] = {key: value for key, value in scene["visualIntent"].items() if key not in ("mode", "claim", "showWithoutText", "primaryObject", "motionMeaning")}
    elif mode != scene["visualIntent"]["mode"]:
        scene["visualIntent"]["mode"] = mode
    return scene


def _storyboard(*scenes: dict) -> dict:
    for index, scene in enumerate(scenes):
        if index:
            scene.setdefault("transition", {"kind": "dissolve", "meaning": "切换到下一段论证"})
    return {
        "version": 3,
        "schemaVersion": 3,
        "directingVersion": 1,
        "directingBrief": {"thesis": "测试命题", "audienceShift": "测试转变", "emotionalArc": ["观察", "确认"], "visualMotif": "路径", "stylePack": "editorial", "avoid": []},
        "visual": {"theme": "dark", "preset": "keynote"},
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "title": "视觉叙事测试",
        "visualDirection": _visual_direction(),
        "scenes": list(scenes),
    }


def _chart_tree(scene_id: str) -> dict:
    return {
        "id": "root",
        "type": "column",
        "children": [
            {"id": f"{scene_id}-title", "type": "text", "contentRef": "data.title", "role": "title"},
            {"id": f"{scene_id}-chart", "type": "chart", "contentRef": "data.values", "chart": "bar", "schematic": True},
        ],
    }


def _chart_scene(scene_id: str) -> dict:
    return _scene(
        scene_id,
        mode="chart",
        tree=_chart_tree(scene_id),
        data={"title": f"{scene_id}的趋势", "values": [{"label": "甲", "value": 1}, {"label": "乙", "value": 2}]},
        intent_extra={"focus": "chart", "composition": "full"},
    )


def _connector_scene(scene_id: str) -> dict:
    tree = {
        "id": "root",
        "type": "row",
        "align": "center",
        "gap": "sm",
        "children": [
            {"id": f"{scene_id}-a", "type": "text", "contentRef": "data.a", "role": "body"},
            {"id": f"{scene_id}-arrow", "type": "connector", "direction": "ltr"},
            {"id": f"{scene_id}-b", "type": "text", "contentRef": "data.b", "role": "body"},
        ],
    }
    return _scene(scene_id, mode="process", tree=tree, data={"text": "推进", "a": "第一步", "b": "第二步"})


def _radial_scene(scene_id: str) -> dict:
    tree = {
        "id": "root",
        "type": "overlay",
        "children": [
            {"id": f"{scene_id}-ring", "type": "shape", "shape": "ring", "state": "muted"},
            {
                "id": f"{scene_id}-wheel",
                "type": "radial",
                "children": [
                    {"id": f"{scene_id}-s1", "type": "surface", "children": [{"id": f"{scene_id}-s1-text", "type": "text", "contentRef": "data.s1", "role": "body"}]},
                    {"id": f"{scene_id}-s2", "type": "surface", "children": [{"id": f"{scene_id}-s2-text", "type": "text", "contentRef": "data.s2", "role": "body"}]},
                ],
            },
        ],
    }
    return _scene(scene_id, mode="cycle", tree=tree, data={"text": "循环", "s1": "阶段一", "s2": "阶段二"})


def _text_leaf(node_id: str) -> dict:
    return {"id": node_id, "type": "text", "contentRef": f"data.{node_id}", "role": "body"}


def _surface_leaf(node_id: str) -> dict:
    return {"id": node_id, "type": "surface", "children": [{"id": f"{node_id}-text", "type": "text", "contentRef": f"data.{node_id}", "role": "body"}]}


# ---------------------------------------------------------------------------
# 1.1 逐幕 visualIntent 论证字段
# ---------------------------------------------------------------------------


class TestVisualIntentFields:
    def test_missing_fields_are_rejected_in_normal_mode(self):
        report = sb.validate(_storyboard(_scene("a", mode=None)))
        assert not report.ok
        assert any(issue.path.endswith("visualIntent") for issue in report.errors)

    def test_missing_fields_are_strict_errors(self):
        report = sb.validate(_storyboard(_scene("a", mode=None)), strict=True)
        assert not report.ok
        assert any(issue.path.endswith("visualIntent") for issue in report.errors)

    def test_mode_enum_error_is_always_reported(self):
        report = sb.validate(_storyboard(_scene("a", mode="slideshow")))
        assert not report.ok
        assert any(issue.path.endswith("visualIntent.mode") for issue in report.errors)

    def test_empty_field_values_are_rejected(self):
        report = sb.validate(_storyboard(_scene("a", intent_extra={"claim": "  "})))
        assert not report.ok
        assert any(issue.path.endswith("visualIntent.claim") for issue in report.errors)

    @pytest.mark.parametrize(
        "show",
        [
            "场景论点",
            "场景论点。",
            "显示场景论点",
            "呈现：场景论点",
            "展示 场景论点",
            "表达场景论点",
        ],
    )
    def test_mechanical_restatements_are_rejected(self, show):
        report = sb.validate(_storyboard(_scene("a", intent_extra={"showWithoutText": show})))
        assert not report.ok
        assert any(issue.path.endswith("visualIntent.showWithoutText") for issue in report.errors)

    def test_substantive_expression_passes(self):
        report = sb.validate(
            _storyboard(_scene("a", intent_extra={"showWithoutText": "投入曲线上升而产出曲线持平，两条线的差距越拉越大"}))
        )
        assert report.ok, [issue.format() for issue in report.issues]

    def test_restatement_helper_matches_only_mechanical_patterns(self):
        assert vn.is_restatement("显示X", "X")
        assert vn.is_restatement("X", "X")
        assert not vn.is_restatement("两根柱子一高一低", "X")
        assert not vn.is_restatement("显示两根柱子一高一低", "X")


# ---------------------------------------------------------------------------
# 1.2 场景树视觉叙事分类
# ---------------------------------------------------------------------------


class TestSceneClassification:
    def test_text_card_with_icon_and_surface_is_text(self):
        # 正是规格里的反例：标题 + 正文 + 两个带符号的文字表面 + 背景光晕
        tree = {
            "id": "root",
            "type": "column",
            "children": [
                {"id": "halo", "type": "shape", "shape": "spotlight", "state": "rest"},
                {"id": "head", "type": "text", "contentRef": "data.title", "role": "headline"},
                {
                    "id": "cards",
                    "type": "row",
                    "gap": "sm",
                    "children": [
                        {
                            "id": "card-1",
                            "type": "surface",
                            "children": [
                                {"id": "card-1-icon", "type": "icon", "icon": "spark"},
                                {"id": "card-1-text", "type": "text", "contentRef": "data.left", "role": "body"},
                            ],
                        },
                        {
                            "id": "card-2",
                            "type": "surface",
                            "children": [
                                {"id": "card-2-icon", "type": "icon", "icon": "check"},
                                {"id": "card-2-text", "type": "text", "contentRef": "data.right", "role": "body"},
                            ],
                        },
                    ],
                },
            ],
        }
        scene = _scene("cards", mode="comparison", tree=tree, data={"title": "对照", "left": "甲", "right": "乙"})
        analysis = vn.analyze_scene(scene)
        assert analysis["structuralClass"] == "text"
        assert analysis["evidence"] == []
        assert analysis["contradictsDeclaration"]

    def test_layout_wrappers_never_turn_text_cards_into_graphics(self):
        # split / grid / overlay / group 包装的纯文字卡片仍是文字幕
        wrappers = {
            "split": {"id": "root", "type": "split", "children": [_text_leaf("l"), _text_leaf("r")]},
            "grid": {
                "id": "root",
                "type": "grid",
                "columns": 2,
                "children": [_surface_leaf("c1"), _surface_leaf("c2")],
            },
            "overlay": {
                "id": "root",
                "type": "overlay",
                "children": [{"id": "glow", "type": "shape", "shape": "spotlight"}, _text_leaf("t")],
            },
            "group": {
                "id": "root",
                "type": "group",
                "direction": "horizontal",
                "children": [_surface_leaf("g1"), _surface_leaf("g2")],
            },
        }
        for name, tree in wrappers.items():
            scene = _scene(f"w-{name}", mode="comparison", tree=tree, data={"text": "文字", "l": "甲", "r": "乙", "t": "文字", "c1": "甲", "c2": "乙", "g1": "甲", "g2": "乙"})
            analysis = vn.analyze_scene(scene)
            assert analysis["structuralClass"] == "text", name
            assert analysis["isTextScene"]

    def test_chart_connector_radial_image_are_evidence(self):
        cases = [
            (_chart_scene("c1"), "chart"),
            (_connector_scene("c2"), "connector"),
            (_radial_scene("c3"), "radial"),
        ]
        for scene, kind in cases:
            analysis = vn.analyze_scene(scene)
            assert analysis["structuralClass"] == "evidence", scene["id"]
            assert kind in analysis["evidence"], scene["id"]
            assert not analysis["isTextScene"]

    def test_radial_without_content_children_is_not_evidence(self):
        tree = {
            "id": "root",
            "type": "radial",
            "children": [
                {"id": "dot-1", "type": "shape", "shape": "circle"},
                {"id": "dot-2", "type": "shape", "shape": "circle"},
            ],
        }
        analysis = vn.analyze_scene(_scene("dots", mode="cycle", tree=tree, data={"text": "圆"}))
        assert analysis["structuralClass"] == "text"

    def test_code_scene_is_structurally_unverifiable(self):
        scene = _scene("code-1", mode="chart")
        scene["renderer"] = {"kind": "code", "module": "some-module"}
        scene.pop("sceneTree")
        scene.pop("motions")
        analysis = vn.analyze_scene(scene)
        assert analysis["structuralClass"] == "code"
        assert analysis["isTextScene"] is False
        assert not analysis["contradictsDeclaration"]

    def test_declared_typography_stays_text_even_with_evidence(self):
        scene = _chart_scene("mixed")
        scene["visualIntent"]["mode"] = "typography"
        analysis = vn.analyze_scene(scene)
        assert analysis["isTextScene"]
        assert not analysis["contradictsDeclaration"]


# ---------------------------------------------------------------------------
# 1.3 版本化全片预算
# ---------------------------------------------------------------------------


class TestBudgetRules:
    @staticmethod
    def _interleaved(text_count: int, chart: int, connector: int, radial: int) -> list[dict]:
        """把文字幕与证据幕交错排列，单独隔离预算规则（避免相邻文字幕）。"""
        evidence = [_chart_scene(f"chart-{i}") for i in range(chart)]
        evidence += [_connector_scene(f"chain-{i}") for i in range(connector)]
        evidence += [_radial_scene(f"wheel-{i}") for i in range(radial)]
        scenes: list[dict] = []
        for index in range(max(text_count, len(evidence))):
            if index < len(evidence):
                scenes.append(evidence[index])
            if index < text_count:
                scenes.append(_scene(f"text-{index}"))
        return scenes

    def test_text_budget_ceil_boundary(self):
        # 10 幕上限 = ceil(3.0) = 3：三幕文字幕、三种非文字模式 → 通过
        ok_report = sb.validate(_storyboard(*self._interleaved(3, 3, 2, 2)), strict=True)
        assert ok_report.ok, [issue.format() for issue in ok_report.errors]

        # 同样 10 幕换成四幕文字幕：4 > 3 → 失败并给出上限
        bad_report = sb.validate(_storyboard(*self._interleaved(4, 2, 2, 2)), strict=True)
        assert not bad_report.ok
        assert any("超过允许上限 3" in issue.message for issue in bad_report.errors)

    def test_adjacent_text_scenes_are_rejected(self):
        report = sb.validate(_storyboard(_scene("a"), _chart_scene("b"), _scene("c"), _scene("d")), strict=True)
        assert not report.ok
        messages = [issue.message for issue in report.errors]
        assert any("相邻两幕均为文字幕" in message and "c、d" in message for message in messages)

    def test_short_film_needs_two_non_text_modes(self):
        # 3 幕、两种非文字模式：通过
        report = sb.validate(_storyboard(_scene("a"), _chart_scene("b"), _connector_scene("c")), strict=True)
        assert report.ok, [issue.format() for issue in report.errors]
        # 换成同一模式两次：失败
        report = sb.validate(_storyboard(_scene("a"), _chart_scene("b"), _chart_scene("c")), strict=True)
        assert not report.ok
        assert any("少于 3 幕作品要求的 2 种" in issue.message for issue in report.errors)

    def test_long_film_needs_three_non_text_modes(self):
        # 8 幕只有 chart + process 两种 → 失败
        scenes = [
            _scene("t0"), _chart_scene("c0"), _scene("t1"), _connector_scene("p0"),
            _scene("t2"), _chart_scene("c1"), _connector_scene("p1"), _chart_scene("c2"),
        ]
        report = sb.validate(_storyboard(*scenes), strict=True)
        assert not report.ok
        assert any("要求的 3 种" in issue.message for issue in report.errors)

        # 补上 cycle（radial）→ 三种模式齐备，预算与相邻规则也满足
        scenes.append(_radial_scene("r0"))
        report = sb.validate(_storyboard(*scenes), strict=True)
        assert report.ok, [issue.format() for issue in report.errors]

    def test_declaration_structure_conflict_reports_scene(self):
        report = sb.validate(_storyboard(_scene("a", mode="comparison")), strict=True)
        assert not report.ok
        conflict = [issue for issue in report.errors if issue.path == "scenes[0].visualIntent.mode"]
        assert conflict, [issue.format() for issue in report.errors]
        assert "comparison" in conflict[0].message

    def test_budget_rules_are_silent_in_normal_mode(self):
        # 普通校验的兼容契约：字段齐全时即便预算违规也不拦（预算属于严格验收）
        report = sb.validate(_storyboard(_scene("a"), _scene("b")))
        assert report.ok
        assert report.warnings == []

    def test_single_scene_cannot_satisfy_mode_coverage(self):
        # 边界：单幕分镜不可能满足「少于八幕至少两种非文字模式」
        report = sb.validate(_storyboard(_chart_scene("solo")), strict=True)
        assert not report.ok
        assert any("要求的 2 种" in issue.message for issue in report.errors)

    def test_rule_version_is_reported(self):
        analysis = vn.analyze(_storyboard(_scene("a")))
        assert analysis["ruleVersion"] == vn.RULE_VERSION
        assert vn.RULE_VERSION >= 1


# ---------------------------------------------------------------------------
# v3 一致接受集合：普通、严格与预览入口都拒绝缺失的导演论证
# ---------------------------------------------------------------------------


class TestV3Contract:
    def test_missing_visual_intent_evidence_fails_in_all_modes(self, tmp_path):
        raw = _storyboard(_scene("a"))
        for field in ("mode", "claim", "showWithoutText", "primaryObject", "motionMeaning"):
            raw["scenes"][0]["visualIntent"].pop(field)
        path = tmp_path / "incomplete-v3.json"
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        ordinary = sb.validate(raw)
        strict = sb.validate(raw, strict=True)
        assert not ordinary.ok and not strict.ok
        assert any(issue.path.endswith("visualIntent") for issue in ordinary.errors)


# ---------------------------------------------------------------------------
# 2.1 review 的 V1–V5 闸门结构
# ---------------------------------------------------------------------------


class TestReviewGates:
    def test_gates_report_scenes_values_and_thresholds(self):
        scenes = [
            _scene("a", mode="comparison"),  # 声明 comparison 却只有文字包装 → V4
            _chart_scene("b"),
            _scene("c"),
            _connector_scene("d"),
            _scene("e"),
            _radial_scene("f"),
            _scene("g"),
        ]
        gates = vn.review_gates(vn.analyze(_storyboard(*scenes)))
        assert gates["ruleVersion"] == vn.RULE_VERSION
        # 7 幕上限 = ceil(2.1) = 3，文字幕 4 幕 → 失败并列出全部场景
        assert gates["v1"]["status"] == "fail"
        assert gates["v1"]["value"] == 4 and gates["v1"]["limit"] == 3
        assert gates["v1"]["sceneCount"] == 7
        assert gates["v1"]["scenes"] == ["a", "c", "e", "g"]
        # 文字幕被证据幕隔开 → 无相邻
        assert gates["v2"]["status"] == "pass"
        assert gates["v2"]["pairs"] == []
        # 非文字模式 {comparison(a 声明), chart, process, cycle} = 4 ≥ 2
        assert gates["v3"]["status"] == "pass"
        assert gates["v3"]["value"] == 4 and gates["v3"]["required"] == 2
        assert gates["v3"]["modes"] == ["chart", "comparison", "cycle", "process"]
        # 只有场景 a 拿不出结构证据却声明了图形模式
        assert gates["v4"]["status"] == "fail"
        assert [item["id"] for item in gates["v4"]["scenes"]] == ["a"]
        assert gates["v4"]["scenes"][0]["declaredMode"] == "comparison"
        assert gates["v4"]["scenes"][0]["evidence"] == []
        # V5 候选 = 全部文字幕，每个都带判定证据
        candidate_ids = [item["id"] for item in gates["v5"]["scenes"]]
        assert candidate_ids == ["a", "c", "e", "g"]
        for item in gates["v5"]["scenes"]:
            assert item["reason"]
            assert item["structuralClass"] == "text"

    def test_v2_reports_adjacent_text_scenes(self):
        gates = vn.review_gates(vn.analyze(_storyboard(_scene("a"), _chart_scene("b"), _scene("c"), _scene("d"))))
        assert gates["v2"]["status"] == "fail"
        assert gates["v2"]["pairs"] == [["c", "d"]]

    def test_v4_reports_declaration_and_structure(self):
        gates = vn.review_gates(vn.analyze(_storyboard(_scene("a", mode="process"))))
        assert gates["v4"]["status"] == "fail"
        assert gates["v4"]["scenes"][0]["declaredMode"] == "process"
        assert gates["v4"]["scenes"][0]["evidence"] == []


# ---------------------------------------------------------------------------
# 2.2 V6 人工结论解析
# ---------------------------------------------------------------------------


class TestReviewV6:
    def test_missing_review_file_is_pending_and_unpublishable(self, tmp_path):
        v6 = vn.review_v6(tmp_path / "review.md", ["a"])
        assert v6["status"] == "待评审"
        assert v6["publishable"] is False
        assert v6["score"] is None

    def test_low_score_blocks_publish(self, tmp_path):
        path = tmp_path / "review.md"
        path.write_text("| 图形论证 | 3 | 图形只是装饰 |\n", encoding="utf-8")
        v6 = vn.review_v6(path, [])
        assert v6["status"] == "不通过"
        assert v6["publishable"] is False

    def test_unresolved_candidates_block_publish(self, tmp_path):
        path = tmp_path / "review.md"
        path.write_text("| 图形论证 | 4 | 依据充分 |\n", encoding="utf-8")
        v6 = vn.review_v6(path, ["a", "b"])
        assert v6["status"] == "候选未裁决"
        assert v6["unresolvedCandidates"] == ["a", "b"]
        assert v6["publishable"] is False

    def test_resolved_candidates_with_good_score_publish(self, tmp_path):
        path = tmp_path / "review.md"
        path.write_text(
            "| 图形论证 | 5 | 循环图承担论证 |\n\n## 候选裁决\n\n- a：radial 圆周承担循环关系，保留\n",
            encoding="utf-8",
        )
        v6 = vn.review_v6(path, ["a", "b"])
        assert v6["status"] == "候选未裁决"  # b 仍未裁决
        path.write_text(
            "| 图形论证 | 4 | 循环图承担论证 |\n\n## 候选裁决\n\n- a：保留\n- b：已重排为连接线推进\n",
            encoding="utf-8",
        )
        v6 = vn.review_v6(path, ["a", "b"])
        assert v6["status"] == "通过"
        assert v6["publishable"] is True

    def test_v6_section_score_format(self, tmp_path):
        path = tmp_path / "review.md"
        path.write_text("### V6 图形承担论证\n\n评分：4/5\n依据：图表直接说出结论\n", encoding="utf-8")
        v6 = vn.review_v6(path, [])
        assert v6["score"] == 4 and v6["status"] == "通过"


class TestCliVisualNarrativePayload:
    """体检报告的 V 系列接线：V1–V4 并入错误数，V5/V6 只呈现。"""

    def _write(self, tmp_path, storyboard: dict):
        path = tmp_path / "storyboard.json"
        path.write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
        return path

    def test_v1_and_v4_failures_enter_the_error_list(self, tmp_path):
        # 两幕都声明图形模式却只有文字包装：V4 逐幕失败，V1 同时超预算
        path = self._write(tmp_path, _storyboard(_scene("a", mode="comparison"), _scene("b", mode="process")))
        combined = sb.Report()
        gates = cli._visual_narrative_payload(path, tmp_path, combined)
        assert gates["v4"]["status"] == "fail" and gates["v1"]["status"] == "fail"
        paths = [issue.path for issue in combined.errors]
        assert "视觉叙事 V4" in paths and "视觉叙事 V1" in paths

    def test_semantic_gates_never_touch_the_exit_code(self, tmp_path):
        path = self._write(tmp_path, _storyboard(_chart_scene("a"), _scene("b")))
        combined = sb.Report()
        cli._visual_narrative_payload(path, tmp_path, combined)
        assert not [issue for issue in combined.issues if "V5" in issue.path or "V6" in issue.path]

    def test_review_md_conclusion_is_read_from_out_dir(self, tmp_path):
        path = self._write(tmp_path, _storyboard(_chart_scene("a"), _scene("b")))
        gates = cli._visual_narrative_payload(path, tmp_path, sb.Report())
        assert [item["id"] for item in gates["v5"]["scenes"]] == ["b"]
        assert gates["v6"]["status"] == "待评审"
        (tmp_path / "review.md").write_text(
            "| 图形论证 | 5 | 图表承担论证 |\n\n## 候选裁决\n\n- b：通过，已改声明为 typography\n",
            encoding="utf-8",
        )
        gates = cli._visual_narrative_payload(path, tmp_path, sb.Report())
        assert gates["v6"]["status"] == "通过" and gates["v6"]["publishable"] is True
        lines = "\n".join(cli._visual_narrative_lines(gates))
        assert "V6 图形承担论证：通过（5/5）" in lines and "可发布=是" in lines


# ---------------------------------------------------------------------------
# 2.3 与多样性检查口径一致
# ---------------------------------------------------------------------------


class TestConsistencyWithDiversity:
    def test_fingerprint_includes_declared_mode_but_not_copy(self):
        from a2v import diversity

        same_tree = _storyboard(_scene("a"), _scene("b"))
        scene_a = dict(same_tree["scenes"][0])
        scene_b = dict(same_tree["scenes"][1])
        scene_b["data"] = {"text": "完全不同的正文"}
        # 文字不同 → 指纹相同
        assert diversity.fingerprint(scene_a) == diversity.fingerprint(scene_b)
        # 声明的视觉模式不同 → 指纹不同
        scene_b["visualIntent"] = _intent(mode="chart")
        assert diversity.fingerprint(scene_a) != diversity.fingerprint(scene_b)

    def test_classification_ignores_copy_too(self):
        first = vn.analyze_scene(_scene("a"))
        second = vn.analyze_scene(_scene("b", data={"text": "另一段完全不同的正文"}))
        assert first["structuralClass"] == second["structuralClass"]
        assert first["evidence"] == second["evidence"]


# ---------------------------------------------------------------------------
# 4.1 rest-not-reward 结构特征的失败回归夹具
# ---------------------------------------------------------------------------


class TestRestNotRewardRegression:
    """抽象自 videos/rest-not-reward 的结构特征（不含作品原文）。

    那支片子的十幕分别用居中光晕、分栏、卡片网格、图标卡、表面堆叠等
    不同布局包装文字卡片，结构合法、体检通过，却全是文字主导。
    这里把「不同布局包装」抽象成夹具：布局换壳不改变文字主导判定，
    严格校验必须失败。
    """

    def _wrapper_storyboard(self) -> dict:
        def glow_center(scene_id: str) -> dict:
            return {
                "id": "root",
                "type": "overlay",
                "children": [
                    {"id": f"{scene_id}-glow", "type": "shape", "shape": "spotlight"},
                    {"id": f"{scene_id}-text", "type": "text", "contentRef": "data.text", "role": "headline"},
                ],
            }

        def icon_cards(scene_id: str, count: int = 4) -> dict:
            return {
                "id": "root",
                "type": "column",
                "gap": "md",
                "children": [
                    {"id": f"{scene_id}-title", "type": "text", "contentRef": "data.title", "role": "title"},
                    {
                        "id": f"{scene_id}-cards",
                        "type": "grid",
                        "columns": 2,
                        "children": [
                            {
                                "id": f"{scene_id}-card-{index}",
                                "type": "surface",
                                "children": [
                                    {"id": f"{scene_id}-icon-{index}", "type": "icon", "icon": "spark"},
                                    {"id": f"{scene_id}-card-{index}-text", "type": "text", "contentRef": f"data.cell{index}", "role": "body"},
                                ],
                            }
                            for index in range(count)
                        ],
                    },
                ],
            }

        def stacked_cards(scene_id: str) -> dict:
            return {
                "id": "root",
                "type": "stack",
                "gap": "sm",
                "children": [
                    {
                        "id": f"{scene_id}-card",
                        "type": "surface",
                        "children": [{"id": f"{scene_id}-card-text", "type": "text", "contentRef": "data.text", "role": "body"}],
                    },
                    {"id": f"{scene_id}-line", "type": "shape", "shape": "line", "state": "muted"},
                ],
            }

        builders = [glow_center, icon_cards, stacked_cards, glow_center, icon_cards, stacked_cards]
        modes = ["typography", "comparison", "process", "metaphor", "comparison", "cycle"]
        scenes = []
        for index, (builder, mode) in enumerate(zip(builders, modes)):
            scene_id = f"scene-{index}"
            data = {"text": f"第{index}幕的论点", "title": f"第{index}幕", **{f"cell{i}": f"条目{i}" for i in range(4)}}
            scene = _scene(
                scene_id,
                mode=mode,
                tree=builder(scene_id),
                data=data,
                intent_extra={"composition": "center", "density": "balanced"},
            )
            scene["motions"] = []
            scenes.append(scene)
        return _storyboard(*scenes)

    def test_different_wrappers_all_classified_as_text(self):
        storyboard = self._wrapper_storyboard()
        analysis = vn.analyze(storyboard)
        assert all(item["structuralClass"] == "text" for item in analysis["scenes"])
        assert len(analysis["textScenes"]) == 6

    def test_strict_validation_fails_with_located_errors(self):
        storyboard = self._wrapper_storyboard()
        report = sb.validate(storyboard, strict=True)
        assert not report.ok
        rules = " ".join(issue.message for issue in report.errors)
        assert "上限" in rules and "相邻两幕均为文字幕" in rules
        # 声明了图形模式但只有文字包装的幕被逐一定位
        assert any(issue.path.endswith("visualIntent.mode") for issue in report.errors)

    def test_normal_mode_stays_compatible(self):
        storyboard = self._wrapper_storyboard()
        report = sb.validate(storyboard)
        assert report.ok

    def test_fixture_contains_no_article_text(self):
        # 夹具文案全部是测试自造的抽象句子，不包含作品原文
        raw = json.dumps(self._wrapper_storyboard(), ensure_ascii=False)
        for banned in ("机器", "疲劳", "产出"):
            assert banned not in raw


# ---------------------------------------------------------------------------
# 3.4 五个中层原语参与结构证据判定
# ---------------------------------------------------------------------------


def _stage(node_id: str) -> dict:
    """一个承载内容的阶段：表面 + 一行文字。"""
    return {
        "id": node_id,
        "type": "surface",
        "children": [{"id": f"{node_id}-text", "type": "text", "contentRef": "data.text", "role": "body"}],
    }


def _relation_tree(scene_id: str, node_type: str, count: int, direction: str = "ltr") -> dict:
    return {
        "id": "root",
        "type": node_type,
        "direction": direction,
        "children": [_stage(f"{scene_id}-s{index}") for index in range(count)],
    }


def _quantity_tree(scene_id: str, node_type: str) -> dict:
    node = {"id": f"{scene_id}-meter", "type": node_type, "contentRef": "data.ratio"}
    if node_type == "pictogram":
        node["icon"] = "users"
    return {"id": "root", "type": "stack", "children": [node]}


class TestMidlevelStructureEvidence:
    """五个中层原语要作为**结构证据**参与 V 系列，而不是被当成文字包装。"""

    def _analysis(self, tree: dict, mode: str = "process") -> dict:
        scene = _scene("mid", mode=mode, tree=tree, data={"text": "中层原语", "ratio": 42})
        scene["motions"] = []
        return vn.analyze_scene(scene)

    @pytest.mark.parametrize("node_type", ["flow", "cycle", "timeline"])
    def test_relation_container_with_two_stages_is_evidence(self, node_type):
        analysis = self._analysis(_relation_tree("mid", node_type, 2))
        assert analysis["structuralClass"] == "evidence"
        assert analysis["evidence"] == [node_type]
        assert analysis["isTextScene"] is False

    @pytest.mark.parametrize("node_type", ["gauge", "pictogram"])
    def test_quantity_primitive_is_evidence_on_its_own(self, node_type):
        analysis = self._analysis(_quantity_tree("mid", node_type))
        assert analysis["structuralClass"] == "evidence"
        assert analysis["evidence"] == [node_type]

    def test_evidence_order_is_fixed(self):
        tree = _relation_tree("mid", "flow", 2)
        tree["children"].append(_quantity_tree("mid", "gauge")["children"][0])
        analysis = self._analysis(tree)
        assert analysis["evidence"] == ["flow", "gauge"]

    def test_single_stage_is_still_a_text_wrapper(self):
        """文字包装反例：一根箭头加一个阶段不构成关系，仍算文字幕。"""
        analysis = self._analysis(_relation_tree("mid", "flow", 1))
        assert analysis["structuralClass"] == "text"
        assert analysis["evidence"] == []
        assert analysis["isTextScene"] is True

    def test_stages_without_content_do_not_count(self):
        """两个子节点里只有一个承载内容时，仍然不构成关系。"""
        tree = _relation_tree("mid", "timeline", 1)
        tree["children"].append({"id": "mid-deco", "type": "shape", "shape": "line", "state": "muted"})
        assert self._analysis(tree)["evidence"] == []

    def test_declaration_conflict_is_reported_for_wrappers_only(self):
        wrapper = _scene("mid", mode="process", tree=_relation_tree("mid", "flow", 1), data={"text": "中层原语", "ratio": 42})
        wrapper["motions"] = []
        findings = vn.analyze(_storyboard(wrapper))["findings"]
        assert any(item["rule"] == "declaration-structure-conflict" for item in findings)

        real = _scene("mid", mode="process", tree=_relation_tree("mid", "flow", 2), data={"text": "中层原语", "ratio": 42})
        real["motions"] = []
        findings = vn.analyze(_storyboard(real))["findings"]
        assert not any(item["rule"] == "declaration-structure-conflict" for item in findings)

    def test_rule_version_bumped(self):
        assert vn.RULE_VERSION == 2
