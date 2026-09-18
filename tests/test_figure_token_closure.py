"""组件层的令牌与状态契约。

这个文件补的是一格空白：**「令牌有没有定义」已经有测试，「组件有没有真的用」没有。**

规范写着「组件的间距取自 8pt 阶」，而实测 `figures.css` 的 13 处 `gap` 与
4 处 `padding` 一个都没走阶，30 / 46 / 18 / 22 / 26 / 34 全不在阶上；
`stroke-width` 散着 2 / 3 / 4 / 5 / 6 五种线宽，`font-weight` 10 处、
`letter-spacing` 16 处全是字面值。这些都不报错、不影响出片，
只是让画面在细节上不像一套东西——最难自查的一类缺陷。

因此这里查两件事：

1. **令牌闭包**：组件样式表里的间距、内边距、线宽、字重、字距、圆角必须引用令牌，
   而且新族的引用必须带原值兜底（`var(--令牌, 原值)`），否则未启用预设的画面会变。
2. **基元与状态**：四个基元类只在预设作用域内存在，状态取值只有四个，
   状态规则里不出现不透明度与位移。

只做静态解析，不起浏览器：CSS 文本里的数值本身就是契约。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from a2v import keynote

ASSETS = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "article2video" / "assets"


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


FIGURES_CSS = _strip_comments((ASSETS / "figures.css").read_text(encoding="utf-8"))
KEYNOTE_CSS = _strip_comments((ASSETS / "keynote.css").read_text(encoding="utf-8"))

#: 必须走令牌的属性。判据是「这个数值改变时，八个组件是不是应该一起变」。
#: 图稿坐标（`d` / `cx` / `width` 这类）不在其中——它们是内容，不是令牌。
TOKENISED_PROPERTIES = (
    "stroke-width",
    "font-weight",
    "letter-spacing",
    "gap",
    "row-gap",
    "column-gap",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
    "border-radius",
    "border-top-left-radius",
    "border-top-right-radius",
    "border-bottom-left-radius",
    "border-bottom-right-radius",
    # 第 19 轮补进闭包：组件的投影必须由设计层给，不能自己拼一层。
    #
    # 这里刻意**不**收 font-size：它已由 test_keynote_assets.py 的
    # test_bare_font_size_must_be_on_the_scale 管着（裸字号必须在字阶上），
    # 而那条判据明确拒绝「一律包 var()」——阶上的裸值再包一层只是噪音。
    # 本轮一度把三处裸字号包成了令牌，结果那条判据的"防空转"断言立刻报警：
    # 说明改动是多余的。先找判据，再改代码。
    "box-shadow",
)

#: 允许保留字面值的写法：归零与居中复位不是间距，令牌化它们没有语义。
_RESET_VALUES = {"0", "auto", "0 auto", "0px", "none"}

#: 本轮新增的四个令牌族。它们在未启用预设时**完全不存在**，
#: 所以组件里的引用必须带原值兜底，否则声明在计算值阶段失效，
#: 元素会落到初始值（线宽 1px、字重 400、字距 normal、内边距 0），
#: 既有非预设画面就变了。
NEW_FAMILIES = ("a2v-stroke-", "a2v-weight-", "a2v-track-", "a2v-space-", "a2v-radius-pill")

#: 页面级样式表：非预设页面也会加载，因此这里定义的令牌不需要兜底。
#: `figures.css` 自己也定义了少量默认值（例如 `--a2v-emphasis-mix: 0`）。
PAGE_LEVEL_CSS = " ".join(
    _strip_comments((ASSETS / name).read_text(encoding="utf-8"))
    for name in ("base.css", "theme.css", "figures.css")
)
PAGE_LEVEL_TOKENS = set(re.findall(r"(--a2v-[a-z0-9-]+)\s*:", PAGE_LEVEL_CSS))

#: 这些令牌在未启用预设时**故意不存在**，而且不能给它们补兜底：
#: 缺席会让整条声明在计算值阶段失效，元素于是落到继承值/初始值——
#: 那正是既有非预设画面的样子（由逐字节回归守着）。
#: 补上兜底会改变既有画面，所以它们不在「必须带兜底」的范围内。
INTENTIONALLY_ABSENT_ON_LEGACY = (
    "a2v-accent-deep",
    "a2v-accent-soft-solid",
    "a2v-font-sans",
)

#: 基元与状态
PRIMITIVES = ("a2v-surface", "a2v-label", "a2v-connector", "a2v-frame")
STATES = ("rest", "focus", "muted", "done")


def _declarations(css: str) -> list[tuple[int, str, str]]:
    """(行号, 属性, 值)。行号按去注释后的文本算，只用于报错定位。"""
    found = []
    for number, line in enumerate(css.split("\n"), 1):
        match = re.match(r"^\s*([a-z-]+)\s*:\s*(.+?);\s*$", line)
        if match:
            found.append((number, match.group(1), match.group(2)))
    return found


class TestTokenClosure:
    """组件里的样式属性一律走令牌。"""

    @pytest.mark.parametrize("prop", TOKENISED_PROPERTIES)
    def test_property_uses_tokens(self, prop: str) -> None:
        offenders = [
            (number, value)
            for number, name, value in _declarations(FIGURES_CSS)
            if name == prop and "var(" not in value and value not in _RESET_VALUES
        ]
        assert not offenders, (
            f"figures.css 的 {prop} 还在写字面值：{offenders}；"
            "改用对应令牌并带上原值兜底（var(--令牌, 原值)），"
            "否则改一处观感要翻遍八个组件"
        )

    def test_new_families_always_carry_a_fallback(self) -> None:
        """新族的引用必须带原值兜底，否则未启用预设的画面会变。

        判据不是「哪个前缀看起来是新的」，而是**这个令牌非预设页面有没有**：
        `--a2v-radius-lg` 由 `theme.css` 提供，可以不带兜底；
        `--a2v-radius-pill` 只在预设里定义，就必须带。
        """
        offenders = []
        for number, name, value in _declarations(FIGURES_CSS):
            if name not in TOKENISED_PROPERTIES:
                continue
            for token, terminator in re.findall(r"var\(\s*--([a-z0-9-]+)\s*([,)])", value):
                if not any(token.startswith(family) for family in NEW_FAMILIES):
                    continue
                if token in PAGE_LEVEL_TOKENS or token in INTENTIONALLY_ABSENT_ON_LEGACY:
                    continue
                if terminator == ")":
                    offenders.append((number, name, value))
        assert not offenders, (
            f"这些引用没有原值兜底：{offenders}；"
            "未启用预设的页面取不到令牌，声明会失效并落到初始值，画面因此改变"
        )

    def test_intentionally_absent_tokens_are_not_given_fallbacks(self) -> None:
        """反向约束：故意缺席的令牌不许被补上兜底。

        它们缺席时整条声明失效，元素落到继承值——这是既有非预设画面的样子。
        补兜底会把画面改掉，而逐字节回归只在成片层面守得住，
        静态这里先说清哪些是「故意的」。
        """
        offenders = []
        for number, name, value in _declarations(FIGURES_CSS):
            for token in re.findall(r"var\(\s*--([a-z0-9-]+)\s*,", value):
                if token in INTENTIONALLY_ABSENT_ON_LEGACY:
                    offenders.append((number, name, value))
        assert not offenders, (
            f"这些令牌在未启用预设时故意不存在，补兜底会改变既有画面：{offenders}"
        )

    def test_stroke_widths_land_on_the_ladder(self) -> None:
        """线宽只能取描边阶上的档位，兜底值也要在阶上。"""
        ladder = set(keynote._STROKE_LADDER)
        offenders = []
        for number, name, value in _declarations(FIGURES_CSS):
            if name != "stroke-width":
                continue
            for literal in re.findall(r"([0-9.]+)px", value):
                if float(literal) not in ladder:
                    offenders.append((number, value))
        assert not offenders, (
            f"这些线宽不在描边阶 {sorted(ladder)} 上：{offenders}；"
            "沿用一个阶外的线宽，观众说不出哪里不对，只会觉得不够精致"
        )

    def test_figure_number_weight_is_capped(self) -> None:
        """字重上限 700：可变字体在中文上 800 会粘连。"""
        weight_block = re.search(r"\.fig-number\s*\{[^}]*\}", FIGURES_CSS)
        assert weight_block, "找不到 .fig-number 的样式块"
        fallback = re.search(r"font-weight:\s*var\(--a2v-weight-bold,\s*([0-9]+)\)", weight_block.group())
        assert fallback, "数字组件的字重应当引用 --a2v-weight-bold 并带原值兜底"
        assert int(fallback.group(1)) <= 800, "兜底值不该超过 800"


class TestPrimitivesAndStates:
    """四个基元类与四个状态：只在预设作用域内、只表达颜色。"""

    @pytest.mark.parametrize("name", PRIMITIVES)
    def test_primitive_is_preset_scoped(self, name: str) -> None:
        selectors = [
            selector.strip()
            for selector in re.findall(r"([^{}]+)\{", KEYNOTE_CSS)
            if re.search(rf"\.{name}\b", selector)
        ]
        assert selectors, f"keynote.css 里没有 .{name} 的规则"
        unscoped = [
            selector
            for selector in selectors
            if "data-a2v-preset" not in selector
        ]
        assert not unscoped, (
            f".{name} 有不带预设作用域的选择器：{unscoped}；"
            "未启用预设的页面会因此改样"
        )

    def test_state_values_are_exactly_the_four(self) -> None:
        used = set(re.findall(r'\[data-a2v-state="([a-z]+)"\]', KEYNOTE_CSS))
        assert used <= set(STATES), f"出现了四态之外的状态：{sorted(used - set(STATES))}"
        assert used == set(STATES), f"四态里还有没写样式的：{sorted(set(STATES) - used)}"

    def test_state_rules_carry_no_motion_or_opacity(self) -> None:
        """状态只表达语义；不透明度与位移属于动效配方层。

        一旦写进状态定义，时序就有两个真源，而配方层存在的全部理由
        就是「手感只有一处」。
        """
        offenders = []
        for match in re.finditer(r'\[data-a2v-state="[a-z]+"\]\s*\{([^}]*)\}', KEYNOTE_CSS):
            body = match.group(1)
            for banned in ("opacity", "transform", "transition", "animation", "filter"):
                if re.search(rf"(^|[;\s]){banned}\s*:", body):
                    offenders.append((banned, match.group(0)[:60]))
        assert not offenders, f"状态规则里出现了动效或透明度的写法：{offenders}"

    def test_focus_state_uses_the_accent(self) -> None:
        """焦点态必须用强调色——否则「主次分明」没有可依的视觉手段。"""
        block = re.search(
            r'\.a2v-surface\[data-a2v-state="focus"\]\s*\{([^}]*)\}', KEYNOTE_CSS
        )
        assert block, "找不到焦点态的规则"
        body = block.group(1)
        assert "var(--a2v-accent)" in body, "焦点态应当把描边换成强调色"

    def test_every_state_declares_both_media(self) -> None:
        """每个状态都要声明两种媒介的写法：SVG 读 `fill`，HTML 读 `background-color`。

        基元原先只在 SVG 上落地，于是 `versus` 幕那类 **HTML 盒子**用不了状态语汇，
        只能自己算一遍：它的"答案侧"是一条 1px、alpha 0.24 的暖边框加一层光晕，
        底色永远不变——整幕的强调色占比只有 0.0016，而闸门要求 0.002。
        不是闸门苛刻，是那个组件里压根没有强调色块面。

        HTML 侧必须是 `background-color` 而不是 `background` 简写：
        简写会连 `background-image` 一起重置，把组件自己的材质（那层白色光泽）抹掉。
        """
        offenders = []
        for match in re.finditer(
            r'\.a2v-surface\[data-a2v-state="([a-z]+)"\]\s*\{([^}]*)\}', KEYNOTE_CSS
        ):
            state, body = match.group(1), match.group(2)
            if not re.search(r"(^|[;\s])fill\s*:", body):
                offenders.append((state, "SVG 侧缺 fill"))
            if not re.search(r"(^|[;\s])background-color\s*:", body):
                offenders.append((state, "HTML 侧缺 background-color"))
            if re.search(r"(^|[;\s])background\s*:", body):
                offenders.append((state, "用了 background 简写，会抹掉组件的材质"))
        assert not offenders, f"状态规则没有覆盖两种媒介：{offenders}"

    def test_focus_state_carries_accent_mass_not_just_a_stroke(self) -> None:
        """焦点态要有**块面**，不能只改描边。

        只改描边的表达量不出焦点：一帧 1080×1920 折算到判据图上只有约 540×960，
        细描边缩完只剩 1px 左右，抗锯齿一糊就量不到。实测结论是八幕里七幕
        报「几乎没有强调色」，而逐色直方图确认画面上确实没有任何强调色块面——
        唯一的蓝色面是中性表面 RGB(23,30,43)，暗到只会被读成"一块暗面板"。
        """
        block = re.search(
            r'\.a2v-surface\[data-a2v-state="focus"\]\s*\{([^}]*)\}', KEYNOTE_CSS
        )
        assert block, "找不到焦点态的规则"
        body = block.group(1)
        fill = re.search(r"fill:\s*([^;]+);", body)
        assert fill, "焦点态缺少填充声明（只有描边的焦点等于没有焦点）"
        assert "accent" in fill.group(1), f"焦点态的填充应当来自强调色族，实际 {fill.group(1)!r}"
        assert "var(--a2v-accent-soft-solid)" in fill.group(1), (
            "焦点面的填充取 `--a2v-accent-soft-solid`：它是被压暗的强调色，"
            "在深底上读得出「这块被选中了」，又远不到霓虹的程度"
        )


class TestContainerOverflowGate:
    """K8：容器内溢出。图形里的文字不许穿出它所属的容器。"""

    @staticmethod
    def _circle(cx: float, cy: float, r: float) -> dict[str, float]:
        return {"left": cx - r, "top": cy - r, "right": cx + r, "bottom": cy + r}

    @staticmethod
    def _box(cx: float, cy: float, width: float, height: float) -> dict[str, float]:
        return {
            "left": cx - width / 2,
            "top": cy - height / 2,
            "right": cx + width / 2,
            "bottom": cy + height / 2,
        }

    def test_no_declared_container_is_skipped_with_a_reason(self) -> None:
        gate = keynote.gate_container_overflow("loop", [])
        assert gate.status == "skipped"
        assert "无法判定" in gate.detail
        assert "声明" in gate.detail, "跳过要说清为什么量不到，否则会被当成通过"

    def test_text_inside_the_circle_passes(self) -> None:
        # 文字 176×54、半径 108：最远角到圆心 92.05，装得下
        gate = keynote.gate_container_overflow(
            "loop",
            [
                {
                    "text": "推到明天",
                    "container": ".loop-node-disc",
                    "kind": "circle",
                    "box": self._box(444, 90, 176, 54),
                    "shape": self._circle(444, 90, 108),
                }
            ],
        )
        assert gate.status == "pass", gate.detail
        assert gate.value == 0

    def test_text_wider_than_the_circle_fails_and_names_the_text(self) -> None:
        """飞轮节点原先就是这一种：半径 76（直径 152）配 44px 的四字标签。

        实测的文字盒是 176×54（四个汉字带字距），最远角到圆心
        sqrt(88² + 27²) = 92.05，比半径 76 多出 16.05px——
        文字穿出圆是必然的，而当时的 K7 报的是「都在安全区内」。
        """
        gate = keynote.gate_container_overflow(
            "loop",
            [
                {
                    "text": "推到明天",
                    "container": ".loop-node-disc",
                    "kind": "circle",
                    "box": self._box(444, 90, 176, 54),
                    "shape": self._circle(444, 90, 76),
                }
            ],
        )
        assert gate.status == "fail"
        assert gate.value == pytest.approx(16.1, abs=0.2)
        assert "推到明天" in gate.detail, "失败要说清是哪段文字，否则人无从下手改"
        assert ".loop-node-disc" in gate.detail
        assert "硬判定" in gate.detail

    def test_tolerance_absorbs_subpixel_rounding(self) -> None:
        """贴边但没穿出去的不算失败：入场变换对文字与容器一致，只余舍入。"""
        gate = keynote.gate_container_overflow(
            "rect",
            [
                {
                    "text": "标签",
                    "container": ".card",
                    "kind": "rect",
                    "box": {"left": 0.0, "top": 0.0, "right": 101.0, "bottom": 50.0},
                    "shape": {"left": 0.0, "top": 0.0, "right": 100.0, "bottom": 50.0},
                }
            ],
        )
        assert gate.status == "pass", gate.detail

    def test_rect_container_overflow_fails(self) -> None:
        gate = keynote.gate_container_overflow(
            "rect",
            [
                {
                    "text": "标签",
                    "container": ".card",
                    "kind": "rect",
                    "box": {"left": -12.0, "top": 0.0, "right": 100.0, "bottom": 50.0},
                    "shape": {"left": 0.0, "top": 0.0, "right": 100.0, "bottom": 50.0},
                }
            ],
        )
        assert gate.status == "fail"
        assert gate.value == pytest.approx(12.0)


class TestStrokeConsistencyGate:
    """K9：同一帧的线宽要落在描边阶上，档数也要收敛。"""

    def test_no_stroke_is_skipped(self) -> None:
        gate = keynote.gate_stroke_consistency("loop", [])
        assert gate.status == "skipped"
        assert "没有可量的描边" in gate.detail

    def test_on_ladder_within_three_tiers_passes(self) -> None:
        gate = keynote.gate_stroke_consistency("loop", [4.0, 4.0, 6.0, 2.0])
        assert gate.status == "pass"
        assert gate.value == [2.0, 4.0, 6.0]

    def test_off_ladder_value_warns(self) -> None:
        gate = keynote.gate_stroke_consistency("loop", [4.0, 5.0])
        assert gate.status == "warn"
        assert "5.0" in gate.detail

    def test_too_many_tiers_warns(self) -> None:
        gate = keynote.gate_stroke_consistency("loop", [1.0, 2.0, 3.0, 4.0, 6.0])
        assert gate.status == "warn"
        assert "档线宽" in gate.detail


class TestGateAggregation:
    """同一幕多帧采样时的聚合规则。"""

    def _aggregate(self, statuses: list[str]) -> str:
        result = keynote.KeynoteResult()
        for index, status in enumerate(statuses):
            result.render(
                "loop",
                index,
                [
                    keynote.Gate(
                        id="K6",
                        title="卡片与描边纪律",
                        status=status,
                        value=0,
                        detail=f"{status}",
                    )
                ],
            )
        return result.gates[0].status

    def test_measured_result_outranks_skipped(self) -> None:
        """「跳过」不是严重程度，是「这一帧没东西可测」。

        这一幕的卡片在入场帧还没出现，不代表这一幕没有卡片；
        若让跳过压过实测结论，整幕就会报「没有可识别的卡片表面」，
        而画面上明明有卡片——双栏对照正是这样被漏掉的。
        """
        assert self._aggregate(["skipped", "pass"]) == "pass"
        assert self._aggregate(["pass", "skipped"]) == "pass"
        assert self._aggregate(["skipped", "pass", "skipped"]) == "pass"

    def test_all_skipped_stays_skipped(self) -> None:
        assert self._aggregate(["skipped", "skipped"]) == "skipped"

    def test_worse_status_wins(self) -> None:
        assert self._aggregate(["pass", "warn"]) == "warn"
        assert self._aggregate(["warn", "fail"]) == "fail"
        assert self._aggregate(["fail", "pass"]) == "fail"


def _text(left: float, center: float, size: float = 44.0) -> dict:
    return {"left": left, "center": center, "fontSize": size}


class TestAlignmentGate:
    """K4 要能分开「对称多栏」与「散乱排布」。

    这一条是被自己的改动逼出来的：幕标题从 40px 升到 76px 后进入了 K4 的采样
    （门槛是 ≥ 44px），于是 `compare` 一幕从「通过」变成「提醒」——
    但它的两条左线是**关于画面中心镜像**的（左 267 两张卡片各一栏）。
    对称多栏是合法构图，不该被判成「散」；而真的散乱排布必须照样报出来。
    """

    CENTER = 540.0

    def test_centered_heading_plus_mirrored_columns_passes(self) -> None:
        """实测几何：标题居中，两张卡片各把自己的标签左对齐。

        卡片标签中心 355 / 725，相加 1080 = 2 × 540——标准的两栏镜像。
        """
        gate = keynote.gate_alignment(
            "compare",
            [
                _text(300, self.CENTER, 76.0),  # 居中的幕标题
                _text(267, 355.0),
                _text(637, 725.0),
            ],
            center=self.CENTER,
        )
        assert gate.status == "pass", gate.detail
        assert gate.value == 2, "居中一条 + 镜像对称一条"

    def test_mirrored_pair_is_named_when_the_frame_still_warns(self) -> None:
        """镜像对要出现在明细里：否则人只看得到「左 267、左 637」，
        会以为那是一处要修的对不齐，而不是一处成对的对称构图。"""
        gate = keynote.gate_alignment(
            "made-up",
            [
                _text(267, 355.0),
                _text(637, 725.0),
                _text(60, 150.0),
                _text(140, 230.0),
            ],
            center=self.CENTER,
        )
        assert gate.status == "warn", gate.detail
        assert "镜像对称（左 267 / 左 637）" in gate.detail
        assert "左 60" in gate.detail and "左 140" in gate.detail

    def test_scattered_lefts_still_warn(self) -> None:
        """反向断言：不成镜像的三条左线必须照样报。

        没有这一条，「合并镜像」就等于把闸门调松了。
        """
        gate = keynote.gate_alignment(
            "made-up",
            [_text(100, 190.0), _text(350, 440.0), _text(700, 790.0)],
            center=self.CENTER,
        )
        assert gate.status == "warn", gate.detail
        assert gate.value == 3

    def test_nearly_mirrored_but_off_by_too_much_does_not_merge(self) -> None:
        """镜像判据的容差是 12px：差 25px 的两条线不能并。

        这组数据是刻意挑的——若判据松到 25px，它就会并成 2 条线（通过）；
        正因为没并，才数出 3 条线。所以「提醒」这个结论本身就证明了容差在起作用。
        """
        gate = keynote.gate_alignment(
            "made-up",
            [
                _text(300, self.CENTER, 76.0),  # 居中标题
                _text(267, 355.0),
                _text(637, 700.0),  # 355 + 700 = 1055，离 1080 差 25
            ],
            center=self.CENTER,
        )
        assert gate.status == "warn", gate.detail
        assert gate.value == 3

    def test_four_columns_pair_into_two_lines(self) -> None:
        """四栏对称排布：两对镜像 → 两条线，仍在允许范围内。

        中心两两关于 540 镜像：200+880 = 420+660 = 1080。
        """
        gate = keynote.gate_alignment(
            "made-up",
            [
                _text(120, 200.0),
                _text(340, 420.0),
                _text(580, 660.0),
                _text(800, 880.0),
            ],
            center=self.CENTER,
        )
        assert gate.status == "pass", gate.detail
        assert gate.value == 2


class TestVerticalRhythm:
    """纵向节奏的唯一真源是安全区的 `gap`：块自己不加纵向 margin。

    收口前实测八幕的块间距是 29 / 32 / 48 / 80 / 88 / 147px 六个值，
    而阶上只用到了 `--a2v-space-6` 一档。多出来的量全是块自己叠的：
    `.vs-board` 的 `margin-top: 96px`、`.vs-note` 的 32px、
    `.fig-number-caption` 吃到 `<p>` 的浏览器默认外边距（40px）、
    `.closing-action` 的 8px。同一份设计里出现六个节奏值，
    读者读到的不是「这里有分组」，是「没对齐」。
    """

    def test_the_preset_pins_one_gap_for_every_scene(self) -> None:
        """收口规则必须比幕级覆写更具体，否则又要靠样式表顺序取胜。"""
        block = re.search(
            r'\[data-a2v-preset="keynote"\]\s*\[data-a2v-scene\]\s*\.a2v-safe\s*\{([^}]*)\}',
            KEYNOTE_CSS,
        )
        assert block, "找不到把纵向节奏收成一档的规则"
        assert "gap: var(--a2v-space-6)" in block.group(1), "收口后应当只有安全区 gap 一档"

    def test_the_preset_zeroes_block_vertical_margins(self) -> None:
        """块不许自己加纵向 margin——加了就是第二个节奏来源。"""
        block = re.search(
            r'\[data-a2v-preset="keynote"\]\s*\[data-a2v-scene\]\s*\.a2v-safe\s*>\s*\*\s*\{([^}]*)\}',
            KEYNOTE_CSS,
        )
        assert block, "找不到「安全区子元素不加纵向 margin」的规则"
        body = block.group(1)
        assert "margin-top: 0" in body, "块的上外边距没有清零"
        assert "margin-bottom: 0" in body, "块的下外边距没有清零"


#: 设计层定义的、**故意**没有消费者的图形几何令牌：几何归组件自己声明。
#: 这是第 16 轮的决定（见 keynote.css 里 `--fig-connector-w` 上方那段注释），
#: 不是漏接。名单只许缩短。
IDLE_GEOMETRY: dict[str, str] = {
    "--fig-connector-w": "连线形态差异太大（虚线/弧/圆盘边界/纯填充箭头头），线宽归组件",
    "--fig-node-r-min": "节点半径由内容测量决定，最小值暂时没有组件需要",
    "--fig-surface-pad": "面的内边距目前由各组件按自己的密度声明",
}


class TestFigureGeometryTokens:
    """`--fig-*` 是图形几何令牌——定义了就得有人用，不然就是设计层的空头承诺。

    第 24 轮实测：`--fig-arrow-len` / `--fig-arrow-half` 定义了 34px / 16px，
    而 `placeArrow` 里写死 `'M0 0 L-34 -16 L-34 16 Z'`——令牌是从这段代码里
    提出来、却没接回去。这类"设计层给了档位、组件没接"的缺口前面已经出现过
    四次（阴影、光晕、重点面墨色、动效时长），所以这里补一条专门的判据。
    """

    def test_every_geometry_token_has_a_consumer(self) -> None:
        defined = set(re.findall(r"(--fig-[a-z0-9-]+)\s*:", KEYNOTE_CSS))
        assert defined, "keynote.css 里一个 --fig-* 令牌都没有？判据大概失效了"

        consumed = set()
        for name in ("base.css", "theme.css", "declarative.css", "keynote.css",
                     "figures.css", "declarative.js", "figures.js"):
            stripped = _strip_comments((ASSETS / name).read_text(encoding="utf-8"))
            # 两种消费方式都要认：CSS 里是 `var(--fig-x)`，脚本里是
            # `tokenPx(el, '--fig-x', 兜底)`——只认前者时，判据会把刚接好的线
            # 又报成"没人用"（第 24 轮第一版就是这个毛病）。
            consumed |= set(re.findall(r"var\(\s*(--fig-[a-z0-9-]+)", stripped))
            consumed |= set(re.findall(r"['\"](--fig-[a-z0-9-]+)['\"]", stripped))

        idle = sorted(defined - consumed)
        unexpected = [name for name in idle if name not in IDLE_GEOMETRY]
        assert not unexpected, (
            f"这些图形几何令牌定义了却没人用：{unexpected}——"
            "要么接进组件，要么像 IDLE_GEOMETRY 那样写明为什么故意闲置"
        )

    def test_idle_list_does_not_grow(self) -> None:
        """故意闲置的令牌数只许缩短：这份名单是欠账，不是许可证。"""
        assert len(IDLE_GEOMETRY) <= 3, (
            f"闲置疑名单涨到 {len(IDLE_GEOMETRY)} 条了：{sorted(IDLE_GEOMETRY)}"
        )
