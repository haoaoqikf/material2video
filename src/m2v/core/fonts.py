"""渲染用字的字体覆盖判定。

**为什么需要它**：缺字是唯一一种静默失败。网页声明的字体里没有某个字时，
浏览器不报错也不警告，直接用系统字体顶上——字宽、字重、基线全变，而现有门禁
照过（K4 对齐与 K7 溢出量的都是元素框，不看字形来自哪个字体）。
这条也是 webfont 子集化的前置条件：不做逐字检查就切字体，等于把上面那种漂移
变成常态。

判据只取字体文件自己的 `cmap`，不按字体名或 Unicode 区段猜覆盖面——
这条闸门存在的唯一理由就是不能猜。`cmap` 解析交给 fontTools：它同时覆盖
格式 4（BMP）与格式 12（含 BMP 之外），同一字符出现在多个子表时
`getBestCmap()` 会取「有字形」的那个，那是字体的正常做法。
"""

from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTFont, TTLibError


def codepoint_coverage(font: str | Path) -> set[int]:
    """字体里有字形的码位集合。认不出的文件转成 `ValueError`。"""
    path = Path(font)
    try:
        with TTFont(str(path), lazy=True) as face:
            cmap = face.getBestCmap() or {}
    except (TTLibError, OSError, ValueError, KeyError) as exc:
        raise ValueError(f"不是认识的字体文件：{path.name}") from exc
    return {code for code, glyph in cmap.items() if glyph and glyph != ".notdef"}


def missing_glyphs(font: str | Path, text: str, coverage: set[int] | None = None) -> list[str]:
    """text 里在字体中没有字形、需要去重的字符（按出现顺序）。"""
    known = codepoint_coverage(font) if coverage is None else coverage
    seen: dict[str, None] = {}
    for char in text:
        if char.isspace():
            continue
        if ord(char) not in known:
            seen.setdefault(char, None)
    return list(seen)


#: 分镜里**会被渲染**的文本字段。`narrationSegments`（分段口播）不渲染，
#: 因此不在其中——把不渲染的文本算进来会让闸门报出人看不见的缺字，那是噪音。
RENDERED_FIELDS = (
    "text", "title", "subtitle", "lead", "label", "labels", "quote", "caption",
    "value", "unit", "name", "note", "footnote", "legend", "tick", "item", "items",
)


def rendered_strings(storyboard: dict) -> list[tuple[str, str]]:
    """分镜里会渲染的文本，逐段返回 (定位, 文本)。

    定位尽量具体（`sceneId.字段路径`），因为「缺字」这个结论只有配上
    「缺在哪儿」才可修。
    """
    found: list[tuple[str, str]] = []

    def walk(node, where: str) -> None:
        if isinstance(node, dict):
            scene = node.get("id") if isinstance(node.get("id"), str) else None
            for key, value in node.items():
                if key == "narrationSegments":
                    continue
                spot = f"{scene or where}.{key}" if scene else f"{where}.{key}"
                if isinstance(value, str) and key in RENDERED_FIELDS:
                    found.append((spot, value))
                elif isinstance(value, (dict, list)):
                    walk(value, spot)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{where}[{index}]")

    walk(storyboard, "storyboard")
    return found


def audit_fonts_strict(font: str | Path, entries: list[tuple[str, str]]) -> list[dict]:
    """用**单一字体**的 cmap 检查，不做跨字体并集。

    全局字体并集会掩盖「宋体缺字、黑体有字」：浏览器实际用前者，缺字仍会静默回退。
    作品选用的风格包字体必须有自己的严格检查。
    """
    coverage = codepoint_coverage(font)
    findings: list[dict] = []
    for where, text in entries:
        missing = missing_glyphs(font, text, coverage)
        if missing:
            findings.append({"where": where, "missing": missing, "font": str(font)})
    return findings


def audit(
    storyboard: dict,
    font: str | Path,
    extra_texts: dict[str, str] | None = None,
) -> list[dict]:
    """逐段查缺字，返回 [{where, missing}]（缺字为空则不出现）。

    `extra_texts` 收预设层里会被渲染的固定字串（如 CSS `content:` 里的符号）：
    它们不属于分镜，但缺了同样会静默回退。
    """
    coverage = codepoint_coverage(font)
    findings: list[dict] = []
    for where, text in [*rendered_strings(storyboard), *(extra_texts or {}).items()]:
        missing = missing_glyphs(font, text, coverage)
        if missing:
            findings.append({"where": where, "missing": missing})
    return findings


def audit_fonts(
    fonts: list[Path],
    storyboard: dict,
    extra_texts: dict[str, str] | None = None,
) -> list[dict]:
    """按一组**实际注册**的字体文件查缺字。

    判据是「所有注册过的字体加起来有没有这个字形」——只有当每个字体都没有时，
    浏览器才真的会回退到系统字体，那才是这条闸门要抓的东西。
    字体清单为空时返回空表：无从判断，也不该凭空拦人。

    各类型 composition 共用同一份字体清单，
    所以清单由调用方给，这里只管判定。
    """
    if not fonts:
        return []
    shared = set()
    for font in fonts:
        try:
            shared |= codepoint_coverage(font)
        except ValueError:  # 认不出的字体文件：跳过，不因此拦人
            continue
    if not shared:
        return []
    findings: list[dict] = []
    for where, text in [*rendered_strings(storyboard), *(extra_texts or {}).items()]:
        missing = missing_glyphs(fonts[0], text, shared)
        if missing:
            findings.append({"where": where, "missing": missing})
    return findings


def charset_for(storyboard: dict, extra_texts: dict[str, str] | None = None) -> str:
    """该作品会被渲染的全部字符（去重、排序稳定）。

    复用 `rendered_strings`：切子集用的字符集必须与体检检查的范围**同一口径**，
    否则会出现「切的时候没带上、体检说缺字」或者反过来的错位。
    """
    chars: set[str] = set()
    for _where, text in [*rendered_strings(storyboard), *(extra_texts or {}).items()]:
        chars.update(char for char in text if not char.isspace())
    return "".join(sorted(chars))


def subset_font(source: str | Path, text: str, target: str | Path) -> Path:
    """切出只含 `text` 里字符的字体，写到 `target`。

    源文件**不动**——共享字体要渲染将来的任意文章，按今天的文本切共享资产
    明天就会缺字。切出来的子集只服务这一支作品。fontTools 是运行时依赖，
    不再有“没装就不可用”的分支。
    """
    from fontTools import subset as fonttools_subset

    source_path, target_path = Path(source), Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    options = fonttools_subset.Options()
    options.layout_features = ["*"]          # 保留排版特性（连字、字距）
    options.name_IDs = ["*"]                 # 保留字体名，避免调试时认不出
    options.notdef_outline = True
    options.recalc_bounds = True
    font = fonttools_subset.load_font(str(source_path), options)
    subsetter = fonttools_subset.Subsetter(options=options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    fonttools_subset.save_font(font, str(target_path), options)
    font.close()
    return target_path
