"""设计宪法：把「什么算高级」里可以机检的部分变成断言。

宪法全文见 `references/design-constitution.md`，每条都有编号。
这里只实现**不需要渲染**就能判定的那几条：结构、曲线纪律、模糊、挂载点、
文案单一真源、安全区。需要看画面才能判定的（对比度、层级、节奏、是否好懂）
留给 `inspect.py` 的量测与人工评审清单，不在这里假装能自动判定。

判定结果复用 storyboard 的 Report：同样区分 error（阻断）与 warning（提醒），
CLI 输出格式也保持一致。
"""

from __future__ import annotations

import re
from pathlib import Path

from . import catalog
from .assets import local_assets
from .storyboard import Report

#: 允许出现的动效曲线。linear 只用于匀速位移（例如上升的光点），
#: 其余一律走三条：出场 outQuint、双向 inOutCubic、逐项门控 outCubic。
ALLOWED_CURVES = frozenset({"outQuint", "outCubic", "inOutCubic", "linear"})

_CURVE_LITERAL = re.compile(r"['\"]((?:in|out)[A-Z][A-Za-z]*|linear)['\"]")
_BLUR = re.compile(r"filter\s*:\s*[^;]*blur\(|backdrop-filter\s*:", re.IGNORECASE)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_JS_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*")

#: 只数出现该属性的**标签**，不数 CSS 选择器里的同名属性
_ATTRIBUTE_TAG = r"<[a-zA-Z][^>]*\b{attr}\b"

#: 分镜里这么长的文案出现在网页源码里，说明网页自己抄了一份
_COPY_MATCH_MIN_CHARS = 8

#: 安全区令牌：由 base.css 提供，网页也可以自己定义
_SAFE_AREA_TOKENS = ("--a2v-safe-top", "--a2v-safe-bottom", "--a2v-safe")


def _strip_comments(text: str, kind: str) -> str:
    """去掉注释：注释里引用文案或曲线名是正常的，不该被当成违规。"""
    if kind == "html":
        text = _HTML_COMMENT.sub(" ", text)
        text = _CSS_COMMENT.sub(" ", text)
        return _JS_COMMENT.sub(" ", text)
    if kind == "css":
        return _CSS_COMMENT.sub(" ", text)
    return _JS_COMMENT.sub(" ", text)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_structure(
    page_text: str, path: str, report: Report, *, runtime_scenes: bool = False
) -> None:
    """C1 三层：舞台 / 背景层 / 场景层都必须存在，且场景在舞台之内。

    `runtime_scenes` 用于共享页面：场景层由它按分镜在运行时创建，源文件里本来就没有
    `[data-a2v-scene]`，因此跳过这一项，而不是把「按分镜生成」误报成「缺少场景」。
    """
    body = _strip_comments(page_text, "html")
    if "data-a2v-stage" not in body:
        report.error(f"{path}#C1", "页面缺少 [data-a2v-stage]：没有舞台就没有统一的层级与安全区")
    if not re.search(r"class=\"[^\"]*\b(?:stage-bg|a2v-bg-[\w-]+)", body):
        report.warn(f"{path}#C1", "页面没有背景层：高级感来自「背景 / 表面 / 焦点」三层，缺一层会显得平")
    if runtime_scenes:
        return
    if "data-a2v-scene" not in body:
        report.error(f"{path}#C1", "页面没有任何 [data-a2v-scene]：运行时按场景切帧，缺了就无法逐帧渲染")


def check_curves(scripts: list[tuple[str, str]], report: Report) -> None:
    """C2 曲线纪律：只有三条曲线（外加匀速位移用的 linear）。"""
    for name, text in scripts:
        body = _strip_comments(text, "js")
        for line_number, line in enumerate(body.splitlines(), start=1):
            for curve in _CURVE_LITERAL.findall(line):
                if curve not in ALLOWED_CURVES:
                    report.warn(
                        f"{name}:{line_number}#C2",
                        f"出现了额外曲线 '{curve}'：只允许 "
                        f"{'/'.join(sorted(ALLOWED_CURVES))}，混用更多曲线会让画面显得杂",
                    )


def check_blur(styles: list[tuple[str, str]], report: Report) -> None:
    """C3 不用大面积模糊：模糊既慢又在逐帧渲染下不稳定。"""
    for name, text in styles:
        body = _strip_comments(text, "css")
        match = _BLUR.search(body)
        if match:
            line = body.count("\n", 0, match.start()) + 1
            report.warn(
                f"{name}:{line}#C3",
                "使用了 blur / backdrop-filter：大面积模糊既拖慢逐帧截图又容易糊成一片，"
                "请改用 radial-gradient 或分层阴影做柔光",
            )


def count_elements(html: str, attribute: str) -> int:
    """数「带某个属性的标签」有多少个。

    不能直接数属性名出现的次数：`[data-a2v-scene] { … }` 这样的选择器
    也会命中，会把场景数多算一个。
    """
    pattern = re.compile(_ATTRIBUTE_TAG.format(attr=re.escape(attribute)), re.IGNORECASE)
    return len(pattern.findall(html))


