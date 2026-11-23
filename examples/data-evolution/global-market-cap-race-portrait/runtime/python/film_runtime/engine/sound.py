"""声音素材摘要；校验与解析在本工程内完成，不在共享层联网。"""
from __future__ import annotations

import hashlib
from pathlib import Path


def asset_digest(path: Path) -> str:
    """声音素材可能很长，摘要同样按块读取，不将文件整体装入内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()
