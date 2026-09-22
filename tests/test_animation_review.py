"""动画论证评审 A1–A5、A7、A8 的机检口径（任务 4.1）。

八条闸门里七条可机检，一条（A6）由人或视觉模型裁决。这里固定机检部分的
行为：**结构**（节拍覆盖、含义声明、状态变化）、**时间**（字幕同步、结尾
停留、稳定结束）与**焦点**（单一焦点）。

判据全部来自分镜与解析时间轴，不起浏览器、不调用模型。
"""

from __future__ import annotations

import pytest

from a2v import animation_review as ar
from a2v import beats as beat_mod

FPS = 30

#: 一幕的帧区间：三条 beat，最后一条在第 96 帧完成，留 24 帧稳定阅读。
SPANS = (("b1", 0, 30), ("b2", 30, 60), ("b3", 60, 96))

SEGMENT_TEXTS = ("先看第一步。", "再看第二步。", "最后收束到结论。")


def _tree() -> dict:
    return {
        "id": "root",
        "type": "flow",
        "direction": "ltr",
        "children": [
            {"id": "flow-a", "type": "surface", "children": [
                {"id": "flow-a-text", "type": "text", "contentRef": "data.stepA", "role": "body"},
            ]},
            {"id": "flow-b", "type": "surface", "children": [
                {"id": "flow-b-text", "type": "text", "contentRef": "data.stepB", "role": "body"},
            ]},
        ],
    }


def _scene(
    scene_id: str = "scene-1",
    *,
    duration: int = 120,
    actions: tuple[str, ...] = ("establish", "transform", "highlight"),
    meanings: tuple[str, ...] = ("先交代起点", "接力到第二步", "收束到结论"),
    targets: tuple[tuple[str, ...], ...] = (("flow-a",), ("flow-b",), ("flow",)),
    texts: tuple[str, ...] = SEGMENT_TEXTS,
    spans=SPANS,
    motions: list[dict] | None = None,
    tree: dict | None = None,
    segments: bool = True,
    resolved: bool = False,
) -> dict:
    """一幕测试分镜。

    ``resolved`` 默认 False：源分镜**不带** ``resolvedBeats``（派生字段由媒体
    清单或有效分镜给出，校验器会拒绝源分镜里的它）。需要有声时间轴的用例
    打开它，再用 :func:`_media_scenes` 搬进媒体清单。
    """
    scene: dict = {
        "id": scene_id,
        "type": "process",
        "durationInFrames": duration,
        "data": {"stepA": "起点", "stepB": "下一步"},
        "visualIntent": {
            "relation": "sequence", "focus": "shape", "composition": "center",
            "density": "balanced", "tone": "neutral", "mode": "process",
            "claim": "两步推进", "showWithoutText": "方向连接与阶段强调",
            "primaryObject": "流程", "motionMeaning": "逐段推进",
        },
        "sceneTree": tree if tree is not None else _tree(),
        "motions": motions if motions is not None else [
            {"target": "flow", "recipe": "reveal", "startFrame": 0, "durationFrames": 24},
        ],
    }
    if segments:
        scene["narrationSegments"] = [
            {"id": f"n{index + 1}", "text": texts[index % len(texts)], "beatId": beat_id}
            for index, (beat_id, _, _) in enumerate(spans)
        ]
        scene["beats"] = [
            {
                "id": beat_id,
                "action": actions[index % len(actions)],
                "targets": list(targets[index % len(targets)]),
                "meaning": meanings[index % len(meanings)],
            }
            for index, (beat_id, _, _) in enumerate(spans)
        ]
        if resolved:
            scene["resolvedBeats"] = [
                {**scene["beats"][index], "startFrame": start, "endFrame": end}
                for index, (_, start, end) in enumerate(spans)
            ]
    return scene


def _storyboard(*scenes: dict) -> dict:
    return {
        "version": 2,
        "schemaVersion": 2,
        "fps": FPS,
        "width": 1080,
        "height": 1920,
        "title": "动画论证测试",
        "visualDirection": {"motif": "测试", "compositionBias": "mixed", "density": "balanced", "rhythm": "steady", "avoid": []},
        "scenes": list(scenes),
    }