def check_mounts(page_text: str, scene_ids: list[str], report: Report, path: str) -> None:
    """C4 每幕一个挂载点。

    完全不用组件库的网页（一个挂载点都没有）只提醒：它自己画图形，
    画面不一定有问题。**部分挂载**才是真错误——那说明有的场景忘了接组件，
    在成片里就是一块空白，而预览时未必看得出来。
    """
    body = _strip_comments(page_text, "html")
    mounts = count_elements(body, "data-a2v-figure")
    scenes = len(scene_ids)
    if not scenes:
        return
    if mounts == 0:
        report.warn(
            f"{path}#C4",
            "网页没有使用视觉组件库（没有 [data-a2v-figure] 挂载点）："
            "先查 references/figure-catalog.md 有没有现成组件可用",
        )
        return
    if mounts != scenes:
        report.error(
            f"{path}#C4",
            f"{scenes} 个场景只有 {mounts} 个 [data-a2v-figure] 挂载点："
            "没接组件的场景在成片里会是一块空白",
        )


def check_single_source(page_text: str, copies: list[str], report: Report, path: str) -> None:
    """C5 文案单一真源：分镜里的长句不得在网页源码里再写一遍。"""
    body = _strip_comments(page_text, "html")
    for text in copies:
        if len(text) < _COPY_MATCH_MIN_CHARS:
            continue
        if text in body:
            head = text[:14] + ("…" if len(text) > 14 else "")
            report.error(
                f"{path}#C5",
                f"网页源码里出现了分镜文案「{head}」：文案只写在分镜里，"
                "网页抄一份就会在改文案时两边不一致",
            )


def check_safe_area(styles: list[tuple[str, str]], page_text: str, report: Report, path: str) -> None:
    """C6 安全区：由 base.css 提供，网页也可以自己声明令牌。"""
    combined = page_text + "\n" + "\n".join(text for _name, text in styles)
    if not any(token in combined for token in _SAFE_AREA_TOKENS):
        report.warn(
            f"{path}#C6",
            "没有找到安全区令牌（--a2v-safe-*）：竖屏上下边缘容易被界面元素盖住，"
            "请引入 base.css 或自行声明",
        )


def check_page(
    page_path: str | Path,
    storyboard_texts: list[str] | None = None,
    *,
    runtime_scenes: bool = False,
) -> Report:
    """对网页做一遍静态体检。storyboard_texts 提供时同时检查文案单一真源。

    `runtime_scenes` 表示网页在运行时按分镜生成场景（共享页面）。这类页面的
    场景层、组件挂载点和画面文案都不在源文件里，依赖源码的三项检查（C1 场景层、
    C4 挂载点、C5 文案单一真源）在这里没有意义，跳过并把结论交给运行时探针；
    曲线纪律、模糊与安全区仍然照常检查。
    """
    report = Report()
    page = Path(str(page_path))
    if not page.is_file():
        report.error(str(page), "网页文件不存在")
        return report

    html = _read(page)
    styles: list[tuple[str, str]] = [(page.name, html)]
    scripts: list[tuple[str, str]] = []
    for reference, candidate in local_assets(page, html):
        try:
            text = _read(candidate)
        except OSError:
            continue
        (scripts if candidate.suffix == ".js" else styles).append((reference, text))

    scene_count = count_elements(_strip_comments(html, "html"), "data-a2v-scene")
    check_structure(html, page.name, report, runtime_scenes=runtime_scenes)
    check_curves(scripts, report)
    check_blur(styles, report)
    if not runtime_scenes:
        check_mounts(html, ["scene"] * scene_count, report, page.name)
    check_safe_area(styles, html, report, page.name)
    if storyboard_texts and not runtime_scenes:
        check_single_source(html, storyboard_texts, report, page.name)
    return report


def storyboard_texts(scenes: list[dict]) -> list[str]:
    """从分镜里挑出「长到可以用于比对」的文案串。

    只取长句：短词（角标、标签）本来就可能与网页上的固定词组重合，
    拿它们比对会产生大量误报。
    """
    found: list[str] = []
    for scene in scenes:
        data = scene.get("data") or {}
        for value in _walk_strings(data):
            # 分镜里允许用 \n 手动折行，网页里也允许，因此按行比对
            for line in value.split("\n"):
                line = line.strip()
                if len(line) >= _COPY_MATCH_MIN_CHARS:
                    found.append(line)
    return found


def _walk_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for key, sub in value.items() if key != "figure" for item in _walk_strings(sub)]
    if isinstance(value, list):
        return [item for sub in value for item in _walk_strings(sub)]
    return []


def known_kinds_hint() -> str:
    """给错误信息用的一句话组件清单。"""
    return "、".join(catalog.known_kinds())
