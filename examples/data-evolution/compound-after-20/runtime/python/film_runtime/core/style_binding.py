"""作品的视觉参考契约。初始化时将同一模块随独立工程分发。"""
from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .fingerprints import fingerprint


BINDING = 'design/style-binding.json'
RELEASE = 'design/style-release.json'
ROLES = {'overall', 'specialist', 'standard'}


def require(condition, message):
    if not condition:
        raise ValueError(f'风格参考：{message}')


def local_path(root, value):
    require(isinstance(value, str) and value.strip() and not Path(value).anchor
            and not any(c in value for c in ('\\', ':', '\x00'))
            and all(p not in ('', '.', '..') for p in value.split('/')), '需要工程内相对路径')
    path = (root / value).resolve()
    require(path.is_relative_to(root.resolve()), '文件链接越过作品目录')
    return path


def read_object(root, relative):
    value = json.loads(local_path(root, relative).read_text(encoding='utf-8'))
    require(isinstance(value, dict), f'{relative} 应为对象')
    return value


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _strings(obj, fields):
    require(isinstance(obj, dict) and all(isinstance(obj.get(k), str) and obj[k].strip()
                                          for k in fields), f'缺少有效字段 {", ".join(fields)}')


def _sha(value):
    require(isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value), '无效的 SHA-256')


def _url(value):
    url = urlsplit(value)
    require(url.scheme in ('http', 'https') and url.hostname and not url.username
            and not url.password, '需要公开 HTTP(S) 参考网址')


def _style(root, style, digest, *, overall):
    require(isinstance(style, dict) and set(style) <= {'id', 'revision', 'references', 'snapshot'},
            '参考集存在未知或旧字段')
    _strings(style, ('id',))
    require(type(style.get('revision')) is int and style['revision'] > 0, '参考修订号无效')
    refs = style.get('references')
    require(isinstance(refs, list) and refs, '参考清单为空')
    ids = {}
    roles = set()
    for ref in refs:
        _strings(ref, ('id', 'role', 'url', 'scope', 'observed', 'accessedAt'))
        ev = ref.get('evidence')
        _strings(ev, ('url', 'locator', 'sha256'))
        _url(ref['url'])
        _url(ev['url'])
        date.fromisoformat(ref['accessedAt'])
        _sha(ev['sha256'])
        require(ref['id'] not in ids and ref['role'] in ROLES, '条目重复或用途未知')
        ids[ref['id']] = ev['sha256']
        roles.add(ref['role'])
    require(not overall or roles == ROLES, '整体目标缺少整体、专项或规范参考')
    snapshots = style.get('snapshot', {})
    require(isinstance(snapshots, dict) and snapshots.keys() <= ids.keys(), '快照引用未知条目')
    for key, record in snapshots.items():
        _strings(record, ('path', 'sha256'))
        require(record['sha256'] == ids[key] == sha256(local_path(root, record['path'])),
                f'{key} 快照摘要不符')
    require(fingerprint(style) == digest, '参考清单摘要不符')
    return ids


def load_binding(root, project):
    """核验本地发布凭据、覆盖原文和范围。准备与渲染均无需联网。"""
    binding = read_object(root, BINDING)
    require(set(binding) == {'schemaVersion', 'projectId', 'type', 'visualStyle',
                             'referenceDigest', 'overrides'}, '绑定字段缺失或版本过旧')
    require(type(binding['schemaVersion']) is int and binding['schemaVersion'] == 1
            and binding['projectId'] == project['id'] and binding['type'] == project['type'],
            '绑定版本或作品身份不符')
    style = binding['visualStyle']
    ids = _style(root, style, binding['referenceDigest'], overall=True)
    release = read_object(root, RELEASE)
    require(release == {'type': project['type'], 'id': style['id'], 'revision': style['revision'],
                        'referenceDigest': binding['referenceDigest']}, '默认绑定与工程内发布凭据不符')
    overrides = binding['overrides']
    require(isinstance(overrides, list), 'overrides 应为数组')
    if not overrides:
        return binding
    board = read_object(root, project['materials']['storyboard'])
    scene_ids = {s['id'] for s in board['scenes']}
    used = set()
    for item in overrides:
        require(isinstance(item, dict) and set(item) == {'scope', 'target', 'referenceDigest', 'authorization'},
                '覆盖须登记目标、摘要、范围和授权')
        auth = item['authorization']
        _strings(auth, ('quote', 'source', 'at'))
        require(datetime.fromisoformat(auth['at']).utcoffset() is not None, '授权时间缺少时区')
        require(auth['quote'] in local_path(root, auth['source']).read_text(encoding='utf-8'),
                '授权原件中找不到登记原话')
        scope = item['scope']
        require(isinstance(scope, dict) and set(scope) == {'scenes', 'uses'}, '覆盖范围无效')
        scenes, uses = scope['scenes'], scope['uses']
        require(scenes == 'all' or (isinstance(scenes, list) and scenes
                and all(isinstance(s, str) and s in scene_ids for s in scenes)
                and len(scenes) == len(set(scenes))), '场景缺失、重复或未知')
        affected = scene_ids if scenes == 'all' else set(scenes)
        require(not (affected & used) and (scenes != 'all' or len(overrides) == 1), '覆盖范围冲突')
        used.update(affected)
        require(uses == 'all' or (isinstance(uses, list) and uses
                and all(isinstance(k, str) and k in ids for k in uses)
                and len(set(uses)) == len(uses)), '覆盖用途应指向已登记的默认条目')
        target = item['target']
        _style(root, target, item['referenceDigest'], overall=uses == 'all')
        if uses != 'all':
            roles = {ref['role'] for ref in style['references'] if ref['id'] in uses}
            require(roles <= {ref['role'] for ref in target['references']}, '覆盖目标缺少已授权用途的对应参考')
    return binding
