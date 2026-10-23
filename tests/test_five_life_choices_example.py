"""人生五选择示例：七幕横屏时间轴、年龄刻度、确定性画面与示意边界。"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/five-life-choices"
STORYBOARD = json.loads((EXAMPLE / "storyboard.json").read_text(encoding="utf-8"))
SCENE = STORYBOARD["scenes"][0]
PROPS = SCENE["content"]["props"]
COPY = PROPS["copy"]
LABELS = PROPS["labels"]
SHOTS = PROPS["shots"]
SOURCE = (EXAMPLE / "scenes/life.tsx").read_text(encoding="utf-8")
RENDER = (EXAMPLE / "scenes/render.ts").read_text(encoding="utf-8")
GEOMETRY = (EXAMPLE / "scenes/geometry.ts").read_text(encoding="utf-8")
DESIGN = (EXAMPLE / "DESIGN.md").read_text(encoding="utf-8")
README = (EXAMPLE / "README.md").read_text(encoding="utf-8")


def _acts() -> list[tuple[str, float, float]]:
    return [(name, float(start), float(end)) for name, start, end in re.findall(
        r"\{id: [\"']([a-z]+)[\"'], start: ([\d.]+), end: ([\d.]+)\}", GEOMETRY)]


def _copy_texts() -> list[str]:
    return [item["text"] for item in COPY]


def test_silent_single_scene_with_an_explicit_frame_budget() -> None:
    assert STORYBOARD["input"]["kind"] == "topic"
    assert not STORYBOARD.get("soundtrack")
    assert len(STORYBOARD["scenes"]) == 1
    assert SCENE["id"] == "life-timeline"
    assert 45 <= STORYBOARD["targetSeconds"] <= 75
    assert SCENE["durationFrames"] == round(STORYBOARD["targetSeconds"] * STORYBOARD["fps"])
    assert SCENE["narrationSegments"] == []
    assert (STORYBOARD["width"], STORYBOARD["height"], STORYBOARD["fps"]) == (1920, 1080, 30)
    assert STORYBOARD["title"] == "普通人一生真正重要的 5 个选择"


def test_seven_acts_tile_the_whole_film_and_match_the_shots() -> None:
    acts = _acts()
    assert [act[0] for act in acts] == [
        "opening", "city", "industry", "partner", "investment", "learning", "ending"]
    assert acts[0][1] == 0 and acts[-1][2] == 60
    for left, right in zip(acts, acts[1:]):
        assert left[2] == right[1], "七幕必须首尾相接，镜头不换舞台"
    shot_windows = [(shot["id"], shot["startFrame"], shot["endFrame"]) for shot in SHOTS]
    assert [shot[0] for shot in shot_windows] == [act[0] for act in acts]
    for (_, start, end), (_, shot_start, shot_end) in zip(acts, shot_windows):
        assert round(start * 30) == shot_start
        assert round(end * 30) == shot_end
    assert any(shot["tier"] == "hero" for shot in SHOTS)


def test_copy_order_is_fixed_and_uses_the_requested_lines() -> None:
    texts = _copy_texts()
    required = [
        "人生不是一条直线。",
        "真正改道的，只有几个岔口。",
        "年龄为叙事刻度，不是人生时间表",
        "普通人一生真正重要的 5 个选择",
        "五项是常见视角，不是唯一标准",
        "城市，会改变哪些门对你打开。",
        "同样努力，先看起来差不多。",
        "行业决定你站在哪条跑道上。",
        "拉远才看见：跑道不同，高度不同。",
        "两个人一起走，路线会互相改写。",
        "关系会改变坡度，也会留下痕迹。",
        "每天一点，时间会把小投入垒高。",
        "同样的时间，留下与不留会分开。",
        "原路会到尽头。",
        "学过的东西，会在别处接上。",
        "换一条路，继续走。",
        "你走过的，只是其中一条。",
        "每一次选择，都长出新的可能。",
        "方向会被时间放大，路也可以改。",
    ]
    positions = [texts.index(line) for line in required]
    assert positions == sorted(positions), "画面文案必须按七幕顺序出现"
    assert [item["id"] for item in COPY] == [
        "opening-1", "opening-2", "age-note", "title", "title-note", "city-line", "industry-line-1",
        "industry-line-2", "industry-reveal", "industry-note", "partner-line-1",
        "partner-line-2", "invest-line-1", "invest-note", "invest-line-2",
        "learning-line-1", "learning-line-2", "learning-line-3", "ending-line-1",
        "ending-line-2", "final-line"]
    assert LABELS["choices"] == ["城市", "行业", "伴侣", "投资", "持续学习"]


def test_labels_cover_the_requested_objects() -> None:
    assert LABELS["ages"] == [0, 18, 22, 25, 30, 38, 47, 60]
    assert LABELS["cities"] == ["北京", "上海", "杭州", "深圳", "家乡"]
    assert LABELS["cityNodes"] == ["工作", "人脉", "机会", "信息", "项目", "公司", "工资"]
    assert LABELS["industries"] == ["传统制造", "房地产", "互联网", "新能源", "AI"]
    assert LABELS["partnerLeft"] == ["争执", "消耗", "各自用力", "沉默"]
    assert LABELS["partnerRight"] == ["分担", "补位", "共同计划", "长期打算", "支持"]
    assert LABELS["learningNodes"] == ["AI", "投资", "表达", "管理", "销售", "创业", "新技术"]
    assert LABELS["learningUpper"] == "先前学过的东西"
    assert LABELS["learningLower"] == "接上新路，继续走"


def test_copy_is_readable_and_stays_out_of_the_subtitle_safe_area() -> None:
    safe_top = 888
    for item in COPY:
        duration = item["to"] - item["from"]
        chars = len(re.sub(r"[\s，。、]", "", item["text"]))
        assert duration >= 1.2, f"{item['id']} 停留过短"
        assert chars / duration <= 15, f"{item['id']} 阅读速度过快"
        assert item["y"] + item["size"] * 1.25 <= safe_top, f"{item['id']} 进入字幕安全区"
        assert item["x"] >= 0 and item["x"] + item["width"] <= 1920


def test_no_guaranteed_returns_or_single_right_answer() -> None:
    visible = SOURCE + "\n" + RENDER + "\n" + GEOMETRY + "\n" + json.dumps(
        {"copy": COPY, "labels": LABELS}, ensure_ascii=False)
    for token in ("保证", "必涨", "稳赚", "收益率", "复利", "越早越好", "唯一答案", "最优解", "翻倍"):
        assert token not in visible, f"画面或文案出现不该有的承诺：{token}"
    assert "示意" in visible, "投资曲线必须标注为示意"
    assert "%" not in json.dumps(COPY, ensure_ascii=False), "画面不出现收益百分比"


def test_source_is_deterministic_and_has_no_media_dependency() -> None:
    for token in ("Math.random", "Date.now", "performance.now", "setInterval", "setTimeout",
                  "requestAnimationFrame"):
        assert token not in SOURCE + RENDER + GEOMETRY, f"代码场景出现非确定性来源：{token}"
    assert "useMediaAsset" not in SOURCE + RENDER + GEOMETRY
    assert "seed" in GEOMETRY, "城市楼体、尘点与决策树必须使用固定种子"
    assert "useLayoutEffect" in SOURCE and "captureScale" in SOURCE
    assert "drawFrame" in SOURCE and "drawFrame" in RENDER


def test_camera_and_age_keys_cover_the_whole_film_without_going_backwards() -> None:
    assert "export const CAMERA_KEYS" in GEOMETRY and "cameraAt" in GEOMETRY
    assert "camKey(0," in GEOMETRY and "{t: 60.0, pos:" in GEOMETRY
    assert "export function cameraAt" in GEOMETRY

    ages = [(float(t), float(age)) for t, age in re.findall(
        r"\{t: ([\d.]+), age: ([\d.]+)\}", GEOMETRY)]
    assert ages[0][0] == 0 and ages[-1][0] == 60
    assert ages[0][1] == 0 and ages[-1][1] == 60
    assert all(b[0] > a[0] for a, b in zip(ages, ages[1:]))
    assert all(b[1] >= a[1] for a, b in zip(ages, ages[1:])), "年龄不能倒退"


def test_canvas_scene_declares_its_visual_world() -> None:
    for token in ("AGE_MARKS", "CAMERA_KEYS", "TREE_PATHS", "YOUTH_BRANCHES",
                  "CITY_LANES", "INDUSTRY_LANES", "PARTNER_TRACKS", "INVEST_STEADY",
                  "LEARNING_THREAD", "LEARNING_BRIDGE", "NEW_PATH", "REALIZED"):
        assert token in GEOMETRY, f"缺少视觉世界定义：{token}"
    for token in ("drawYouth", "drawCity", "drawIndustry", "drawPartner", "drawInvestment",
                  "drawLearning", "drawTree"):
        assert token in RENDER, f"缺少绘制层：{token}"


def test_design_documents_the_six_questions_and_the_boundaries() -> None:
    for token in ("立意六项", "一句话命题", "核心体验", "表达载体", "揭示与记忆",
                  "可验算骨架", "重点投入", "不借清单", "无旁白", "无配乐", "无音效",
                  "60 秒", "画幅", "配色", "构图", "声音", "示意"):
        assert token in DESIGN, f"DESIGN.md 缺少：{token}"
    assert "life-timeline" in README
    for line in ("城市，会改变哪些门对你打开。", "行业决定你站在哪条跑道上。",
                 "两个人一起走，路线会互相改写。", "每天一点，时间会把小投入垒高。",
                 "原路会到尽头。", "学过的东西，会在别处接上。",
                 "方向会被时间放大，路也可以改。"):
        assert line in README, f"README 未记录画面文案：{line}"
