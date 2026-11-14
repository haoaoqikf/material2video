"""显式本地库登记、核验与安全清理；默认不跟随链接，不扫描隐私目录根。

不同目录里的相同字节只共享内容对象；来源、用途与许可记录仍各自独立，
不因字节相同而继承另一作品或另一路径的采用结论。
"""
from __future__ import annotations

import logging
import stat
from pathlib import Path

from .contracts import Artifact, fingerprint, utc_now
from .errors import MaterialError
from .fetch import MEDIA_SUFFIXES, FetchBudget, fetch_local
from .paths import no_links
from .registration import register_local
from .store import MaterialStore

logger = logging.getLogger(__name__)

MAX_SCAN_FILES = 500


def _guard_directory(directory: Path, *, recursive: bool) -> Path:
    path = no_links(Path(directory).expanduser())
    if not path.is_dir():
        raise MaterialError('not-found', '库目录不存在或不是目录', stage='library')
    home = Path.home().resolve()
    if path == home or path == Path(path.anchor) or path == home.parent:
        raise MaterialError('security-blocked', '拒绝扫描用户主目录或磁盘根；请显式指定具体素材目录', stage='library')
    if recursive:
        depth = len(path.parts)
        if depth <= 2:
            raise MaterialError('security-blocked', '递归登记至少需要两级以上的明确目录', stage='library')
    return path


def _files(directory: Path, *, recursive: bool, budget: FetchBudget) -> tuple[list[Path], list[dict]]:
    skipped, found = [], []
    if recursive:
        import os
        entries: list[Path] = []
        for root, directories, names in os.walk(directory, followlinks=False):
            kept = []
            for name in directories:
                path = Path(root) / name
                try:
                    info = path.lstat()
                except OSError:
                    skipped.append({'name': name, 'reason': 'unreadable'})
                    continue
                if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                    skipped.append({'name': name, 'reason': 'link'})
                    continue
                kept.append(name)
            directories[:] = kept
            entries.extend(Path(root) / name for name in names)
        iterator = entries
    else:
        iterator = directory.iterdir()
    for item in iterator:
        try:
            info = item.lstat()
        except OSError:
            skipped.append({'name': item.name, 'reason': 'unreadable'})
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            skipped.append({'name': item.name, 'reason': 'link'})
            continue
        if not stat.S_ISREG(info.st_mode):
            continue
        if item.suffix.lower() not in MEDIA_SUFFIXES:
            continue
        if info.st_size <= 0 or info.st_size > budget.max_bytes:
            skipped.append({'name': item.name, 'reason': 'size'})
            continue
        found.append(item)
        if len(found) >= MAX_SCAN_FILES:
            skipped.append({'name': '*', 'reason': 'file-budget'})
            break
    return sorted(found), skipped


def scan_directory(store: MaterialStore, directory: Path, *, recursive: bool = False,
                   budget: FetchBudget | None = None) -> dict:
    """显式目录登记；只处理该目录内的受支持媒体，不追溯其他引用。"""
    budget = budget or FetchBudget()
    root = _guard_directory(Path(directory), recursive=recursive)
    files, skipped = _files(root, recursive=recursive, budget=budget)
    media_ids, source_ids, seen, duplicates = [], [], {}, []
    total = 0
    for path in files:
        registered = register_local(path, store=store)
        fetched = fetch_local(store, source=registered.document, path=path, budget=budget)
        sha = fetched.media.data.artifact.sha256
        total += fetched.media.data.artifact.bytes
        media_ids.append(fetched.media.id)
        source_ids.append(registered.document.id)
        if sha in seen:
            duplicates.append({'sha256': sha, 'mediaIds': [seen[sha], fetched.media.id]})
        else:
            seen[sha] = fetched.media.id
    return {'directory': str(root), 'files': len(files), 'bytes': total,
            'mediaIds': media_ids, 'sourceIds': source_ids,
            'duplicateContents': duplicates, 'skipped': skipped,
            'note': '同字节共享内容对象；各来源分别保留用途/许可状态，不自动继承'}


