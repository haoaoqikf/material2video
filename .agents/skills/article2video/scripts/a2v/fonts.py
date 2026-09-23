"""渲染用字的字体覆盖判定。

**为什么需要它**：缺字是唯一一种静默失败。网页声明的字体里没有某个字时，
浏览器不报错也不警告，直接用系统字体顶上——字宽、字重、基线全变，而现有门禁
照过（K4 对齐与 K7 溢出量的都是元素框，不看字形来自哪个字体）。
这条也是 webfont 子集化的前置条件：不做逐字检查就切字体，等于把上面那种漂移
变成常态。

判据只取字体文件自己的 `cmap`，不按字体名或 Unicode 区段猜覆盖面——
这条闸门存在的唯一理由就是不能猜。零依赖：支持格式 4（BMP）与格式 12（含
BMP 之外）；同一字符出现在多个子表时取「有字形」的那个，那是字体的正常做法。
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

from . import assets

_FONT_URL = re.compile(r"""url\(\s*["']?([^"')]+\.(?:ttf|otf|woff2?))["']?\s*\)""", re.IGNORECASE)
_CONTENT_STRING = re.compile(r"""content\s*:\s*["']([^"']+)["']""")


def _cmap_offsets(data: bytes) -> list[tuple[int, int, int]]:
    """返回 (platformID, encodingID, offset) 列表。"""
    if len(data) < 12:
        raise ValueError("不是字体文件：太短")
    tag = data[:4]
    if tag not in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf"):
        raise ValueError(f"不是认识的字体格式：{tag!r}")
    num_tables = struct.unpack(">H", data[4:6])[0]
    cmap_offset = None
    for index in range(num_tables):
        start = 12 + index * 16
        entry = data[start:start + 16]
        if len(entry) < 16:
            break
        if entry[:4] == b"cmap":
            cmap_offset = struct.unpack(">I", entry[8:12])[0]
            break
    if cmap_offset is None:
        raise ValueError("字体里没有 cmap 表")
    count = struct.unpack(">H", data[cmap_offset + 2:cmap_offset + 4])[0]
    found = []
    for index in range(count):
        base = cmap_offset + 4 + index * 8
        platform, encoding, offset = struct.unpack(">HHI", data[base:base + 8])
        found.append((platform, encoding, cmap_offset + offset))
    return found


def _format4_codepoints(data: bytes, offset: int) -> set[int]:
    seg_x2 = struct.unpack(">H", data[offset + 6:offset + 8])[0]
    segments = seg_x2 // 2
    ends = struct.unpack(f">{segments}H", data[offset + 14:offset + 14 + seg_x2])
    starts_at = offset + 16 + seg_x2
    starts = struct.unpack(f">{segments}H", data[starts_at:starts_at + seg_x2])
    deltas_at = starts_at + seg_x2
    deltas = struct.unpack(f">{segments}h", data[deltas_at:deltas_at + seg_x2])
    ranges_at = deltas_at + seg_x2
    ranges = struct.unpack(f">{segments}H", data[ranges_at:ranges_at + seg_x2])
    points: set[int] = set()
    for index in range(segments):
        start, end = starts[index], ends[index]
        if start == 0xFFFF or end < start:
            continue
        for code in range(start, end + 1):
            if ranges[index] == 0:
                glyph = (code + deltas[index]) & 0xFFFF
            else:
                at = ranges_at + index * 2 + ranges[index] + (code - start) * 2
                if at + 2 > len(data):
                    continue
                glyph = struct.unpack(">H", data[at:at + 2])[0]
                if glyph:
                    glyph = (glyph + deltas[index]) & 0xFFFF
            if glyph:
                points.add(code)
    return points


def _format12_codepoints(data: bytes, offset: int) -> set[int]:
    groups = struct.unpack(">I", data[offset + 12:offset + 16])[0]
    points: set[int] = set()
    for index in range(groups):
        base = offset + 16 + index * 12
        start, end, glyph = struct.unpack(">III", data[base:base + 12])
        if glyph == 0 or end < start or end - start > 0x11000:
            continue
        points.update(range(start, end + 1))
    return points


def codepoint_coverage(font: str | Path) -> set[int]:
    """字体里有字形的码位集合。"""
    data = Path(font).read_bytes()
    points: set[int] = set()
    for _platform, _encoding, offset in _cmap_offsets(data):
        fmt = struct.unpack(">H", data[offset:offset + 2])[0]
        if fmt == 4:
            points |= _format4_codepoints(data, offset)
        elif fmt == 12:
            points |= _format12_codepoints(data, offset)
    return points


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


#: 分镜里**会被渲染**的文本字段。`narration` 当前不渲染，因此不在其中——
#: 把不渲染的文本算进来会让闸门报出人看不见的缺字，那是噪音。
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


def page_fonts(page_file: Path) -> list[Path]:
    """网页实际声明的字体文件：页面自身与它引用的样式表里的 @font-face。"""
    html = page_file.read_text(encoding="utf-8", errors="replace")
    sources = [(page_file, html)]
    for _reference, candidate in assets.local_assets(page_file, html):
        if candidate.suffix.lower() == ".css":
            sources.append((candidate, candidate.read_text(encoding="utf-8", errors="replace")))
    fonts: list[Path] = []
    for owner, text in sources:
        for reference in _FONT_URL.findall(text):
            if reference.startswith(("http://", "https://", "//", "data:")):
                continue
            path = (owner.parent / reference.split("?")[0].split("#")[0]).resolve()
            if path.is_file() and path not in fonts:
                fonts.append(path)
    return fonts


def preset_strings(page_file: Path) -> dict[str, str]:
    """样式表里会被渲染但不在分镜里的固定字串（CSS `content:`）。"""
    html = page_file.read_text(encoding="utf-8", errors="replace")
    found: dict[str, str] = {}
    for _reference, candidate in assets.local_assets(page_file, html):
        if candidate.suffix.lower() != ".css":
            continue
        text = candidate.read_text(encoding="utf-8", errors="replace")
        for literal in _CONTENT_STRING.findall(text):
            if literal and literal not in ("", "none", "normal"):
                found[f"{candidate.name} content:{literal}"] = literal
    return found


def audit_fonts(
    fonts: list[Path],
    storyboard: dict,
    extra_texts: dict[str, str] | None = None,
) -> list[dict]:
    """按一组**实际注册**的字体文件查缺字。

    判据是「所有注册过的字体加起来有没有这个字形」——只有当每个字体都没有时，
    浏览器才真的会回退到系统字体，那才是这条闸门要抓的东西。
    字体清单为空时返回空表：无从判断，也不该凭空拦人。

    取字体文件的方式与画面实现有关（旧页面解析样式表里的 `@font-face`，
    React 路径读字体清单），所以清单由调用方给，这里只管判定。
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


