"""新画面工程的设计令牌真源与基元状态契约。

这一份把既有的两条判据**原样**搬到 React 路径上，而不是另写一套：

1. **令牌闭包与四态**：复用 `test_figure_token_closure.py` 里的常量与函数
   （`PRIMITIVES` / `STATES` / `TOKENS_ONLY_IN_PRESET_*` 那套口径），
   断言 `web/src/styles/primitives.css` 满足同一套约束；
2. **令牌取值逐值一致**：新工程是**移植**，不是重设计。因此这里按旧资产的
   层叠顺序算出「深色预设 / 浅色预设 / 未启用预设」三种情形下的**有效取值**，
   再与新工程同样顺序算出的有效取值逐个比对。少了这一条，移植时漏抄一个值
   或把层的顺序写反（`patch` 必须在 `dark` 之前，否则强调色的兜底值会压掉深色
   主题的强调色）都会静默通过。

还有一条新工程特有的判据：令牌真源必须写成 `@theme static`。Tailwind 默认的
`@theme` 只输出「被工具类用到」的变量，而这些令牌是**组件直接引用**的——
实测在 `@theme` 下这些名字一个都不会进产物，组件安静地落到兜底值或初始值，
画面变了却没有任何报错。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from test_figure_token_closure import PRIMITIVES, STATES

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / ".agents" / "skills" / "article2video" / "assets"
STYLES = ROOT / "web" / "src" / "styles"

TOKENS_CSS = (STYLES / "tokens.css").read_text(encoding="utf-8")
PRIMITIVES_CSS = (STYLES / "primitives.css").read_text(encoding="utf-8")

KEYNOTE_CSS = (ASSETS / "keynote.css").read_text(encoding="utf-8")
BASE_CSS = (ASSETS / "base.css").read_text(encoding="utf-8")
THEME_CSS = (ASSETS / "theme.css").read_text(encoding="utf-8")

#: 令牌名 → 取值。只解析单行声明：这几份样式表里的令牌声明都是单行的，
#: 一旦出现跨行声明，下面的完整性断言会先把这件事报出来。
_DECLARATION = re.compile(r"^\s*(--[a-z0-9-]+)\s*:\s*(.+?);\s*$", re.M)


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _body(css: str, selector: str) -> str:
    """取出某个选择器块的主体（顶层大括号配平）。

    选择器可以是**逗号列表的第一项**：浅色主题写在两条并列的选择器下
    （见 `tokens.css` 的注释——两级属性在新旧路径里挂在不同的元素上）。
    """
    lines = css.split("\n")
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if line.strip() == selector
            or line.startswith(selector + " {")
            or line.startswith(selector + ",")
        ),
        None,
    )
    assert start is not None, f"找不到选择器 {selector}"
    while "{" not in lines[start]:
        start += 1
    end = next(i for i in range(start + 1, len(lines)) if lines[i].rstrip() == "}")
    return "\n".join(lines[start + 1 : end])


def _values(body: str) -> dict[str, str]:
    return {name: value for name, value in _DECLARATION.findall(_strip_comments(body))}


def _effective(*bodies: str) -> dict[str, str]:
    """按 CSS 层叠顺序合并：后面的块覆盖前面的同名令牌。"""
    merged: dict[str, str] = {}
    for body in bodies:
        merged.update(_values(body))
    return merged


def _normalise(value: str) -> str:
    """比对前的规整：空白与引号写法不算差异。"""
    text = re.sub(r"\s+", " ", value.strip())
    text = text.replace('"', "'")
    return text


#: 旧资产里这一段的属性名丢了（只剩表达式），等于 `--a2v-grid-column` 从来没被定义过，
#: 也没有任何消费者。移植时不再带走这段死文本——旧资产是冻结的对照实现，不改它。
DEAD_TEXT = ("a2v-grid-column",)


class TestTokenSource:
    def test_uses_theme_static_so_every_token_reaches_the_output(self) -> None:
        assert "@theme static {" in TOKENS_CSS, (
            "令牌真源必须写成 `@theme static`：默认的 `@theme` 只输出被工具类用到的变量，"
            "而这里的令牌是组件直接引用的，会被静默丢掉"
        )

    def test_the_preset_layer_is_scoped_to_the_preset(self) -> None:
        """预设层不许进 `@theme`。

        `@theme` 只能把变量输出到 `:root`，而预设层改变的是同一个名字在**启用预设时**
        的取值。写进 `@theme` 就会在未启用预设时同样生效——字体、安全区、画布底色
        整体换掉，而校验、渲染、成片全部照常通过。
        """
        theme_block = _body(TOKENS_CSS, "@theme static")
        assert "--a2v-safe-top: 220px" in theme_block, "默认层应当是旧 base.css 的 220px"
        assert "--a2v-safe-top: 240px" not in theme_block, (
            "预设层的 240px 混进了 `@theme`：它会在未启用预设的画面里生效"
        )
        preset_block = _body(TOKENS_CSS, ":root[data-a2v-preset='keynote']")
        assert "--a2v-safe-top: 240px" in preset_block
        assert "--a2v-size-body" in preset_block, "字阶是预设专有的令牌族，应当只在预设层"

    def test_the_two_layers_are_additive(self) -> None:
        """预设层只覆盖它定义的名字，默认层始终在——旧路径就是这样叠加的。"""
        default = self._default_layer()
        preset = _values(_body(TOKENS_CSS, ":root[data-a2v-preset='keynote']"))
        only_default = sorted(set(default) - set(preset))
        assert only_default, "默认层没有任何独有令牌：预设层大概把整层抄了一遍"
        for name in ("--a2v-width", "--a2v-height", "--a2v-surface"):
            assert name in only_default, (
                f"{name} 只由默认层给。启用预设时它必须仍然可用——"
                "旧路径里裸 :root 与预设选择器是同时命中的，预设层没有权利把它拿掉"
            )

    @staticmethod
    def _default_layer() -> dict[str, str]:
        return _values(_body(TOKENS_CSS, "@theme static"))

    def test_theme_switch_is_not_only_a_token_override(self) -> None:
        # `color-scheme` 不是令牌，Tailwind 的 @theme 只输出变量，因此它必须单独写
        assert re.search(r"color-scheme:\s*dark", TOKENS_CSS)
        assert re.search(r"color-scheme:\s*light", TOKENS_CSS)


class TestTokenValuesMatchTheLegacySource:
    """新工程是移植：三种情形下的有效取值必须与旧资产逐个相同。

    有效取值按旧路径的**层叠顺序**算：默认层（base + theme + 裸 `:root` 的派生色）
    始终在，预设层（字体 + 字阶 + 配色）在属性命中时覆盖它。
    """

    @staticmethod
    def _legacy(kind: str) -> dict[str, str]:
        patch = _body(KEYNOTE_CSS, ":root {")
        font = _body(KEYNOTE_CSS, ':root[data-a2v-preset="keynote"] {')
        scale = re.findall(
            r':root\[data-a2v-preset="keynote"\] \{(.*?)\n\}', KEYNOTE_CSS, re.S
        )[-1]
        defaults = _effective(
            _body(BASE_CSS, ":root {"), _body(THEME_CSS, ":root {"), patch
        )
        if kind == "dark":
            themed = _body(
                KEYNOTE_CSS, ':root[data-a2v-preset="keynote"][data-a2v-theme="dark"] {'
            )
            return _effective(
                _body(BASE_CSS, ":root {"), _body(THEME_CSS, ":root {"), patch,
                font, scale, themed,
            )
        if kind == "light":
            themed = _body(
                KEYNOTE_CSS, ':root[data-a2v-preset="keynote"][data-a2v-theme="light"] {'
            )
            return _effective(
                _body(BASE_CSS, ":root {"), _body(THEME_CSS, ":root {"), patch,
                font, scale, themed,
            )
        return defaults

    @staticmethod
    def _ported(kind: str) -> dict[str, str]:
        defaults = _values(_body(TOKENS_CSS, "@theme static"))
        if kind == "default":
            return defaults
        preset = _body(TOKENS_CSS, ":root[data-a2v-preset='keynote']")
        if kind == "light":
            preset += "\n" + _body(
                TOKENS_CSS, ":root[data-a2v-preset='keynote'][data-a2v-theme='light']"
            )
        return _effective(_body(TOKENS_CSS, "@theme static"), preset)

    @pytest.mark.parametrize("kind", ["dark", "light", "default"])
    def test_every_token_keeps_its_value(self, kind: str) -> None:
        legacy = self._legacy(kind)
        ported = self._ported(kind)
        missing = sorted(name for name in legacy if name not in ported)
        assert not missing, f"{kind}：新工程少了这些令牌：{missing}"
        drifted = [
            (name, legacy[name], ported[name])
            for name in sorted(legacy)
            if _normalise(legacy[name]) != _normalise(ported[name])
        ]
        assert not drifted, f"{kind}：这些令牌的取值与旧资产不一致：{drifted[:5]}"

    def test_dark_palette_beats_the_default_derived_colors(self) -> None:
        """默认层那三个派生色必须被深色预设覆盖（旧路径靠属性选择器的权重）。"""
        dark = self._ported("dark")
        assert dark["--a2v-accent-deep"] == "#2f7fa8"
        assert dark["--a2v-emphasis-fade"] == "#d5dce8"
        assert self._ported("default")["--a2v-accent-deep"] == "#c2352a"

    def test_light_theme_only_overrides_colors(self) -> None:
        """浅色与深色共用字阶与几何，只有配色不同。"""
        dark = self._ported("dark")
        light = self._ported("light")
        same = [name for name in dark if dark[name] == light[name]]
        assert len(same) >= 100, f"深浅两套只有 {len(same)} 个令牌取值相同，浅色大概漏抄了字阶"
        assert dark["--a2v-bg-0"] != light["--a2v-bg-0"]
        assert dark["--a2v-size-body"] == light["--a2v-size-body"]


class TestPrimitiveStatesOnTheNewStyles:
    """四族基元 × 四个状态 × 两种媒介：复用既有判据的同一套口径。"""

    def test_every_primitive_rule_is_preset_scoped(self) -> None:
        selectors = [
            selector.strip() for selector in re.findall(r"([^{}]+)\{", _strip_comments(PRIMITIVES_CSS))
        ]
        for name in PRIMITIVES:
            owned = [selector for selector in selectors if re.search(rf"\.{name}\b", selector)]
            assert owned, f"primitives.css 里没有 .{name} 的规则"
            unscoped = [selector for selector in owned if "data-a2v-preset" not in selector]
            assert not unscoped, (
                f".{name} 有不带预设作用域的选择器：{unscoped}；"
                "未启用预设的画面会因此改样"
            )

    def test_state_values_are_exactly_the_four(self) -> None:
        used = set(re.findall(r'\[data-a2v-state="([a-z]+)"\]', _strip_comments(PRIMITIVES_CSS)))
        assert used <= set(STATES), f"出现了四态之外的状态：{sorted(used - set(STATES))}"
        assert used == set(STATES), f"四态里还有没写样式的：{sorted(set(STATES) - used)}"

    def test_state_rules_carry_no_motion_or_opacity(self) -> None:
        offenders = []
        for match in re.finditer(
            r'\[data-a2v-state="[a-z]+"\]\s*\{([^}]*)\}', _strip_comments(PRIMITIVES_CSS)
        ):
            for banned in ("opacity", "transform", "transition", "animation", "filter"):
                if re.search(rf"(^|[;\s]){banned}\s*:", match.group(1)):
                    offenders.append((banned, match.group(0)[:60]))
        assert not offenders, f"状态规则里出现了动效或透明度的写法：{offenders}"

    def test_every_surface_state_declares_both_media(self) -> None:
        offenders = []
        for match in re.finditer(
            r'\.a2v-surface\[data-a2v-state="([a-z]+)"\]\s*\{([^}]*)\}',
            _strip_comments(PRIMITIVES_CSS),
        ):
            state, body = match.group(1), match.group(2)
            if not re.search(r"(^|[;\s])fill\s*:", body):
                offenders.append((state, "SVG 侧缺 fill"))
            if not re.search(r"(^|[;\s])background-color\s*:", body):
                offenders.append((state, "HTML 侧缺 background-color"))
            if re.search(r"(^|[;\s])background\s*:", body):
                offenders.append((state, "用了 background 简写，会抹掉组件的材质"))
        assert not offenders, f"状态规则没有覆盖两种媒介：{offenders}"

    def test_focus_state_uses_the_accent(self) -> None:
        body = _body(PRIMITIVES_CSS, '[data-a2v-preset="keynote"] .a2v-surface[data-a2v-state="focus"]')
        assert "--a2v-focus-mix: 1" in body, "焦点态必须把连续通道钉在 1（完整焦点外观）"
        assert body.count("var(--a2v-accent-soft-solid)") >= 2, "焦点态要有块面，不能只改描边"

    def test_all_four_families_have_states(self) -> None:
        """四族里少一族，`data-a2v-state` 挂在它上面就是个静默空操作。"""
        for name in PRIMITIVES:
            states = set(
                re.findall(
                    rf'\.{name}\[data-a2v-state="([a-z]+)"\]', _strip_comments(PRIMITIVES_CSS)
                )
            )
            assert states, f".{name} 一条状态规则都没有"


class TestTokenClosureOnTheNewStyles:
    """新样式表引用的每个令牌都必须在真源里声明。

    旧路径靠「引用处带原值兜底」容错，因为共享页面在没有预设时也会加载组件样式。
    新路径的约束更强也更简单：**真源里一定有这个名字**，因此引用处不需要兜底，
    也就不存在「兜底值与真源值悄悄分叉」这种缺陷。
    """

    @staticmethod
    def _sources() -> list[Path]:
        skip = ("node_modules", "dist", ".gen")
        return [
            path
            for path in (ROOT / "web" / "src").rglob("*")
            if path.suffix in {".css", ".ts", ".tsx"}
            and not any(part in path.parts for part in skip)
        ]

    def test_every_referenced_token_is_declared(self) -> None:
        """引用处不需要兜底：每个被引用的令牌都要在工程里**有声明**。

        判据是「声明」而不是「真源」：组件会把连续量写进行内自定义属性
        （`'--vs-heat': …`），基元层会按状态声明局部变量（`--a2v-connector-ink`），
        这些都不该进 `tokens.css`（它们不是设计令牌，而是运行期算出来的值）。
        真正要挡住的是「引用了谁都没声明过的名字」——那会安静地落回初始值。
        """
        sources = self._sources()
        assert len(sources) >= 10, f"只扫到 {len(sources)} 个源文件，扫描规则可能失效了"

        # 先收集整个工程的声明：CSS 的 `--x: v` 与 TSX 行内样式对象的 `'--x': v`
        declared = {name for name, _value in _DECLARATION.findall(_strip_comments(TOKENS_CSS))}
        assert len(declared) >= 150, f"真源里只解析出 {len(declared)} 个令牌"
        for path in sources:
            if path.name == "tokens.css":
                continue
            text = _strip_comments(path.read_text(encoding="utf-8"))
            declared.update(re.findall(r"['\"]?(--[a-z0-9-]+)['\"]?\s*:", text))

        offenders: list[tuple[str, str]] = []
        for path in sources:
            if path.name == "tokens.css":
                continue
            text = _strip_comments(path.read_text(encoding="utf-8"))
            for name in set(re.findall(r"var\(\s*(--[a-z0-9-]+)", text)):
                if name not in declared:
                    offenders.append((path.relative_to(ROOT).as_posix(), name))
        assert not offenders, (
            f"这些令牌被引用却在工程里找不到任何声明：{sorted(set(offenders))}——"
            "补进 tokens.css（设计令牌）或补上组件的行内声明（连续量）"
        )
