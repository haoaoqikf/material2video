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
