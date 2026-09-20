"""flow 组件的端到端验证（任务 8.2 / 8.3 的「验证」部分）。

三件事都走**既有的判定管线**，不为 flow 另起炉灶：

1. **K8 容器内溢出（硬判定）**：节点文字声明了 `data-a2v-inside=".flow-node-box"`，
   体检的元素事实里必须出现这些文字，且全部在节点盒子内——盒子尺寸由实测
   文字宽度反推，如果哪天有人把尺寸写死，这条会直接失败。
2. **M 系列动效结论**：`motion.audit` 对 flow 幕给出入场结论（节点依次入场），
   且连线几何的长度在布局确定时缓存（组件侧不逐帧测量——那是
   `Flow.test.ts` 的断言；这里的证据是 M 系列在该幕量到了入场元素）。
3. **确定性**：同一帧求值两次逐像素一致（PSNR = ∞）。

容量超限的校验警告不需要浏览器：直接走分镜校验器。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from a2v import browser, catalog, contract_page, determinism, inspect, keynote, motion, storyboard

ROOT = Path(__file__).resolve().parents[1]

#: 一幕 flow 的最小分镜：因果链 + 反馈回路，启用预设让元素事实可用。
FLOW_STORYBOARD = {
    "version": 1,
    "fps": 30,
    "width": 1080,
    "height": 1920,
    "title": "flow 确定性",
    "visual": {"preset": "keynote", "theme": "dark"},
    "scenes": [
        {
            "id": "flow-demo",
            "type": "diagram",
            "durationInFrames": 150,
            "data": {
                "title": "落选的因果链",
                "nodes": ["报名", "准备", "上场", "落选", "再报名"],
                "edges": [
                    ["报名", "准备"],
                    ["准备", "上场"],
                    ["上场", "落选"],
                    ["落选", "再报名"],
                ],
                "figure": {"kind": "flow", "motion": "normal"},
            },
        },
    ],
}


@pytest.fixture
def flow_page(chromium_ready, tmp_path):
    """flow 分镜的契约页。契约页未构建时跳过（构建产物不入库）。"""
    built = contract_page.contract_page_path()
    if not built.is_file():
        pytest.skip(f"契约页尚未构建：{built}（先执行 cd web && pnpm install && pnpm build）")
    scratch = ROOT / ".gen" / f"flow-e2e-{tmp_path.name}"
    scratch.mkdir(parents=True, exist_ok=True)
    storyboard_json = scratch / "flow-storyboard.json"
    storyboard_json.write_text(json.dumps(FLOW_STORYBOARD, ensure_ascii=False), encoding="utf-8")
    try:
        with contract_page.serve_contract_page(storyboard_json, ROOT) as url:
            with browser.open_animated_page(url, width=1080, height=1920) as page:
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                yield page
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------- 校验器（容量警告）

def _flow_scene(nodes: int) -> dict:
    data = json.loads(json.dumps(FLOW_STORYBOARD["scenes"][0], ensure_ascii=False))
    data["data"]["nodes"] = [f"节点{index}" for index in range(nodes)]
    data["data"]["edges"] = [
        [f"节点{index}", f"节点{index + 1}"] for index in range(nodes - 1)
    ]
    return data


def test_flow_is_a_registered_component() -> None:
    entry = catalog.component("flow")
    assert entry is not None
    assert entry.items == (2, 6), "flow 的容量声明变了，下面的警告断言要跟着改"


def test_capacity_overrun_warns() -> None:
    """7 个节点超出 (2, 6) 的舒适区：校验器报警告且指名条目数。"""
    script = {
        **FLOW_STORYBOARD,
        "visual": {"preset": "keynote", "theme": "dark"},
        "scenes": [_flow_scene(7)],
    }
    report = storyboard.validate(script, declarative=True)
    assert report.ok, [issue.format() for issue in report.errors]
    capacity = [
        issue
        for issue in report.warnings
        if issue.path == "scenes[0].data.nodes" and "适合" in issue.message
    ]
    assert capacity, [issue.format() for issue in report.warnings]
    assert any("当前 7 项" in issue.message for issue in capacity), [
        issue.format() for issue in capacity
    ]


def test_capacity_within_range_does_not_warn() -> None:
    script = {
        **FLOW_STORYBOARD,
        "visual": {"preset": "keynote", "theme": "dark"},
        "scenes": [_flow_scene(6)],
    }
    report = storyboard.validate(script, declarative=True)
    capacity = [
        issue
        for issue in report.warnings
        if issue.path == "scenes[0].data.nodes" and "适合" in issue.message
    ]
    assert not capacity, [issue.format() for issue in report.warnings]


# ---------------------------------------------------------------- 端到端（契约页 + Chromium）

def test_flow_scene_passes_the_full_inspection(flow_page, tmp_path):
    """整条体检管线在 flow 幕上工作：K8 量到节点文字并判通过，M 系列给出入场结论。"""
    # report_dir 需要已存在（contact-sheet 的文字清单直接 open 写入）
    frames_dir = tmp_path / "frames"
    report_dir = tmp_path / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    report, extra = inspect.run_inspect(
        flow_page,
        FLOW_STORYBOARD["scenes"],
        frames_dir,
        report_dir,
        preset="keynote",
    )
    # 组件契约：挂载的是 flow，整幕有文字
    contract = {item["scene"]: item for item in extra["contract"]}
    assert contract["flow-demo"]["kind"] == "flow"
    assert contract["flow-demo"]["ok"]
    assert not report.errors, report.errors

    # K8：节点文字都声明了容器，全部量到且在盒子内
    keynote_json = extra["keynote"]
    k8 = next(
        gate
        for gate in keynote_json["gates"]
        if gate["id"] == "K8" and gate["scene"] == "flow-demo"
    )
    assert k8["status"] == "pass", k8
    assert "1 个" not in k8["detail"], k8  # 至少量到多个节点文字（5 个节点）

    # M 系列：该幕的入场元素被量到，结论落在动效结论栏里
    motion_json = extra["motion"]
    assert motion_json["enabled"], motion_json
    entrances = [
        record for record in motion_json["entrances"] if record["scene"] == "flow-demo"
    ]
    assert entrances, motion_json


def test_flow_motion_audit_reports_entrances(flow_page):
    """M 系列对该幕给出入场结论：节点依次入场，被量到的是 flow 幕自己的元素。"""
    result = motion.audit(flow_page, FLOW_STORYBOARD["scenes"])
    assert result.enabled
    flow_records = [record for record in result.records if record.scene == "flow-demo"]
    assert flow_records, "flow 幕没有量到任何入场元素"
    # 有位移的入场不超过速度阈值：spring 配方在闸门门槛内（M1/M2 判据共用一份实现）
    for record in flow_records:
        assert (
            record.first_opacity <= motion.MAX_FIRST_FRAME_OPACITY
            or not record.moving
        ), record


def test_flow_frame_is_deterministic(flow_page):
    """同一帧求值两次逐像素一致（PSNR = ∞）：布局、取档与描边进度都是帧号的纯函数。"""
    verdicts = determinism.judge_frames(
        lambda frame: (flow_page.seek(frame), flow_page.capture("png"))[1],
        [8, 60, 120],
    )
    failures = determinism.failures(verdicts)
    assert not failures, determinism.summarize(verdicts)
    assert all(verdict.psnr == float("inf") for verdict in verdicts), determinism.summarize(verdicts)


def test_flow_keeps_the_gates_honest(flow_page):
    """K8 的判定范围如实报出：量了几个声明了容器的图形文字，一条都不少。"""
    flow_page.seek(120)
    facts = flow_page.evaluate(inspect._AESTHETIC_SCRIPT)  # noqa: SLF001 - 事实采集脚本是管线的一部分
    inside = facts.get("inside") or []
    flow_inside = [item for item in inside if item.get("container") == ".flow-node-box"]
    assert len(flow_inside) == 5, flow_inside
    gate = keynote.gate_container_overflow("flow-demo", flow_inside)
    assert gate.status == "pass", gate
    assert "5 个" in gate.detail, gate
