"""图形颜色令牌的对比度预算。

这一组测试守的是一类以前完全没有守卫的静默失效：

- 令牌**有定义**由 `TestClassification.test_both_themes_define_the_same_tokens`
  把关：`figures.css` 引用的每个 `--fig-*` 令牌在两套主题里都必须存在；
- K5 正文对比度只量 DOM 里的**文本样张**，SVG 的 `fill` / `stroke` 不在量程内；
- K1 留白预算量的是背景像素占比——图形越淡，背景占比越高，**越容易通过**。

三者叠起来的结果是：预设层的 `--fig-line-soft` 只有 1.63:1、浅色主题的主描边只有
3.31:1，而所有检查全绿。这里把「图形看不看得见」变成可验证契约。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KEYNOTE_CSS = ROOT / "web" / "src" / "styles" / "tokens.css"

#: 图形颜色令牌的分类表。新增令牌必须先进这张表，否则
#: `test_every_token_is_classified` 会失败——「没有对应规则」不等于「可以放行」。
#: 取值：`(类, 判定参照)`，参照为 `bg`（对 `--a2v-bg-0`）或 `ink`（对 `--fig-ink` 成对判定）。

#: 参与画面绘制的活样式层：v1 的 figures.css 已随整页组件删除，
#: 图形令牌的使用方是 keynote / primitives / scene-tree 这几层。
#: 剥掉注释再扫描，避免把说明文字当成令牌引用。
LIVE_STYLES = (
    ROOT / "web" / "src" / "styles" / "keynote.css",
    ROOT / "web" / "src" / "styles" / "primitives.css",
    ROOT / "web" / "src" / "styles" / "scene-tree.css",
)


def _live_css() -> str:
    parts = []
    for path in LIVE_STYLES:
        text = path.read_text(encoding="utf-8")
        parts.append(re.sub(r"/\*.*?\*/", "", text, flags=re.S))
    return "\n".join(parts)


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
    # 边界描边：判据基座是它落座的面（抬升面 `--a2v-bg-2`），不是画布。
    # 同一个颜色在两层的比值不同（深色分隔线对画布 1.52:1、对抬升面 1.64:1），
    # 拿画布去量一个压在面板上的边框，只会得到一个乐观的数字。
    "--a2v-hairline-strong": ("边界描边", "bg2"),
}

#: SVG 表现属性里允许出现的取值。「空壳」的填充曾经写死成 `rgba(22,24,29,0.035)`：
#: 在浅色页面上是很淡的灰，换到深色预设下就与底色同色——组件里写死的颜色
#: 不跟主题走，正是设计宪法里点名的那条静默失效。下面这条规则把它变成机检。
PAINT_KEYWORDS = {
    "none",
    "transparent",
    "currentcolor",
    "inherit",
    "context-fill",
    "context-stroke",
}
LITERAL_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")

#: 每类的对比度下限。面填充**没有**下限：形状的可读性由数据描边负责，
#: 而浅色主题自己的面阶（`--a2v-bg-0` → `--a2v-surface-1`）就只有 1.13:1，
#: 给面填充设下限会把正确的做法判成缺陷。
BUDGETS: dict[str, float] = {
    "数据描边": 4.5,
    "图形内文本": 4.5,
    "边界描边": 3.0,
    "装饰描边": 1.5,
}

#: 判定基座：`bg` → `--a2v-bg-0`，`bg2` → `--a2v-bg-2`，`ink` → 对 `--fig-ink` 成对判定。
BASES = {"bg": "--a2v-bg-0", "bg2": "--a2v-bg-2"}

#: 纯分隔线：刻意保持耳语。WCAG 1.4.11 管的是「理解内容所必需的图形对象」，
#: 纯分隔线本来就在豁免范围内；每条都提到 3:1 会让画面整体变重、层次变平。
#: 单独列出来，是为了让「不抬高它」也成为一条被守住的决定，而不是一句注释。
DECORATIVE_SEPARATORS = {"--a2v-hairline": "--a2v-bg-2"}

THEMES = {"keynote-dark": "dark", "keynote-light": "light"}

#: 主题块里用来做判定基准的画布色。
CANVAS = {"dark": "#08090c", "light": "#eff1f4"}


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


def _theme_blocks() -> dict[str, dict[str, str]]:
    """从 `keynote.css` 里按主题抽出图形颜色令牌的取值。

    用**带主题名的完整选择器**切块：只写 `[data-a2v-preset="keynote"]` 会先命中
    `:root[data-a2v-preset="keynote"]` 那个基础块，只写 `[data-a2v-theme` 会先命中
    深色块——两种都会让测试安静地量错东西（曾经如此）。
    """
    source = KEYNOTE_CSS.read_text(encoding="utf-8")
    blocks: dict[str, dict[str, str]] = {}
    base_selector = ":root[data-a2v-preset='keynote']"
    for theme in ("dark", "light"):
        selector = base_selector if theme == "dark" else ":root[data-a2v-preset='keynote'][data-a2v-theme='light']"
        start = source.find(selector)
        assert start != -1, f"`keynote.css` 里找不到 {theme} 主题块（选择器 {selector}）"
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
        assert end != -1, f"{theme} 主题块没有闭合"
        segment = source[source.find("{", start) : end]
        tokens: dict[str, str] = {}
        # 连 `--a2v-*` 一起抽：边界描边的判据基座是抬升面 `--a2v-bg-2`，
        # 只抽 `--fig-*` 就拿不到基座。
        for match in re.finditer(r"(--[a-z0-9-]+):\s*([^;]+);", segment):
            tokens[match.group(1)] = match.group(2).strip()
        figure_tokens = {k: v for k, v in tokens.items() if k.startswith("--fig-")}
        assert figure_tokens, f"{theme} 主题块里没有抽出任何图形颜色令牌，选择器可能又错了"
        for base in ("--a2v-bg-0", "--a2v-bg-2"):
            assert base in tokens, f"{theme} 主题块里没有 {base}，无法做判定基座"
        blocks[theme] = tokens
    return blocks


BLOCKS = _theme_blocks()


def _figure_tokens(theme: str) -> dict[str, str]:
    return {
        k: v for k, v in BLOCKS[theme].items()
        if k.startswith("--fig-")
        and k not in {"--fig-surface-pad", "--fig-connector-w"}
        and ("#" in v or "rgb" in v or v.startswith("var("))
    }


def _ratio(theme: str, value: str, base: str = "--a2v-bg-0") -> float:
    canvas = _rgb(BLOCKS[theme][base])
    return _contrast(_composite(_rgb(value), canvas), _composite(canvas, canvas))


def _resolved(theme: str, token: str) -> str:
    """跟着 `var()` 取值，最多五层。令牌互相引用时不至于量成一个字符串。"""
    value = BLOCKS[theme].get(token)
    assert value is not None, f"{theme} 主题块里没有 {token}"
    for _ in range(5):
        match = re.fullmatch(r"var\(\s*(--[a-z0-9-]+)\s*\)", value.strip())
        if not match:
            return value.strip()
        value = BLOCKS[theme][match.group(1)]
    raise AssertionError(f"{token} 的 var() 链条超过五层，可能有环")


@pytest.fixture(scope="module")
def over_budget() -> list[tuple[str, str, str, str, float, float]]:
    """返回所有不达标的条目，供逐类断言与失败信息共用。"""
    failures = []
    for theme, tokens in BLOCKS.items():
        for token, (klass, reference) in CLASSES.items():
            budget = BUDGETS.get(klass)
            if budget is None or reference == "-":
                continue
            value = tokens.get(token)
            if value is None:
                continue
            if reference == "ink":
                ink = tokens.get("--fig-ink")
                ratio = _contrast(_rgb(value)[:3], _rgb(ink)[:3])
            else:
                ratio = _ratio(theme, value, BASES[reference])
            if ratio < budget:
                failures.append((theme, token, klass, value, ratio, budget))
    return failures


class TestClassification:
    def test_every_token_is_classified(self):
        # 「没有对应规则」不等于「可以放行」：新令牌必须先归类
        known = set(CLASSES)
        for theme in BLOCKS:
            unknown = sorted(set(_figure_tokens(theme)) - known)
            assert not unknown, (
                f"{theme} 主题里有未归类的图形颜色令牌：{unknown}；"
                "请先在 tests/test_figure_contrast.py 的 CLASSES 里归类"
            )

    def test_both_themes_define_the_same_tokens(self):
        # 两套主题必须提供同一组令牌名，否则换主题就会掉回未定义的颜色
        dark, light = set(_figure_tokens("dark")), set(_figure_tokens("light"))
        assert dark == light, f"两套主题令牌不一致：{sorted(dark ^ light)}"

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
        # 面填充不设下限是刻意的：浅色主题自己的面阶（bg-0 → surface-1）就只有 1.13:1，
        # 设下限等于要求把正确的白色面阶改成灰色。
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

    def test_svg_paint_never_hardcodes_a_color(self):
        """`fill` / `stroke` / `background` 只允许引用令牌。

        写死的颜色不跟主题走。实测过两处：`.load-hollow` 的 `rgba(22,24,29,0.035)`
        在深色预设下与底色同色，「看着很大其实没有重量」的空壳只剩虚线；
        `.drop-track` 的 `rgba(22,24,29,0.025)` 与 `.drop-fill` 的
        `#3a3f4a→#23262d` 压在近黑底上，一幕「差量」只剩虚线框——
        运行时的计算值就是这两个浅色页面上的字面值。
        `test_classes_cover_the_tokens_figures_css_actually_uses`
        抓不到它们：那条只看 `var(--fig-*)` 引用，字面值是隐形的。
        """
        figures = _live_css()
        offenders = []
        for match in re.finditer(r"\b(fill|stroke|background)\s*:\s*([^;]+);", figures):
            prop, value = match.group(1), match.group(2).strip()
            # 令牌的回落位置允许写字面值——那正是「未启用预设时保持原样」的手段
            stripped = re.sub(r"var\(--[a-z0-9-]+,\s*[^()]*(?:\([^()]*\))?[^()]*\)", "var()", value)
            if stripped.lower() in PAINT_KEYWORDS or stripped.startswith("url("):
                continue
            # `rgba(var(--a2v-accent-rgb), 0.5)` 是合法的令牌用法：色值来自令牌，
            # 只有 alpha 是就地写的。所以「含 var() 且不含十六进制字面值」放行。
            if "var(--" in stripped and not re.search(r"#[0-9a-fA-F]{3,8}\b", stripped):
                continue
            if LITERAL_COLOR.search(stripped):
                offenders.append(f"{prop}: {value}")
        assert not offenders, (
            "画面样式层的 fill/stroke/background 里写死了颜色，换主题就会原地留一抹旧主题的颜色：\n  "
            + "\n  ".join(offenders)
        )


class TestBoundaryStrokes:
    """边界描边：一个物体唯一可见的边界。

    这一组守的是「承重的线躲在装饰类里」和「令牌定义了却没人用」两种失效。
    `--a2v-hairline-strong` 曾经就是后者：令牌表里有它、注释里写着 2.99:1，
    实际一处都没引用，按新基座量也只有 2.49:1。
    """

    def test_boundary_tokens_are_actually_used(self):
        figures = _live_css()
        declarations = re.findall(r"\bborder(?:-color|-top|-right|-bottom|-left)?\s*:\s*([^;]+);", figures)
        declarations += re.findall(r"\bstroke\s*:\s*([^;]+);", figures)
        text = " ".join(declarations)
        boundaries = [t for t, (klass, _) in CLASSES.items() if klass == "边界描边"]
        assert boundaries, "分类表里没有边界描边"
        for token in boundaries:
            assert f"var({token}" in text, (
                f"{token} 被归为边界描边，但组件里没有任何边界声明引用它——"
                "定义了却没人用的令牌看似成体系，实际不承担任何东西"
            )

    def test_shape_borders_use_a_token(self):
        # 场景树的形状与面板靠边框获得边界；边框一但写死颜色，换主题就失明
        figures = _live_css()
        for match in re.finditer(r"\.(?:a2v-shape-[a-z]+|a2v-primitive-surface)\s*\{([^}]*)\}", figures):
            body = match.group(1)
            if "border" not in body:
                continue
            assert "var(--" in body, (
                f"边框声明未引用令牌：{body.strip()[:80]}——写死的颜色不跟主题走"
            )

    def test_decorative_separators_stay_a_whisper(self):
        """纯分隔线刻意保持耳语，并且这件事要被守住而不是被「顺手统一」。

        WCAG 1.4.11 管的是「理解内容所必需的图形对象」，纯分隔线在豁免范围内。
        把每条分隔线都提到 3:1 会让画面整体变重、层次变平——
        这和 K2 早期「强调色占比低就判失败」是同一类误判：规则惩罚了正确的做法。
        """
        for token, base in DECORATIVE_SEPARATORS.items():
            for theme in BLOCKS:
                value = BLOCKS[theme].get(token)
                assert value is not None, f"{theme} 缺少分隔线令牌 {token}"
                ratio = _ratio(theme, value, base)
                assert ratio < 3.0, (
                    f"{theme} 的 {token} 达到了 {ratio:.2f}:1，已经不像分隔线了；"
                    "要抬的是界定物体边界的那条描边，不是所有线"
                )


class TestBudgetsHold:
    def test_no_token_is_below_budget(self, over_budget):
        detail = "\n".join(
            f"  {theme} {token}（{klass}）{value} 实测 {ratio:.2f}:1，需 ≥ {budget}"
            for theme, token, klass, value, ratio, budget in over_budget
        )
        assert not over_budget, f"图形令牌低于对比度预算：\n{detail}"

    def test_data_strokes_are_measured_in_both_themes(self):
        # 浅色主题曾经全面不达标（主描边 3.31:1、水体描边 1.89:1），
        # 这条防止只修深色主题。
        for theme, tokens in BLOCKS.items():
            for token in ("--fig-line", "--fig-line-data", "--fig-water-line"):
                ratio = _ratio(theme, tokens[token])
                assert ratio >= 4.5, f"{theme} 的 {token} 只有 {ratio:.2f}:1"

    def test_the_new_data_stroke_is_actually_stronger_than_the_soft_one(self):
        # `--fig-line-data` 的存在意义就是比软线强；两者相等说明回落写法白加了
        for theme, tokens in BLOCKS.items():
            strong = _ratio(theme, tokens["--fig-line-data"])
            soft = _ratio(theme, tokens["--fig-line-soft"])
            assert strong > soft, f"{theme} 的 --fig-line-data 没有比 --fig-line-soft 更强"


class TestFaceTiersStayDistinct:
    """三档面填充按**性质**区分，不能塌成同一个取值。

    这一条是「面填充不设数值下限」的另一半。看过基准示例的实测帧之后确认：
    实心物体（台阶柱、圆盘、块体）读作「细描边 + 耳语填充」，形状毫无歧义；
    冰山图里水上尖端是耳语填充、水下主体是冷色实心——**这个差就是那张图的语义**
    （看得见的一角与看不见的主体不是一回事）。所以给实心物体加重填充不是
    「变得更实」，而是把刻意做出来的层级抹平。

    数值大小不作判据（浅色主题自己的面阶只有 1.13:1，`--fig-surface` 取白色
    正是跟着它走），但**同不同**可以判：

      * 实心面 SHALL NOT 等于画布，否则实心物体在背景上没有面、只剩描边；
      * 实心面、次级面（水体）、空壳 SHALL NOT 塌成同一个取值。

    已知边界：浅色主题的 `--fig-surface` 就等于抬升面 `--a2v-bg-2`（都是 `#ffffff`），
    深色主题两者只差 1.01:1——所以画在面板**上**的实心物体没有面阶，识别只能靠描边。
    这是接受的取舍，不是缺陷：面板本身已经与画布分开了。
    """

    TIERS = ("--fig-surface", "--fig-water", "--fig-hollow")

    def test_solid_face_is_visible_against_the_canvas(self):
        for theme in THEMES.values():
            surface = _resolved(theme, "--fig-surface")
            canvas = _resolved(theme, "--a2v-bg-0")
            assert _rgb(surface) != _rgb(canvas), (
                f"{theme} 主题的 --fig-surface 与画布同色，实心物体在背景上没有面"
            )
            assert _ratio(theme, surface, "--a2v-bg-0") > 1.0

    def test_the_three_face_tiers_do_not_collapse(self):
        for theme in THEMES.values():
            values = {}
            for token in self.TIERS:
                values[token] = _rgb(_resolved(theme, token))
            collapsed = [
                (one, other)
                for index, one in enumerate(self.TIERS)
                for other in self.TIERS[index + 1 :]
                if values[one] == values[other]
            ]
            assert not collapsed, (
                f"{theme} 主题里这几档面填充塌成了同一个取值：{collapsed}——"
                "层级会消失，水体、实心物体与空壳只剩线型之差"
            )

    def test_the_secondary_face_carries_a_tint(self):
        """次级面（水体）是唯一的冷色面：它靠色相与水下的语义绑定，不能退成中性灰。"""
        for theme in THEMES.values():
            water = _rgb(_resolved(theme, "--fig-water"))
            assert water[3] < 1.0, f"{theme} 主题的 --fig-water 不再是与底叠合的透明面"
            spread = max(water[:3]) - min(water[:3])
            assert spread >= 20, (
                f"{theme} 主题的 --fig-water（{water[:3]}）色相跨度只有 {spread}，"
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

    def test_classes_cover_the_tokens_the_live_styles_actually_use(self):
        # 分类表要覆盖画面真正引用的令牌，否则规则会漏掉正在用的东西
        used = set(re.findall(r"var\((--fig-[a-z-]+)", _live_css()))
        assert used <= set(CLASSES), f"画面样式层引用了未归类的令牌：{sorted(used - set(CLASSES))}"
