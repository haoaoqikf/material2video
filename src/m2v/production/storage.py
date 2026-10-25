"""作品内安全路径、原子写盘与跨进程写锁。"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from m2v.core.delivery import digest, outputs
from m2v.core.errors import M2VError

logger = logging.getLogger(__name__)


def local(base: Path, reference: str, *, exists: bool = True) -> Path:
    """拒绝绝对路径、越界和链接，防止证据登记扩大读取或删除范围。"""
    relative = Path(reference)
    if base.is_symlink() or (hasattr(base, 'is_junction') and base.is_junction()):
        raise M2VError('制作证据根不允许符号链接或目录联接')
    if relative.is_absolute() or not relative.parts or '..' in relative.parts:
        raise M2VError(f"非法制作证据路径：{reference}")
    candidate = base / relative
    if any((base.joinpath(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)):
        raise M2VError(f"制作证据不允许符号链接：{reference}")
    if not candidate.resolve().is_relative_to(base.resolve()):
        raise M2VError(f"制作证据越界：{reference}")
    if exists and not candidate.is_file():
        raise M2VError(f"制作证据文件不存在：{reference}")
    return candidate


def read(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise M2VError(f"无法读取制作记录 {path}：{exc}") from exc


def write(path: Path, value) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.m2v-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def locked(root: Path):
    """锁文件保留，OS 字节锁随进程退出释放；避免崩溃遗留独占标记。"""
    directory = outputs(root) / 'production'
    if outputs(root).is_symlink() or directory.is_symlink():
        raise M2VError('制作输出与锁目录不允许符号链接')
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / '.lock'
    with path.open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise M2VError('作品制作记录正在写入，请稍后重试') from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_UN)


def receipt(base: Path, path: Path) -> dict:
    safe = local(base, path.relative_to(base).as_posix())
    return {'path': safe.relative_to(base).as_posix(), 'sha256': digest(safe)}
