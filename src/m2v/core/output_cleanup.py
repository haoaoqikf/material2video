"""Remove superseded, reproducible media from one project's outputs directory."""
from __future__ import annotations

import os
import re
from pathlib import Path


VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv", ".avi"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg"}
SIDECAR_SUFFIXES = (".srt", ".provenance.json", ".performance.json")
_TEMP_DIR = re.compile(r"^(?:a2v|m2v|debug|tmp|render)(?:-|$)", re.IGNORECASE)
_KNOWN_REGENERABLE_DIRS = {"previews", "qa", "bench", "review-contact-sheets"}


def cleanup_after_render(outputs_dir: str | Path, current_video: str | Path) -> list[str]:
    """Clean old video/review artifacts without risking files outside outputs.

    Returns human-readable failures. A failure never removes the current render or
    changes its successful status; callers should report every returned path.
    """
    requested_outputs = Path(outputs_dir)
    if requested_outputs.is_symlink():
        return [f"作品 outputs 是符号链接，未执行清理：{requested_outputs}"]
    try:
        outputs = requested_outputs.resolve()
        current = Path(current_video).resolve()
    except (OSError, RuntimeError) as exc:
        return [f"无法解析作品输出路径，未执行清理：{exc}"]
    if current.parent != outputs:
        return [f"当前成片不是作品 outputs 的直接文件，未执行清理：{current}"]
    if not current.is_file():
        return [f"当前成片不存在，未执行清理：{current}"]

    keep = {current}
    keep.update(current.with_suffix(suffix) for suffix in SIDECAR_SUFFIXES)
    failures: list[str] = []

    # These folders only contain regenerable inspection previews and render caches.
    try:
        children = list(outputs.iterdir()) if outputs.is_dir() else []
    except OSError as exc:
        return [f"无法读取作品输出目录 {outputs}：{exc}"]
    for child in children:
        if child.is_dir() and not child.is_symlink() and (
            child.name.lower() in _KNOWN_REGENERABLE_DIRS or _TEMP_DIR.match(child.name)
        ):
            _remove_tree(child, outputs, failures)
    _unlink(outputs / "preview-record.json", failures)

    # Old final videos and their known output sidecars can occur at any depth,
    # including history/. Never recurse into prepared media, which is render input.
    candidates = list(_iter_output_files(outputs, failures))
    for path in candidates:
        if _inside_named_dir(path, outputs, "media"):
            continue
        if path in keep:
            continue
        if path.suffix.lower() in VIDEO_SUFFIXES:
            _unlink(path, failures)
            for suffix in SIDECAR_SUFFIXES:
                sidecar = path.with_suffix(suffix)
                if sidecar not in keep:
                    _unlink(sidecar, failures)
        elif path.name.endswith((".provenance.json", ".performance.json")) or path.suffix.lower() in {".srt", *IMAGE_SUFFIXES}:
            _unlink(path, failures)

    # Remove directories emptied by media cleanup, but preserve media and outputs.
    for directory, child_dirs, _ in os.walk(
        outputs, topdown=False, followlinks=False,
        onerror=lambda exc: failures.append(f"无法遍历输出目录 {exc.filename}: {exc}"),
    ):
        target = Path(directory)
        if target == outputs or _inside_named_dir(target / "_", outputs, "media"):
            continue
        try:
            target.rmdir()
        except OSError:
            pass
    return failures


def _iter_output_files(outputs: Path, failures: list[str]):
    for directory, child_dirs, files in os.walk(
        outputs, topdown=True, followlinks=False,
        onerror=lambda exc: failures.append(f"无法遍历输出目录 {exc.filename}: {exc}"),
    ):
        # Prepared media is a render input, and symlinks must never be traversed.
        safe_children = []
        for name in child_dirs:
            child = Path(directory) / name
            if child.is_symlink():
                failures.append(f"符号链接目录未递归清理：{child}")
            elif name.lower() != "media":
                safe_children.append(name)
        child_dirs[:] = safe_children
        for name in files:
            yield Path(directory) / name


def _inside_named_dir(path: Path, root: Path, name: str) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return name in relative.parts


def _unlink(path: Path, failures: list[str]) -> None:
    try:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
    except OSError as exc:
        failures.append(f"{path}: {exc}")


def _remove_tree(path: Path, outputs: Path, failures: list[str]) -> None:
    """Unlink a known generated directory without following symlinks."""
    try:
        path.resolve().relative_to(outputs)
    except ValueError:
        failures.append(f"目录解析到 outputs 外部，已跳过：{path}")
        return
    for directory, child_dirs, files in os.walk(
        path, topdown=False, followlinks=False,
        onerror=lambda exc: failures.append(f"无法遍历旧产物目录 {exc.filename}: {exc}"),
    ):
        parent = Path(directory)
        for name in files:
            _unlink(parent / name, failures)
        for name in child_dirs:
            child = parent / name
            if child.is_symlink():
                try:
                    child.unlink(missing_ok=True)
                except OSError as exc:
                    failures.append(f"{child}: {exc}")
            # Normal child directories were already visited and removed by the
            # bottom-up walk; removing them again would report a false failure.
        try:
            parent.rmdir()
        except OSError as exc:
            failures.append(f"{parent}: {exc}")
