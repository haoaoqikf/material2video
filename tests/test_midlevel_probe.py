"""中层原语在契约页上的 DOM 量测（任务 3.4）。

规格（scene-primitive-tree）要求五个中层原语「由节拍驱动且布局冻结」：
- 画面必须显示**方向连接与当前阶段**，而不是把标签排成行或圆周；
- 节点数量、内容与基础几何在帧间不变；
- 量级原语的指示状态按 beat 局部进度变化。

这些都要在真实浏览器里量：`data-a2v-*` 锚点是契约探针唯一的读数入口，
量的是页面上的实际值，而不是再算一遍分镜。

契约页未构建时跳过（构建产物不入库）。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from a2v import browser, contract_page

ROOT = Path(__file__).resolve().parents[1]

#: 幕内帧区间：四条 beat 依次驱动流程、闭环、进度轴、仪表与象形图。
#: 动作必须落在**目标原语支持的清单**里（阶段是 surface，支持 establish/transform）；
#: 最后一条在幕尾前 12 帧结束，留出稳定阅读时间。
BEATS = [
    ("b1", "establish", ["flow-a", "cycle-a", "timeline-a"], "先看流程的起点", 0, 30),
    ("b2", "transform", ["flow-b", "cycle-b", "timeline-b"], "下一步接上", 30, 60),
    ("b3", "accumulate", ["meter"], "量级一路累积", 60, 96),
    ("b4", "highlight", ["units"], "最后强调占比", 96, 108),
]

SEGMENT_TEXTS = ["先看流程的起点。", "再看推进到的下一步。", "量级一路累积。", "最后强调占比。"]


def _stages(prefix: str) -> list[dict]:
    """两个阶段：节点 id 必须整幕唯一，所以按容器前缀区分。"""
    return [
        {"id": f"{prefix}-a", "type": "surface", "children": [
            {"id": f"{prefix}-a-text", "type": "text", "contentRef": "data.stepA", "role": "body"},
        ]},
        {"id": f"{prefix}-b", "type": "surface", "children": [
            {"id": f"{prefix}-b-text", "type": "text", "contentRef": "data.stepB", "role": "body"},
        ]},
    ]


def _storyboard() -> dict:
    """一幕装下五个中层原语，逐帧状态由 resolvedBeats 直接给出（不经过 TTS）。"""
    return {
        "version": 3,
        "schemaVersion": 3,
        "directingVersion": 1,
        "directingBrief": {"thesis": "五个中层原语各司其职", "audienceShift": "从列表转向关系", "emotionalArc": ["观察", "理解"], "visualMotif": "方向关系", "stylePack": "technical", "avoid": []},
        "visual": {"theme": "dark", "preset": "keynote"},
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "title": "中层原语量测",
        "visualDirection": {"motif": "量测", "compositionBias": "mixed", "density": "balanced", "rhythm": "steady", "avoid": []},
        "scenes": [
            {
                "id": "midlevel",
                "type": "process",
                "durationInFrames": 120,
                "renderer": {"kind": "tree"},
                "data": {"stepA": "起点", "stepB": "下一步", "ratio": 80},
                "visualIntent": {
                    "relation": "sequence", "focus": "shape", "composition": "center",
                    "density": "balanced", "tone": "neutral", "mode": "process",
                    "claim": "五个中层原语各司其职",
                    "showWithoutText": "方向连接、闭环轨道、进度轴与两处量级指示",
                    "primaryObject": "流程与量级指示", "motionMeaning": "逐段推进",
                },
                "camera": {"shot": "wide", "composition": "center", "depth": "flat", "focus": "flow", "segments": [{"kind": "hold", "phase": "establish", "focus": "flow", "intensity": 0}, {"kind": "settle", "phase": "settle", "focus": "flow", "intensity": 0}]},
                "narrationSegments": [
                    {"id": f"n{index + 1}", "text": text, "beatId": BEATS[index][0]}
                    for index, text in enumerate(SEGMENT_TEXTS)
                ],
                "beats": [
                    {"id": beat_id, "action": action, "targets": targets, "meaning": meaning}
                    for beat_id, action, targets, meaning, _, _ in BEATS
                ],
                "resolvedBeats": [
                    {"id": beat_id, "action": action, "targets": targets, "meaning": meaning,
                     "startFrame": start, "endFrame": end}
                    for beat_id, action, targets, meaning, start, end in BEATS
                ],
                "sceneTree": {
                    "id": "root",
                    "type": "column",
                    "gap": "md",
                    "children": [
                        {"id": "flow", "type": "flow", "direction": "ltr", "children": _stages("flow")},
                        {"id": "cycle", "type": "cycle", "direction": "ccw", "children": _stages("cycle")},
                        {"id": "timeline", "type": "timeline", "direction": "ltr", "children": _stages("timeline")},
                        {"id": "meter", "type": "gauge", "contentRef": "data.ratio", "schematic": True},
                        {"id": "units", "type": "pictogram", "contentRef": "data.ratio", "icon": "users", "schematic": True},
                    ],
                },
                "motions": [
                    {"target": "flow", "recipe": "reveal", "phase": "establish", "durationFrames": 12},
                    {"target": "meter", "recipe": "reveal", "phase": "change", "durationFrames": 12},
                ],
            },
        ],
    }


@pytest.fixture
def midlevel_page(chromium_ready, tmp_path):
    """中层原语分镜的契约页；分镜必须落在工作区根之内，因此放进被忽略的 `.gen`。"""
    built = contract_page.contract_page_path()
    if not built.is_file():
        pytest.skip(f"契约页尚未构建：{built}（先执行 cd web && pnpm install && pnpm build）")
    scratch = ROOT / ".gen" / f"midlevel-e2e-{tmp_path.name}"
    scratch.mkdir(parents=True, exist_ok=True)
    storyboard = scratch / "midlevel-storyboard.json"
    storyboard.write_text(json.dumps(_storyboard(), ensure_ascii=False), encoding="utf-8")
    try:
        with contract_page.serve_contract_page(storyboard, ROOT) as url:
            with browser.open_animated_page(url, width=1080, height=1920) as page:
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                yield page
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


_FACTS = """
() => {
  const scenes = Array.from(document.querySelectorAll('section[data-a2v-scene]'));
  const active = scenes.find((el) => el.style.display !== 'none') || scenes[0];
  const attr = (node, name) => (node ? node.getAttribute(name) : null);
  const flow = active.querySelector('.a2v-primitive-flow');
  const cycle = active.querySelector('.a2v-primitive-cycle');
  const timeline = active.querySelector('.a2v-primitive-timeline');
  const gauge = active.querySelector('.a2v-gauge');
  const pictogram = active.querySelector('.a2v-pictogram');
  const stageState = (root) => root
    ? Array.from(root.querySelectorAll('[data-a2v-stage-state]')).map((el) => attr(el, 'data-a2v-stage-state'))
    : [];
  const canvasHeight = 1920;
  const geometry = (root) => {
    if (!root) return [];
    return Array.from(root.children)
      .filter((el) => el.hasAttribute('data-a2v-node-id'))
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return {id: attr(el, 'data-a2v-node-id'), height: Math.round(rect.height), width: Math.round(rect.width)};
      });
  };
  return {
    canvasHeight,
    beat: {
      current: attr(active, 'data-a2v-beat-current'),
      progress: Number(attr(active, 'data-a2v-beat-progress')),
      completed: attr(active, 'data-a2v-beat-completed'),
      estimated: attr(active, 'data-a2v-beat-estimated'),
    },
    flowArrows: flow ? flow.querySelectorAll('[data-a2v-relation="flow"]').length : -1,
    flowArrowDirection: flow ? attr(flow.querySelector('[data-a2v-relation="flow"]'), 'data-a2v-direction') : null,
    flowStages: stageState(flow),
    flowGeometry: geometry(flow),
    flowNodes: flow ? flow.querySelectorAll('[data-a2v-node-id]').length : -1,
    cycleRing: Boolean(cycle && cycle.querySelector('.a2v-cycle-ring')),
    cycleHead: cycle ? attr(cycle.querySelector('.a2v-cycle-head'), 'points') : null,
    cycleFill: cycle ? attr(cycle.querySelector('.a2v-cycle-fill'), 'stroke-dasharray') : null,
    cycleStages: stageState(cycle),
    cycleGeometry: geometry(cycle),
    timelineFill: timeline ? attr(timeline.querySelector('.a2v-timeline-fill'), 'style') : null,
    timelineStages: stageState(timeline),
    timelineGeometry: geometry(timeline),
    timelineNodes: timeline ? timeline.querySelectorAll('[data-a2v-node-id]').length : -1,
    gaugeShown: gauge ? Number(attr(gauge, 'data-a2v-shown')) : -1,
    gaugeValue: gauge ? Number(attr(gauge, 'data-a2v-value')) : -1,
    pictogramFilled: pictogram ? Number(attr(pictogram, 'data-a2v-filled')) : -1,
    pictogramUnits: pictogram ? Number(attr(pictogram, 'data-a2v-units')) : -1,
    pictogramIcons: pictogram ? pictogram.querySelectorAll('svg').length : -1,
  };
}
"""


def _facts(page, frame: int) -> dict:
    page.seek(frame)
    return page.evaluate(_FACTS)


def test_flow_draws_direction_connectors_and_marks_the_current_stage(midlevel_page):
    """flow 的「不只是排成一行」落在方向连接与当前阶段上。"""
    first = _facts(midlevel_page, 10)
    assert first["flowArrows"] == 1, "两个阶段之间必须有一条方向连接"
    assert first["flowArrowDirection"] == "ltr"
    assert first["flowStages"] == ["active", "pending"]

    second = _facts(midlevel_page, 40)
    assert second["flowStages"] == ["done", "active"], "当前阶段必须跟着 beat 换"
    # 阶段只改强调：节点数量在帧间完全不变
    assert first["flowNodes"] == second["flowNodes"]


def test_cycle_draws_a_ring_with_the_declared_direction(midlevel_page):
    facts = _facts(midlevel_page, 40)
    assert facts["cycleRing"] is True, "闭环必须有可见的轨道"
    # ccw 的箭头指向左侧；cw 指向右侧——方向在画面上可辨
    assert facts["cycleHead"] == "56,3.5 56,16.5 45,10"
    assert facts["cycleFill"], "轨道要有按当前阶段推进的高亮弧"
    assert facts["cycleStages"] == ["done", "active"]


def test_timeline_fill_advances_with_the_beat(midlevel_page):
    first = _facts(midlevel_page, 10)["timelineFill"]
    second = _facts(midlevel_page, 40)["timelineFill"]
    assert "scaleX" in (first or ""), f"时间轴进度要用变换表达而不是改宽高：{first}"
    assert first != second, "进度必须随帧推进"


def test_gauge_and_pictogram_follow_the_beat_progress(midlevel_page):
    before = _facts(midlevel_page, 55)
    middle = _facts(midlevel_page, 78)
    after = _facts(midlevel_page, 110)
    assert before["gaugeValue"] == 80 and after["gaugeValue"] == 80, "满值来自分镜的 contentRef"
    # 累积 beat 进行中：指示状态按局部进度增长
    assert before["gaugeShown"] < middle["gaugeShown"] <= after["gaugeShown"]
    assert before["pictogramFilled"] == 0, "还没轮到时起点为零"
    assert after["pictogramFilled"] == 8, "80% 对应 10 格里的 8 格"
    # 单位数与图标数固定：帧间不重排、不增删
    assert before["pictogramUnits"] == after["pictogramUnits"] == 10
    assert before["pictogramIcons"] == after["pictogramIcons"] == 10


def test_beat_state_is_exposed_on_the_scene_and_not_estimated(midlevel_page):
    facts = _facts(midlevel_page, 40)
    assert facts["beat"]["current"] == "b2"
    assert facts["beat"]["completed"] == "b1"
    assert facts["beat"]["estimated"] == "0", "有 resolvedBeats 时不得标记为估算"
    assert 0 <= facts["beat"]["progress"] <= 1
    # 末条 beat 结束后的稳定阅读段：没有当前 beat，四条全部完成
    last = _facts(midlevel_page, 119)
    assert last["beat"]["current"] == ""
    assert last["beat"]["completed"] == "b1,b2,b3,b4"


def test_same_frame_is_reproducible(midlevel_page):
    assert _facts(midlevel_page, 78) == _facts(midlevel_page, 78)


def test_stage_children_keep_their_content_height(midlevel_page):
    """阶段子节点必须按内容撑开，而不是被撑成整块画布。

    回归背景：节点上的阶段状态属性一度写成 `data-a2v-stage`，与画布容器的
    `[data-a2v-stage]`（base.css 里声明 1080×1920 + `overflow: hidden`）同名，
    于是每个阶段子节点都被撑成整块画布：flow 的文字被裁掉、timeline 把标题
    挤出安全区、整幕墨迹掉到 0.4%。这里按几何钉住这条不变量。
    """
    facts = _facts(midlevel_page, 40)
    canvas = facts["canvasHeight"]
    for key in ("flowGeometry", "cycleGeometry", "timelineGeometry"):
        boxes = facts[key]
        assert boxes, f"{key} 必须量到阶段子节点"
        for box in boxes:
            assert 0 < box["height"] < canvas / 2, f"{key} 的 {box['id']} 高度异常：{box}"
    # 画布属性只能出现在舞台容器上：阶段状态用独立的属性名
    assert midlevel_page.evaluate(
        "() => Array.from(document.querySelectorAll('.a2v-primitive[data-a2v-stage]')).length"
    ) == 0
