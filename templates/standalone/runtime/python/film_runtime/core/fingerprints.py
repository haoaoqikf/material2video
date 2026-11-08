"""Stable content hashing shared by project types and rendering infrastructure."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

_TEXT = {".css", ".js", ".mjs", ".cjs", ".json", ".html", ".htm", ".svg", ".txt", ".md"}


def fingerprint(source: dict) -> str:
    encoded = json.dumps(source, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def file_digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in _TEXT:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def module_files(module) -> list[Path]:
    """一个模块的实现文件：包返回包内全部 `.py`，单文件模块返回自身。

    拆包后 `module.__file__` 只是 `__init__.py`（通常只有重导出），拿它做指纹会漏掉
    真正的实现，让「改了实现却判成当前」。指纹按文件内容算，因此把包内每个文件都算进去
    与把整包当一个文件是等价的强度，而前者在拆包后不会失效。
    """
    path = Path(module.__file__).resolve()
    if path.name != "__init__.py":
        return [path]
    return sorted(path.parent.rglob("*.py"))
