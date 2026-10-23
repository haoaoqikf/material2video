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
        r"\{id: '([a-z]+)', start: ([\d.]+), end: ([\d.]+)\}", GEOMETRY)]


def _copy_texts() -> list[str]:
    return [item["text"] for item in COPY]


def test_silent_single_scene_with_an_explicit_frame_budget() -> None:
    assert STORYBOARD["input"]["kind"] == "topic"
    assert not STORYBOARD.get("soundtrack")
    assert len(STORYBOARD["scenes"]) == 1
    assert SCENE["id"] == "life-timeline"
    assert SCENE["durationFrames"] == 60 * 30
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
        "人的一生，看起来有无数个选择。",
        "但真正改变人生轨迹的，可能只有几个。",
        "普通人一生真正重要的 5 个选择",
        "城市，决定你每天会撞见什么机会。",
        "努力决定你跑多快。",
        "行业决定你站在哪条跑道上。",
        "伴侣不是人生的配角，而是最大的长期变量之一。",
        "时间",
        "投资真正强大的地方，是让时间替你工作。",
        "城市、行业、伴侣、投资，决定你走哪条路。",
        "持续学习，决定你还能不能换路。",
        "一个人的人生，只是无数可能路径中的一条。",
        "人生的差距，往往不是一天拉开的。",
        "而是几个重要选择，被时间不断放大。",
        "选对方向，比一直用力更重要。",
    ]
    positions = [texts.index(line) for line in required]
    assert positions == sorted(positions), "画面文案必须按七幕顺序出现"
    assert [item["id"] for item in COPY] == [
        "opening-1", "opening-2", "title", "city-line", "effort-line", "runway-line",
        "partner-line", "time-giant", "invest-line", "invest-note", "learning-line-1",
        "learning-line-2", "path-line", "closing-1", "closing-2", "final-line"]
    assert LABELS["choices"] == ["城市", "行业", "伴侣", "投资", "持续学习"]


def test_labels_cover_the_requested_objects() -> None:
    assert LABELS["ages"] == [0, 10, 18, 22, 30, 40, 60, 80]
    assert LABELS["cities"] == ["北京", "上海", "深圳", "杭州", "家乡"]
    assert LABELS["cityNodes"] == ["工作", "公司", "人脉", "信息", "机会", "工资", "项目"]
    assert LABELS["industries"] == ["传统制造", "房地产", "互联网", "新能源", "AI"]
    assert LABELS["partnerLeft"] == ["争吵", "债务", "内耗", "焦虑"]
    assert LABELS["partnerRight"] == ["支持", "沟通", "储蓄", "成长", "长期计划"]
    assert LABELS["learningNodes"] == ["AI", "投资", "表达", "管理", "销售", "创业", "新技术"]
    assert LABELS["learningUpper"] == "25 岁以后停止学习"
    assert LABELS["learningLower"] == "持续学习"


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
    camera = [(float(t),) for t in re.findall(r"\{t: ([\d.]+), pos:", GEOMETRY)]
    times = [item[0] for item in camera]
    assert times[0] == 0 and times[-1] == 60
    assert times == sorted(times), "镜头关键帧必须按时间递增"

    ages = [(float(t), float(age)) for t, age in re.findall(
        r"\{t: ([\d.]+), age: ([\d.]+)\}", GEOMETRY)]
    assert ages[0][0] == 0 and ages[-1][0] == 60
    assert ages[0][1] == 0 and ages[-1][1] == 60
    assert all(b[0] > a[0] for a, b in zip(ages, ages[1:]))
    assert all(b[1] >= a[1] for a, b in zip(ages, ages[1:])), "年龄不能倒退"


def test_canvas_scene_declares_its_visual_world() -> None:
    for token in ("AGE_MARKS", "CAMERA_KEYS", "TREE_PATHS", "CITY_BRANCHES",
                  "INDUSTRY_PATHS", "PARTNER_TRACKS", "INVEST_GROW", "LEARNING_PATH"):
        assert token in GEOMETRY, f"缺少视觉世界定义：{token}"
    for token in ("drawCity", "drawIndustry", "drawPartnerSplit", "drawInvestment",
                  "drawLearning", "drawTree"):
        assert token in RENDER, f"缺少绘制层：{token}"


def test_design_documents_the_six_questions_and_the_boundaries() -> None:
    for token in ("立意六项", "一句话命题", "核心体验", "表达载体", "揭示与记忆",
                  "可验算骨架", "重点投入", "不借清单", "无旁白", "无配乐", "无音效",
                  "60 秒", "画幅", "配色", "构图", "声音", "示意"):
        assert token in DESIGN, f"DESIGN.md 缺少：{token}"
    assert "life-timeline" in README
    for line in ("城市，决定你每天会撞见什么机会。", "行业决定你站在哪条跑道上。",
                 "伴侣不是人生的配角", "投资真正强大的地方", "持续学习，决定你还能不能换路。",
                 "选对方向，比一直用力更重要。"):
        assert line in README, f"README 未记录画面文案：{line}"
