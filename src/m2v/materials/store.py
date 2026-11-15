"""SQLite 权威工作库、不可变文件对象与可审计引用。

耗时的网络、复制和推理均在短事务之外。文件先完整发布再入库；崩溃可能留
孤立对象，但不会让新记录指向未发布的半文件。JSON 快照是派生导出，不双向同步。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import tempfile
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path

from m2v.core.delivery import digest
from m2v.core.errors import M2VError
from m2v.core.security import deliver
from m2v.production.storage import atomic_text, local, locked
from .contracts import Artifact, Document, IndexRecord, canonical, fingerprint, parse_document, relative_path, utc_now
from .errors import MaterialError
from .paths import no_links

logger = logging.getLogger(__name__)
_DB_VERSION = 1


def workspace_root(*, project: Path | None = None, workspace: Path | None = None) -> Path:
    if workspace is not None:
        return no_links(workspace)
    if project is None:
        raise MaterialError('invalid-request', '需要显式 --project 或 --workspace', stage='storage')
    return no_links(project / 'outputs' / 'materials')


class MaterialStore:
    def __init__(self, root: Path, *, readonly: bool = False):
        self.root = no_links(root)
        self.readonly = readonly
        if readonly:
            database = self.path('catalog.sqlite3', exists=True)
            self.connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=10)
            self.connection.row_factory = sqlite3.Row
            if self.connection.execute('PRAGMA user_version').fetchone()[0] != _DB_VERSION:
                self.connection.close()
                raise MaterialError('invalid-request', '只读素材库版本无效', stage='storage')
            return
        self.root.mkdir(parents=True, exist_ok=True)
        self.path('objects', directory=True).mkdir(exist_ok=True)
        self.path('snapshots', directory=True).mkdir(exist_ok=True)
        self.path('staging', directory=True).mkdir(exist_ok=True)
        database = self.path('catalog.sqlite3', exists=False)
        self.connection = sqlite3.connect(database, timeout=10, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys=ON')
        self.connection.execute('PRAGMA busy_timeout=10000')
        version = self.connection.execute('PRAGMA user_version').fetchone()[0]
        if version not in {0, _DB_VERSION}:
            self.connection.close()
            raise MaterialError('invalid-request', '不支持此素材数据库版本', stage='storage')
        self.connection.executescript('''
            CREATE TABLE IF NOT EXISTS documents(
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, digest TEXT NOT NULL,
                payload TEXT NOT NULL, created_at TEXT NOT NULL, cache_key TEXT UNIQUE);
            CREATE INDEX IF NOT EXISTS documents_kind ON documents(kind,created_at,id);
            CREATE TABLE IF NOT EXISTS refs(
                owner TEXT NOT NULL REFERENCES documents(id),
                target TEXT NOT NULL REFERENCES documents(id),
                PRIMARY KEY(owner,target));
            CREATE INDEX IF NOT EXISTS refs_target ON refs(target);
            CREATE TABLE IF NOT EXISTS artifacts(
                sha256 TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE, bytes INTEGER NOT NULL CHECK(bytes>=0));
            CREATE TABLE IF NOT EXISTS document_artifacts(
                owner TEXT NOT NULL REFERENCES documents(id),
                sha256 TEXT NOT NULL REFERENCES artifacts(sha256),
                PRIMARY KEY(owner,sha256));
            CREATE TABLE IF NOT EXISTS operations(
                id TEXT PRIMARY KEY, status TEXT NOT NULL,
                payload TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS index_records(
                index_id TEXT NOT NULL REFERENCES documents(id), record_id TEXT NOT NULL,
                channel TEXT NOT NULL, text TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(index_id,record_id));
            CREATE TABLE IF NOT EXISTS record_sets(
                index_id TEXT PRIMARY KEY REFERENCES documents(id), digest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tokens(
                token TEXT NOT NULL, index_id TEXT NOT NULL, record_id TEXT NOT NULL,
                PRIMARY KEY(token,index_id,record_id),
                FOREIGN KEY(index_id,record_id) REFERENCES index_records(index_id,record_id));
            CREATE INDEX IF NOT EXISTS records_channel ON index_records(channel);
        ''')
        self.connection.execute(f'PRAGMA user_version={_DB_VERSION}')

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def path(self, reference: str, *, exists: bool = False, directory: bool = False) -> Path:
        try:
            relative_path(reference)
            no_links(self.root)
            result = local(self.root, reference, exists=exists and not directory)
            no_links(result)
            if exists and directory and not result.is_dir():
                raise ValueError('目录不存在')
            return result
        except (M2VError, ValueError) as exc:
            raise MaterialError('security-blocked', '素材库路径无效、越界或包含链接', stage='storage') from exc

    def _writable(self):
        if self.readonly:
            raise MaterialError('read-only', '只读素材库不允许写入', stage='storage')

    @contextmanager
    def transaction(self):
        self._writable()
        try:
            self.connection.execute('BEGIN IMMEDIATE')
            yield self.connection
            self.connection.execute('COMMIT')
        except sqlite3.OperationalError as exc:
            if self.connection.in_transaction:
                self.connection.execute('ROLLBACK')
            code = 'store-busy' if 'locked' in str(exc).lower() else 'conflict'
            raise MaterialError(code, '素材数据库事务失败，请核验后重试', stage='storage', retryable=code == 'store-busy') from exc
        except BaseException:
            if self.connection.in_transaction:
                self.connection.execute('ROLLBACK')
            raise

    def publish_file(self, source: Path, *, max_bytes: int | None = None,
                     min_free_bytes: int = 64 * 1024 * 1024) -> Artifact:
        self._writable()
        source = no_links(source)
        if not source.is_file():
            raise MaterialError('not-found', '输入素材文件不存在', stage='storage')
        expected_size = source.stat().st_size
        if max_bytes is not None and expected_size > max_bytes:
            raise MaterialError('resource-limit', '输入文件超过当前素材预算', stage='storage')
        if shutil.disk_usage(self.root).free < expected_size + min_free_bytes:
            raise MaterialError('resource-limit', '素材库磁盘余量不足', stage='storage')
        staging = self.path('staging', exists=True, directory=True)
        fd, name = tempfile.mkstemp(prefix='object-', dir=staging)
        temporary = Path(name)
        size, hasher = 0, hashlib.sha256()
        try:
            with os.fdopen(fd, 'wb') as target, source.open('rb') as origin:
                while block := origin.read(1024 * 1024):
                    size += len(block)
                    if max_bytes is not None and size > max_bytes:
                        raise MaterialError('resource-limit', '读取期间文件超过素材预算', stage='storage')
                    hasher.update(block)
                    target.write(block)
                target.flush()
                os.fsync(target.fileno())
            sha = hasher.hexdigest()
            reference = f'objects/{sha[:2]}/{sha}'
            destination = self.path(reference)
            destination.parent.mkdir(parents=True, exist_ok=True)
            # 与其它进程协同发布；不让既有内容对象被同名新文件覆盖。
            with locked(self.root):
                self.path(reference)
                if destination.exists():
                    if destination.stat().st_size != size or digest(destination) != sha:
                        raise MaterialError('hash-mismatch', '已有内容对象损坏，未覆盖', stage='storage')
                else:
                    deliver(temporary, destination)
            artifact = Artifact(path=reference, sha256=sha, bytes=size)
            with self.transaction() as db:
                db.execute('INSERT OR IGNORE INTO artifacts VALUES(?,?,?)', (sha, reference, size))
                row = db.execute('SELECT path,bytes FROM artifacts WHERE sha256=?', (sha,)).fetchone()
                if tuple(row) != (reference, size):
                    raise MaterialError('conflict', '内容对象登记冲突', stage='storage')
            logger.debug('素材对象发布 sha256=%s bytes=%s', sha, size)
            return artifact
        finally:
            temporary.unlink(missing_ok=True)

    def publish_bytes(self, value: bytes, **kwargs) -> Artifact:
        self._writable()
        fd, name = tempfile.mkstemp(prefix='bytes-', dir=self.path('staging', exists=True, directory=True))
        temporary = Path(name)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(value)
            return self.publish_file(temporary, **kwargs)
        finally:
            temporary.unlink(missing_ok=True)

    def verify_artifact(self, artifact: Artifact) -> Path:
        path = self.path(artifact.path, exists=True)
        if path.stat().st_size != artifact.bytes or digest(path) != artifact.sha256:
            raise MaterialError('hash-mismatch', '素材对象摘要或大小不一致', stage='storage')
        return path

    def _artifacts(self, value):
        if isinstance(value, dict):
            if set(value) == {'path', 'sha256', 'bytes'}:
                yield Artifact.model_validate(value)
            else:
                for child in value.values():
                    yield from self._artifacts(child)
        elif isinstance(value, list):
            for child in value:
                yield from self._artifacts(child)

    def _check_bindings(self, document: Document) -> None:
        """通用外键只保证存在；这里核对种类、字节和时间关系，防止可信身份串线。"""
        data = document.data
        value = data.model_dump(mode='json')
        expected = {'sourceId': 'material.source', 'mediaId': 'material.media',
                    'requirementId': 'material.requirement', 'candidateId': 'material.candidate',
                    'selectionId': 'material.selection'}
        linked = {key: self.get(value[key], kind=kind) for key, kind in expected.items() if value.get(key)}
        media = linked.get('mediaId')
        if media is not None:
            if data.mediaSha256 != media.data.artifact.sha256:
                raise MaterialError('hash-mismatch', '引用媒体摘要与实际绑定不一致', stage='storage')
            if hasattr(data, 'timelineMappingSha256') and data.timelineMappingSha256 != fingerprint(media.data.probe.timeline):
                raise MaterialError('hash-mismatch', '时间映射身份与引用媒体不一致', stage='storage')
            if hasattr(data, 'localRange'):
                interval = data.localRange
                duration = media.data.probe.durationUs
                if ((media.data.probe.kind == 'image' and interval is not None)
                        or (media.data.probe.kind != 'image' and (interval is None or interval.endUs > duration))):
                    raise MaterialError('invalid-request', '窗口与实际媒体种类或时长不一致', stage='storage')
                if data.sourceRange != media.data.probe.timeline.source_range(interval):
                    raise MaterialError('invalid-request', '源区间与已验证媒体映射不一致', stage='storage')
            if 'sourceId' in linked and data.sourceId != media.data.sourceId:
                raise MaterialError('conflict', '候选来源与媒体实际来源不一致', stage='storage')
        if 'requirementId' in linked and data.requirementDigest != fingerprint(linked['requirementId']):
            raise MaterialError('hash-mismatch', '候选需求摘要不一致', stage='storage')
        if 'candidateId' in linked:
            candidate = linked['candidateId']
            if (data.candidateDigest != fingerprint(candidate) or data.mediaId != candidate.data.mediaId
                    or data.mediaSha256 != candidate.data.mediaSha256):
                raise MaterialError('hash-mismatch', '选择未绑定原候选和媒体', stage='storage')
        for index_id in value.get('indexIds', []):
            index = self.get(index_id, kind='material.index')
            if (index.data.status != 'complete' or index.data.mediaSha256 != data.mediaSha256
                    or index.data.timelineMappingSha256 != data.timelineMappingSha256):
                raise MaterialError('conflict', '候选索引的状态、媒体或映射不一致', stage='storage')
        if 'selectionId' in linked:
            selection = linked['selectionId']
            origin = self.get(selection.data.mediaId, kind='material.media')
            if (data.selectionDigest != fingerprint(selection) or data.inputMediaSha256 != selection.data.mediaSha256
                    or data.localRange != selection.data.localRange or data.sourceRange != selection.data.sourceRange
                    or data.sourceId != origin.data.sourceId or data.timeline != origin.data.probe.timeline
                    or data.sourceUrl != linked['sourceId'].data.sourceUrl
                    or data.upstreamFullSha256 != origin.data.upstreamFullSha256
                    or selection.data.outputArtifact is None
                    or data.outputArtifactSha256 != selection.data.outputArtifact.sha256):
                raise MaterialError('hash-mismatch', '凭据未绑定实际选择、输出和来源', stage='storage')

    def put(self, document: Document, *, cache_key: str | None = None,
            references: Iterable[str] = ()) -> Document:
        document = parse_document(document.model_dump(mode='json'))
        value = document.model_dump(mode='json')
        payload, checksum = canonical(value), fingerprint(value)
        data = value['data']
        self._check_bindings(document)
        refs = set(references)
        for key in ('sourceId', 'mediaId', 'requirementId', 'candidateId', 'selectionId'):
            if data.get(key):
                refs.add(data[key])
        refs.update(data.get('indexIds', []))
        artifacts = {item.sha256: item for item in self._artifacts(data)}
        for artifact in artifacts.values():
            self.verify_artifact(artifact)
        try:
            with self.transaction() as db:
                existing = db.execute('SELECT digest,cache_key FROM documents WHERE id=?', (document.id,)).fetchone()
                if existing:
                    if existing[0] != checksum:
                        raise MaterialError('conflict', '不可变素材记录 ID 已有不同内容', stage='storage')
                    existing_refs = {row[0] for row in db.execute('SELECT target FROM refs WHERE owner=?', (document.id,))}
                    if refs != existing_refs or (cache_key is not None and cache_key != existing[1]):
                        raise MaterialError('conflict', '不可变记录的引用或缓存身份不同，未静默更改', stage='storage')
                else:
                    db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?)',
                               (document.id, document.kind, checksum, payload, document.createdAt, cache_key))
                    for target in refs:
                        db.execute('INSERT INTO refs VALUES(?,?)', (document.id, target))
                    for artifact in artifacts.values():
                        db.execute('INSERT OR IGNORE INTO artifacts VALUES(?,?,?)',
                                   (artifact.sha256, artifact.path, artifact.bytes))
                        db.execute('INSERT INTO document_artifacts VALUES(?,?)', (document.id, artifact.sha256))
        except sqlite3.IntegrityError as exc:
            raise MaterialError('conflict', '素材关系缺失或缓存身份已存在', stage='storage') from exc
        # DB 已经提交，快照中断不应误报“记录未发生”。export 可随时补出。
        try:
            self.export(document.id)
        except OSError:
            logger.warning('素材记录已提交但 JSON 快照待恢复 id=%s', document.id)
        return document

    def get(self, document_id: str, *, kind: str | None = None) -> Document:
        row = self.connection.execute('SELECT payload,digest FROM documents WHERE id=?', (document_id,)).fetchone()
        if row is None:
            raise MaterialError('not-found', '素材记录不存在', stage='storage', source_id=document_id)
        document = self._decode(row)
        if kind is not None and document.kind != kind:
            raise MaterialError('invalid-request', '素材记录种类不匹配', stage='storage')
        return document

    @staticmethod
    def _decode(row) -> Document:
        try:
            value = json.loads(row['payload'])
            if fingerprint(value) != row['digest']:
                raise ValueError('digest')
            return parse_document(value)
        except (ValueError, MaterialError) as exc:
            raise MaterialError('hash-mismatch', '素材数据库记录损坏', stage='storage') from exc

    def cached(self, cache_key: str) -> Document | None:
        row = self.connection.execute('SELECT id FROM documents WHERE cache_key=?', (cache_key,)).fetchone()
        return self.get(row[0]) if row else None

    def documents(self, kind: str, *, limit: int | None = None) -> list[Document]:
        sql = 'SELECT payload,digest FROM documents WHERE kind=? ORDER BY created_at,id'
        parameters: tuple = (kind,)
        if limit is not None:
            if type(limit) is not int or limit < 1:
                raise MaterialError('invalid-request', '列表数量必须为正整数', stage='storage')
            sql += ' LIMIT ?'
            parameters += (limit,)
        return [self._decode(row) for row in self.connection.execute(sql, parameters).fetchall()]

    def export(self, document_id: str) -> Path:
        self._writable()
        document = self.get(document_id)
        path = self.path(f'snapshots/{document.id}.json')
        atomic_text(path, json.dumps(document.model_dump(mode='json'), ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        return path

    def operation(self, operation_id: str, *, status: str | None = None, payload: dict | None = None) -> dict | None:
        if status is None:
            row = self.connection.execute('SELECT status,payload,updated_at FROM operations WHERE id=?', (operation_id,)).fetchone()
            return dict(status=row[0], payload=json.loads(row[1]), updatedAt=row[2]) if row else None
        if status not in {'pending', 'committed', 'failed'}:
            raise MaterialError('invalid-request', '未知操作状态', stage='storage')
        with self.transaction() as db:
            db.execute('INSERT INTO operations VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                       'status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at',
                       (operation_id, status, canonical(payload or {}), utc_now()))
        return self.operation(operation_id)

    def add_records(self, index_id: str, records: list[IndexRecord], *, tokenize=None):
        index = self.get(index_id, kind='material.index')
        if index.data.status != 'complete' or len(records) != index.data.recordCount:
            raise MaterialError('invalid-request', '索引状态或条目数不一致', stage='storage')
        if len({record.id for record in records}) != len(records) or any(record.channel != index.data.channel for record in records):
            raise MaterialError('invalid-request', '索引条目不能重复 ID 或跨通道', stage='storage')
        try:
            bound = json.loads(self.verify_artifact(index.data.artifacts[0]).read_text(encoding='utf-8'))
            declared = [IndexRecord.model_validate(item) for item in bound]
        except (ValueError, TypeError, UnicodeError) as exc:
            raise MaterialError('hash-mismatch', '索引首个产物必须是绑定的条目 JSON 集合', stage='storage') from exc
        ordered = sorted((record.model_dump(mode='json') for record in records), key=lambda item: item['id'])
        if ordered != sorted((record.model_dump(mode='json') for record in declared), key=lambda item: item['id']):
            raise MaterialError('hash-mismatch', '索引条目与不可变产物集合不同', stage='storage')
        checksum = fingerprint(ordered)
        with self.transaction() as db:
            published = db.execute('SELECT digest FROM record_sets WHERE index_id=?', (index_id,)).fetchone()
            if published:
                if published[0] != checksum:
                    raise MaterialError('conflict', '已发布索引不能替换或追加不同条目集合', stage='storage')
                return
            if db.execute('SELECT count(*) FROM index_records WHERE index_id=?', (index_id,)).fetchone()[0]:
                raise MaterialError('conflict', '存在未绑定完整集合的索引行，需核验恢复', stage='storage')
            for record in records:
                encoded = canonical(record)
                db.execute('INSERT INTO index_records VALUES(?,?,?,?,?)',
                           (index_id, record.id, record.channel, record.text, encoded))
                if tokenize:
                    db.executemany('INSERT OR IGNORE INTO tokens VALUES(?,?,?)',
                                   ((token, index_id, record.id) for token in set(tokenize(record.text))))
            db.execute('INSERT INTO record_sets VALUES(?,?)', (index_id, checksum))

    def records(self, index_id: str) -> list[IndexRecord]:
        if self.connection.execute('SELECT 1 FROM record_sets WHERE index_id=?', (index_id,)).fetchone() is None:
            raise MaterialError('conflict', '索引条目集合未完整发布，需从绑定产物恢复', stage='storage')
        return [IndexRecord.model_validate(json.loads(row[0])) for row in self.connection.execute(
            'SELECT payload FROM index_records WHERE index_id=? ORDER BY rowid', (index_id,))]
