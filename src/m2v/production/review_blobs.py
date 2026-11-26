"""评审原件的内容寻址存储和隔离副本。"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path

from m2v.core.delivery import digest, outputs
from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from m2v.core.security import deliver_directory

from . import dependencies
from .storage import local, read, write

IDENTIFIER = re.compile(r"[a-f0-9]{32}")
SHA256 = re.compile(r"[a-f0-9]{64}")
MEDIA = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".wav", ".mp3", ".ttf", ".otf", ".woff", ".woff2"}


def _record(pack_dir: Path) -> Path:
    if pack_dir.parent.name != "review-pack" or not IDENTIFIER.fullmatch(pack_dir.name):
        raise M2VError("评审包身份无效")
    return local(pack_dir.parent.parent, f"review-blobs/packs/{pack_dir.name}.json", exists=False)


def _blob(pack_dir: Path, sha: str, *, exists: bool = True) -> Path:
    if not isinstance(sha, str) or not SHA256.fullmatch(sha):
        raise M2VError("评审媒体摘要无效")
    return local(pack_dir.parent.parent, f"review-blobs/objects/{sha[:2]}/{sha}.blob", exists=exists)


def manifest_files(records: list) -> dict[str, str]:
    if not isinstance(records, list) or not records:
        raise M2VError("评审清单缺少文件记录")
    files = {}
    for entry in records:
        name, sha = entry["path"], entry["sha256"]
        if (not isinstance(name, str) or not name or name in files
                or name == "manifest.json" or not isinstance(sha, str) or not SHA256.fullmatch(sha)):
            raise M2VError("评审文件身份无效")
        files[name] = sha
    return files


def index(pack_dir: Path, files: dict[str, str]) -> dict[str, str]:
    path = _record(pack_dir)
    if not path.exists():
        return {}
    record = read(path)
    if (not isinstance(record, dict) or record.get("version") != 1
            or record.get("manifestSha256") != dependencies.digest(local(pack_dir, "manifest.json"))
            or not isinstance(record.get("files"), dict)):
        raise M2VError("评审媒体存储记录损坏")
    archived = record["files"]
    if any(files.get(name) != sha for name, sha in archived.items()):
        raise M2VError("评审媒体存储记录与原清单不一致")
    return archived


def file_for(pack_dir: Path, name: str, archived: dict[str, str]) -> Path:
    original = local(pack_dir, name, exists=False)
    if original.is_file():
        return original
    if name not in archived:
        raise M2VError(f"评审原件不存在：{name}")
    return _blob(pack_dir, archived[name])


def verified(pack_dir: Path, records: list) -> bool:
    try:
        files = manifest_files(records)
        archived = index(pack_dir, files)
        return all(dependencies.digest(file_for(pack_dir, name, archived)) == sha for name, sha in files.items())
    except (M2VError, OSError, KeyError, TypeError):
        return False


def recorded_file(base: Path, name: str) -> Path:
    """账本仍以原相对路径标识证据；仅在已发布的评审存储记录存在时解析缺失媒体。"""
    path = local(base, name, exists=False)
    parts = path.relative_to(base).parts
    if path.is_file() or len(parts) < 3 or parts[0] != "review-pack":
        return local(base, name)
    pack_dir = base.joinpath(*parts[:2])
    record = _record(pack_dir)
    if not record.is_file():
        return local(base, name)
    manifest = read(local(pack_dir, "manifest.json"))
    return file_for(pack_dir, "/".join(parts[2:]), index(pack_dir, manifest_files(manifest["files"])))


def _publish_blob(source: Path, target: Path, sha: str) -> int:
    if target.is_file():
        if dependencies.digest(target) != sha:
            raise M2VError(f"评审原件摘要失配：{target.name}")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".object-", dir=target.parent)
    os.close(fd)
    pending = Path(name)
    try:
        shutil.copyfile(source, pending)
        if digest(pending) != sha:
            raise M2VError(f"评审媒体复制期间发生变化：{source.name}")
        size = pending.stat().st_size
        os.replace(pending, target)
        return size
    finally:
        pending.unlink(missing_ok=True)


def compact(pack_dir: Path, *, keep: set[str] | None = None, planned: dict | None = None) -> dict:
    """先核验全部原始内容，再发布替代索引，唯有已核验的文件会移除其额外副本。"""
    manifest = local(pack_dir, "manifest.json")
    manifest_sha = digest(manifest)
    if planned is not None and planned["manifestSha256"] != manifest_sha:
        raise M2VError("评审清单已变化")
    files = manifest_files(read(manifest)["files"])
    archived = index(pack_dir, files)
    candidates = []
    for name, sha in files.items():
        path = file_for(pack_dir, name, archived)
        if dependencies.digest(path) != sha:
            raise M2VError(f"评审媒体与原清单摘要不一致：{path}")
        if path.is_relative_to(pack_dir) and path.suffix.lower() in MEDIA and name not in (keep or ()):
            info = path.stat()
            candidates.append((name, path, sha, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino))
    if planned is not None:
        identity = fingerprint([[name, sha, size, modified, created]
                                for name, _, sha, size, modified, created, _ in candidates])
        if identity != planned["identity"]:
            raise M2VError("评审媒体文件身份已变化")
    if not candidates:
        return {"archivedFiles": 0, "logicalRemovedBytes": 0, "objectBytesAdded": 0}

    stored = 0
    created_objects = []
    try:
        for name, path, sha, *_ in candidates:
            target = _blob(pack_dir, sha, exists=False)
            absent = not target.exists()
            stored += _publish_blob(path, target, sha)
            if absent:
                created_objects.append(target)
            archived[name] = sha
        if digest(manifest) != manifest_sha:
            raise M2VError("评审清单在封存期间发生变化")
        write(_record(pack_dir), {"version": 1, "manifestSha256": manifest_sha, "files": archived})
    except (M2VError, OSError, ValueError):
        # 尚未发布索引时只撤回本次新对象，原包字节仍在。
        for target in created_objects:
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
        raise

    removed, count = 0, 0
    for name, path, sha, size, modified, created, inode in candidates:
        local(pack_dir, name)
        info = path.stat()
        if (info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino) != (size, modified, created, inode):
            raise M2VError(f"评审媒体在封存期间发生变化：{path}")
        path.unlink()
        count += 1
        removed += size
    return {"archivedFiles": count, "logicalRemovedBytes": removed, "objectBytesAdded": stored}


def export(root: Path, pack_id: str, destination: Path) -> dict:
    if not IDENTIFIER.fullmatch(pack_id):
        raise M2VError("评审包身份无效")
    manifest = local(outputs(root), f"review-pack/{pack_id}/manifest.json")
    pack_sha = digest(manifest)
    files = manifest_files(read(manifest)["files"])
    archived = index(manifest.parent, files)
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink() or destination.resolve().is_relative_to(outputs(root).resolve()):
        raise M2VError("请选择作品 outputs 外尚未存在的评审副本目录")
    if not destination.parent.is_dir():
        raise M2VError("评审副本的父目录需要预先存在")
    with tempfile.TemporaryDirectory(prefix=".review-export-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "pack"
        staging.mkdir()
        shutil.copyfile(manifest, staging / "manifest.json")
        for name, sha in files.items():
            source = file_for(manifest.parent, name, archived)
            target = local(staging, name, exists=False)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if digest(target) != sha:
                raise M2VError(f"隔离观察副本摘要失配：{name}")
        if digest(staging / "manifest.json") != pack_sha:
            raise M2VError("评审清单在副本生成期间变化")
        deliver_directory(staging, destination)
    return {"path": str(destination), "files": len(files), "packSha256": pack_sha}
