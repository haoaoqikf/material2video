"""管理录制中间帧的工作目录及中断后的回收。"""

from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from film_runtime.core.process_liveness import process_is_alive
from film_runtime.core.security import local_directory_mtime_ns

logger = logging.getLogger(__name__)

STALE_SECONDS = 24 * 3600
_RECORDING_DIRECTORY = ".recordings"
_OWNER = re.compile(r"code-([1-9][0-9]*)-[a-z0-9_]{8}")
_WORKER = re.compile(r"\.worker-([1-9][0-9]*)")


def register_worker(directory: Path) -> None:
    """并行子进程在写中间帧前登记，即使父进程异常退出仍受保护。"""
    if directory.parent.name == _RECORDING_DIRECTORY and _OWNER.fullmatch(directory.name):
        (directory / f".worker-{os.getpid()}").touch(exist_ok=False)


def _workers_inactive(directory: Path) -> bool:
    for marker in directory.iterdir():
        if not marker.name.startswith(".worker-"):
            continue
        match = _WORKER.fullmatch(marker.name)
        if match is None or process_is_alive(int(match[1])):
            return False
    return True


def _reap_abandoned(root: Path) -> None:
    """只回收本运行时创建且可确认无人写入的工作目录。"""
    cutoff = time.time_ns() - STALE_SECONDS * 1_000_000_000
    for directory in root.iterdir():
        match = _OWNER.fullmatch(directory.name)
        if match is None:
            continue
        try:
            mtime = local_directory_mtime_ns(directory)
            if mtime is None or mtime >= cutoff or process_is_alive(int(match[1])):
                continue
            if _workers_inactive(directory):
                shutil.rmtree(directory)
                logger.info("已清理中断录制的临时目录 %s", directory)
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.warning("无法清理录制临时目录 %s：%s", directory, exc)


@contextmanager
def recording_workspace(cache: Path) -> Iterator[Path]:
    root = cache / _RECORDING_DIRECTORY
    root.mkdir(exist_ok=True)
    if all(local_directory_mtime_ns(path) is not None for path in (cache.parent, cache, root)):
        try:
            _reap_abandoned(root)
        except OSError as exc:
            logger.warning("无法扫描录制临时目录 %s：%s", root, exc)
    temporary = tempfile.TemporaryDirectory(prefix=f"code-{os.getpid()}-", dir=root)
    try:
        yield Path(temporary.name)
    finally:
        try:
            temporary.cleanup()
        except OSError as exc:
            logger.warning("无法清理录制临时目录 %s：%s", temporary.name, exc)
