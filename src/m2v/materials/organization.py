"""媒体组织信息独立于不可变来源与媒体；标签和集合不表示许可或事实结论。"""
from __future__ import annotations

import json
import unicodedata

from .contracts import utc_now
from .errors import MaterialError


def labels(values):
    if not isinstance(values, (list, tuple)) or len(values) > 64:
        raise MaterialError('invalid-request', '标签或集合必须是至多 64 项的列表', stage='library')
    result = set()
    for value in values:
        if not isinstance(value, str):
            raise MaterialError('invalid-request', '标签或集合必须是文字', stage='library')
        value = unicodedata.normalize('NFKC', value).strip().casefold()
        if not value or len(value) > 64 or any(unicodedata.category(c).startswith('C') for c in value):
            raise MaterialError('invalid-request', '标签或集合须为 1..64 字符且不含控制字符', stage='library')
        result.add(value)
    return sorted(result)


def _exists(store):
    return store.connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='library_annotations'").fetchone() is not None


def _schema(store):
    store.connection.execute('''CREATE TABLE IF NOT EXISTS library_annotations(
        media_id TEXT PRIMARY KEY REFERENCES documents(id), tags TEXT NOT NULL,
        collections TEXT NOT NULL, favorite INTEGER NOT NULL CHECK(favorite IN (0,1)),
        note TEXT NOT NULL, updated_at TEXT NOT NULL)''')


def annotation(store, media_id):
    store.get(media_id, kind='material.media')
    row = (store.connection.execute('SELECT * FROM library_annotations WHERE media_id=?', (media_id,)).fetchone()
           if _exists(store) else None)
    return {'mediaId': media_id, 'tags': json.loads(row['tags']) if row else [],
            'collections': json.loads(row['collections']) if row else [],
            'favorite': bool(row['favorite']) if row else False,
            'note': row['note'] if row else '', 'updatedAt': row['updated_at'] if row else None}


def annotate(store, media_id, *, tags=(), remove_tags=(), collections=(), remove_collections=(),
             favorite=None, note=None):
    add, remove = labels(tags), labels(remove_tags)
    groups, remove_groups = labels(collections), labels(remove_collections)
    if set(add) & set(remove) or set(groups) & set(remove_groups):
        raise MaterialError('invalid-request', '同一项不能同时添加和移除', stage='library')
    if favorite is not None and type(favorite) is not bool:
        raise MaterialError('invalid-request', '收藏状态必须为布尔值', stage='library')
    if note is not None and (not isinstance(note, str) or len(note) > 2000 or '\x00' in note):
        raise MaterialError('invalid-request', '备注须为不含 NUL 的至多 2000 字符文字', stage='library')
    store.get(media_id, kind='material.media')
    _schema(store)
    with store.transaction() as db:
        current = annotation(store, media_id)
        updated_tags = labels(sorted((set(current['tags']) | set(add)) - set(remove)))
        updated_groups = labels(sorted((set(current['collections']) | set(groups)) - set(remove_groups)))
        db.execute('INSERT INTO library_annotations VALUES(?,?,?,?,?,?) ON CONFLICT(media_id) DO UPDATE SET '
                   'tags=excluded.tags,collections=excluded.collections,favorite=excluded.favorite,'
                   'note=excluded.note,updated_at=excluded.updated_at',
                   (media_id, json.dumps(updated_tags, ensure_ascii=False), json.dumps(updated_groups, ensure_ascii=False),
                    int(current['favorite'] if favorite is None else favorite), current['note'] if note is None else note, utc_now()))
    return annotation(store, media_id)


def list_media(store, *, tags=(), collection=None, favorites=False, query=None, limit=100, offset=0):
    wanted = set(labels(tags))
    group = labels([collection])[0] if collection is not None else None
    if type(limit) is not int or not 1 <= limit <= 2000 or type(offset) is not int or offset < 0:
        raise MaterialError('invalid-request', '列表预算须为 1..2000 且偏移非负', stage='library')
    if query is not None and (not isinstance(query, str) or len(query) > 1000):
        raise MaterialError('invalid-request', '筛选文字须为至多 1000 字符', stage='library')
    has = _exists(store)
    annotation_fields = 'a.tags,a.collections,a.favorite,a.note' if has else "'[]' AS tags,'[]' AS collections,0 AS favorite,'' AS note"
    join = 'LEFT JOIN library_annotations a ON a.media_id=d.id' if has else ''
    rows = store.connection.execute(f'''SELECT d.payload,d.digest,s.payload AS source_payload,s.digest AS source_digest,
        {annotation_fields} FROM documents d LEFT JOIN documents s ON s.id=json_extract(d.payload,'$.data.sourceId')
        {join} WHERE d.kind='material.media' ORDER BY d.created_at,d.id''')
    found, matched = [], 0
    for row in rows:
        media = store._decode(row)
        source = store._decode({'payload': row['source_payload'], 'digest': row['source_digest']}) if row['source_payload'] else None
        item_tags = json.loads(row['tags'] or '[]')
        collections = json.loads(row['collections'] or '[]')
        favorite = bool(row['favorite'])
        title = source.data.title if source else '来源未知'
        text = ' '.join([title, row['note'] or '', *item_tags, *collections]).casefold()
        if not wanted.issubset(item_tags) or (group and group not in collections) or (favorites and not favorite):
            continue
        if query and query.casefold() not in text:
            continue
        matched += 1
        if matched <= offset:
            continue
        if len(found) >= limit:
            return {'items': found, 'hasMore': True, 'offset': offset, 'nextOffset': offset + limit}
        found.append({'mediaId': media.id, 'sourceId': media.data.sourceId, 'title': title,
            'sourceUrl': source.data.sourceUrl if source else None, 'provider': source.data.provider if source else None,
            'author': source.data.author if source else '未知', 'license': source.data.license if source else '未知',
            'kind': media.data.probe.kind, 'width': media.data.probe.width, 'height': media.data.probe.height,
            'durationUs': media.data.probe.durationUs, 'artifact': media.data.artifact.model_dump(mode='json'),
            'tags': item_tags, 'collections': collections, 'favorite': favorite, 'note': row['note'] or ''})
    return {'items': found, 'hasMore': False, 'offset': offset, 'nextOffset': None}
