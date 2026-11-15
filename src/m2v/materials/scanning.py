"""显式目录的流式增量获取；检查点逐件提交，失败不阻断其余媒体。"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
import stat

from .contracts import fingerprint
from .errors import MaterialError
from .fetch import MEDIA_SUFFIXES, FetchBudget, fetch_local
from .paths import no_links
from .registration import file_stamp, register_local

logger = logging.getLogger(__name__)
MAX_SCAN_FILES = 500


class _Details(list):
    """错误目录也不能令诊断列表随整棵目录树无限增长。"""
    def __init__(self):
        super().__init__()
        self.total = 0
        self.counts = {}

    def append(self, item):
        self.total += 1
        code = item.get('reason', item.get('code', 'unknown'))
        self.counts[code] = self.counts.get(code, 0) + 1
        if len(self) < 1000:
            super().append(item)


def _directory(directory: Path, recursive: bool) -> Path:
    path = no_links(Path(directory).expanduser())
    home = Path.home().resolve()
    if not path.is_dir():
        raise MaterialError('not-found', '库目录不存在或不是目录', stage='library')
    if path in {home, Path(path.anchor), home.parent} or (recursive and len(path.parts) <= 2):
        raise MaterialError('security-blocked', '请显式指定具体素材目录，不扫描主目录或磁盘根', stage='library')
    return path


def _walk(directory: Path, recursive: bool, issues: list[dict], depth=0):
    if depth > 64:
        issues.append({'name': directory.name, 'reason': 'depth-budget'})
        return
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                try:
                    info = entry.stat(follow_symlinks=False)
                    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                        issues.append({'name': entry.name, 'reason': 'link'})
                    elif stat.S_ISDIR(info.st_mode) and recursive:
                        yield from _walk(Path(entry.path), True, issues, depth + 1)
                    elif stat.S_ISREG(info.st_mode) and Path(entry.name).suffix.lower() in MEDIA_SUFFIXES:
                        yield Path(entry.path), info
                except OSError:
                    issues.append({'name': entry.name, 'reason': 'unreadable'})
    except OSError:
        issues.append({'name': directory.name, 'reason': 'unreadable-directory'})


def _digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def scan_directory(store, directory: Path, *, recursive=False, budget=None, max_files=MAX_SCAN_FILES,
                   retry_failed=False):
    if type(max_files) is not int or not 1 <= max_files <= 10_000:
        raise MaterialError('invalid-request', '每轮获取预算必须为 1..10000', stage='library')
    budget = budget or FetchBudget()
    root = _directory(directory, recursive)
    # 独立可变检查点，不改不可变来源/媒体文档；原文件摘要与成品摘要分别保留。
    store.connection.execute('''CREATE TABLE IF NOT EXISTS library_scan(
        path_key TEXT PRIMARY KEY, input_sha TEXT NOT NULL, source_id TEXT NOT NULL,
        media_id TEXT NOT NULL REFERENCES documents(id))''')
    store.connection.execute('''CREATE TABLE IF NOT EXISTS library_scan_failures(
        path_key TEXT PRIMARY KEY, input_sha TEXT NOT NULL, code TEXT NOT NULL)''')
    skipped, failures = _Details(), _Details()
    acquired, reused_rows, duplicates = [], [], []
    attempted = reused = inspected = total = 0
    has_more = False
    seen = {}
    for path, info in _walk(root, recursive, skipped):
        inspected += 1
        if not 0 < info.st_size <= budget.max_bytes:
            skipped.append({'name': path.relative_to(root).as_posix(), 'reason': 'size'})
            continue
        attempt_counted = False
        key = fingerprint({'directory': str(root), 'file': path.relative_to(root).as_posix()})
        original_sha = fingerprint({'bytes': info.st_size, 'mtime': info.st_mtime_ns, 'file': info.st_ino})
        try:
            no_links(path)
            stamp = file_stamp(path)
            original_sha = _digest(path)
            if stamp != file_stamp(path):
                raise MaterialError('conflict', '素材在读取时变化，请重试', stage='library')
            failed = store.connection.execute('SELECT input_sha,code FROM library_scan_failures WHERE path_key=?', (key,)).fetchone()
            if failed and failed[0] == original_sha and not retry_failed:
                failures.append({'name': path.relative_to(root).as_posix(), 'code': failed[1],
                                 'stage': 'library', 'retryable': True, 'reusedFailure': True})
                continue
            previous = store.connection.execute('SELECT input_sha,source_id,media_id FROM library_scan WHERE path_key=?', (key,)).fetchone()
            cached = None
            if previous and previous[0] == original_sha:
                try:
                    cached = store.get(previous[2], kind='material.media')
                    store.verify_artifact(cached.data.artifact)
                except (MaterialError, OSError):
                    cached = None
            if cached is not None:
                reused += 1
                if len(reused_rows) < max_files:
                    reused_rows.append((previous[1], cached.id))
                continue
            if attempted >= max_files:
                has_more = True
                break
            attempted += 1
            attempt_counted = True
            registered = register_local(path, store=store)
            fetched = fetch_local(store, source=registered.document, path=path, budget=budget)
            if stamp != file_stamp(path):
                raise MaterialError('conflict', '素材在获取时变化，未登记增量成功', stage='library')
            with store.transaction() as db:
                db.execute('INSERT INTO library_scan VALUES(?,?,?,?) ON CONFLICT(path_key) DO UPDATE SET '
                           'input_sha=excluded.input_sha,source_id=excluded.source_id,media_id=excluded.media_id',
                           (key, original_sha, registered.document.id, fetched.media.id))
                db.execute('DELETE FROM library_scan_failures WHERE path_key=?', (key,))
            acquired.append((registered.document.id, fetched.media.id))
            sha = fetched.media.data.artifact.sha256
            total += fetched.media.data.artifact.bytes
            if sha in seen:
                duplicates.append({'sha256': sha, 'mediaIds': [seen[sha], fetched.media.id]})
            else:
                seen[sha] = fetched.media.id
        except (MaterialError, OSError) as exc:
            # 读取失败也消耗尝试预算，防止坏件制造无界工作；逐件状态仍可恢复。
            if not attempt_counted:
                previous_failure = store.connection.execute('SELECT input_sha,code FROM library_scan_failures WHERE path_key=?', (key,)).fetchone()
                if previous_failure and previous_failure[0] == original_sha and not retry_failed:
                    failures.append({'name': path.relative_to(root).as_posix(), 'code': previous_failure[1],
                                     'stage': 'library', 'retryable': True, 'reusedFailure': True})
                    continue
                if attempted >= max_files:
                    has_more = True
                    break
                attempted += 1
            failures.append({'name': path.relative_to(root).as_posix(),
                             'code': getattr(exc, 'code', 'unreadable'), 'stage': 'library',
                             'retryable': True})
            with store.transaction() as db:
                db.execute('INSERT INTO library_scan_failures VALUES(?,?,?) ON CONFLICT(path_key) DO UPDATE SET '
                           'input_sha=excluded.input_sha,code=excluded.code',
                           (key, original_sha, getattr(exc, 'code', 'unreadable')))
            logger.warning('素材入库单件失败 file=%s type=%s', path.name, type(exc).__name__)
    for reason in ('unreadable', 'unreadable-directory', 'depth-budget'):
        if skipped.counts.get(reason):
            failures.append({'stage': 'library', 'code': reason, 'count': skipped.counts[reason],
                             'retryable': True, 'note': '部分目录或条目未能遍历，不代表这些位置没有素材'})
    rows = acquired or reused_rows
    return {'directory': str(root), 'files': len(rows), 'bytes': total, 'inspected': inspected,
            'attempted': attempted, 'acquired': len(acquired), 'reused': reused,
            'mediaIds': [row[1] for row in rows], 'sourceIds': [row[0] for row in rows],
            'duplicateContents': duplicates, 'skipped': skipped, 'failures': failures,
            'skippedCount': skipped.total, 'failureCount': failures.total,
            'hasMore': has_more, 'continuation': '重复同一命令，已完成且有效的项不消耗获取预算' if has_more else None,
            'note': '源字节摘要用于增量判断；同字节共享对象，来源/用途/许可分别保留'}