def audit_page(page_file: Path, storyboard: dict) -> list[dict]:
    """按网页**实际声明**的字体查缺字。

    网页没声明任何字体文件时不报（无从判断，也不该凭空拦人）。
    """
    return audit_fonts(
        page_fonts(page_file),
        storyboard,
        preset_strings(page_file),
    )




def charset_for(storyboard: dict, extra_texts: dict[str, str] | None = None) -> str:
    """该作品会被渲染的全部字符（去重、排序稳定）。

    复用 `rendered_strings`：切子集用的字符集必须与体检检查的范围**同一口径**，
    否则会出现「切的时候没带上、体检说缺字」或者反过来的错位。
    """
    chars: set[str] = set()
    for _where, text in [*rendered_strings(storyboard), *(extra_texts or {}).items()]:
        chars.update(char for char in text if not char.isspace())
    return "".join(sorted(chars))


class SubsetUnavailable(RuntimeError):
    """没装可选依赖（fonttools）。"""


def subset_font(source: str | Path, text: str, target: str | Path) -> Path:
    """切出只含 `text` 里字符的字体，写到 `target`。

    源文件**不动**——共享字体要渲染将来的任意文章，按今天的文本切共享资产
    明天就会缺字。切出来的子集只服务这一支作品。
    需要可选依赖 `fonttools`（`uv sync --extra fonts`）；没装时抛
    `SubsetUnavailable`，由调用方给出清楚的提示而不是崩掉。
    """
    try:
        from fontTools import subset as fonttools_subset
    except ImportError as exc:  # pragma: no cover - 取决于环境
        raise SubsetUnavailable(
            "切字体子集需要可选依赖：uv sync --extra fonts（默认渲染不需要它）"
        ) from exc

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
