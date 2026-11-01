"""设计令牌的对比度预算与单一真源。

这一组守的是一类以前完全没有守卫的静默失效：

- 令牌**有定义**由 `TestClassification.test_every_token_is_classified` 把关：
  画面引用的每个 `--fig-*` 令牌都必须在分类表里；
- 正文对比度只量 DOM 里的**文本样张**，SVG 的 `fill` / `stroke` 不在量程内；
- 留白预算量的是背景像素占比——图形越淡，背景占比越高，**越容易通过**。

三者叠起来的结果是：`--fig-line-soft` 只有 1.63:1，而所有检查全绿。
这里把「图形看不看得见」变成可验证契约。

令牌只有**一层**（`tokens.css` 的 `@theme static`），因此这一组不再按主题
分块量测；`TestSingleSource` 反过来守住「不许再出现作用域层」——曾经
`:root[data-m2v-preset='keynote']` 承载了整套字阶与间距，而没有任何代码会挂上
那个属性，于是作品里的 `var(--m2v-space-3)` 一直是空值。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOKENS_CSS = ROOT / "web" / "src" / "styles" / "tokens.css"

#: 图形颜色令牌的分类表。新增令牌必须先进这张表，否则
#: `test_every_token_is_classified` 会失败——「没有对应规则」不等于「可以放行」。
#: 取值：`(类, 判定参照)`，参照为 `bg`（对 `--m2v-bg-0`）或 `ink`（对 `--fig-ink` 成对判定）。
CLASSES: dict[str, tuple[str, str]] = {
    "--fig-line": ("数据描边", "bg"),
    "--fig-line-data": ("数据描边", "bg"),
    "--fig-water-line": ("数据描边", "bg"),
    "--fig-water-text": ("图形内文本", "bg"),
    "--fig-line-soft": ("装饰描边", "bg"),
    "--fig-ink": ("面填充", "-"),
    "--fig-on-ink": ("图形内文本", "ink"),
    "--fig-surface": ("面填充", "-"),
    "--fig-water": ("面填充", "-"),
    "--fig-hollow": ("面填充", "-"),
    "--fig-node-shadow": ("面填充", "-"),
    "--fig-drop-track": ("面填充", "-"),
    "--fig-drop-fill-from": ("面填充", "-"),
    "--fig-drop-fill-to": ("面填充", "-"),
    "--fig-drop-fact-from": ("面填充", "-"),
    "--fig-drop-fact-to": ("面填充", "-"),
    "--fig-gauge-track": ("面填充", "-"),
    "--fig-title-grad-from": ("图形内文本", "bg"),
    "--fig-title-grad-to": ("图形内文本", "bg"),
    # 边界描边：判据基座是它落座的面（抬升面 `--m2v-bg-2`），不是画布。
    # 同一个颜色在两层的比值不同（分隔线对画布 1.52:1、对抬升面 1.64:1），
    # 拿画布去量一个压在面板上的边框，只会得到一个乐观的数字。
    "--m2v-hairline-strong": ("边界描边", "bg2"),
    "--m2v-line": ("边界描边", "bg"),
}

#: 每类的对比度下限。面填充**没有**下限：形状的可读性由数据描边负责，
#: 而面阶本身（`--m2v-bg-0` → `--m2v-surface-1`）就只有 1.1:1 左右，
#: 给面填充设下限会把正确的做法判成缺陷。
BUDGETS: dict[str, float] = {
    "数据描边": 4.5,
    "图形内文本": 4.5,
    "边界描边": 3.0,
    "装饰描边": 1.5,
}

#: 判定基座：`bg` → `--m2v-bg-0`，`bg2` → `--m2v-bg-2`，`ink` → 对 `--fig-ink` 成对判定。
BASES = {"bg": "--m2v-bg-0", "bg2": "--m2v-bg-2"}

#: 纯分隔线：刻意保持耳语。WCAG 1.4.11 管的是「理解内容所必需的图形对象」，
#: 纯分隔线本来就在豁免范围内；每条都提到 3:1 会让画面整体变重、层次变平。
#: 单独列出来，是为了让「不抬高它」也成为一条被守住的决定，而不是一句注释。
DECORATIVE_SEPARATORS = {"--m2v-hairline": "--m2v-bg-2"}

#: 令牌定义里不允许再出现的旧作用域选择器。
FORBIDDEN_SCOPES = ("data-m2v-preset", "data-m2v-theme", "data-m2v-style-pack")


def _rgb(value: str) -> tuple[int, int, int, float]:
    value = value.strip()
    hex_match = re.fullmatch(r"#([0-9a-fA-F]{6})", value)
    if hex_match:
        raw = int(hex_match.group(1), 16)
        return ((raw >> 16) & 255, (raw >> 8) & 255, raw & 255, 1.0)
    fn_match = re.fullmatch(r"rgba?\(([^)]+)\)", value)
    if not fn_match:
        raise AssertionError(f"无法解析的颜色取值：{value}")
    parts = [part.strip() for part in fn_match.group(1).split(",")]
    red, green, blue = (int(round(float(part))) for part in parts[:3])
    alpha = float(parts[3]) if len(parts) > 3 else 1.0
    return (red, green, blue, alpha)


def _composite(
    foreground: tuple[int, int, int, float], background: tuple[int, int, int, float]
) -> tuple[float, float, float]:
    red, green, blue, alpha = foreground
    return (
        red * alpha + background[0] * (1 - alpha),
        green * alpha + background[1] * (1 - alpha),
        blue * alpha + background[2] * (1 - alpha),
    )


def _luminance(color: tuple[float, float, float]) -> float:
    def channel(value: float) -> float:
        value /= 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(color[0]) + 0.7152 * channel(color[1]) + 0.0722 * channel(color[2])


def _contrast(
    foreground: tuple[float, float, float], background: tuple[float, float, float]
) -> float:
    one, two = _luminance(foreground), _luminance(background)
    return (max(one, two) + 0.05) / (min(one, two) + 0.05)


def _theme_block() -> dict[str, str]:
    """从 `tokens.css` 的 `@theme static` 块里抽出全部令牌取值。

    只认那一个块：别的 `:root` 规则（例如 `color-scheme`）不提供令牌，
    混进来会让「抽到了什么」变成看文件顺序的事。
    """
    source = TOKENS_CSS.read_text(encoding="utf-8")
    start = source.find("@theme static")
    assert start != -1, "`tokens.css` 里找不到 `@theme static` 块"
    depth, index, end = 0, source.find("{", start), -1
    while index < len(source):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
        index += 1
    assert end != -1, "`@theme static` 块没有闭合"
    segment = source[source.find("{", start) : end]
    tokens: dict[str, str] = {}
    # 连 `--m2v-*` 一起抽：边界描边的判据基座是抬升面 `--m2v-bg-2`，
    # 只抽 `--fig-*` 就拿不到基座。
    for match in re.finditer(r"(--[a-z0-9-]+):\s*([^;]+);", segment):
        tokens[match.group(1)] = match.group(2).strip()
    figure_tokens = {k: v for k, v in tokens.items() if k.startswith("--fig-")}
    assert figure_tokens, "令牌块里没有抽出任何图形颜色令牌"
    for base in ("--m2v-bg-0", "--m2v-bg-2"):
        assert base in tokens, f"令牌块里没有 {base}，无法做判定基座"
    return tokens


TOKENS = _theme_block()


def _figure_tokens() -> dict[str, str]:
    return {
        k: v for k, v in TOKENS.items()
        if k.startswith("--fig-")
        and k not in {"--fig-surface-pad", "--fig-connector-w"}
        and ("#" in v or "rgb" in v or v.startswith("var("))
    }


def _ratio(value: str, base: str = "--m2v-bg-0") -> float:
    canvas = _rgb(TOKENS[base])
    return _contrast(_composite(_rgb(value), canvas), _composite(canvas, canvas))


def _resolved(token: str) -> str:
    """跟着 `var()` 取值，最多五层。令牌互相引用时不至于量成一个字符串。"""
    value = TOKENS.get(token)
    assert value is not None, f"令牌块里没有 {token}"
    for _ in range(5):
        match = re.fullmatch(r"var\(\s*(--[a-z0-9-]+)\s*(?:,[^)]*)?\)", value.strip())
        if not match:
            return value.strip()
        value = TOKENS[match.group(1)]
    raise AssertionError(f"{token} 的 var() 链条超过五层，可能有环")


@pytest.fixture(scope="module")
def over_budget() -> list[tuple[str, str, str, float, float]]:
    """返回所有不达标的条目，供逐类断言与失败信息共用。"""
    failures = []
    for token, (klass, reference) in CLASSES.items():
        budget = BUDGETS.get(klass)
        if budget is None or reference == "-":
            continue
        value = TOKENS.get(token)
        if value is None:
            continue
        if reference == "ink":
            ink = TOKENS.get("--fig-ink")
            ratio = _contrast(_rgb(value)[:3], _rgb(ink)[:3])
        else:
            ratio = _ratio(value, BASES[reference])
        if ratio < budget:
            failures.append((token, klass, value, ratio, budget))
    return failures


class TestSingleSource:
    def test令牌只有一层(self):
        """不许再出现按属性切换的作用域层。

        `:root[data-m2v-preset='keynote']` 曾经承载整套字阶、间距、圆角与描边阶，
        而没有任何代码会挂上那个属性：那 103 个令牌在运行时永远取不到，
        作品里的 `var(--m2v-space-3)` 一直是空值。作用域层一回来，
        这条会先失败。
        """
        source = TOKENS_CSS.read_text(encoding="utf-8")
        # 先剥注释：文件头的沿革说明会提到这些名字，那不是作用域层
        live = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
        for scope in FORBIDDEN_SCOPES:
            assert scope not in live, (
                f"`tokens.css` 里又出现了 `{scope}` 作用域层；"
                "令牌必须是单层，否则取值取决于有没有代码挂那个属性"
            )

    def test令牌块声明了画布尺寸(self):
        # 渲染脚本把视口设成这个尺寸，布局量测的绝对坐标判据依赖它
        assert TOKENS["--m2v-width"] == "1080px"
        assert TOKENS["--m2v-height"] == "1920px"

    def test间距与圆角阶在令牌块里(self):
        # 这两阶曾经只写在预设层里，作品引用时取不到值
        for name in ("--m2v-space-1", "--m2v-space-3", "--m2v-space-10",
                     "--m2v-radius-xs", "--m2v-radius-sm", "--m2v-radius-md",
                     "--m2v-radius-lg", "--m2v-radius-xl", "--m2v-radius-pill"):
            assert name in TOKENS, f"{name} 不在令牌块里，作品引用它会取到空值"

    def test字号与描边阶在令牌块里(self):
        # 同一类失效：阶缺一档时引用它的画面会静默落到初始值
        for name in ("--m2v-size-caption", "--m2v-size-body",
                     "--m2v-leading-body", "--m2v-tracking-label",
                     "--m2v-weight-regular", "--m2v-weight-bold",
                     "--m2v-stroke-1", "--m2v-stroke-5",
                     "--m2v-ink-1", "--m2v-text-1", "--m2v-line", "--m2v-hairline"):
            assert name in TOKENS, f"{name} 不在令牌块里，画面引用它会取到空值"


class TestClassification:
    def test_every_token_is_classified(self):
        # 「没有对应规则」不等于「可以放行」：新令牌必须先归类
        unknown = sorted(set(_figure_tokens()) - set(CLASSES))
        assert not unknown, (
            f"令牌块里有未归类的图形颜色令牌：{unknown}；"
            "请先在 tests/common/test_figure_contrast.py 的 CLASSES 里归类"
        )

    def test_budgets_cover_every_class_that_needs_one(self):
        classes = {klass for klass, reference in CLASSES.values() if reference != "-"}
        assert classes == set(BUDGETS), f"分类与预算表不对应：{sorted(classes ^ set(BUDGETS))}"

    def test_every_class_has_a_declared_base(self):
        # 判据基座写进表里，规则才没有解释空间
        for klass, reference in CLASSES.values():
            if reference == "-":
                continue
            assert reference in BASES or reference == "ink", f"{klass} 的判定基座没定义"

    def test_fills_have_no_numeric_budget(self):
        # 面填充不设下限是刻意的：面阶本身就只有 1.1:1 左右，
        # 设下限等于要求把正确的面阶改成另一种灰。
        fills = {token for token, (klass, ref) in CLASSES.items() if klass == "面填充"}
        assert fills == {
            "--fig-ink",
            "--fig-surface",
            "--fig-water",
            "--fig-hollow",
            "--fig-node-shadow",
            "--fig-drop-track",
            "--fig-drop-fill-from",
            "--fig-drop-fill-to",
            "--fig-drop-fact-from",
            "--fig-drop-fact-to",
            "--fig-gauge-track",
        }
        assert "面填充" not in BUDGETS


class TestBoundaryStrokes:
    """边界描边：一个物体唯一可见的边界。"""

    def test_decorative_separators_stay_a_whisper(self):
        """纯分隔线刻意保持耳语，并且这件事要被守住而不是被「顺手统一」。

        WCAG 1.4.11 管的是「理解内容所必需的图形对象」，纯分隔线在豁免范围内。
        把每条分隔线都提到 3:1 会让画面整体变重、层次变平——
        规则惩罚了正确的做法。
        """
        for token, base in DECORATIVE_SEPARATORS.items():
            value = TOKENS.get(token)
            assert value is not None, f"缺少分隔线令牌 {token}"
            ratio = _ratio(value, base)
            assert ratio < 3.0, (
                f"{token} 达到了 {ratio:.2f}:1，已经不像分隔线了；"
                "要抬的是界定物体边界的那条描边，不是所有线"
            )


class TestBudgetsHold:
    def test_no_token_is_below_budget(self, over_budget):
        detail = "\n".join(
            f"  {token}（{klass}）{value} 实测 {ratio:.2f}:1，需 ≥ {budget}"
            for token, klass, value, ratio, budget in over_budget
        )
        assert not over_budget, f"图形令牌低于对比度预算：\n{detail}"

    def test_data_strokes_clear_the_floor(self):
        for token in ("--fig-line", "--fig-line-data", "--fig-water-line"):
            ratio = _ratio(TOKENS[token])
            assert ratio >= 4.5, f"{token} 只有 {ratio:.2f}:1"

    def test_the_new_data_stroke_is_actually_stronger_than_the_soft_one(self):
        # `--fig-line-data` 的存在意义就是比软线强；两者相等说明回落写法白加了
        strong = _ratio(TOKENS["--fig-line-data"])
        soft = _ratio(TOKENS["--fig-line-soft"])
        assert strong > soft, "--fig-line-data 没有比 --fig-line-soft 更强"


class TestFaceTiersStayDistinct:
    """三档面填充按**性质**区分，不能塌成同一个取值。

    这一条是「面填充不设数值下限」的另一半。实心物体（台阶柱、圆盘、块体）
    读作「细描边 + 耳语填充」，形状毫无歧义；冰山图里水上尖端是耳语填充、
    水下主体是冷色实心——**这个差就是那张图的语义**（看得见的一角与看不见的
    主体不是一回事）。所以给实心物体加重填充不是「变得更实」，
    而是把刻意做出来的层级抹平。

    数值大小不作判据，但**同不同**可以判：

      * 实心面 SHALL NOT 等于画布，否则实心物体在背景上没有面、只剩描边；
      * 实心面、次级面（水体）、空壳 SHALL NOT 塌成同一个取值。

    已知边界：`--fig-surface` 与抬升面 `--m2v-bg-2` 只差 1.01:1——所以画在面板
    **上**的实心物体没有面阶，识别只能靠描边。这是接受的取舍，不是缺陷：
    面板本身已经与画布分开了。
    """

    TIERS = ("--fig-surface", "--fig-water", "--fig-hollow")

    def test_solid_face_is_visible_against_the_canvas(self):
        surface = _resolved("--fig-surface")
        canvas = _resolved("--m2v-bg-0")
        assert _rgb(surface) != _rgb(canvas), "--fig-surface 与画布同色，实心物体在背景上没有面"
        assert _ratio(surface, "--m2v-bg-0") > 1.0

    def test_the_three_face_tiers_do_not_collapse(self):
        values = {token: _rgb(_resolved(token)) for token in self.TIERS}
        collapsed = [
            (one, other)
            for index, one in enumerate(self.TIERS)
            for other in self.TIERS[index + 1 :]
            if values[one] == values[other]
        ]
        assert not collapsed, (
            f"这几档面填充塌成了同一个取值：{collapsed}——"
            "层级会消失，水体、实心物体与空壳只剩线型之差"
        )

    def test_the_secondary_face_carries_a_tint(self):
        """次级面（水体）是唯一的冷色面：它靠色相与水下的语义绑定，不能退成中性灰。"""
        water = _rgb(_resolved("--fig-water"))
        assert water[3] < 1.0, "--fig-water 不再是与底叠合的透明面"
        spread = max(water[:3]) - min(water[:3])
        assert spread >= 20, (
            f"--fig-water（{water[:3]}）色相跨度只有 {spread}，"
            "已经接近中性灰——水下的「另一回事」会看不出来"
        )


class TestContrastMath:
    def test_known_ratios(self):
        white = _composite(_rgb("#ffffff"), _rgb("#ffffff"))
        black = _composite(_rgb("#000000"), _rgb("#000000"))
        assert _contrast(white, black) == pytest.approx(21.0, abs=0.01)

    def test_alpha_is_composited_before_measuring(self):
        # 半透明令牌必须先合成到底色：直接拿 alpha 前的取值算会高估对比度
        canvas = _rgb("#08090c")
        faint = _contrast(_composite(_rgb("rgba(255,255,255,0.18)"), canvas), _composite(canvas, canvas))
        opaque = _contrast(_rgb("#ffffff")[:3], _composite(canvas, canvas))
        assert faint < opaque
        assert faint == pytest.approx(1.63, abs=0.05)