def _media(scenes: list[dict], cues: list[dict] | None = None) -> dict:
    return {"version": 2, "scenes": scenes, "cues": cues if cues is not None else []}


def _gates(storyboard: dict, media: dict | None = None) -> dict:
    return ar.review_gates(ar.analyze(storyboard, media))


def _status(gates: dict, gate_id: str) -> str:
    return str((gates.get(gate_id.lower()) or {}).get("status"))


def _issues(gates: dict, gate_id: str) -> list[str]:
    return list((gates.get(gate_id.lower()) or {}).get("issues") or [])


# ---------------------------------------------------------------------------
# 基线：一条合规的幕要七条全过
# ---------------------------------------------------------------------------


class TestBaseline:
    def test_silent_storyboard_passes_the_machine_gates(self):
        gates = _gates(_storyboard(_scene()))
        assert _status(gates, "A1") == "pass"
        assert _status(gates, "A2") == "pass"
        assert _status(gates, "A3") == "pass"
        assert _status(gates, "A5") == "pass"
        assert _status(gates, "A7") == "pass"
        assert _status(gates, "A8") == "pass"
        assert not ar.gate_issues(gates)

    def test_silent_storyboard_skips_subtitle_sync(self):
        gates = _gates(_storyboard(_scene()))
        assert _status(gates, "A4") == "skipped"
        assert "无声" in str(gates["a4"]["detail"])

    def test_old_string_narration_is_skipped_not_passed(self):
        """旧字符串口播的幕：不适用就要如实写「跳过」，不能悄悄记成通过。"""
        scene = _scene(segments=False)
        scene["narration"] = "这是一段旧格式的口播。"
        gates = _gates(_storyboard(scene))
        for gate_id in ("A1", "A2", "A3", "A5", "A7", "A8"):
            assert _status(gates, gate_id) == "skipped", gate_id
        assert not ar.gate_issues(gates)

    def test_estimated_timeline_is_used_without_media(self):
        analysis = ar.analyze(_storyboard(_scene()))
        assert analysis["scenes"][0]["estimated"] is True
        assert analysis["scenes"][0]["resolved"][0]["startFrame"] == 0


# ---------------------------------------------------------------------------
# A1 节拍覆盖
# ---------------------------------------------------------------------------


class TestA1BeatCoverage:
    def test_beat_without_segment_fails(self):
        scene = _scene()
        scene["beats"].append({"id": "b4", "action": "connect", "targets": ["flow"], "meaning": "多余的 beat"})
        gates = _gates(_storyboard(scene))
        assert _status(gates, "A1") == "fail"
        assert any("没有被任何口播段引用" in issue for issue in _issues(gates, "A1"))

    def test_segment_without_beat_fails(self):
        scene = _scene()
        scene["narrationSegments"].append({"id": "n4", "text": "多出来的一段。", "beatId": "b9"})
        gates = _gates(_storyboard(scene))
        assert _status(gates, "A1") == "fail"
        assert any("b9" in issue for issue in _issues(gates, "A1"))

    def test_non_contiguous_reference_fails(self):
        """同一 beat 的两段被别的 beat 隔开：时间轴会倒退或重叠。

        这份时间轴只能来自被手改过的有效分镜——有声路径的解析器与 TS schema
        都拦住了它，A1 再拦一次是为了让「读进来的东西」也自证一致。
        """
        scene = _scene(spans=(("b1", 0, 20), ("b2", 20, 40), ("b1", 40, 60), ("b3", 60, 96)), resolved=True)
        gates = _gates(_storyboard(scene))
        assert _status(gates, "A1") == "fail"
        assert any("不连续" in issue for issue in _issues(gates, "A1"))

    def test_missing_resolved_interval_fails(self):
        """声明了三条 beat，媒体清单只解析出两条：覆盖不完整。"""
        scene = _scene(resolved=True)
        media_scene = {"id": scene["id"], "durationInFrames": scene["durationInFrames"],
                       "resolvedBeats": scene["resolvedBeats"][:2]}
        gates = _gates(_storyboard(scene), _media([media_scene], _cues_for()))
        assert _status(gates, "A1") == "fail"
        assert any("只解析出 2 条帧区间" in issue for issue in _issues(gates, "A1"))


