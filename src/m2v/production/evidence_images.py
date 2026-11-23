"""复用净化 PNG 并派生其他评审尺寸。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image


def derive_images(source: Path, widths: list[int]) -> list[Path]:
    paths = []
    with Image.open(source) as image:
        image.load()
        for width in dict.fromkeys(widths):
            if width == image.width:
                paths.append(source)
                continue
            path = source.with_name(f"{source.stem}-{width}.png")
            height = round(image.height * width / image.width)
            with image.resize((width, height), Image.Resampling.LANCZOS) as resized:
                resized.save(path)
            paths.append(path)
    return paths


def reuse_native_displays(pack: dict) -> tuple[list[dict], set[str]]:
    """按已核验的封存摘要复用原图，返回新观察项和可省略的文件。"""
    receipts = {record["path"]: record["sha256"] for record in pack["files"]}
    items = []
    redundant = set()
    used = set()
    for item in pack["items"]:
        used.add(item["path"])
        sequence = []
        for frame in item["sequence"]:
            source = frame["path"]
            used.add(source)
            displays = []
            for path in frame["displayPaths"]:
                if path != source and path in receipts and receipts[path] == receipts.get(source):
                    redundant.add(path)
                    path = source
                used.add(path)
                displays.append(path)
            sequence.append({**frame, "displayPaths": displays})
        items.append({**item, "sequence": sequence})
    return items, redundant - used
