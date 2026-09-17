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

import struct
from pathlib import Path


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