# ---------------------------------------------------------------------------
# A2 含义声明
# ---------------------------------------------------------------------------


class TestA2Meaning:
    def test_meaning_cannot_be_blank(self):
        gates = _gates(_storyboard(_scene(meanings=("先交代起点", "   ", "收束到结论"))))
        assert _status(gates, "A2") == "fail"
        assert any("没有声明 meaning" in issue for issue in _issues(gates, "A2"))

    def test_meaning_cannot_restate_the_narration(self):
        gates = _gates(_storyboard(_scene(meanings=("先交代起点", "再看第二步。", "收束到结论"))))
        assert _status(gates, "A2") == "fail"
        assert any("复述" in issue for issue in _issues(gates, "A2"))

    def test_meaning_cannot_repeat_the_action_label(self):
        label = beat_mod.ACTION_LABELS["transform"]
        gates = _gates(_storyboard(_scene(meanings=("先交代起点", label, "收束到结论"))))
        assert _status(gates, "A2") == "fail"
        assert any("只重复了动作名" in issue for issue in _issues(gates, "A2"))


# ---------------------------------------------------------------------------
# A3 状态或关系变化
# ---------------------------------------------------------------------------


class TestA3StateChange:
    def test_all_neutral_actions_fail(self):
        """场景的规格场景：多个元素入场，但没有任何 beat 改变状态或关系。"""
        gates = _gates(_storyboard(_scene(actions=("establish", "highlight", "highlight"))))
        assert _status(gates, "A3") == "fail"
        assert any("没有任何 beat 改变对象状态或关系" in issue for issue in _issues(gates, "A3"))

    def test_single_beat_fails(self):
        scene = _scene(spans=(("b1", 0, 30),), actions=("transform",), meanings=("接力",), targets=(("flow-a",),))
        scene["narrationSegments"] = scene["narrationSegments"][:1]
        gates = _gates(_storyboard(scene))
        assert _status(gates, "A3") == "fail"
        assert any("至少需要 2 条" in issue for issue in _issues(gates, "A3"))

    def test_text_scene_is_exempt(self):
        """文字幕不靠图形解释论点，A3 不适用（它的预算由 V 系列管）。"""
        tree = {
            "id": "root", "type": "stack",
            "children": [{"id": "copy", "type": "text", "contentRef": "data.text", "role": "headline"}],
        }
        scene = _scene(tree=tree, actions=("establish", "highlight", "highlight"))
        scene["data"] = {"text": "一句话论点"}
        gates = _gates(_storyboard(scene))
        assert _status(gates, "A3") == "skipped"

    def test_change_action_passes(self):
        gates = _gates(_storyboard(_scene(actions=("establish", "accumulate", "highlight"))))
        assert _status(gates, "A3") == "pass"


# ---------------------------------------------------------------------------
# A4 字幕同步
# ---------------------------------------------------------------------------


def _media_scenes(*scenes: dict) -> list[dict]:
    """媒体清单里的逐幕条目：派生时长 + 已解析节拍（来自 ``resolved=True`` 的分镜）。"""
    return [
        {
            "id": scene["id"],
            "durationInFrames": scene["durationInFrames"],
            "resolvedBeats": scene.get("resolvedBeats") or [],
        }
        for scene in scenes
    ]


def _cues_for(spans=SPANS) -> list[dict]:
    """按帧区间造出与之一致的字幕 cue（秒）。"""
    return [
        {"text": text, "start": start / FPS, "end": end / FPS}
        for (_, start, end), text in zip(spans, SEGMENT_TEXTS)
    ]