def stats(store: MaterialStore) -> dict:
    counts = {kind: store.connection.execute('SELECT count(*) FROM documents WHERE kind=?', (kind,)).fetchone()[0]
              for kind in ('material.source', 'material.media', 'material.index', 'material.candidate',
                           'material.selection', 'material.receipt')}
    artifacts = store.connection.execute('SELECT count(*), coalesce(sum(bytes),0) FROM artifacts').fetchone()
    referenced = store.connection.execute(
        'SELECT count(DISTINCT sha256) FROM document_artifacts').fetchone()[0]
    staging = store.path('staging', exists=True, directory=True)
    staging_files = sum(1 for _ in staging.iterdir())
    return {'documents': counts, 'artifacts': artifacts[0], 'artifactBytes': artifacts[1],
            'referencedArtifacts': referenced, 'unreferencedArtifacts': artifacts[0] - referenced,
            'stagingEntries': staging_files}


def verify_library(store: MaterialStore) -> dict:
    issues, verified = [], 0
    for media in store.documents('material.media'):
        try:
            store.verify_artifact(media.data.artifact)
            verified += 1
        except MaterialError as exc:
            issues.append({'mediaId': media.id, 'code': exc.code, 'note': '媒体对象缺失或摘要不符'})
    for row in store.connection.execute('SELECT sha256,path,bytes FROM artifacts ORDER BY sha256').fetchall():
        try:
            store.verify_artifact(Artifact(path=row['path'], sha256=row['sha256'], bytes=row['bytes']))
        except (MaterialError, OSError) as exc:
            issues.append({'sha256': row['sha256'], 'code': getattr(exc, 'code', 'not-found')})
    return {'verifiedMedia': verified, 'issues': issues, 'ok': not issues}


def cleanup_plan(store: MaterialStore) -> dict:
    """只计划清理未被任何工作文档绑定的对象与暂存残留；作品正式文件不在范围内。"""
    unbound = [dict(row) for row in store.connection.execute(
        '''SELECT sha256,path,bytes FROM artifacts WHERE sha256 NOT IN
           (SELECT DISTINCT sha256 FROM document_artifacts) ORDER BY sha256''').fetchall()]
    known = {row['path'] for row in store.connection.execute('SELECT path FROM artifacts')}
    objects = store.path('objects', exists=True, directory=True)
    on_disk = []
    for item in sorted(objects.rglob('*')):
        if not item.is_file():
            continue
        reference = item.relative_to(store.root).as_posix()
        if reference not in known:
            on_disk.append({'path': reference, 'bytes': item.stat().st_size})
    staging = store.path('staging', exists=True, directory=True)
    staging_files = [{'path': item.name, 'bytes': item.stat().st_size}
                     for item in sorted(staging.iterdir()) if item.is_file()]
    plan = {'schemaVersion': 1, 'createdAt': utc_now(), 'unboundArtifacts': unbound,
            'orphanObjectFiles': on_disk, 'stagingFiles': staging_files}
    plan['digest'] = fingerprint({key: plan[key] for key in
                                  ('unboundArtifacts', 'orphanObjectFiles', 'stagingFiles')})
    return plan


def apply_cleanup(store: MaterialStore, digest_value: str) -> dict:
    plan = cleanup_plan(store)
    if digest_value != plan['digest']:
        raise MaterialError('conflict', '清理计划已过期；请重新生成后显式执行', stage='library')
    deleted, bytes_freed = [], 0
    with store.transaction() as db:
        for row in plan['unboundArtifacts']:
            if db.execute('SELECT 1 FROM document_artifacts WHERE sha256=?', (row['sha256'],)).fetchone():
                raise MaterialError('conflict', '对象在计划后已被引用，已停止清理', stage='library')
            path = store.path(row['path'], exists=False)
            if path.exists():
                bytes_freed += path.stat().st_size
                path.unlink()
            db.execute('DELETE FROM artifacts WHERE sha256=?', (row['sha256'],))
            deleted.append({'path': row['path'], 'bytes': row['bytes']})
    for row in plan['orphanObjectFiles']:
        path = store.path(row['path'], exists=False)
        if path.exists():
            bytes_freed += path.stat().st_size
            path.unlink()
        deleted.append({'path': row['path'], 'bytes': row['bytes']})
    for row in plan['stagingFiles']:
        path = store.path('staging/' + row['path'], exists=False)
        if path.exists():
            path.unlink()
    return {'deleted': len(deleted), 'bytesFreed': bytes_freed, 'items': deleted,
            'protected': '工作文档绑定的对象、选择输出、索引帧、凭据与作品正式文件均不在清理范围'}
