"""五种选择，五种人生：保护连续人生世界、尺度事件与输出边界。"""
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
WORLD = (EXAMPLE / "scenes/world.tsx").read_text(encoding="utf-8")
MATH = (EXAMPLE / "scenes/lifeMath.ts").read_text(encoding="utf-8")
DESIGN = (EXAMPLE / "DESIGN.md").read_text(encoding="utf-8")


def test_silent_single_scene_has_the_declared_65_second_budget() -> None:
    assert STORYBOARD["input"]["kind"] == "topic"
    assert not STORYBOARD.get("soundtrack")
    assert len(STORYBOARD["scenes"]) == 1
    assert SCENE["id"] == "life-world"
    assert STORYBOARD["targetSeconds"] == 65
    assert SCENE["durationFrames"] == 1950
    assert SCENE["narrationSegments"] == []
    assert (STORYBOARD["width"], STORYBOARD["height"], STORYBOARD["fps"]) == (1920, 1080, 30)


def test_seven_acts_tile_the_film_and_match_the_shots() -> None:
    acts = re.findall(r"\{id: '([a-z-]+)', start: (\d+), end: (\d+)\}", MATH)
    assert [item[0] for item in acts] == [
        "opening", "city", "industry", "partner", "investment", "learning", "finale"]
    assert int(acts[0][1]) == 0 and int(acts[-1][2]) == 65
    assert all(int(a[2]) == int(b[1]) for a, b in zip(acts, acts[1:]))
    shots = PROPS["shots"]
    assert [shot["id"] for shot in shots] == [item[0] for item in acts]
    assert all(shot["startFrame"] == int(act[1]) * 30 and shot["endFrame"] == int(act[2]) * 30
               for shot, act in zip(shots, acts))


def test_copy_only_names_the_variables_and_the_final_claim() -> None:
    copy = PROPS["copy"]
    assert [item["id"] for item in copy] == [
        "title", "city", "industry", "partner", "investment", "learning", "finale"]
    assert [item["text"] for item in copy] == [
        "人生真正拉开差距的，\n往往是几个重要选择。",
        "城市", "行业", "伴侣", "投资", "学习",
        "人生的差距，往往是一次次选择慢慢拉开的。",
    ]
    assert PROPS["labels"]["choices"] == ["城市", "行业", "伴侣", "投资", "学习"]
    visible = "\n".join(item["text"] for item in copy) + WORLD + SOURCE
    for token in ("保证收益", "必涨", "稳赚", "唯一成功路径", "行业排名", "决定机会密度"):
        assert token not in visible


def test_implementation_is_one_deterministic_continuous_scene() -> None:
    assert "from 'm2v/code-scene'" in SOURCE
    assert "<Canvas" in SOURCE and "<LifeWorld t={t}" in SOURCE
    for source in (SOURCE, WORLD, MATH):
        for forbidden in ("window.requestAnimationFrame", "Date.now", "Math.random",
                          "setInterval", "setTimeout"):
            assert forbidden not in source
    assert "pathUAt" in WORLD and "cameraAt" in WORLD
    assert "drawFrame" not in SOURCE + WORLD
    assert "AGE_MARKS" not in WORLD and "TREE_PATHS" not in WORLD
    assert "geometry.ts" not in SOURCE + WORLD and "render.ts" not in SOURCE + WORLD


def test_world_contains_the_five_mechanisms_and_a_final_map() -> None:
    for token in ("makeNetwork", "RISE", "PLUS_MAIN", "GROWTH_GEO", "unlockAt", "FAN_CURVES", "FAN_ARCS"):
        assert token in WORLD, token
    assert "open" in WORLD and "opacity" in WORLD
    assert "65" in MATH and "DURATION" in MATH
    assert "cameraAt" in MATH and "pathUAt" in MATH


def test_keyframe_gate_and_scale_rules_are_documented() -> None:
    for token in ("七张无文字关键帧", "去文字", "尺度阶梯", "城市网络", "行业地形",
                  "最终人生世界", "65 秒", "1950"):
        assert token in DESIGN, token
    assert "当前不渲染" not in DESIGN or "关键帧" in DESIGN


def test_old_scene_implementation_and_its_tests_are_retired() -> None:
    assert not (EXAMPLE / "scenes/geometry.ts").exists()
    assert not (EXAMPLE / "scenes/render.ts").exists()
    assert not (ROOT / "web/src/code-scene/five-life-geometry.test.ts").exists()