class TestA4Sync:
    def test_matching_cues_pass(self):
        scene = _scene(resolved=True)
        gates = _gates(_storyboard(scene), _media(_media_scenes(scene), _cues_for()))
        assert _status(gates, "A4") == "pass"

    def test_shifted_cues_fail(self):
        scene = _scene(resolved=True)
        cues = _cues_for()
        cues[1]["start"] += 0.5  # 第二段字幕晚了半秒
        gates = _gates(_storyboard(scene), _media(_media_scenes(scene), cues))
        assert _status(gates, "A4") == "fail"
        assert any("相差超过" in issue for issue in _issues(gates, "A4"))

    def test_cue_crossing_a_segment_boundary_fails(self):
        """一段口播切在句子中间时，cue 会跨过段边界：两者没有共用边界。"""
        scene = _scene(resolved=True)
        cues = [
            {"text": "先看第一步。再看第二步。", "start": 0.0, "end": 2.0},
            {"text": "最后收束到结论。", "start": 2.0, "end": 3.2},
        ]
        gates = _gates(_storyboard(scene), _media(_media_scenes(scene), cues))
        assert _status(gates, "A4") == "fail"
        assert any("切法不一致" in issue for issue in _issues(gates, "A4"))

    def test_second_scene_cues_are_measured_in_scene_time(self):
        """整片 cue 必须按幕切开再换算：否则第二幕会被拿去和第一幕比。"""
        first, second = _scene("scene-1", resolved=True), _scene("scene-2", resolved=True)
        cues = _cues_for()
        offset = first["durationInFrames"] / FPS
        cues += [{**cue, "start": cue["start"] + offset, "end": cue["end"] + offset} for cue in _cues_for()]
        gates = _gates(_storyboard(first, second), _media(_media_scenes(first, second), cues))
        assert _status(gates, "A4") == "pass"

    def test_estimated_timeline_with_media_fails(self):
        """有媒体却没有解析结果：画面按估算走、字幕按真实词边界走。"""
        scene = _scene()
        media_scene = {"id": scene["id"], "durationInFrames": scene["durationInFrames"]}
        gates = _gates(_storyboard(scene), _media([media_scene], _cues_for()))
        assert _status(gates, "A4") == "fail"
        assert any("无声估算" in issue for issue in _issues(gates, "A4"))

    def test_media_without_segmented_scenes_skips(self):
        scene = _scene(segments=False)
        scene["narration"] = "旧格式口播。"
        gates = _gates(_storyboard(scene), _media([{"id": scene["id"], "durationInFrames": 120}], _cues_for()))
        assert _status(gates, "A4") == "skipped"

    def test_tts_extended_scene_is_measured_against_the_derived_duration(self):
        """场景被 TTS 拉长后，字幕区间必须按**派生**时长解析。

        回归背景：源分镜声明 120 帧，配音把它拉到 150 帧；若拿声明时长去
        解析，合法的 beat 区间会被报成「超出场景」，A4 在真实配音上误报失败。
        """
        spans = (("b1", 0, 30), ("b2", 30, 60), ("b3", 60, 108))
        scene = _scene(spans=spans, resolved=True)  # 源分镜 120 帧
        media_scene = {
            "id": scene["id"],
            "durationInFrames": 150,
            "resolvedBeats": scene["resolvedBeats"],
        }
        gates = _gates(_storyboard(scene), _media([media_scene], _cues_for(spans)))
        assert _status(gates, "A4") == "pass", _issues(gates, "A4")

    def test_cues_beyond_the_declared_duration_still_fail_when_not_extended(self):
        """没有派生时长时，越界字幕照旧报错——回归不能把这条检查一起放宽。"""
        spans = (("b1", 0, 30), ("b2", 30, 60), ("b3", 60, 108))
        scene = _scene(spans=spans, resolved=True)  # 声明 120 帧，最后一条到 108 帧
        late = _cues_for(spans)
        late[-1]["end"] = 4.4  # 132 帧 > 120
        gates = _gates(_storyboard(scene), _media(_media_scenes(scene), late))
        assert _status(gates, "A4") == "fail"
        assert any("超出场景" in issue for issue in _issues(gates, "A4"))


# ---------------------------------------------------------------------------
# A5 结尾停留
# ---------------------------------------------------------------------------


