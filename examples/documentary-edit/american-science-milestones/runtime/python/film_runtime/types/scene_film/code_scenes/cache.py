"""场景录制片段预算与合成期间的使用登记。"""
from __future__ import annotations

import logging
import os
import re
import stat
import uuid
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from film_runtime.core.recording_identity import process_start, recording_ended
from film_runtime.core.security import local_directory_mtime_ns

logger = logging.getLogger(__name__)
CACHE_BYTES = 512 * 1024**2
CLIP = re.compile(r"[a-f0-9]{64}-[0-9]+-[0-9]+")
CLIP_REFERENCE = re.compile(rb"([a-f0-9]{64}-[0-9]+-[0-9]+)\.(?:mp4|json)")
LEASE = re.compile(r"lease-([1-9][0-9]*)-[a-f0-9]{32}")


def _file(path: Path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    attributes = getattr(info, "st_file_attributes", 0)
    if stat.S_ISREG(info.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        return info
    return None


@contextmanager
def _gate(directory: Path):
    path = directory / ".lock"
    if path.is_symlink() or (path.exists() and _file(path) is None):
        raise OSError(f"存储锁不是普通文件：{path}")
    with path.open("a+b") as stream:
        if not stream.tell():
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX)
        # 关闭句柄即释放锁。
        yield


def _in_use(directory: Path) -> bool:
    occupied = False
    for marker in directory.iterdir():
        if marker.name == ".lock":
            continue
        match = LEASE.fullmatch(marker.name)
        if not match or _file(marker) is None or not recording_ended(int(match[1]), marker):
            occupied = True
        else:
            marker.unlink()
    return occupied


def _references(outputs: Path) -> set[str]:
    """作品直接运行时也保护登记在制作记录及物化契约中的片段。"""
    pinned = set()

    def failed(exc):
        raise exc

    for directory, children, names in os.walk(outputs, followlinks=False, onerror=failed):
        branch = Path(directory)
        children[:] = [
            name for name in children
            if name not in {"code-cache", "review-blobs"}
            and local_directory_mtime_ns(branch / name) is not None
        ]
        for name in names:
            path = branch / name
            if path.suffix.lower() not in {".json", ".jsonl", ".md"} or _file(path) is None:
                continue
            with path.open("rb") as stream:
                for line in stream:
                    pinned.update(match[1].decode("ascii") for match in CLIP_REFERENCE.finditer(line))
    return pinned


def _prune(cache: Path) -> None:
    total, entries = 0, []
    for clip in cache.glob("*.mp4"):
        if not CLIP.fullmatch(clip.stem):
            continue
        receipt = clip.with_suffix(".json")
        video_stat, receipt_stat = _file(clip), _file(receipt)
        if video_stat is None or receipt_stat is None:
            continue
        size = video_stat.st_size + receipt_stat.st_size
        total += size
        entries.append((video_stat.st_mtime_ns, clip, receipt, size))
    if total <= CACHE_BYTES:
        return
    pins = _references(cache.parent)
    for _, clip, receipt, size in sorted(entries):
        if total <= CACHE_BYTES:
            break
        if clip.stem not in pins:
            clip.unlink()
            receipt.unlink()
            total -= size
    if total > CACHE_BYTES:
        logger.info("场景缓存仍超过预算，登记引用保留 %d 字节", total)


def _try_prune(cache: Path, leases: Path) -> None:
    try:
        if not _in_use(leases):
            _prune(cache)
    except OSError as exc:
        logger.warning("暂缓场景片段清理：%s", exc)


@contextmanager
def scene_cache(root: Path):
    cache = root / "outputs/code-cache"
    if not cache.parent.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
    if local_directory_mtime_ns(cache.parent) is None:
        raise OSError(f"作品输出不是普通目录：{cache.parent}")
    cache.mkdir(exist_ok=True)
    if local_directory_mtime_ns(cache) is None:
        raise OSError(f"场景缓存不是普通目录：{cache}")
    leases = cache / ".leases"
    leases.mkdir(exist_ok=True)
    if local_directory_mtime_ns(leases) is None:
        raise OSError(f"缓存租约不是普通目录：{leases}")
    marker = leases / f"lease-{os.getpid()}-{uuid.uuid4().hex}"
    with _gate(leases):
        _try_prune(cache, leases)
        with marker.open("x", encoding="ascii") as stream:
            stream.write(process_start(os.getpid()))
    try:
        yield
    finally:
        try:
            with _gate(leases):
                marker.unlink(missing_ok=True)
                _try_prune(cache, leases)
        except OSError as exc:
            logger.warning("暂缓关闭场景缓存租约：%s", exc)


def using_scene_cache(action):
    @wraps(action)
    def run(root, *args, **kwargs):
        with scene_cache(root):
            return action(root, *args, **kwargs)

    return run
