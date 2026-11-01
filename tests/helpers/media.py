"""跨类型测试共用的媒体夹具：图像生成、素材导入与素材记录。"""
from __future__ import annotations

import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.types.general import media_assets


def make_image(path: Path, size: str = "864x700") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"color=c=0x334455:s={size}", "-frames:v", "1", str(path)], check=True)
    return path


def importer(root: Path, entries, base: Path | None = None, **kwargs):
    return media_assets.import_assets(root, {"schemaVersion": 1, "assets": entries},
                                     base=base or root, **kwargs)


def entry(identity, kind, **extra):
    return {"id": identity, "kind": kind, **extra}