class TestA5Hold:
    def test_tight_ending_fails(self):
        """有声时间轴由真实词边界决定，声明时长留不够就真的不够。"""
        gates = _gates(_storyboard(_scene(spans=(("b1", 0, 30), ("b2", 30, 60), ("b3", 60, 115)), resolved=True)))
        assert _status(gates, "A5") == "fail"
        assert any("稳定阅读" in issue for issue in _issues(gates, "A5"))
        assert gates["a5"]["scenes"][0]["remainingFrames"] == 5

    def test_exactly_twelve_frames_passes(self):
        gates = _gates(_storyboard(_scene(spans=(("b1", 0, 30), ("b2", 30, 60), ("b3", 60, 108)), resolved=True)))
        assert _status(gates, "A5") == "pass"

    def test_silent_estimation_always_leaves_the_tail(self):
        """无声估算按同一下限切预算，因此自己不会报余量不足。"""
        gates = _gates(_storyboard(_scene(spans=(("b1", 0, 30), ("b2", 30, 60), ("b3", 60, 115)))))
        assert _status(gates, "A5") == "pass"

    def test_media_extension_raises_the_budget(self):
        """派生时长把场景拉长后，同一份 beat 区间就留够了阅读时间。"""
        spans = (("b1", 0, 30), ("b2", 30, 60), ("b3", 60, 108))
        scene = _scene(spans=spans, resolved=True)
        media_scene = {"id": scene["id"], "durationInFrames": 150, "resolvedBeats": scene["resolvedBeats"]}
        gates = _gates(_storyboard(scene), _media([media_scene], _cues_for(spans)))
        assert _status(gates, "A5") == "pass"


# ---------------------------------------------------------------------------
# A7 单一焦点
# ---------------------------------------------------------------------------


class TestA7Focus:
    def test_two_declared_focus_nodes_fail(self):
        tree = {
            "id": "root", "type": "stack",
            "children": [
                {"id": "card-a", "type": "surface", "state": "focus", "children": [
                    {"id": "card-a-text", "type": "text", "contentRef": "data.stepA", "role": "body"},
                ]},
                {"id": "card-b", "type": "surface", "state": "focus", "children": [
                    {"id": "card-b-text", "type": "text", "contentRef": "data.stepB", "role": "body"},
                ]},
            ],
        }
        scene = _scene(tree=tree, targets=(("card-a",), ("card-b",), ("card-a",)))
        gates = _gates(_storyboard(scene))
        assert _status(gates, "A7") == "fail"
        assert any("个焦点" in issue for issue in _issues(gates, "A7"))

    def test_two_containers_active_at_once_fail(self):
        """两个关系容器同时点亮当前阶段，等于同时给两处打光。"""
        tree = {
            "id": "root", "type": "column",
            "children": [
                {"id": "flow", "type": "flow", "direction": "ltr", "children": [
                    {"id": "flow-a", "type": "surface", "children": [
                        {"id": "flow-a-text", "type": "text", "contentRef": "data.stepA", "role": "body"}]},
                    {"id": "flow-b", "type": "surface", "children": [
                        {"id": "flow-b-text", "type": "text", "contentRef": "data.stepB", "role": "body"}]},
                ]},
                {"id": "timeline", "type": "timeline", "direction": "ltr", "children": [
                    {"id": "tl-a", "type": "surface", "children": [
                        {"id": "tl-a-text", "type": "text", "contentRef": "data.stepA", "role": "body"}]},
                    {"id": "tl-b", "type": "surface", "children": [
                        {"id": "tl-b-text", "type": "text", "contentRef": "data.stepB", "role": "body"}]},
                ]},
            ],
        }
        scene = _scene(tree=tree, targets=(("flow-a", "tl-a"), ("flow-b",), ("flow",)))
        gates = _gates(_storyboard(scene))
        assert _status(gates, "A7") == "fail"

    def test_one_stage_at_a_time_passes(self):
        gates = _gates(_storyboard(_scene()))
        assert _status(gates, "A7") == "pass"

    def test_declared_focus_plus_active_stage_fails(self):
        tree = _tree()
        tree["children"][0]["state"] = "focus"
        scene = _scene(tree=tree)
        gates = _gates(_storyboard(scene))
        assert _status(gates, "A7") == "fail"


# ---------------------------------------------------------------------------
# A8 稳定结束
# ---------------------------------------------------------------------------


