"""Remove superseded, reproducible media from one project's outputs directory."""
from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote


VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv", ".avi"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg"}
SIDECAR_SUFFIXES = (".srt", ".provenance.json", ".performance.json")
_TEMP_DIR = re.compile(r"^(?:a2v|m2v|debug|tmp|render)(?:-|$)", re.IGNORECASE)
_KNOWN_REGENERABLE_DIRS = {"previews", "qa", "bench", "review-contact-sheets"}
_PREPARED_MEDIA_DIRS = {"media", "code-cache"}


def cleanup_after_render(outputs_dir: str | Path, current_video: str | Path, *, preserve_previews: bool = False,
                         preserve_visual_evidence: bool = False,
                         protected_files: Iterable[Path] = ()) -> list[str]:
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
    # 评审层解析自己的绑定；通用清理只接受本 outputs 内的具体文件，不认识评审格式。
    try:
        for path in protected_files:
            resolved = path.resolve()
            relative = path.absolute().relative_to(outputs)
            if not relative.parts or not resolved.is_relative_to(outputs) or any(
                outputs.joinpath(*relative.parts[:i]).is_symlink()
                or (hasattr(outputs.joinpath(*relative.parts[:i]), 'is_junction')
                    and outputs.joinpath(*relative.parts[:i]).is_junction())
                for i in range(1, len(relative.parts) + 1)
            ):
                raise ValueError(f"受保护文件路径不安全：{path}")
            keep.add(resolved)
    except (OSError, RuntimeError, ValueError) as exc:
        return [f"无法确认受保护文件，未执行清理：{exc}"]
    # 只保护当前候选，旧版本候选仍随成功交付清理；失败时调用方不进入清理。
    from .delivery import read_record
    record = read_record(outputs)
    try:
        reference = record.get('path')
        if (not isinstance(reference, str) or not reference or Path(reference).anchor
                or ':' in reference or '\\' in reference or '..' in Path(reference).parts):
            raise ValueError('候选必须使用作品内相对路径')
        candidate = (outputs.parent / reference).resolve()
        if candidate.parent == outputs / "candidates" and candidate.is_file():
            keep.add(candidate)
            keep.update(candidate.with_suffix(suffix) for suffix in (*SIDECAR_SUFFIXES, ".delivery.json"))
    except (OSError, TypeError, ValueError):
        pass
    failures: list[str] = []
    if preserve_visual_evidence:
        try:
            keep.update(_visual_evidence(outputs))
            # 制作门、隔离评审、目标关键帧和基线有各自保留契约，普通交付清理不能抢先删除。
            # 目标关键帧是独立的静态美术证据，不是可由成片重放得到的普通静帧。
            # 基线媒体仅由显式 baseline prune 在引用检查与写锁下删除。
            for name in ('production', 'review-pack', 'baselines', 'design'):
                directory = outputs / name
                if directory.is_symlink():
                    return [f'制作证据目录是符号链接，未执行清理：{directory}']
                keep.update(p.resolve() for p in directory.rglob('*') if p.is_file() and not p.is_symlink())
        except OSError as exc:
            return [str(exc)]

    # These folders only contain regenerable inspection previews and render caches.
    try:
        children = list(outputs.iterdir()) if outputs.is_dir() else []
    except OSError as exc:
        return [f"无法读取作品输出目录 {outputs}：{exc}"]
    for child in children:
        if child.is_dir() and not child.is_symlink() and (
            (child.name.lower() in _KNOWN_REGENERABLE_DIRS and not (preserve_previews and child.name.lower() == "previews"))
            or _TEMP_DIR.match(child.name)
        ):
            _remove_tree(child, outputs, failures, keep=keep)
    if outputs / "preview-record.json" not in keep:
        _unlink(outputs / "preview-record.json", failures)
    if not preserve_previews:
        financial_preview_record = outputs / "previews" / "preview-record.json"
        if financial_preview_record.is_file() and financial_preview_record not in keep:
            _unlink(financial_preview_record, failures)

    # Old final videos and their known output sidecars can occur at any depth,
    # including history/. Render inputs and recording workspaces own their cleanup.
    candidates = list(_iter_output_files(outputs, failures))
    for path in candidates:
        if preserve_previews and _inside_named_dir(path, outputs, "previews"):
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

    # Check directories bottom-up without walking into a concurrent recording.
    directories = []
    for directory, child_dirs, _ in os.walk(
        outputs, followlinks=False,
        onerror=lambda exc: failures.append(f"无法遍历输出目录 {exc.filename}: {exc}"),
    ):
        child_dirs[:] = [name for name in child_dirs if name.lower() not in _PREPARED_MEDIA_DIRS]
        if Path(directory) != outputs:
            directories.append(Path(directory))
    for target in reversed(directories):
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
        # Leave render inputs and active recording workspaces to their own lifecycle.
        safe_children = []
        for name in child_dirs:
            child = Path(directory) / name
            if child.is_symlink():
                failures.append(f"符号链接目录未递归清理：{child}")
            elif name.lower() not in _PREPARED_MEDIA_DIRS:
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


def _visual_evidence(outputs: Path) -> set[Path]:
    """保留观看记录中显式引用的本地文件，不跟随链接到作品输出目录之外。

    记录使用相对 visual-notes.md 的 Markdown 文件链接。只保留直接引用，
    不递归读取其他文档，也不将目录链接解释为保留整棵历史树。
    """
    notes = outputs / "visual-notes.md"
    if not notes.is_file() or notes.is_symlink():
        return set()
    keep = {notes}
    try:
        text = notes.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        # 记录不可读时宁可保留产物，不能声称已经完成安全清理。
        raise OSError(f"无法读取视觉证据记录 {notes}: {exc}") from exc
    for raw in re.findall(r"\]\((<[^>]+>|[^\s)]+)\)", text):
        value = unquote(raw.strip("<>").split("#", 1)[0])
        if not value or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value):
            continue
        candidate = outputs / value
        try:
            resolved = candidate.resolve()
            relative = resolved.relative_to(outputs)
            # 不保留符号链接；避免外部路径或链接将清理例外扩大到其他作品。
            lexical = candidate.relative_to(outputs)
            if any((outputs.joinpath(*lexical.parts[:index])).is_symlink()
                   for index in range(1, len(lexical.parts) + 1)):
                continue
            if relative.parts and resolved.is_file():
                keep.add(resolved)
        except (ValueError, OSError, RuntimeError):
            continue
    return keep


def _unlink(path: Path, failures: list[str]) -> None:
    try:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
    except OSError as exc:
        failures.append(f"{path}: {exc}")


def _remove_tree(path: Path, outputs: Path, failures: list[str], *, keep: set[Path] | None = None) -> None:
    """Unlink a known generated directory without following symlinks."""
    protected = keep or set()
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
            if parent / name not in protected:
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
            if not any(item.is_relative_to(parent) for item in protected):
                failures.append(f"{parent}: {exc}")
