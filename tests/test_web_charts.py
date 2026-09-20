"""图表原语的机检（v2 场景树）。

三件事，全部在**源码层**成立，不需要起浏览器：

1. **原语内不含默认数据**：图表的每一个数值都必须来自分镜的 contentRef。
   「原语里躺着一组示例数据」是这类缺陷的温床——分镜没写数据时画面
   静默地画出示例值，校验通过、成片照出，谁都看不出数据是编的。
   判据：图表相关源码里不允许出现字面量的数据点（`label: '…'`、`value: 12`）。
2. **数据入口只有 contentRef**：图表原语经 `resolveContent(scene.data, node.contentRef)`
   读序列，而不是别处。
3. **示意标记能到达画面**：`node.schematic` 必须渲染成可见的「示意」标。
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from a2v import browser, contract_page, determinism, keynote  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "src"

#: 图表的数据侧源码。新增图表模块时在这里登记，漏登的文件不受机检保护。
CHART_SOURCES = (
    WEB / "primitives" / "SceneTree.tsx",
)

#: 字面量数据点的两种形态：`label: '四月'` 与 `value: 12`。
#: 类型注解（`label: string`）与属性读取（`point.label`）都不匹配；
#: label 限定中文内容，避免误伤 `label: 'a2v-label'` 这类类名映射。
_LABEL_LITERAL = re.compile(r"\blabel\s*:\s*['\"][^'\"]*[一-鿿]")
_VALUE_LITERAL = re.compile(r"\bvalue\s*:\s*-?\d")


def test_chart_sources_carry_no_default_data() -> None:
    assert all(path.is_file() for path in CHART_SOURCES), (
        f"图表源码清单与实际文件对不上：{[str(p) for p in CHART_SOURCES if not p.is_file()]}"
    )
    offenders: list[str] = []
    for path in CHART_SOURCES:
        text = path.read_text(encoding="utf-8")
        for match in _LABEL_LITERAL.finditer(text):
            offenders.append(f"{path.name}:{text.count(chr(10), 0, match.start()) + 1}: label 字面量")
        for match in _VALUE_LITERAL.finditer(text):
            offenders.append(f"{path.name}:{text.count(chr(10), 0, match.start()) + 1}: value 字面量")
    assert not offenders, (
        "图表源码里出现了字面量数据点（默认数据）：\n  " + "\n  ".join(offenders)
        + "\n  数据只能来自分镜的 data.values。"
    )


def test_chart_primitive_reads_data_from_the_storyboard() -> None:
    text = (WEB / "primitives" / "SceneTree.tsx").read_text(encoding="utf-8")
    assert "resolveContent(scene.data, node.contentRef)" in text, "图表原语必须经 contentRef 拿分镜数据"
    assert "chartPoints" in text, "图表数据必须经 chartPoints 归一化为 {label, value} 序列"
    assert "node.schematic" in text, "示意标记必须能到达画面（node.schematic）"


# ---------------------------------------------------------------- 端到端（契约页 + Chromium）

def _chart_storyboard() -> dict:
    """一幕图表的最小 v2 分镜：60 帧覆盖入场与收尾，schematic 打开示意标。"""
    return {
        "version": 2,
        "schemaVersion": 2,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "title": "图表确定性",
        "visualDirection": {"motif": "量测", "compositionBias": "centered", "density": "balanced", "rhythm": "steady", "avoid": []},
        "scenes": [
            {
                "id": "chart-demo",
                "type": "chart",
                "durationInFrames": 60,
                "data": {
                    "title": "每月投入",
                    "values": [
                        {"label": "四月", "value": 12},
                        {"label": "五月", "value": 30},
                        {"label": "六月", "value": 18},
                    ],
                },
                "visualIntent": {"relation": "focus", "focus": "chart", "composition": "center", "density": "balanced", "tone": "neutral"},
                "sceneTree": {
                    "id": "root",
                    "type": "stack",
                    "children": [
                        {"id": "heading", "type": "text", "contentRef": "data.title", "role": "title"},
                        {"id": "bars", "type": "chart", "contentRef": "data.values", "chart": "bar", "schematic": True},
                    ],
                },
                "motions": [{"target": "bars", "recipe": "reveal", "startFrame": 6, "durationFrames": 24}],
            },
        ],
    }


@pytest.fixture
def chart_page(chromium_ready, tmp_path):
    """图表分镜的契约页。契约页未构建时跳过（构建产物不入库）。

    分镜必须落在工作区根**之内**（契约页经由静态服务器取它），
    因此放进仓库的 `.gen`（构建产物目录，已被忽略），用完即删。
    """
    built = contract_page.contract_page_path()
    if not built.is_file():
        pytest.skip(f"契约页尚未构建：{built}（先执行 cd web && pnpm install && pnpm build）")
    scratch = ROOT / ".gen" / f"chart-e2e-{tmp_path.name}"
    scratch.mkdir(parents=True, exist_ok=True)
    storyboard = scratch / "chart-storyboard.json"
    storyboard.write_text(
        json.dumps(_chart_storyboard(), ensure_ascii=False), encoding="utf-8"
    )
    try:
        with contract_page.serve_contract_page(storyboard, ROOT) as url:
            with browser.open_animated_page(url, width=1080, height=1920) as page:
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                yield page
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _bar_labels(page: object) -> list[str]:
    return page.evaluate(
        "() => Array.from(document.querySelectorAll('.a2v-primitive-bar span')).map((el) => el.textContent || '')"
    )


def test_chart_outputs_storyboard_labels_as_dom_text(chart_page):
    """数据点标签在任何一帧都来自分镜：内容不允许出现编造或缺失。"""
    chart_page.seek(1)  # 入场刚开始：文字可能还是透明的，但内容必须已在 DOM
    assert _bar_labels(chart_page) == ["四月", "五月", "六月"]
    chart_page.seek(45)
    assert _bar_labels(chart_page) == ["四月", "五月", "六月"]


def test_chart_marks_schematic(chart_page):
    """声明 schematic 的图表必须在画面上出现「示意」标。"""
    chart_page.seek(30)
    assert chart_page.evaluate(
        "() => document.querySelector('.a2v-schematic')?.textContent"
    ) == "示意"


def test_chart_changes_between_frames(chart_page):
    """图表内容随帧号变化：两帧的像素必须可区分（PSNR < 60 dB）。"""
    chart_page.seek(10)
    early = chart_page.capture("png")
    chart_page.seek(45)
    late = chart_page.capture("png")
    assert determinism.psnr(early, late) < determinism.DEFAULT_PSNR_DB


def test_chart_frame_is_deterministic(chart_page):
    """同一帧求值两次逐像素一致（PSNR = ∞）：柱高与 DOM 文本都要确定性。"""
    verdicts = determinism.judge_frames(
        lambda frame: (chart_page.seek(frame), chart_page.capture("png"))[1],
        [5, 30, 55],
    )
    failures = determinism.failures(verdicts)
    assert not failures, determinism.summarize(verdicts)
    assert all(verdict.psnr == float("inf") for verdict in verdicts), determinism.summarize(
        verdicts
    )


# ---------------------------------------------------------------- 观感闸门的判定范围（v2）

_SAFE = {"left": 96.0, "right": 984.0, "top": 240.0, "bottom": 1600.0}


def test_overflow_gates_cover_the_whole_scene() -> None:
    """v2 图表原语是 DOM/SVG：K7/K8 对整幕生效，不再有量不到的 canvas 内部。"""
    gate = keynote.gate_overflow("chart", [], _SAFE)
    assert gate.status == "pass"
    assert "canvas" not in gate.detail
    container = keynote.gate_container_overflow("chart", [])
    assert container.status == "skipped"  # 没有声明容器的图形文字时如实跳过
    assert "canvas" not in container.detail
