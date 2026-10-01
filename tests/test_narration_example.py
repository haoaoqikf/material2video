"""端到端示例：分段口播 + 语义节拍（`examples/narration-beats/`）。

这个示例是「字幕、配音与画面共用同一批边界」的可运行参照：五幕覆盖
`flow`、`cycle`、`timeline`、`gauge`、`pictogram` 五个中层原语，每段口播都绑定
一条会改变状态或关系的 beat。同目录的 `article.md` 是抽象示例内容，不含真实文章。

反例在测试里就地构造、**不写入仓库**：把同一幕的 beat 全换成 `establish`/`highlight`
后，严格校验与 A3 闸门都必须拦下它——「依次出现」不是「一次推理」。

仓库里的 `examples/narration-beats/` 仍是 v3（尚未改编到 v4），而执行入口只接受
v4，因此「有声路径共用同一批边界」的检查改由 `conftest` 的 v4 夹具在 `tmp_path`
里驱动，见 `test_subtitle_boundaries_match_beats_with_media`。
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from a2v import animation_review as ar
from a2v import storyboard as sb

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "narration-beats" / "storyboard.json"
DOC = ROOT / ".agents" / "skills" / "article2video" / "references" / "article-to-storyboard.md"


def _example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _messages(report: sb.Report) -> str:
    return "\n".join(issue.format() for issue in report.issues)


@pytest.fixture(scope="module")
def example() -> dict:
    return _example()


class TestExample:
    def test_example_is_a_repo_file(self):
        assert EXAMPLE.is_file(), "端到端示例必须留在仓库内（examples/ 不入 .gitignore）"

    def test_strict_validation_passes(self, example):
        report = sb.validate(example, strict=True)
        assert report.errors == [], _messages(report)

    def test_covers_all_five_midlevel_primitives(self, example):
        used = set()

        def walk(node):
            if not isinstance(node, dict):
                return
            used.add(node.get("type"))
            for child in node.get("children") or []:
                walk(child)

        for scene in example["scenes"]:
            walk(scene.get("sceneTree"))
        assert {"flow", "cycle", "timeline", "gauge", "pictogram"} <= used

    def test_every_scene_uses_segmented_narration(self, example):
        for scene in example["scenes"]:
            assert scene.get("narrationSegments"), f"{scene['id']} 应声明分段口播"
            assert "narration" not in scene, f"{scene['id']} 不能同时声明字符串口播"

    def test_narration_is_the_concatenation_of_segments(self, example):
        # 完整口播只存在于各段，不另存一份：拼接结果必须逐段可还原。
        for scene in example["scenes"]:
            joined = "".join(segment["text"] for segment in scene["narrationSegments"])
            assert joined
            for segment in scene["narrationSegments"]:
                assert segment["text"] in joined

    def test_machine_gates_pass_without_media(self, example):
        gates = ar.review_gates(ar.analyze(example))
        assert ar.gate_issues(gates) == []
        assert gates["a1"]["status"] == "pass"
        assert gates["a2"]["status"] == "pass"
        assert gates["a3"]["status"] == "pass"
        assert gates["a5"]["status"] == "pass"
        assert gates["a7"]["status"] == "pass"
        assert gates["a8"]["status"] == "pass"
        # 无声预览没有字幕边界可核对——跳过，而不是通过。
        assert gates["a4"]["status"] == "skipped"

    def test_decorations_are_reported_for_human_adjudication(self, example):
        names = {item["id"] for item in ar.decorations(ar.analyze(example))}
        # 标题入场与装饰光晕不服务于任何 beat，必须交给 A6 人工裁决。
        assert "claim:claim-halo" in names
        assert any(name.endswith(":stages-title") for name in names)

    def test_subtitle_boundaries_match_beats_with_media(self, valid_script_v4, tmp_path, speech):
        """有声路径：字幕 cue 与画面 beat 必须落在同一批边界上（A4）。

        仓库里的 ``examples/narration-beats/`` 仍是 v3，而入口只接受 v4，因此这里
        在 tmp_path 里用 v4 夹具驱动同一类检查：把 cue 归回各段口播得到词边界区间，
        再按 fps 解析成帧区间，必须与媒体清单里的画面 beat 对上（判据与 A4 闸门
        一致，含 ``SYNC_TOLERANCE_FRAMES`` 的取整容差）。
        """
        from a2v import beats as beat_mod
        from a2v import media as media_mod
        from a2v import prepare as prep

        source = tmp_path / "storyboard.json"
        source.write_text(json.dumps(valid_script_v4, ensure_ascii=False), encoding="utf-8")
        path = prep.prepare(source, tmp_path / "media")
        media = media_mod.load_media(path, source)
        board = media.data["source"]
        fps = board["fps"]
        # 每段口播都在标点处断开，因此每条 stage 至少产出一条 cue。
        assert len(media.data["cues"]) >= len(board["stages"])
        cursor = 0
        for stage, resolved in zip(board["stages"], media.data["stages"]):
            frames = resolved["durationInFrames"]
            cues = ar.scene_cues(media.data["cues"], cursor, frames, fps)
            assert cues, f"{stage['id']} 必须有自己的字幕 cue"
            texts = [segment["text"] for segment in stage["narrationSegments"]]
            windows = ar._cue_windows("".join(texts), texts, cues)
            assert windows is not None, f"{stage['id']} 的 cue 与口播段切法不一致"
            from_cues = beat_mod.resolve_from_windows(stage, windows, fps, frames)
            actual = [beat for beat in media.data["resolvedBeats"] if beat["stageId"] == stage["id"]]
            assert len(from_cues.beats) == len(actual), f"{stage['id']} 的字幕与 beat 数量不一致"
            for from_cue, beat in zip(from_cues.beats, actual):
                for expected, got in ((from_cue.start_frame, beat["startFrame"] - cursor),
                                      (from_cue.end_frame, beat["endFrame"] - cursor)):
                    assert abs(expected - got) <= ar.SYNC_TOLERANCE_FRAMES, (
                        f"{stage['id']} 的字幕边界 {expected} 与画面 beat 边界 {got} 不一致"
                    )
            cursor += frames

    def test_reference_doc_links_the_example(self):
        text = DOC.read_text(encoding="utf-8")
        assert "examples/narration-beats/" in text


class TestTextCardCounterexample:
    """全中性动作的文字卡片：严格校验与 A3 都要拦下，且不落盘。"""

    @staticmethod
    def _counterexample() -> dict:
        board = {
            "version": 3,
            "schemaVersion": 3,
            "directingVersion": 1,
            "directingBrief": {"thesis": "卡片论证", "audienceShift": "看见顺序", "emotionalArc": ["观察", "确认"], "visualMotif": "卡片", "stylePack": "editorial", "avoid": []},
            "visual": {"theme": "dark", "preset": "keynote"},
            "fps": 30,
            "width": 1080,
            "height": 1920,
            "title": "中性动作反例",
            "visualDirection": {
                "motif": "卡片",
                "compositionBias": "centered",
                "density": "balanced",
                "rhythm": "steady",
                "avoid": [],
            },
            "scenes": [
                {
                    "id": "cards",
                    "type": "diagram",
                    "durationInFrames": 180,
                    "narrationSegments": [
                        {"id": "n1", "text": "先看第一张卡片。", "beatId": "b1"},
                        {"id": "n2", "text": "再看第二张卡片。", "beatId": "b2"},
                        {"id": "n3", "text": "最后把它们都强调一遍。", "beatId": "b3"},
                    ],
                    "beats": [
                        {"id": "b1", "action": "establish", "targets": ["card-a"], "meaning": "让第一张卡片出现"},
                        {"id": "b2", "action": "establish", "targets": ["card-b"], "meaning": "让第二张卡片出现"},
                        {"id": "b3", "action": "highlight", "targets": ["card-c"], "meaning": "把第三张卡片提亮"},
                    ],
                    "data": {"title": "三张卡片", "items": ["第一项", "第二项", "第三项"]},
                    "visualIntent": {
                        "relation": "collection",
                        "focus": "shape",
                        "composition": "center",
                        "density": "balanced",
                        "tone": "neutral",
                        "mode": "process",
                        "claim": "三件事按顺序出现",
                        "showWithoutText": "三张卡片排成一列依次出现，位置说明顺序",
                        "primaryObject": "三张卡片表面",
                        "motionMeaning": "卡片依次入场",
                    },
                    "sceneTree": {
                        "id": "root",
                        "type": "flow",
                        "direction": "ttb",
                        "gap": "md",
                        "children": [
                            {
                                "id": f"card-{suffix}",
                                "type": "surface",
                                "children": [
                                    {
                                        "id": f"card-{suffix}-text",
                                        "type": "text",
                                        "contentRef": f"data.items[{index}]",
                                        "role": "body",
                                    }
                                ],
                            }
                            for index, suffix in enumerate("abc")
                        ],
                    },
                    "motions": [
                        {"target": f"card-{suffix}", "recipe": "rise", "beatId": f"b{index + 1}", "durationFrames": 20}
                        for index, suffix in enumerate("abc")
                    ],
                    "renderer": {"kind": "tree"},
                    "camera": {"shot": "wide", "composition": "center", "depth": "flat", "focus": "root", "segments": [{"beatId": "b1", "kind": "hold"}, {"beatId": "b2", "kind": "push-in"}, {"beatId": "b3", "kind": "settle"}]},
                }
            ],
        }
        return board

    def test_structure_alone_is_valid(self):
        # 反例的「结构」是合规的：原语、证据、分段都对得上。
        report = sb.validate(self._counterexample(), strict=True)
        problems = [issue for issue in report.issues if issue.path.endswith(".beats")]
        assert problems, "严格校验必须报出节拍问题"
        assert all("改变对象状态或关系" in issue.message for issue in problems)

    def test_strict_validation_rejects_all_neutral_beats(self):
        report = sb.validate(self._counterexample(), strict=True)
        assert report.errors, "全中性动作必须在严格校验下失败"
        text = _messages(report)
        assert "至少一个 beat 要改变对象状态或关系" in text
        assert "establish" in text and "highlight" in text

    def test_a3_gate_fails_with_the_neutral_actions(self):
        gates = ar.review_gates(ar.analyze(self._counterexample()))
        assert gates["a3"]["status"] == "fail"
        issues = gates["a3"]["issues"]
        assert any("没有任何 beat 改变对象状态或关系" in issue for issue in issues)
        # A3 之外的门不必失败：问题只在「动作没有推进推理」这一条上。
        assert gates["a1"]["status"] == "pass"
        assert gates["a2"]["status"] == "pass"
        assert gates["a5"]["status"] == "pass"

    def test_one_change_action_is_enough_to_pass(self):
        board = copy.deepcopy(self._counterexample())
        board["scenes"][0]["beats"][1]["action"] = "transform"
        report = sb.validate(board, strict=True)
        # 单幕作品会另有一条「非文字模式不足 2 种」的预算错误，这里只看节拍质量。
        beat_issues = [issue for issue in report.issues if issue.path.endswith(".beats")]
        assert beat_issues == [], _messages(report)
        gates = ar.review_gates(ar.analyze(board))
        assert gates["a3"]["status"] == "pass"

    def test_counterexample_is_never_written_to_disk(self):
        # 反例只作为测试夹具存在：examples/ 里不得出现它，避免把退化写法当范例交付。
        assert not (ROOT / "examples" / "text-card-counterexample").exists()
        assert "中性动作反例" not in EXAMPLE.read_text(encoding="utf-8")