class TestA8StableEnding:
    def test_motion_running_into_the_ending_fails(self):
        scene = _scene(motions=[{"target": "flow", "recipe": "reveal", "startFrame": 100, "durationFrames": 24}])
        gates = _gates(_storyboard(scene))
        assert _status(gates, "A8") == "fail"
        assert any("距幕尾不足" in issue for issue in _issues(gates, "A8"))

    def test_motion_ending_at_the_deadline_passes(self):
        scene = _scene(motions=[{"target": "flow", "recipe": "reveal", "startFrame": 84, "durationFrames": 24}])
        gates = _gates(_storyboard(scene))
        assert _status(gates, "A8") == "pass"

    def test_motion_without_duration_counts_as_one_frame(self):
        scene = _scene(motions=[{"target": "flow", "recipe": "fade", "startFrame": 119}])
        gates = _gates(_storyboard(scene))
        assert _status(gates, "A8") == "fail"


# ---------------------------------------------------------------------------
# A6 装饰动画人工裁决
# ---------------------------------------------------------------------------

#: 不服务于任何 beat 的配方：纯装饰，需要人工裁决。
DECORATIVE_MOTIONS = [
    {"target": "flow", "recipe": "reveal", "startFrame": 0, "durationFrames": 24},
    {"target": "flow-a-text", "recipe": "fade", "startFrame": 24, "durationFrames": 12},
]


class TestA6HumanAdjudication:
    def _analysis(self, motions: list[dict] | None = None) -> dict:
        return ar.analyze(_storyboard(_scene(motions=motions if motions is not None else DECORATIVE_MOTIONS)))

    def test_decorations_are_the_motions_outside_every_beat(self):
        assert [item["id"] for item in ar.decorations(self._analysis())] == ["scene-1:flow-a-text"]

    def test_missing_conclusion_is_pending_and_not_publishable(self, tmp_path):
        result = ar.review_a6(tmp_path / "review.md", self._analysis())
        assert result["status"] == "待评审"
        assert result["score"] is None
        assert result["publishable"] is False

    def test_rubric_row_and_rulings_pass(self, tmp_path):
        path = tmp_path / "review.md"
        path.write_text(
            "| 项 | 分 | 依据 |\n| --- | --- | --- |\n| 动效服务 | 5 | 入场动效都在引导视线 |\n\n"
            "### A6 候选裁决\n- scene-1:flow-a-text：节奏需要，保留\n",
            encoding="utf-8",
        )
        result = ar.review_a6(path, self._analysis())
        assert result["status"] == "通过"
        assert result["score"] == 5
        assert result["publishable"] is True

    def test_dedicated_decoration_row_is_accepted(self, tmp_path):
        path = tmp_path / "review.md"
        path.write_text("| 装饰动画 | 4 |\n\n### 候选裁决\n- scene-1:flow-a-text：保留\n", encoding="utf-8")
        result = ar.review_a6(path, self._analysis())
        assert result["score"] == 4
        assert result["status"] == "通过"

    def test_inline_score_is_accepted(self, tmp_path):
        path = tmp_path / "review.md"
        path.write_text("## A6 装饰动画\n评分：4/5\n", encoding="utf-8")
        result = ar.review_a6(path, self._analysis())
        assert result["score"] == 4
        assert result["status"] == "候选未裁决"

    def test_low_score_fails(self, tmp_path):
        path = tmp_path / "review.md"
        path.write_text("| 装饰动画 | 2 |\n", encoding="utf-8")
        result = ar.review_a6(path, self._analysis())
        assert result["status"] == "不通过"
        assert result["publishable"] is False

    def test_unresolved_candidate_blocks_publishing(self, tmp_path):
        path = tmp_path / "review.md"
        path.write_text("| 装饰动画 | 5 |\n\n### 候选裁决\n- scene-9:other：与这一幕无关\n", encoding="utf-8")
        result = ar.review_a6(path, self._analysis())
        assert result["status"] == "候选未裁决"
        assert result["unresolvedCandidates"] == ["scene-1:flow-a-text"]
        assert result["publishable"] is False

    def test_no_candidates_with_score_passes(self, tmp_path):
        path = tmp_path / "review.md"
        path.write_text("| 装饰动画 | 5 |\n", encoding="utf-8")
        analysis = ar.analyze(_storyboard(_scene()))  # 配方全部服务于 beat
        result = ar.review_a6(path, analysis)
        assert result["candidates"] == []
        assert result["status"] == "通过"

    def test_a6_is_not_wired_into_the_error_count(self, tmp_path):
        gates = _gates(_storyboard(_scene(motions=DECORATIVE_MOTIONS)))
        gates["a6"] = ar.review_a6(tmp_path / "review.md", ar.analyze(_storyboard(_scene(motions=DECORATIVE_MOTIONS))))
        assert not ar.gate_issues(gates), "人工结论缺失不能伪造成脚本错误"


