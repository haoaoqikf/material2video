"""Backup-first relocation of one project into the type-partitioned workspace."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.core.project import load_project
from m2v.types import catalog, registry
from m2v.core.workspace import (
    CONTENT_ROOT_ENV,
    PROJECT_MARKER,
    bundle_repo_root,
    content_root as configured_content_root,
)


@dataclass(frozen=True)
class RelocationResult:
    source: Path
    target: Path
    backup: Path
    conflicts: tuple[Path, ...]

    @property
    def message(self) -> str:
        if self.conflicts:
            paths = "\n".join(f"  {path}" for path in self.conflicts)
            return (f"已迁移至 {self.target}；完整备份：{self.backup}\n"
                    f"以下同名目标文件未覆盖，源文件仍在旧目录，处理后可重试：\n{paths}")
        return f"已迁移至 {self.target}；完整备份：{self.backup}"


def relocate(project: str | Path, *, content_root: str | Path | None = None) -> RelocationResult:
    """Move one legacy ``videos/<slug>`` project, retaining conflicts for retry."""
    source = Path(project).expanduser().resolve()
    if not source.is_dir():
        if source.parent.name != "videos":
            raise M2VError(f"旧作品目录不存在：{source}")
        candidates = sorted(source.parent.glob(f"*/{source.name}/project.json"))
        if candidates:
            raise M2VError(f"作品已经迁移到标准目录：{candidates[0].parent}")
        raise M2VError(f"旧作品目录不存在：{source}")
    if source.parent.name != "videos":
        raise M2VError(f"路径迁移只接受 videos/<slug>/ 旧路径：{source}")

    repo_root = _repo_root(source)
    workspace = _workspace_root(source, repo_root, content_root)
    try:
        source.relative_to(workspace)
    except ValueError as exc:
        raise M2VError(f"来源不在工作区根 {workspace} 内：{source}") from exc

    previous_backups = sorted(source.parent.glob(f"{source.name}.m2v-relocation-backup-*"))
    if (source / "project.json").is_file():
        root, manifest = load_project(source)
    elif previous_backups and any(p.is_file() or p.is_symlink() for p in source.rglob("*")):
        # A retry may remain after the root manifest already moved. In that case
        # prefer the destination manifest, which is the active project's truth.
        discovered_targets = sorted(source.parent.glob(f"*/{source.name}/project.json"))
        manifest_source = discovered_targets[0].parent if discovered_targets else previous_backups[0]
        root, manifest = load_project(manifest_source)
    else:
        raise M2VError(f"旧作品目录缺少 project.json：{source}")
    type_name = manifest["type"]
    catalog.catalog().get(type_name)
    registry.get(type_name)
    target_parent = workspace / "videos" / type_name
    target = target_parent / source.name
    if target == source:
        raise M2VError(f"作品已经位于标准目录：{source}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = previous_backups[0] if previous_backups else source.with_name(f"{source.name}.m2v-relocation-backup-{stamp}")
    if not previous_backups:
        shutil.copytree(source, backup, copy_function=shutil.copy2, symlinks=True)
    target_parent.mkdir(parents=True, exist_ok=True)

    conflicts: list[Path] = []
    for current, directories, files in os.walk(source, topdown=True, followlinks=False):
        current_path = Path(current)
        # os.walk lists symlinked directories separately; move the link itself.
        symlink_dirs = [name for name in directories if (current_path / name).is_symlink()]
        directories[:] = [name for name in directories if name not in symlink_dirs]
        for name in symlink_dirs:
            _move_one(current_path / name, target / (current_path / name).relative_to(source), conflicts)
        for name in files:
            item = current_path / name
            _move_one(item, target / item.relative_to(source), conflicts)

    for current, directories, _files in os.walk(source, topdown=False, followlinks=False):
        directory = Path(current)
        if directory == source:
            continue
        if any(directory.iterdir()):
            continue
        directory.rmdir()
    if not any(source.iterdir()):
        source.rmdir()
    return RelocationResult(source, target, backup, tuple(conflicts))


def _move_one(source: Path, destination: Path, conflicts: list[Path]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        conflicts.append(source)
        return
    source.replace(destination)


def _repo_root(source: Path) -> Path:
    for directory in (source, *source.parents):
        if (directory / PROJECT_MARKER).is_file():
            return directory
    # Content roots may live outside the checkout; use the installed bundle's
    # repository for shared registry and type metadata in that case.
    return bundle_repo_root()


def _workspace_root(source: Path, repo_root: Path, explicit: str | Path | None) -> Path:
    external = configured_content_root(explicit)
    if external is not None:
        try:
            source.relative_to(external)
            return external
        except ValueError:
            pass
    try:
        source.relative_to(repo_root)
        return repo_root
    except ValueError:
        raise M2VError(
            f"来源 {source} 不在仓库根或内容根中；请使用 --content-root 或 {CONTENT_ROOT_ENV} 指定内容根"
        )
