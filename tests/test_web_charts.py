"""图表组件的静态机检（任务 7.2 / 7.4 的「机检」部分）。

三件事，全部在**源码层**成立，不需要起浏览器：

1. **组件内不含默认数据**：图表的每一个数值都必须来自分镜。
   「组件里躺着一组示例数据」是这类缺陷的温床——分镜没写数据时画面
   静默地画出示例值，校验通过、成片照出，谁都看不出数据是编的。
   判据：图表相关源码里不允许出现字面量的数据点（`label: '…'`、`value: 0`）。
2. **数据入口只有分镜**：组件从 `data['values']` 读序列，而不是别处。
3. **canvas 用到的令牌都存在**：ECharts 读不了 CSS 变量，颜色映射表里
   的每个令牌名必须在 `tokens.css` 里有声明——引用一个不存在的令牌
   会安静地落回空字符串，画面不报错但变成透明。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "src"

#: 图表的数据侧源码。新增图表模块时在这里登记，漏登的文件不受机检保护。
CHART_SOURCES = (
    WEB / "components" / "Chart.tsx",
    WEB / "charts" / "echarts.ts",
    WEB / "charts" / "series.ts",
    WEB / "charts" / "options.ts",
    WEB / "charts" / "colors.ts",
    WEB / "charts" / "useFrameChart.ts",
)

#: 字面量数据点的两种形态：`label: '四月'` 与 `value: 12`。
#: 类型注解（`label: string`）与属性读取（`point.label`）都不匹配。
_LABEL_LITERAL = re.compile(r"\blabel\s*:\s*['\"]")
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


def test_chart_component_reads_data_from_the_storyboard() -> None:
    text = (WEB / "components" / "Chart.tsx").read_text(encoding="utf-8")
    assert "useFigure" in text, "图表组件必须经 useFigure 拿分镜数据"
    assert "data['values']" in text, "图表组件必须从分镜的 data.values 读数据序列"
    assert "fig.spec.schematic" in text, "示意标记必须能到达画面（figure.schematic）"


def test_canvas_color_tokens_are_declared_in_the_token_source() -> None:
    colors = (WEB / "charts" / "options.ts").read_text(encoding="utf-8")
    tokens_css = (WEB / "styles" / "tokens.css").read_text(encoding="utf-8")
    declared = set(re.findall(r"^\s*(--[a-z0-9-]+)\s*:", tokens_css, re.M))
    used = set(re.findall(r"'(--[a-z0-9-]+)'", colors))
    assert used, "没有在 colors 映射里发现令牌：机检可能已经失效"
    missing = sorted(used - declared)
    assert not missing, (
        f"canvas 颜色映射引用了未声明的令牌：{missing}——"
        "补进 tokens.css，否则画面安静地变成透明。"
    )


# ---------------------------------------------------------------- 观感闸门的判定范围（任务 7.4）

from a2v import keynote  # noqa: E402

_SAFE = {"left": 96.0, "right": 984.0, "top": 240.0, "bottom": 1600.0}


def test_overflow_gates_declare_the_chart_interior_out_of_scope() -> None:
    """图表幕的 K7/K8 必须写明「图形内部量不到」：如实报范围，不装作量过了。"""
    gate = keynote.gate_overflow("chart", [], _SAFE, chart_interior=True)
    assert gate.status == "pass"
    assert "canvas" in gate.detail
    assert "DOM 文本" in gate.detail
    # 普通组件不受影响：说明文字不出现
    plain = keynote.gate_overflow("s", [], _SAFE)
    assert "canvas" not in plain.detail


def test_container_gate_declares_the_chart_interior_out_of_scope() -> None:
    gate = keynote.gate_container_overflow("chart", [], chart_interior=True)
    assert gate.status == "skipped"
    assert "canvas" in gate.detail
    plain = keynote.gate_container_overflow("s", [])
    assert "canvas" not in plain.detail


def test_the_scope_note_survives_fail_details() -> None:
    """失败详情同样要带范围说明：读者得知道「报出的失败」量的是哪一层。"""
    block = {
        "role": "note",
        "block": "note",
        "left": 200.0,
        "right": 800.0,
        "top": 100.0,
        "bottom": 700.0,
        "text": "越界的一句话",
    }
    gate = keynote.gate_overflow("chart", [block], _SAFE, chart_interior=True)
    assert gate.status == "fail"
    assert "canvas" in gate.detail


# ---------------------------------------------------------------- 端到端（契约页 + Chromium）

import json  # noqa: E402
import shutil  # noqa: E402

import pytest  # noqa: E402

from a2v import browser, contract_page, determinism  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

#: 一幕图表的最小分镜：60 帧覆盖入场与收尾，schematic 打开示意标。
CHART_STORYBOARD = {
    "version": 1,
    "fps": 30,
    "width": 1080,
    "height": 1920,
    "title": "图表确定性",
    "scenes": [
        {
            "id": "chart-demo",
            "type": "chart",
            "durationInFrames": 60,
            "data": {
                "title": "每月投入",
                "chart": "bar",
                "values": [
                    {"label": "四月", "value": 12},
                    {"label": "五月", "value": 30},
                    {"label": "六月", "value": 18},
                ],
                "figure": {"schematic": True, "labels": {"unit": " 小时"}},
            },
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
        json.dumps(CHART_STORYBOARD, ensure_ascii=False), encoding="utf-8"
    )
    try:
        with contract_page.serve_contract_page(storyboard, ROOT) as url:
            with browser.open_animated_page(url, width=1080, height=1920) as page:
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                yield page
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


#: 第 index 行的**数值**文本。`data-el='value-<i>'` 落在数值 span 上
#: （`has_any_text` / K7 量的是这些文本），行容器还含标签，不能混读。
_JS_ROW_TEXT = (
    "([i]) => { const els = document.querySelectorAll('.fig-chart-row-value');"
    " const el = els[i]; return el ? el.textContent : null; }"
)


def _row_text(page: object, index: int) -> str:
    return page.evaluate(_JS_ROW_TEXT, [index]) or ""


def test_chart_outputs_final_values_as_dom_text(chart_page):
    """数值列在任何一帧都显示**最终值**：文字不允许出现中间数（任务 7.4）。"""
    chart_page.seek(1)  # 入场刚开始：文字可能还是透明的，但内容必须已是最终值
    for index, expected in enumerate(("12", "30", "18")):
        assert _row_text(chart_page, index) == f"{expected} 小时"
    chart_page.seek(45)
    for index, expected in enumerate(("12", "30", "18")):
        assert _row_text(chart_page, index) == f"{expected} 小时"


def test_chart_marks_schematic_and_reads_the_storyboard(chart_page):
    chart_page.seek(30)
    assert chart_page.evaluate(
        "() => document.querySelector('[data-el=\"schematic\"]')?.textContent"
    ) == "示意"
    assert chart_page.evaluate(
        "() => document.querySelector('[data-el=\"title\"]')?.textContent"
    ) == "每月投入"
    assert chart_page.evaluate(
        "() => document.querySelector('[data-chart-type]')?.getAttribute('data-chart-type')"
    ) == "bar"


def test_chart_canvas_changes_between_frames(chart_page):
    """图表内容随帧号变化：两帧的像素必须可区分（PSNR < 60 dB）。"""
    chart_page.seek(15)
    early = chart_page.capture("png")
    chart_page.seek(45)
    late = chart_page.capture("png")
    assert determinism.psnr(early, late) < determinism.DEFAULT_PSNR_DB


def test_chart_frame_is_deterministic(chart_page):
    """同一帧求值两次逐像素一致（PSNR = ∞）：canvas 切片与 DOM 文本都要确定性。"""
    verdicts = determinism.judge_frames(
        lambda frame: (chart_page.seek(frame), chart_page.capture("png"))[1],
        [5, 30, 55],
    )
    failures = determinism.failures(verdicts)
    assert not failures, determinism.summarize(verdicts)
    assert all(verdict.psnr == float("inf") for verdict in verdicts), determinism.summarize(
        verdicts
    )
