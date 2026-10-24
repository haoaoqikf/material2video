"""五种选择剪纸短片：保护30秒画面、文案与声音预算。"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/five-life-choices"
STORYBOARD = json.loads((EXAMPLE / "storyboard.json").read_text(encoding="utf-8"))
SCENE = STORYBOARD["scenes"][0]
PROPS = SCENE["content"]["props"]
SOURCE = (EXAMPLE / "scenes/life.tsx").read_text(encoding="utf-8")
LEARNING = (EXAMPLE / "scenes/learningWindow.tsx").read_text(encoding="utf-8")
MATH = (EXAMPLE / "scenes/lifeMath.ts").read_text(encoding="utf-8")
DESIGN = (EXAMPLE / "DESIGN.md").read_text(encoding="utf-8")


def test_paper_cut_film_has_900_frames_and_three_action_sounds() -> None:
    assert STORYBOARD["input"]["kind"] == "topic"
    assert len(STORYBOARD["scenes"]) == 1 and SCENE["id"] == "life-world"
    assert STORYBOARD["targetSeconds"] == 30 and SCENE["durationFrames"] == 900
    assert SCENE["narrationSegments"] == []
    assert (STORYBOARD["width"], STORYBOARD["height"], STORYBOARD["fps"]) == (1920, 1080, 30)
    soundtrack = STORYBOARD["soundtrack"]
    assert soundtrack["music"]["sourceRef"] == "assets/sound/score.wav"
    assert len(soundtrack["effects"]) == 3
    assert [item["sourceRef"] for item in soundtrack["effects"]] == [
        "assets/sound/door.wav", "assets/sound/bridge.wav", "assets/sound/page.wav"]
    source_record = json.loads((EXAMPLE / "assets/sound/sources.json").read_text(encoding="utf-8"))
    assert source_record["schemaVersion"] == 1
    records = {item["path"]: item for item in source_record["assets"]}
    paths = [soundtrack["music"]["sourceRef"], *(item["sourceRef"] for item in soundtrack["effects"])]
    assert set(paths) == {f"assets/sound/{path}" for path in records}
    assert {item["id"] for item in records.values()} == {
        "score", "door-opening", "bridge-join", "page-turn"}
    assert all(item["sampleRateHz"] == 24000 and item["channels"] == 1 for item in records.values())
    assert records["score.wav"]["durationSeconds"] == 30
    assert all(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) for item in records.values())


def test_seven_acts_tile_the_film_and_match_keyframe_windows() -> None:
    acts = re.findall(r"\{id: '([a-z-]+)', start: (\d+), end: (\d+)\}", MATH)
    ids = ["opening", "city", "industry", "partner", "investment", "learning", "finale"]
    assert [item[0] for item in acts] == ids
    assert int(acts[0][1]) == 0 and int(acts[-1][2]) == 30
    assert all(int(a[2]) == int(b[1]) for a, b in zip(acts, acts[1:]))
    shots = PROPS["shots"]
    assert [shot["id"] for shot in shots] == ids
    assert all(shot["startFrame"] == int(act[1]) * 30 and shot["endFrame"] == int(act[2]) * 30
               for shot, act in zip(shots, acts))


def test_copy_order_is_concise_and_five_choices_are_preserved() -> None:
    copy = PROPS["copy"]
    assert [item["id"] for item in copy] == [
        "opening", "city", "industry", "partner", "investment", "learning", "finale"]
    assert [item["text"] for item in copy] == [
        "同样的起点", "城市，改变机会", "行业，改变速度", "伴侣，影响方向",
        "投资，积累未来", "学习，打开可能", "每次选择，都在塑造以后"]
    assert PROPS["labels"]["choices"] == ["城市", "行业", "伴侣", "投资", "学习"]
    visible = "\n".join(item["text"] for item in copy) + SOURCE + LEARNING
    for token in ("保证收益", "必涨", "稳赚", "唯一成功路径", "行业排名"):
        assert token not in visible


def test_scene_is_deterministic_code_and_learning_window_has_a_clear_page_path() -> None:
    assert "useSceneContext" in SOURCE and "elapsedSeconds" in SOURCE
    assert "<svg" in SOURCE and "<Canvas" not in SOURCE
    assert "LearningWindow" in SOURCE and "clipPath" in LEARNING
    for source in (SOURCE, LEARNING, MATH):
        for forbidden in ("window.requestAnimationFrame", "Date.now", "Math.random", "setInterval", "setTimeout"):
            assert forbidden not in source


def test_keyframe_and_phone_readability_gate_is_documented() -> None:
    for token in ("七段", "30秒", "900帧", "393", "静帧", "盲审"):
        assert token in DESIGN
    assert "当前不渲染" not in DESIGN or "关键帧" in DESIGN
