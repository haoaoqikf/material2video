"""设计语言层的资产一致性。

这一层回答的是「令牌是不是自洽的」：字号阶、间距阶、对比度、以及
`figures.css` 引用的每一个 `--fig-*` 是否在两套主题里都真的有定义。
缺一个令牌不会报错——浏览器会安静地画出透明图形，成片之后才会发现，
因此这几条必须由测试兜住，而不是靠人眼复核。

只做静态解析，不起浏览器：CSS 文本里的数值本身就是契约。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from a2v import keynote

ASSETS = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "article2video" / "assets"


def _strip_comments(css: str) -> str:
    """去掉注释再解析。

    注释里为了说明用法会写 `"visual": { "preset": "keynote" }` 这类示例，
    大括号会打乱配对；不先剥掉，选择器就会解析到注释正文上。
    """
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


_RAW_CSS = (ASSETS / "keynote.css").read_text(encoding="utf-8")
KEYNOTE_CSS = _strip_comments(_RAW_CSS)
FIGURES_CSS = _strip_comments((ASSETS / "figures.css").read_text(encoding="utf-8"))
KEYNOTE_JS = (ASSETS / "typography.js").read_text(encoding="utf-8")

#: 界面上要落的字体资产（包含许可证与说明），名字写错就等于静默回退系统字体
FONT_ASSETS = (
    "Inter-Variable.ttf",
    "NotoSansSC-Variable.ttf",
    "OFL-Inter.txt",
    "OFL-NotoSansSC.txt",
    "README.md",
)


def _blocks(css: str, selector: str) -> list[str]:
    """取出以指定选择器开头的全部声明块（按花括号配对，不是正则到行尾）。"""
    blocks: list[str] = []
    for match in re.finditer(r"(?:^|\n)([^\n{}]*)\{", css):
        if match.group(1).strip() != selector:
            continue
        start = match.end()
        depth = 1
        index = start
        while index < len(css) and depth:
            if css[index] == "{":
                depth += 1
            elif css[index] == "}":
                depth -= 1
            index += 1
        blocks.append(css[start : index - 1])
    return blocks


def theme_block(selector: str, needle: str = "") -> str:
    """截出某个选择器的声明块；同一选择器出现多次时用 needle 指明是哪一块。"""
    blocks = _blocks(KEYNOTE_CSS, selector)
    assert blocks, f"keynote.css 里找不到选择器 {selector}"
    if needle:
        matched = [block for block in blocks if needle in block]
        assert matched, f"{selector} 的块里没有 {needle}"
        return matched[0]
    return blocks[0]


def root_block() -> str:
    """`:root` 共享块：默认主题的三个兜底令牌都在这里。"""
    return theme_block(":root")


def scale_block() -> str:
    """字号阶与间距阶：两套主题共用，挂在预设选择器上。"""
    return theme_block(':root[data-a2v-preset="keynote"]', needle="--a2v-size-")


def declarations(block: str, prefix: str) -> dict[str, str]:
    """把声明块里以 prefix 开头的自定义属性抽成字典。"""
    return {
        name: value.strip()
        for name, value in re.findall(r"(--" + prefix + r"[\w-]*)\s*:\s*([^;]+);", block)
    }


def merged_theme(dark: bool = True) -> str:
    """共享块 + 该主题块：令牌可以定义在任一处，取用时合并。"""
    theme = 'data-a2v-theme="dark"' if dark else 'data-a2v-theme="light"'
    return root_block() + "\n" + theme_block(f':root[data-a2v-preset="keynote"][{theme}]')


@pytest.fixture(scope="module")
def dark() -> str:
    return scale_block() + "\n" + merged_theme(True)


@pytest.fixture(scope="module")
def light() -> str:
    return scale_block() + "\n" + merged_theme(False)


class TestFontAssets:
    @pytest.mark.parametrize("name", FONT_ASSETS)
    def test_asset_present(self, name: str) -> None:
        assert (ASSETS / "fonts" / name).is_file()

    def test_font_face_declared(self) -> None:
        assert KEYNOTE_CSS.count("@font-face {") == 2
        for family in ("A2V Inter", "A2V Sans"):
            assert f'  font-family: "{family}";' in KEYNOTE_CSS

    def test_variable_weight_range(self) -> None:
        # 可变字体必须声明完整字重区间，否则粗细档会被合成（看起来发糊）
        assert KEYNOTE_CSS.count("  font-weight: 100 900;") == 2

    def test_block_until_loaded(self) -> None:
        # 逐帧截图不能拍到「回退字体已经画上、真字体还没到」的那一帧
        assert KEYNOTE_CSS.count("  font-display: block;") == 2


class TestTypeScale:
    def test_scale_levels_are_ordered(self, dark: str) -> None:
        # 字号阶按从小到大声明：档位必须单调，且相邻比例落在一个窄区间里，
        # 否则层级会「忽大忽小」，这也是 K3 闸门存在的前提。
        sizes = declarations(dark, "a2v-size-")
        assert sizes, "深色预设里没有字号档"
        values = [int(re.match(r"(\d+)px", value).group(1)) for value in sizes.values()]
        assert values == sorted(values)
        ratios = [round(b / a, 3) for a, b in zip(values, values[1:])]
        for ratio in ratios:
            assert 1.1 <= ratio <= 1.6, f"相邻档位比例 {ratio} 超出 1.1–1.6"

    def test_scale_matches_typescript_engine(self, dark: str) -> None:
        # 令牌与排版引擎的档位必须一一对应：对不上就会出现
        # 「引擎算出来 96px，样式表预置的却是 124px」这种静默错位
        sizes = declarations(dark, "a2v-size-")
        assert len(sizes) == 8, f"字号阶档位数量变了：{sorted(sizes)}"
        for level, token in sizes.items():
            px = int(re.match(r"(\d+)px", token).group(1))
            name = level.replace("--a2v-size-", "")
            entry = re.search(re.escape(name) + r"[^\n]*?" + str(px) + r"\b", KEYNOTE_JS)
            assert entry, f"typography.js 的 SCALE 里没有与 {level}={px} 对应的档位"

    def test_every_size_has_leading_and_tracking(self, dark: str) -> None:
        sizes = declarations(dark, "a2v-size-")
        leading = declarations(dark, "a2v-leading-")
        tracking = declarations(dark, "a2v-tracking-")
        for name in sizes:
            suffix = name.replace("--a2v-size-", "")
            assert f"--a2v-leading-{suffix}" in leading, suffix
            assert f"--a2v-tracking-{suffix}" in tracking, suffix

    def test_line_height_reaches_chromium_line_box(self, dark: str) -> None:
        # 实测：Inter 与 Noto Sans SC 在 Chromium 里的行盒都是 1.32em。
        # 行高低于它，中文行会互相贴住，因此下限写在这里当契约。
        leading = declarations(dark, "a2v-leading-")
        for name, value in leading.items():
            ratio = float(value)
            assert ratio >= 1.0, f"{name} 的行高 {ratio} 会让行叠在一起"


class TestSpacingGrid:
    def test_spacing_follows_8pt_grid(self, dark: str) -> None:
        # 8pt 网格允许一个半档（4px）处理发丝级间隙，其余必须落在 8 的倍数上。
        # 不写「全部 8 的倍数」是因为那样会逼着组件用 8px 去凑视觉上的 4px。
        spacing = declarations(dark, "a2v-space-")
        assert len(spacing) >= 8, f"间距阶档位太少：{sorted(spacing)}"
        for name, value in spacing.items():
            px = int(re.match(r"(\d+)px", value).group(1))
            assert px % 4 == 0, f"{name}={px}px 连半档都不在网格上"
            if px > 4:
                assert px % 8 == 0, f"{name}={px}px 不在 8pt 网格上"

    def test_spacing_is_monotonic(self, dark: str) -> None:
        spacing = declarations(dark, "a2v-space-")
        values = [int(re.match(r"(\d+)px", value).group(1)) for value in spacing.values()]
        assert values == sorted(values)


class TestContrastBudget:
    """令牌层的对比度下限。数值来源与实测见 references/keynote-design-system.md。"""

    def _ratio(self, color: str, background: str) -> float:
        parsed = keynote.parse_color(color)
        assert parsed is not None, color
        alpha = keynote.parse_alpha(color)
        composited = keynote.composite(parsed, alpha, keynote.parse_color(background))
        return keynote.contrast_ratio(composited, keynote.parse_color(background) or (0, 0, 0))

    def test_dark_ink_meets_wcag(self, dark: str) -> None:
        bg = declarations(dark, "a2v-bg-")["--a2v-bg-0"]
        ink = declarations(dark, "a2v-ink-")
        # 一级与二级墨色用于正文，必须过 7:1
        for name in ("--a2v-ink-1", "--a2v-ink-2"):
            assert self._ratio(ink[name], bg) >= 7.0, name
        # 三级以下只用于大字与图形，4.5:1 是可接受下限
        assert self._ratio(ink["--a2v-ink-3"], bg) >= 4.5

    def test_dark_accent_meets_large_text(self, dark: str) -> None:
        bg = declarations(dark, "a2v-bg-")["--a2v-bg-0"]
        accent = declarations(dark, "a2v-accent")["--a2v-accent"]
        assert self._ratio(accent, bg) >= 4.5

    def test_light_ink_meets_wcag(self, light: str) -> None:
        bg = declarations(light, "a2v-bg-")["--a2v-bg-0"]
        ink = declarations(light, "a2v-ink-")
        for name in ("--a2v-ink-1", "--a2v-ink-2"):
            assert self._ratio(ink[name], bg) >= 7.0, name
        assert self._ratio(ink["--a2v-ink-3"], bg) >= 4.5

    def test_light_accent_meets_large_text(self, light: str) -> None:
        bg = declarations(light, "a2v-bg-")["--a2v-bg-0"]
        accent = declarations(light, "a2v-accent")["--a2v-accent"]
        assert self._ratio(accent, bg) >= 4.5


class TestFigureTokenCoverage:
    """figures.css 引用的每个 --fig-* 都必须在两套主题里有定义。"""

    def _used_tokens(self) -> set[str]:
        return set(re.findall(r"var\((--fig-[\w-]+)", FIGURES_CSS))

    def test_theme_formats_are_self_contained(self, dark: str, light: str) -> None:
        used = self._used_tokens()
        for label, block in (("暗色预设", dark), ("浅色预设", light)):
            defined = set(re.findall(r"(--fig-[\w-]+)\s*:", block))
            missing = sorted(used - defined)
            assert not missing, f"{label}缺少图形令牌：{missing}（缺了会安静地画出透明图形）"

    def test_emphasis_mix_contract(self) -> None:
        # 组件用这个自定义属性报告「强调词褪到哪一档」，样式表负责把它变成颜色
        blocks = _blocks(KEYNOTE_CSS, '[data-a2v-preset="keynote"] .key')
        assert blocks, "keynote.css 里没有预设生效时的强调词规则"
        assert "--a2v-emphasis-mix" in blocks[0]
        # 默认落点也必须存在，否则未启用预设的页面会丢掉这段褪色
        assert "--a2v-emphasis-mix" in FIGURES_CSS

    def test_emphasis_fade_is_readable(self, dark: str, light: str) -> None:
        # 强调词褪色后仍要能读：褪到看不见等于让重点词凭空消失。
        # 比的是标题所在的那一层底色（bg-1），不是最底层的画布。
        dark_bg = declarations(dark, "a2v-bg-")["--a2v-bg-1"]
        light_bg = declarations(light, "a2v-bg-")["--a2v-bg-1"]
        assert self._ratio(declarations(dark, "a2v-emphasis-fade")["--a2v-emphasis-fade"], dark_bg) >= 4.5
        assert self._ratio(declarations(light, "a2v-emphasis-fade")["--a2v-emphasis-fade"], light_bg) >= 4.5

    def test_emphasis_mix_default_keeps_legacy_color(self) -> None:
        # 默认落点必须与组件原来的目标色一致，否则既有视频会变
        assert "#23262d" in FIGURES_CSS

    def _ratio(self, color: str, background: str) -> float:
        parsed = keynote.parse_color(color)
        assert parsed is not None, color
        return keynote.contrast_ratio(parsed, keynote.parse_color(background) or (0, 0, 0))


class TestPresetScoping:
    """设计语言层不能泄漏到未启用预设的页面。

    这里守住的是一类「不报错的破坏」：`@font-face` 是全局注册的，`:root` 也是
    全局的，任何一条漏掉 `[data-a2v-preset="keynote"]` 的令牌规则都会静默改写
    既有视频的画面——校验通过、渲染通过，只有成片变了。曾经就发生过：
    字体栈写在裸 `:root` 上，浅色主题的既有示例整体换了字体；
    深色主题块写成 `:root, :root[data-a2v-preset…]`，把浅色页面整片刷黑。
    """

    def _selectors(self) -> list[str]:
        return [match.group(1).strip() for match in re.finditer(r"(?:^|\n)([^\n{}]*)\{", KEYNOTE_CSS)]

    def test_no_bare_root_carries_visual_tokens(self) -> None:
        bare_root = [text for text in self._selectors() if text == ":root"]
        assert len(bare_root) <= 1, "keynote.css 里有多个裸 :root 块，容易漏掉作用域"
        # 唯一的裸 :root 只允许放「默认主题的补充令牌」，且必须是旧值兜底
        block = theme_block(":root")
        assert "--a2v-font" not in block, "字体栈写在裸 :root 上会泄漏给所有页面"
        assert "--a2v-bg-0" not in block, "表面令牌写在裸 :root 上会泄漏给所有页面"
        assert "--a2v-size-" not in block, "字号阶写在裸 :root 上会泄漏给所有页面"
        # 允许的三个兜底令牌必须存在，且必须是旧主题的取值
        assert declarations(block, "a2v-accent-deep")["--a2v-accent-deep"] == "#c2352a"
        assert declarations(block, "a2v-accent-soft-solid")["--a2v-accent-soft-solid"] == "#7d1c16"
        assert declarations(block, "a2v-emphasis-fade")["--a2v-emphasis-fade"] == "#23262d"

    def test_theme_block_selector_is_preset_only(self) -> None:
        for theme in ("dark", "light"):
            selector = f':root[data-a2v-preset="keynote"][data-a2v-theme="{theme}"]'
            assert _blocks(KEYNOTE_CSS, selector), f"找不到 {theme} 主题块"
        # `:root,` 这种并列选择器一旦出现，就等于把主题送给了所有页面
        assert ":root,\n" not in KEYNOTE_CSS, "主题块与裸 :root 并列，会泄漏给所有页面"

    def test_every_visual_rule_is_scoped(self) -> None:
        # 允许出现的选择器：预设作用域、字体定义、以及裸 :root
        # （裸 :root 只准放默认主题的兜底令牌，由下一条测试盯着）
        allowed = (
            ":root[data-a2v-preset=",
            ":root",
            "[data-a2v-preset=",
            "@font-face",
            "@media",
        )
        for selector in self._selectors():
            if not selector.startswith((":", "[", "@", "*")):
                continue
            assert selector.startswith(allowed), f"未加预设作用域的规则：{selector}"

    def test_no_selector_mixes_preset_and_root(self) -> None:
        # `:root, :root[data-a2v-preset…]` 这种并列就是泄漏的来源
        for selector in self._selectors():
            assert not ("," in selector and ":root" in selector), f"并列选择器里混了 :root：{selector}"

    def test_font_face_is_global_but_stack_is_not(self) -> None:
        # 字体文件本身全局注册无害（没人引用就不会下载），但引用必须作用域化
        assert KEYNOTE_CSS.count("@font-face {") == 2
        assert "--a2v-font:" not in theme_block(":root")


class TestNoRawValues:
    """新增样式里不该出现裸色值与裸字号：它们会绕过令牌与字号阶。"""

    def test_no_raw_hex_in_figure_section_of_keynote(self) -> None:
        # 令牌定义本身允许写色值，用法段不允许（分节标题写在注释里，用原文）
        usage = _RAW_CSS.split("六、排版工具类")[1]
        offenders = re.findall(r"#[0-9a-fA-F]{3,8}\b", usage)
        assert not offenders, f"用法段出现裸色值：{offenders}"

    def test_figures_css_has_no_hardcoded_warm_red(self) -> None:
        # 写死的暖红不跟主题走，换主题时会留下一抹属于旧主题的颜色
        assert "194, 53, 42" not in FIGURES_CSS
        assert "#c2352a" not in FIGURES_CSS
