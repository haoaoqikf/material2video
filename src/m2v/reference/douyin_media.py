"""抖音参考素材的媒体下载、摘要与目录校验。"""
from __future__ import annotations

import hashlib
import json
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.engine.media_probe import probe_dimensions
from .douyin_detail import DESKTOP_UA, REFERER

_IMAGE_SUFFIXES = {".webp", ".jpg", ".jpeg", ".png", ".gif", ".avif"}


def _short(url: str, limit: int = 100) -> str:
    return url if len(url) <= limit else url[:limit] + "…"


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": DESKTOP_UA, "Referer": REFERER, "Accept": "*/*"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise M2VError(f"HTTP {status}")
        with destination.open("wb") as sink:
            shutil.copyfileobj(response, sink, length=1 << 20)


def _media_signature(path: Path, kind: str) -> bool:
    with path.open("rb") as stream:
        head = stream.read(32)
    if kind == "video":
        return b"ftyp" in head[:16] or head.startswith(b"\x1aE\xdf\xa3")
    return (
        head.startswith(b"\xff\xd8")  # JPEG
        or head.startswith(b"\x89PNG")
        or head.startswith(b"GIF8")
        or (head.startswith(b"RIFF") and head[8:12] == b"WEBP")
        or (head[4:8] == b"ftyp" and head[8:12] in {b"avif", b"avis"})
    )


def _download_first(urls: list[str], destination: Path, kind: str) -> dict:
    errors: list[str] = []
    for url in urls:
        try:
            _download(url, destination)
            if destination.stat().st_size == 0:
                raise M2VError("响应为空")
            if not _media_signature(destination, kind):
                raise M2VError("返回内容不是可识别的媒体（可能是登录或风控页面）")
            return {
                "sha256": _digest(destination),
                "bytes": destination.stat().st_size,
            }
        except (OSError, M2VError) as exc:
            errors.append(f"{_short(url)}：{exc}")
            destination.unlink(missing_ok=True)
    label = "视频" if kind == "video" else "图片"
    raise M2VError(f"{label}下载失败；" + "；".join(errors))


def _guess_ext(url: str, kind: str) -> str:
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    if kind == "video":
        return ".mp4"
    if suffix in _IMAGE_SUFFIXES:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".webp"


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _measure(path: Path) -> dict:
    try:
        width, height = probe_dimensions(path)
    except M2VError:
        return {}
    return {"width": width, "height": height}


def verify_directory(directory: Path, *, quiet: bool = False) -> list[dict]:
    """按 ``recipe.json`` 复核每个文件；任何缺失、字节数或摘要变化都失败。"""
    directory = directory.expanduser().resolve()
    recipe_path = directory / "recipe.json"
    metadata_path = directory / "metadata.json"
    if not recipe_path.is_file():
        raise M2VError(f"缺少 recipe.json：{directory}")
    if not metadata_path.is_file():
        raise M2VError(f"缺少 metadata.json：{directory}")
    try:
        recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise M2VError(f"recipe.json 不是合法 JSON：{exc}") from exc
    if recipe.get("schemaVersion") != 1:
        raise M2VError(f"不支持的 recipe.json 版本：{recipe.get('schemaVersion')!r}")
    entries = recipe.get("files") or []
    if not entries:
        raise M2VError("recipe.json 没有登记任何文件")

    records: list[dict] = []
    problems: list[str] = []
    for entry in entries:
        relative = entry.get("path")
        if not isinstance(relative, str) or not relative:
            problems.append("登记项缺少 path")
            continue
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            problems.append(f"非法路径：{relative}")
            continue
        target = directory / path
        if not target.is_file():
            problems.append(f"缺少文件：{relative}")
            continue
        actual_bytes = target.stat().st_size
        actual_digest = _digest(target)
        if actual_bytes != entry.get("bytes") or actual_digest != entry.get("sha256"):
            problems.append(f"摘要或字节数不符：{relative}")
            continue
        records.append({
            "path": relative,
            "sha256": actual_digest,
            "bytes": actual_bytes,
            "width": entry.get("width"),
            "height": entry.get("height"),
        })
        if not quiet:
            print(f"通过：{relative}（{actual_bytes} 字节）")
    if problems:
        raise M2VError("；".join(problems))
    return records
