"""同帧只解码一次，使用已有 Pillow 派生评审尺寸。"""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image


def derive_images(source: Path, targets: dict[int, Path]) -> None:
    with Image.open(source) as image:
        image.load()
        for width, path in targets.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            if width == image.width:
                # 原生证据保留原始字节，避免无意义重编码或元数据变化。
                shutil.copyfile(source, path)
            else:
                height = round(image.height * width / image.width)
                with image.resize((width, height), Image.Resampling.LANCZOS) as resized:
                    resized.save(path)
