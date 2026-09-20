"""新画面工程的样式栈：老样式表里剩下的结构性规则必须逐条搬完。

背景：这一轮把老管线冻结的样式表搬进 `web/src/styles/`，目标是新旧画面**几何完全
一致**（后续要做逐像素 PSNR ≥ 60 dB 的抽帧对照）。这类移植的失败方式全是静默的：
漏搬一条规则不会报错，只会让某几帧的像素差超阈值，或者在浏览器里表现为「差不多」。

因此这里不跑浏览器，只做纯文本判据，分四件事：

1. **搬运保真**（`base.css` / `theme.css` / `declarative.css`）：新文件去掉注释、
   空白、`@import` 之后，必须与旧文件去掉 `:root` 令牌块之后的内容**逐字符一致**。
   令牌块之所以要排除，是因为它们已经被搬进令牌真源 `tokens.css`——同一批名字出现
   在两处必然漂移，而漂移不会报错。
2. **选择器全覆盖**（`keynote.css`）：旧文件里出现过的**每一个选择器**，都必须在
   `keynote.css` / `tokens.css` / `primitives.css` 三者之一里找到**完全相同的文本**，
   且只能落在一个文件里（两份真源同样会漂移）。清单在下面的 `KEYNOTE_SELECTORS` 里，
   是显式写死的，不做模糊匹配。
3. **加载顺序**：`index.css` 的 `@import` 顺序必须与旧页面 `assets/declarative.html`
   的 `<link>` 顺序一致。顺序不同，同权重选择器的胜负就不同，画面会变。
4. **画面不许有 CSS 动效**：`web/src/styles/` 下不许出现 `animation` / `@keyframes` /
   `transition` 声明。老样式表里本来就没有，唯一的 `:hover` 在预览控件条上
   （`[data-a2v-controls] button:hover`），那是预览专用元素，导出时被
   `html.a2v-rendering` 整块隐藏，按 `PREVIEW_ONLY_SELECTORS` 显式排除。

失败信息一律写清「哪条规则 / 哪个选择器没搬」，不要只说 assert False。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / ".agents" / "skills" / "article2video" / "assets"
STYLES = ROOT / "web" / "src" / "styles"

#: 旧页面决定加载顺序的地方。顺序即优先级：同权重选择器由源序决定胜负。
DECLARATIVE_HTML = ASSETS / "declarative.html"

#: 逐字符搬运的三份（令牌块除外），以及旧文件。
CHARACTER_COPY = ("base.css", "theme.css", "declarative.css")

#: 新工程专有的层：旧页面没有对应文件，排在旧 `<link>` 之前。
#: `primitives.css` **不在这里**：它搬的是旧 `keynote.css` 的尾部，
#: 必须紧跟 `keynote.css` 才保得住源序（见 `test_primitives_layer_sits_right_after_…`）。
NEW_LAYER_IMPORTS = (
    "tailwindcss/theme.css",
    "tailwindcss/utilities.css",
    "./tokens.css",
)

#: 允许留在搬运文件里的 `:root` 块：文件 → 该文件里可以保留的选择器。
#:
#: `declarative.css` 的 `:root[data-a2v-theme="light"]` **必须留在原位**：
#: 它是「未启用预设」那套主题的默认浅色层（暖白 + 砖红强调），不挂在预设上，
#: 而 `theme.css` 里也有一层浅色令牌，两者是「后写的赢」的关系。
#: 搬到 `tokens.css`（排在最前）会让 `theme.css` 反过来压过它——
#: 实测那一版每一帧都只有 1.4 dB（整幅画面的底色、墨色全换了）。
#: 允许保留不等于允许改：下面仍然逐字符比对这一块的内容。
ALLOWED_ROOT_BLOCKS: dict[str, tuple[str, ...]] = {
    "declarative.css": (':root[data-a2v-theme="light"]',),
}

#: 搬运到令牌真源里的三组 `:root` 块：旧 keynote.css 里「只有令牌声明」的块。
#: 键是旧文件里的选择器文本（`_top_level_blocks` 会逐个取出来），值是这一组
#: 至少必须已经出现在 `tokens.css` 里的令牌名。
KEYNOTE_TOKEN_BLOCKS: dict[str, tuple[str, ...]] = {
    ':root[data-a2v-preset="keynote"]': ("--a2v-font", "--a2v-size-body"),
    ':root[data-a2v-preset="keynote"][data-a2v-theme="dark"]': ("--a2v-bg-0", "--a2v-ink-1"),
    ':root[data-a2v-preset="keynote"][data-a2v-theme="light"]': ("--a2v-bg-0", "--a2v-ink-1"),
}

#: 裸 `:root` 上的三个默认主题派生色（旧 keynote.css 第一节末）。
BARE_ROOT_TOKENS = ("--a2v-accent-deep", "--a2v-accent-soft-solid", "--a2v-emphasis-fade")

#: 旧 keynote.css 的**每一个**顶层选择器 → 它在新工程里的归属文件。
#:
#: 写成显式清单而不是正则匹配，是为了让「漏搬一条」变成一个必须动这份清单的
#: 失败：清单里少一条，`test_every_legacy_selector_is_ported` 会指名道姓地报出来。
KEYNOTE_SELECTORS: dict[str, str] = {
    # 五、基础版式（页面骨架、版面、字幕、角标、焦点线、强调短语、标题渐变）
    '[data-a2v-preset="keynote"] [data-a2v-stage]': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-safe': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-scene] .a2v-safe': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-scene] .a2v-safe > *': "keynote.css",
    '[data-a2v-preset="keynote"] [data-layout="center"] .a2v-safe,\n'
    '[data-a2v-preset="keynote"] .a2v-safe.a2v-safe-center': "keynote.css",
    '[data-a2v-preset="keynote"] [data-layout="left"] .a2v-safe,\n'
    '[data-a2v-preset="keynote"] .a2v-safe.a2v-safe-left': "keynote.css",
    '[data-a2v-preset="keynote"] [data-layout="lower"] .a2v-safe': "keynote.css",
    '[data-a2v-preset="keynote"][data-a2v-theme="dark"] .a2v-subtitle': "keynote.css",
    '[data-a2v-preset="keynote"][data-a2v-theme="light"] .a2v-subtitle': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-scene-index': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-scene-index .a2v-scene-number': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-focus-rule': "keynote.css",
    '[data-a2v-preset="keynote"] .key': "keynote.css",
    '[data-a2v-preset="keynote"][data-a2v-theme="dark"] .title-text': "keynote.css",
    '[data-a2v-preset="keynote"][data-a2v-theme="light"] .title-text': "keynote.css",
    '[data-a2v-preset="keynote"] .key-underline': "keynote.css",
    # 六、排版工具类（字号档的唯一入口 + 卡片 + 网格）
    '[data-a2v-preset="keynote"] .a2v-hero': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-display': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-headline': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-title': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-lead': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-body': "keynote.css",
    # 旧文件里这个选择器**出现两次**：一次在排版尺度一节（字号/行高），
    # 一次在基元一节（四族基元的基础规则）。两次都保留，因此新工程里也落在两个文件。
    '[data-a2v-preset="keynote"] .a2v-label': "keynote.css,primitives.css",
    '[data-a2v-preset="keynote"] .a2v-caption': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-numeric': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-card': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-card-focus': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-grid': "keynote.css",
    '[data-a2v-preset="keynote"] .a2v-safe-bottom-offset': "keynote.css",
    # 七、字号档的 CSS 声明（`data-a2v-fit` 的落点）
    '[data-a2v-preset="keynote"] [data-a2v-fit="numeral"]': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-fit="mega"]': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-fit="hero"]': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-fit="display"]': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-fit="headline"]': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-fit="title"]': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-fit="lead"]': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-fit="body"]': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-fit="label"]': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-fit="caption"]': "keynote.css",
    '[data-a2v-preset="keynote"] [data-a2v-fit]': "keynote.css",
    # 七、引文块与主角数字
    '[data-a2v-preset="keynote"] .quote-block': "keynote.css",
    '[data-a2v-preset="keynote"] .quote-text': "keynote.css",
    '[data-a2v-preset="keynote"] .quote-rule': "keynote.css",
    '[data-a2v-preset="keynote"] .quote-mark': "keynote.css",
    '[data-a2v-preset="keynote"] [data-layout="center"] .quote-rule,\n'
    '[data-a2v-preset="keynote"] [data-layout="center"] .quote-mark,\n'
    '[data-a2v-preset="keynote"] .a2v-safe-center .quote-rule,\n'
    '[data-a2v-preset="keynote"] .a2v-safe-center .quote-mark': "keynote.css",
    '[data-a2v-preset="keynote"] .fig-number': "keynote.css",
    '[data-a2v-preset="keynote"] .fig-number-label': "keynote.css",
    '[data-a2v-preset="keynote"] .fig-number-caption': "keynote.css",
    # 八、图形基元与状态：这一族整块搬进了 primitives.css
    '[data-a2v-preset="keynote"] .a2v-surface': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-connector': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-frame': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-surface[data-a2v-state="rest"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-surface[data-a2v-state="focus"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-surface[data-a2v-state="muted"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-surface[data-a2v-state="done"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-frame[data-a2v-state="rest"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-frame[data-a2v-state="focus"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-frame[data-a2v-state="muted"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-frame[data-a2v-state="done"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-connector[data-a2v-state="rest"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-connector[data-a2v-state="focus"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-connector[data-a2v-state="muted"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-connector[data-a2v-state="done"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-label[data-a2v-state="focus"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-label[data-a2v-state="muted"]': "primitives.css",
    '[data-a2v-preset="keynote"] .a2v-label[data-a2v-state="done"]': "primitives.css",
    # 八之后的收尾覆写：圆形容器里的标签、浅色面板标签、浅色时间线正文
    '[data-a2v-preset="keynote"] .loop-node-text': "keynote.css",
    '[data-a2v-preset="keynote"][data-a2v-theme="light"] .gauge-label,\n'
    '[data-a2v-preset="keynote"][data-a2v-theme="light"] .drop-label': "keynote.css",
    '[data-a2v-preset="keynote"][data-a2v-theme="light"] [data-scene-id="freedom"] span': "keynote.css",
}

#: 工具类选择器在新工程里的**归属**：它们由哪个旧文件提供。
#:
#: `index.css` 这一轮不再手写任何元素级规则，因此每一条都必须能追到一个搬来的
#: 文件上——否则就是「删掉手写规则时顺手删掉了一条真规则」，表现为画面缺一块。
#: 顺带写明为什么它们没有动画：**画面只由帧号推导**，CSS 动画会带来第二个时间源。
LAYOUT_SELECTOR_OWNERS: dict[str, tuple[str, ...]] = {
    "html,\nbody": ("base.css",),
    "[data-a2v-stage]": ("base.css", "declarative.css"),
    "[data-a2v-scene]": ("base.css", "declarative.css"),
    ".a2v-safe": ("base.css",),
    ".a2v-with-subtitles .a2v-safe": ("base.css",),
    ".a2v-subtitle": ("base.css", "keynote.css"),
    "[data-a2v-controls]": ("base.css",),
    "[data-a2v-controls] button": ("base.css",),
    "[data-a2v-seek]": ("base.css",),
    "[data-a2v-time]": ("base.css",),
    "html.a2v-rendering [data-a2v-controls],\nhtml.a2v-rendering .a2v-preview-only": ("base.css",),
    "html.a2v-rendering [data-a2v-stage]": ("base.css",),
}

#: 老样式表里唯一允许出现的交互态：预览控件条。它不是画面的一部分——
#: 导出时 `html.a2v-rendering` 会把 `[data-a2v-controls]` 与 `.a2v-preview-only`
#: 一起 `display: none !important`，因此抽帧对照永远看不到它。
PREVIEW_ONLY_SELECTORS: tuple[str, ...] = ("[data-a2v-controls]",)

#: 旧 keynote.css 里那处**死文本**：属性名丢了，`--a2v-grid-column` 因此从来没有被
#: 定义过，也没有任何消费者。它**不进新工程**：那段文本里的右括号没有配对的
#: 左括号，Tailwind 的解析器会因此拒绝整份样式表（`Missing opening (`）。
#: 省略它不改变画面（浏览器本来就会丢掉这条声明），但让新路径能构建。
DEAD_TEXT_LINES: tuple[str, ...] = (
    "  --a2v-grid-columns: 12;",
    "  --a2v-grid-gutter: 24px;",
    "    (var(--a2v-content-width) - (var(--a2v-grid-columns) - 1) * var(--a2v-grid-gutter)) /",
    "      var(--a2v-grid-columns)",
    "  );",
)

#: 上面清单里**具有辨识度**的行：`  );` 这种单独一行在别的规则里到处都是，
#: 拿它做「新文件里不许出现」的判据会误报。
DEAD_TEXT_DISTINCTIVE: tuple[str, ...] = DEAD_TEXT_LINES[:4]

#: 画面里不许出现的 CSS 动效属性。
MOTION_PROPERTIES: tuple[str, ...] = ("animation", "@keyframes", "transition", "animation-name")


# ---------------------------------------------------------------------------
# 纯文本工具
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _strip_at_blocks(css: str) -> str:
    """删掉 `@font-face { … }` / `@media { … }` 这类整块结构（括号配平）。"""
    out: list[str] = []
    i = 0
    while i < len(css):
        if css[i] == "@":
            brace = css.find("{", i)
            semi = css.find(";", i)
            if brace != -1 and (semi == -1 or brace < semi):
                depth = 0
                j = brace
                while j < len(css):
                    if css[j] == "{":
                        depth += 1
                    elif css[j] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                out.append(" ")
                i = j + 1
                continue
        out.append(css[i])
        i += 1
    return "".join(out)


def _strip_root_blocks(css: str) -> tuple[str, list[tuple[str, str]]]:
    """删掉所有顶层 `:root … { … }` 块，并把它们连同选择器一起返回。

    返回值第二项是 `[(选择器文本, 块正文), …]`，用来断言「令牌确实已经落到
    `tokens.css` 里」，而不是凭空消失。
    """
    removed: list[tuple[str, str]] = []
    text = css
    while True:
        match = re.search(r"^:root[^\n{]*\{", text, flags=re.M)
        if match is None:
            return text, removed
        brace = text.index("{", match.start())
        depth = 0
        j = brace
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        selector = text[match.start() : brace].strip()
        removed.append((selector, text[brace + 1 : j]))
        text = text[: match.start()] + text[j + 1 :]


def _without_at_imports(css: str) -> str:
    return re.sub(r"^\s*@import[^;]*;\s*$", "", css, flags=re.M)


def _squeeze(css: str) -> str:
    """比对前的规整：去掉全部注释与空白（含换行）。

    只做这一件事：新文件里的注释、缩进与换行不算差异，因为它们不参与层叠。
    声明里的值一个都不许变——那正是要守住的东西。
    """
    return re.sub(r"\s+", "", _strip_comments(css))


def _collapse(css: str) -> str:
    """只折空白、保留结构：用于选择器文本比对。"""
    text = _strip_comments(css)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n+", "\n", text)


def _blocks(css: str) -> list[tuple[str, str]]:
    """按顶层大括号拆出 `[(选择器, 块正文), …]`（选择器保留原样，含换行）。"""
    clean = _strip_comments(css)
    found: list[tuple[str, str]] = []
    i = 0
    while i < len(clean):
        brace = clean.find("{", i)
        if brace == -1:
            break
        selector = clean[i:brace].strip()
        depth = 0
        j = brace
        while j < len(clean):
            if clean[j] == "{":
                depth += 1
            elif clean[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        found.append((selector, clean[brace + 1 : j]))
        i = j + 1
    return found


def _top_level_blocks(css: str) -> list[tuple[str, str]]:
    return [block for block in _blocks(css) if not block[0].startswith("@")]


def _merged_blocks(css: str) -> dict[str, str]:
    """同选择器的多个块合并成一条：旧文件里有两条 `:root[data-a2v-preset…]`
    （第一条给字体栈、第四条给字阶），按选择器取值会只剩最后一条。"""
    merged: dict[str, str] = {}
    for selector, body in _top_level_blocks(css):
        key = _selector_key(selector)
        merged[key] = merged[key] + "\n" + body if key in merged else body
    return merged


def _token_blocks_of_keynote() -> tuple[dict[str, str], list[str]]:
    """旧 keynote.css 里那些**只有令牌声明**的 `:root` 块 → (选择器 → 正文, 选择器列表)。

    判定「只有令牌声明」的口径与 `tests/test_web_design_tokens.py` 一致：
    块正文里除了 `--name: value;` 与 `color-scheme` 之外没有别的东西。
    """
    only_tokens: dict[str, str] = {}
    selectors: list[str] = []
    for selector, body in _merged_blocks(_read(ASSETS / "keynote.css")).items():
        if not selector.startswith(":root"):
            continue
        leftovers = _strip_comments(body)
        leftovers = re.sub(r"--[a-z0-9-]+\s*:[^;]*;", "", leftovers)
        leftovers = re.sub(r"color-scheme\s*:[^;]*;", "", leftovers)
        # 已知死文本先摘掉：它没有属性名，会让「这一块是不是只有令牌」的判定失效
        # （见 DEAD_TEXT_LINES）。摘掉它之后，承载它的那个预设令牌块才能被正确归类。
        for line in DEAD_TEXT_LINES:
            leftovers = leftovers.replace(line, "")
        if leftovers.strip():
            continue  # 这一块里有元素级声明，不归令牌真源管
        selectors.append(selector)
        only_tokens[selector] = body
    return only_tokens, selectors


def _selector_key(selector: str) -> str:
    """选择器文本的规范化：只折空白，不去掉任何字符。

    旧文件里两条并列选择器写在同一个块上（例如「居中 / 左对齐」那条），
    换行属于原文，因此键里保留换行、只折行内空白。
    """
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in selector.strip().split("\n")]
    return "\n".join(line for line in lines if line)


def _legacy_selector_map() -> dict[str, list[str]]:
    """旧 keynote.css 的顶层选择器 → 出现次数（`_selector_key` 规范化）。"""
    counted: dict[str, list[str]] = {}
    for selector, _body in _top_level_blocks(_read(ASSETS / "keynote.css")):
        counted.setdefault(_selector_key(selector), []).append(selector)
    return counted


def _new_selector_map() -> dict[str, list[str]]:
    """三份新文件里的顶层选择器 → 出现在哪些文件。"""
    owners: dict[str, list[str]] = {}
    for name in ("keynote.css", "tokens.css", "primitives.css"):
        for selector, _body in _top_level_blocks(_read(STYLES / name)):
            owners.setdefault(_selector_key(selector), []).append(name)
    return owners


def _declarations(body: str) -> list[str]:
    """块正文里的声明（按分号切，折掉空白），用于报出具体的差异。"""
    parts = [re.sub(r"\s+", " ", part).strip() for part in _strip_comments(body).split(";")]
    return [part for part in parts if part]


# ---------------------------------------------------------------------------
# 1. 逐字符搬运
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", CHARACTER_COPY)
def test_character_copy_of_the_legacy_sheet(name: str) -> None:
    """去掉 `:root` 令牌块后，新文件必须与旧文件逐字符一致。

    允许的差异只有三类，且都显式写在这里：
      - 注释（新文件多了一段「搬运说明」，旧文件的注释一字不动地留着）；
      - `@import`（旧文件没有这一层）；
      - `ALLOWED_ROOT_BLOCKS` 里点名的 `:root` 块（目前只有 `declarative.css`
        的默认浅色层），内容仍然逐字符比对。
    空白与换行不算差异：它们不参与层叠，因此比对前被折掉。
    """
    legacy = _read(ASSETS / name)
    ported = _read(STYLES / name)

    legacy_body, legacy_roots = _strip_root_blocks(legacy)
    ported_body, ported_roots = _strip_root_blocks(ported)

    allowed = ALLOWED_ROOT_BLOCKS.get(name, ())
    kept = [selector for selector, _ in ported_roots if selector not in allowed]
    assert not kept, (
        f"web/src/styles/{name} 里仍然留着 `:root` 块：{kept}；"
        "令牌的真源是 tokens.css，同一批名字两处声明必然漂移"
    )
    # 允许保留的那几块不许被改写：搬走令牌之后又「顺手调一下颜色」是最难查的一类偏差
    legacy_blocks = dict(legacy_roots)
    for selector, body in ported_roots:
        assert _squeeze(body) == _squeeze(legacy_blocks.get(selector, "")), (
            f"{name} 里的 `{selector}` 与旧资产不再逐字符一致；"
            "它之所以留在原位是因为层叠位置，不是因为可以改内容"
        )

    expected = _squeeze(legacy_body)
    actual = _squeeze(_without_at_imports(ported_body))
    if expected != actual:
        legacy_decls = _declarations(_strip_at_blocks(legacy_body))
        ported_decls = _declarations(_strip_at_blocks(ported_body))
        missing = [item for item in legacy_decls if item not in ported_decls]
        extra = [item for item in ported_decls if item not in legacy_decls]
        pytest.fail(
            f"{name} 与旧资产的正文不再逐字符一致。\n"
            f"  旧文件里有、新文件里没有的声明：{missing[:8]}\n"
            f"  新文件里有、旧文件里没有的声明：{extra[:8]}\n"
            f"  旧文件被删掉的 `:root` 块：{[s for s, _ in legacy_roots]}\n"
            "  规则漏搬或多搬都会变成像素差，请对齐两边。"
        )


@pytest.mark.parametrize("name", CHARACTER_COPY)
def test_removed_token_blocks_really_live_in_the_token_source(name: str) -> None:
    """被删掉的 `:root` 块里的令牌，必须在 `tokens.css` 里找得到同名声明。

    「删掉」与「搬走」是两件事：这里防的是把令牌顺手删掉而不是搬走——
    令牌缺失不会报错，只会让引用它的规则安静地落到兜底值或初始值。
    """
    legacy = _read(ASSETS / name)
    _body, removed = _strip_root_blocks(legacy)
    tokens = _read(STYLES / "tokens.css")

    names = re.findall(r"(--[a-z0-9-]+)\s*:", _strip_comments(
        "\n".join(body for _sel, body in removed)
    ))
    assert names, f"旧 {name} 里没有解析出任何令牌，解析规则可能失效了"

    missing = sorted({item for item in names if not re.search(rf"{re.escape(item)}\s*:", tokens)})
    assert not missing, (
        f"旧 {name} 的 `:root` 块里这些令牌既不在新文件里、也不在 tokens.css 里：{missing}；"
        "它们是从旧文件删掉的，必须已经在令牌真源里落了户"
    )


def test_keynote_token_blocks_are_covered_by_the_token_source() -> None:
    """旧 keynote.css 里那几组「只有令牌声明」的块，已经整组搬进 tokens.css。

    这是这一轮唯二「没有逐字符搬」的地方（另一处是裸 `:root` 那三个默认派生色）。
    判据是两句话：
      - 旧文件里所有**只有令牌声明**的 `:root` 块，合起来声明的每一个令牌名
        都必须在 `tokens.css` 里找得到（漏一个都会让预设静默落回默认值）；
      - 这些块的选择器与上面的清单 `KEYNOTE_TOKEN_BLOCKS` 一一对应，
        防止清单过期后「看起来检查过了、其实什么都没检查」。
    """
    only_tokens, selectors = _token_blocks_of_keynote()
    tokens = _read(STYLES / "tokens.css")

    assert selectors, "旧 keynote.css 里一个「只有令牌声明」的 `:root` 块都没找到，判定规则失效了"
    # 裸 `:root`（默认主题的三个派生色）也在「只有令牌声明」之列，它的探针令牌
    # 由下面的 BARE_ROOT_TOKENS 分支单独核对，因此清单里只需补上这个键
    assert sorted(selectors) == sorted(set(KEYNOTE_TOKEN_BLOCKS) | {":root"}), (
        "旧文件里「只有令牌声明」的 `:root` 块与 KEYNOTE_TOKEN_BLOCKS 清单不一致：\n"
        f"  旧文件：{sorted(selectors)}\n"
        f"  清单：  {sorted(set(KEYNOTE_TOKEN_BLOCKS) | {':root'})}"
    )

    problems: list[str] = []
    for selector, body in only_tokens.items():
        declared = set(re.findall(r"(--[a-z0-9-]+)\s*:", _strip_comments(body)))
        absent = sorted(item for item in declared if not re.search(rf"{re.escape(item)}\s*:", tokens))
        if absent:
            problems.append(f"块 `{selector}` 里这些令牌没进 tokens.css：{absent[:6]}")
        for probe in KEYNOTE_TOKEN_BLOCKS.get(selector, BARE_ROOT_TOKENS):
            if probe not in declared:
                problems.append(f"块 `{selector}` 里找不到探针令牌 {probe}（清单过期了？）")

    bare = _merged_blocks(_read(ASSETS / "keynote.css")).get(":root")
    if bare is None:
        problems.append("旧文件里找不到裸 `:root` 块（默认主题派生色所在处）")
    else:
        for token in BARE_ROOT_TOKENS:
            if f"{token}:" not in _strip_comments(bare):
                problems.append(f"裸 `:root` 块里没有 {token}（清单过期了？）")
            elif not re.search(rf"{re.escape(token)}\s*:", tokens):
                problems.append(f"{token} 只由裸 `:root` 给出，却没有进 tokens.css")

    assert not problems, "keynote.css 的令牌块没有完整搬进 tokens.css：\n  " + "\n  ".join(problems)


# ---------------------------------------------------------------------------
# 2. 选择器全覆盖
# ---------------------------------------------------------------------------


def test_keynote_selector_inventory_is_complete_and_disjoint() -> None:
    """旧 keynote.css 的每个选择器都要在清单里，且清单自己不许重复。

    语汇的划分是硬性的：
      - `:root…` 块是**令牌块**，归 `tokens.css` 与
        `test_keynote_token_blocks_are_covered_by_the_token_source` 管；
      - 其余每一个选择器都是**元素级规则**，必须在 `KEYNOTE_SELECTORS` 清单里。

    这条先跑，是为了让后面两条的失败信息指向「清单过期」而不是「规则漏搬」。
    """
    legacy = _legacy_selector_map()
    token_selectors = set(_token_blocks_of_keynote()[1])
    legacy_rules = {key: value for key, value in legacy.items() if key not in token_selectors}
    expected = {_selector_key(selector) for selector in KEYNOTE_SELECTORS}

    unlisted = sorted(set(legacy_rules) - expected)
    assert not unlisted, (
        "旧 assets/keynote.css 里这些选择器没有写进 KEYNOTE_SELECTORS 清单：\n  "
        + "\n  ".join(unlisted)
        + "\n  新增或改动旧文件后请同步清单（清单是「逐条比对」的唯一依据）。"
    )

    stale = sorted(expected - set(legacy_rules))
    assert not stale, (
        "KEYNOTE_SELECTORS 里这些选择器在旧 assets/keynote.css 里已经不存在了：\n  "
        + "\n  ".join(stale)
        + "\n  清单与旧文件必须一一对应，否则它守不住任何东西。"
    )

    keys = [_selector_key(selector) for selector in KEYNOTE_SELECTORS]
    duplicated = sorted({key for key in keys if keys.count(key) > 1})
    assert not duplicated, f"KEYNOTE_SELECTORS 清单里有重复条目：{duplicated[:5]}"


def test_every_legacy_selector_is_ported() -> None:
    """旧文件的每个元素级选择器都必须在新工程的某一份样式表里逐字出现，且只落在一处。

    `:root` 令牌块不在本条的范围内（它们的去向由令牌那条判据守着）：它们的选择器
    在 `tokens.css` 里换了写法（`[data-a2v-preset='keynote']`，不带 `:root`），
    这是**刻意的**——两处写法都命中同一个元素（`<html>`，见 `A2VComposition` 里
    把 `data-a2v-preset` 写到 `documentElement` 的那一步，与旧页面
    `assets/declarative.js` 一致），而自定义属性沿 DOM 继承，因此不必把 `:root`
    写进选择器。逐字比对选择器会把这处刻意的差异误报成漏搬。
    """
    legacy = _legacy_selector_map()
    owners = _new_selector_map()
    token_selectors = set(_token_blocks_of_keynote()[1])

    missing: list[str] = []
    duplicated: list[str] = []
    moved: list[str] = []

    for selector, occurrences in legacy.items():
        if selector in token_selectors:
            continue
        where = owners.get(selector, [])
        if not where:
            missing.append(selector)
            continue
        if len(where) > len(occurrences):
            duplicated.append(
                f"{selector} → {where}（旧文件只有 {len(occurrences)} 处，新工程却有 {len(where)} 份）"
            )
        expected_files = {item.strip() for item in KEYNOTE_SELECTORS[selector].split(",")}
        if set(where) != expected_files:
            moved.append(
                f"{selector} → 在 {sorted(set(where))}，清单说是 {sorted(expected_files)}"
            )
        if len(occurrences) != len(where):
            missing.append(f"{selector}（旧文件 {len(occurrences)} 处，新工程 {len(where)} 处）")

    assert not missing, (
        "这些选择器没有搬到新工程（画面会缺掉它们对应的那块样式）：\n  "
        + "\n  ".join(missing)
    )
    assert not duplicated, (
        "这些选择器同时出现在两份以上样式表里，等于两处真源，改一处漏一处不会报错：\n  "
        + "\n  ".join(duplicated)
    )
    assert not moved, (
        "这些选择器的归属与清单不符（要么搬错了文件，要么清单该更新）：\n  "
        + "\n  ".join(moved)
    )


def test_ported_rule_bodies_match_the_legacy_bodies() -> None:
    """不只是选择器：每条规则的**正文**也要逐字符相同。

    选择器搬对了、正文里少写一个 `gap` 是最容易发生的漏搬，而它照样只表现为像素差。
    """
    legacy = {
        _selector_key(selector): body
        for selector, body in _top_level_blocks(_read(ASSETS / "keynote.css"))
    }
    ported = {
        _selector_key(selector): body
        for name in ("keynote.css", "tokens.css", "primitives.css")
        for selector, body in _top_level_blocks(_read(STYLES / name))
    }

    drifted: list[str] = []
    for selector, body in legacy.items():
        new_body = ported.get(selector)
        if new_body is None:
            continue  # 缺规则由 test_every_legacy_selector_is_ported 报，这里不重复
        if re.sub(r"\s+", "", body) != re.sub(r"\s+", "", new_body):
            old_decls = _declarations(body)
            new_decls = _declarations(new_body)
            lost = [item for item in old_decls if item not in new_decls]
            gained = [item for item in new_decls if item not in old_decls]
            drifted.append(
                f"{selector}\n      少了：{lost[:6]}\n      多了：{gained[:6]}"
            )

    assert not drifted, "这些规则的正文与旧资产不一致：\n  " + "\n  ".join(drifted)


def test_the_dead_grid_column_text_is_left_out_on_purpose() -> None:
    """旧文件里那处死文本**不进新工程**，而且省略这件事被写明。

    它没有消费者（`--a2v-grid-column` 从来没被定义过），浏览器会把这一条声明丢掉，
    因此省略它不改变任何画面。真正的原因是**可构建性**：那段文本里的右括号
    没有配对的左括号，Tailwind 的解析器会因此让整份样式表构建失败
    （`Missing opening (`），而这份样式表是画面几何的唯一真源。

    这条断言两侧都钉住：旧资产里那几行**仍在**（冻结参考不许被改），
    新文件里**不再有**，并且新文件的注释里写明了为什么。
    """
    legacy_lines = _read(ASSETS / "keynote.css").split("\n")
    ported = _read(STYLES / "keynote.css")
    ported_lines = ported.split("\n")

    for line in DEAD_TEXT_LINES:
        assert line in legacy_lines, f"旧资产里找不到这行死文本（冻结参考不该被改）：{line!r}"
    for line in DEAD_TEXT_DISTINCTIVE:
        assert line not in ported_lines, (
            "web/src/styles/keynote.css 里又出现了这行死文本："
            f"{line!r}\n"
            "  它会带进一个没有配对左括号的右括号，Tailwind 会拒绝整份样式表；"
            "  真要让画面用上 12 列栅格，请补全属性名与左括号，而不是照抄这段坏文本。"
        )

    assert "Tailwind 的 CSS 解析器会直接让整份样式表构建失败" in ported, (
        "省略死文本这件事必须在 keynote.css 的注释里写明原因，"
        "否则下一个人只会看到「少搬了几行」"
    )
    assert "--a2v-grid-column:" not in _read(STYLES / "tokens.css"), (
        "死文本不该进令牌真源：它不是一个合法的令牌声明，"
        "留在 tokens.css 只会让「哪些名字是真令牌」变得不可判定"
    )


# ---------------------------------------------------------------------------
# 3. 加载顺序
# ---------------------------------------------------------------------------


def _imports_of_index() -> list[str]:
    index = _read(STYLES / "index.css")
    return re.findall(r"@import\s+(?:url\()?['\"]([^'\"]+)['\"]", index)


def _legacy_link_order() -> list[str]:
    html = _read(DECLARATIVE_HTML)
    hrefs = re.findall(r'<link[^>]*href="([^"]+)"', html)
    return [Path(href).name for href in hrefs if href.endswith(".css")]


def test_import_order_matches_the_legacy_link_order() -> None:
    """`index.css` 的 `@import` 顺序 = 旧页面 `<link>` 顺序（新层排在最前）。

    顺序是几何的一部分：`.a2v-safe` 的 `gap` 由 keynote.css 与 declarative.css
    各有一条同权重声明，谁在后谁赢。顺序对调不会报错，只会让版面差几十像素。

    新工程可以在**两端**追加自己的层：旧五份之前（`NEW_LAYER_IMPORTS`，令牌与
    Tailwind 产出）或旧五份之后（`third-party.css`、`charts.css` 这类按组件
    归类的追加层）。追加必须**整块**进行：插进旧五份中间，同权重规则的胜负
    就会变，而画面只会「看起来差一点」。
    """
    imports = _imports_of_index()
    legacy = _legacy_link_order()

    assert legacy == [
        "base.css",
        "theme.css",
        "keynote.css",
        "figures.css",
        "declarative.css",
    ], f"旧页面的 `<link>` 顺序变了：{legacy}；本测试的前提是那五份的顺序"

    assert imports[: len(NEW_LAYER_IMPORTS)] == list(NEW_LAYER_IMPORTS), (
        f"新工程专有的层必须排在最前（tailwindcss → tokens.css）：{imports}"
    )
    tail = [
        Path(item).name
        for item in imports[len(NEW_LAYER_IMPORTS) :]
        # primitives.css 是 keynote.css 尾部的分身，位置由下面那条专门的测试守；
        # 这里比的是「旧五份」的相对顺序。
        if Path(item).name != "primitives.css"
    ]
    legacy_set = set(legacy)
    ported_order = [name for name in tail if name in legacy_set]
    appended = [name for name in tail if name not in legacy_set]
    assert ported_order == legacy, (
        "index.css 的 `@import` 顺序与 assets/declarative.html 的 `<link>` 顺序不一致：\n"
        f"  index.css：{ported_order}\n"
        f"  旧页面：  {legacy}\n"
        "  顺序不同，同权重选择器的胜负就不同——画面会变，却不会有任何报错。"
    )
    assert appended == tail[len(tail) - len(appended) :], (
        f"追加层必须整块地排在搬运层之后，不许插进旧五份中间：{imports}"
    )


def test_primitives_layer_sits_right_after_the_keynote_layer() -> None:
    """`primitives.css` 必须紧跟 `keynote.css`，不能提到最前面。

    它不是「新工程专有的层」，而是旧 `keynote.css` 的**尾部**（第 853–1064 行）
    搬出来的：四族基元（`a2v-surface` / `a2v-label` / `a2v-connector` / …）在旧文件里
    位于设计语言层之后，靠源序压过同权重的规则。搬到最前面会让源序反过来——
    实测 `[data-a2v-preset="keynote"] .a2v-label` 的字距从 `normal` 变成 `0.14em`，
    冰山幕的标注从 136px 宽变成 155px，那一帧的 PSNR 从 inf 掉到 34.2 dB。
    """
    imports = _imports_of_index()
    assert "./primitives.css" in imports, f"index.css 没有引 primitives.css：{imports}"
    index = imports.index("./primitives.css")
    assert imports[index - 1] == "./keynote.css", (
        "primitives.css 必须紧跟在 keynote.css 之后（它搬的是 keynote.css 的尾部）："
        f"{imports}"
    )


def test_index_css_has_no_hand_written_rules() -> None:
    """`index.css` 只留 `@import`：元素级规则一律由搬来的文件提供。

    这一轮把原先手写在 index.css 里的舞台 / 安全区 / 渲染模式规则删掉了，
    改成由 base.css 等文件提供。这里防的是它们又长回来——两处真源意味着
    「改了一处、另一处继续生效」，而画面只会看起来「没生效」。
    """
    index = _strip_comments(_read(STYLES / "index.css"))
    body = _without_at_imports(index).strip()
    assert body == "", (
        "web/src/styles/index.css 里还有 `@import` 之外的内容：\n"
        f"{body[:400]}\n"
        "  手写的舞台 / 安全区 / 渲染模式规则应当由搬来的样式表提供。"
    )


@pytest.mark.parametrize("selector, owners", sorted(LAYOUT_SELECTOR_OWNERS.items()))
def test_layout_rules_come_from_ported_files(selector: str, owners: tuple[str, ...]) -> None:
    """页面骨架的每条规则都要能在搬来的文件里找到（删掉手写规则的兜底判据）。"""
    found: list[str] = []
    for name in owners:
        if not (STYLES / name).is_file():
            continue
        if _selector_key(selector) in {
            _selector_key(item) for item, _body in _top_level_blocks(_read(STYLES / name))
        }:
            found.append(name)

    assert found, (
        f"`{selector}` 在 {list(owners)} 里都找不到：手写规则删掉了，搬来的文件里也没有，"
        "这一块版式会整块失效（不报错，只是画面塌掉）"
    )


def test_subtitle_rules_come_from_base_and_keynote() -> None:
    """字幕的两套规则各就各位：底子是 base.css，预设覆写是 keynote.css。"""
    base = _read(STYLES / "base.css")
    keynote = _read(STYLES / "keynote.css")

    assert ".a2v-subtitle" in base and "text-shadow" in base.split(".a2v-subtitle", 1)[1][:600], (
        "base.css 里的默认字幕规则（白字深描边）没有搬全"
    )
    for theme in ("dark", "light"):
        assert f'[data-a2v-preset="keynote"][data-a2v-theme="{theme}"] .a2v-subtitle' in keynote, (
            f"keynote.css 里少了 {theme} 主题的字幕覆写："
            "浅色底上的白字几乎读不出来，这一条是唯一的兜底"
        )


# ---------------------------------------------------------------------------
# 4. 画面不许有 CSS 动效
# ---------------------------------------------------------------------------


def _motion_offenders(text: str) -> list[str]:
    """找出 `animation:` / `transition:` / `@keyframes` 这类声明（注释已去掉）。"""
    clean = _strip_comments(text)
    offenders = [
        match.group(0).strip()
        for match in re.finditer(
            r"(^|[;{\s])(animation|animation-name|transition|transition-property)\s*:", clean, re.M
        )
    ]
    offenders += [match.group(0).strip() for match in re.finditer(r"@keyframes\b", clean)]
    return offenders


def test_no_motion_declarations_anywhere_in_the_new_styles() -> None:
    """新工程的所有样式表里都不许有 CSS 动效。

    画面只由帧号推导（`runtime/motion.ts` + `A2VComposition`）：CSS 动画会引入
    第二个时间源，预览与导出将不再逐帧对应，而且它无法被确定性校验覆盖。
    """
    files = sorted(STYLES.glob("*.css"))
    assert files, f"{STYLES} 下没有样式表，扫描规则可能失效了"

    offenders: list[str] = []
    for path in files:
        for hit in _motion_offenders(_read(path)):
            offenders.append(f"{path.name}: {hit}")

    assert not offenders, (
        "这些样式表里出现了 CSS 动效，画面会多出一个与帧号无关的时间源：\n  "
        + "\n  ".join(sorted(set(offenders)))
        + "\n  动效一律走 runtime/motion.ts 的帧驱动配方。"
    )


def test_legacy_sheets_have_no_motion_outside_preview_only_selectors() -> None:
    """旧样式表里允许存在的动效只有「预览控件」这一处。

    这是一个**显式排除清单**，不是一个宽松匹配：只有 `PREVIEW_ONLY_SELECTORS`
    里那几条选择器命中的规则才允许带动效属性，其余任何一处都直接失败。
    导出时 `html.a2v-rendering` 会把预览专用元素整块 `display: none`，
    因此它们不会进入任何一帧画面。
    """
    allow = tuple(_selector_key(item) for item in PREVIEW_ONLY_SELECTORS)
    offenders: list[str] = []

    for path in sorted(ASSETS.glob("*.css")):
        for selector, body in _blocks(_read(path)):
            hits = _motion_offenders(body)
            if not hits:
                continue
            key = _selector_key(selector)
            if any(item in key for item in allow):
                continue
            offenders.append(f"{path.name} → {key}: {hits}")

    assert not offenders, (
        "旧样式表里出现了「非预览控件」的 CSS 动效：\n  "
        + "\n  ".join(offenders)
        + "\n  画面本身不许有 CSS 动画；如果这是预览控件新增的规则，"
        "请把它的选择器加进 PREVIEW_ONLY_SELECTORS 并说明理由。"
    )