# ---------------------------------------------------------------------------
# 报告结构
# ---------------------------------------------------------------------------


class TestReportShape:
    def test_gate_ids_and_titles_are_fixed(self):
        gates = _gates(_storyboard(_scene()))
        assert gates["ruleVersion"] == ar.RULE_VERSION
        assert [gates[key]["id"] for key in ("a1", "a2", "a3", "a4", "a5", "a7", "a8")] == [
            "A1", "A2", "A3", "A4", "A5", "A7", "A8",
        ]
        assert [gates[key]["title"] for key in ("a1", "a3", "a8")] == ["节拍覆盖", "状态或关系变化", "稳定结束"]

    def test_a6_is_not_machine_checked_here(self):
        gates = _gates(_storyboard(_scene()))
        assert "a6" not in gates
        assert "A6" not in ar.MACHINE_GATES
        assert dict(ar.A_GATES)["A6"] == "装饰动画人工裁决"

    def test_gate_issues_only_reports_failures(self):
        gates = _gates(_storyboard(_scene(actions=("establish", "highlight", "highlight"))))
        issues = ar.gate_issues(gates)
        assert [where for where, _ in issues] == ["动画论证 A3"]

    def test_analysis_is_json_serializable(self):
        import json

        scene = _scene(resolved=True)
        analysis = ar.analyze(_storyboard(scene), _media(_media_scenes(scene), _cues_for()))
        json.dumps(analysis, ensure_ascii=False)
        json.dumps(ar.review_gates(analysis), ensure_ascii=False)

    def test_stable_reading_frames_shared_with_beats(self):
        assert ar.STABLE_READING_FRAMES == beat_mod.STABLE_READING_FRAMES == 12

    def test_empty_storyboard_skips_everything(self):
        gates = _gates(_storyboard())
        for gate_id in ar.MACHINE_GATES:
            assert _status(gates, gate_id) == "skipped"
        assert not ar.gate_issues(gates)


# ---------------------------------------------------------------------------
# 接入评审入口：机检失败要进错误数，人工结论要进 JSON 与终端
# ---------------------------------------------------------------------------


class TestReviewWiring:
    def _payload(self, tmp_path, storyboard: dict, media: dict | None = None) -> tuple[dict, object]:
        import json

        from a2v import cli
        from a2v.storyboard import Report

        path = tmp_path / "storyboard.json"
        path.write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
        combined = Report()

        class _Media:
            data = media

        result = cli._animation_review_payload(path, _Media() if media is not None else None, tmp_path, combined)
        return result, combined

    def test_passing_storyboard_adds_no_errors(self, tmp_path):
        result, combined = self._payload(tmp_path, _storyboard(_scene()))
        assert combined.ok
        assert result["a1"]["status"] == "pass"
        assert result["a6"]["status"] == "待评审"

    def test_machine_failure_enters_the_error_list(self, tmp_path):
        result, combined = self._payload(tmp_path, _storyboard(_scene(actions=("establish", "highlight", "highlight"))))
        assert not combined.ok
        assert result["a3"]["status"] == "fail"
        assert any("动画论证 A3" == issue.path for issue in combined.errors)

    def test_a6_is_reported_but_never_an_error(self, tmp_path):
        result, combined = self._payload(tmp_path, _storyboard(_scene()))
        assert result["a6"]["publishable"] is False
        assert not any("A6" in issue.path for issue in combined.issues)

    def test_terminal_summary_lists_every_gate(self, tmp_path):
        from a2v import cli

        result, _ = self._payload(tmp_path, _storyboard(_scene()))
        lines = "\n".join(cli._animation_review_lines(result))
        for gate_id in ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"):
            assert gate_id in lines
        assert "可发布=否" in lines

    def test_summary_is_empty_without_the_payload(self):
        from a2v import cli

        assert cli._animation_review_lines(None) == []
