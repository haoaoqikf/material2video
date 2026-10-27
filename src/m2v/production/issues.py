"""唯一问题表中的机器块；不复制问题现象到状态数据库。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from .contract import fields, text
from .workflow import GATE_IDS
from .storage import atomic_text, local

BLOCK = re.compile(r'^```m2v-issues\s*\n(.*?)^```\s*$', re.M | re.S)


def load(root: Path, *, required=False) -> list[dict]:
    path = outputs(root) / 'visual-notes.md'
    if not path.exists():
        if required:
            raise M2VError('缺少唯一问题表，不能推断没有保护引用')
        return []
    source = path.read_text(encoding='utf-8')
    matches = BLOCK.findall(source)
    if not matches and not required:
        return []
    if len(matches) != 1:
        raise M2VError('唯一问题表必须含一个 m2v-issues JSON 块')
    try:
        items = json.loads(matches[0])
    except ValueError as exc:
        raise M2VError('唯一问题表机器块损坏') from exc
    validate(root, items)
    return items


def validate(root: Path, items) -> None:
    if not isinstance(items, list):
        raise M2VError('问题机器块必须为列表')
    seen = set()
    for item in items:
        fields(item, {'id', 'status', 'required', 'gate', 'sceneId', 'checkpointId', 'caughtAt', 'catchableAt',
                      'evidence', 'versionRefs'}, {'uncatchableReason'})
        if text(item['id']) in seen or item['status'] not in ('open', 'closed') or type(item['required']) is not bool:
            raise M2VError('问题 ID 重复、状态或必改标识无效')
        seen.add(item['id'])
        for key in ('gate', 'caughtAt', 'catchableAt'):
            if item[key] not in GATE_IDS:
                raise M2VError(f'问题 {key} 无效')
        if not isinstance(item['versionRefs'], list) or not isinstance(item['evidence'], list):
            raise M2VError('问题证据与版本引用必须为列表')
        if item['status'] == 'closed':
            if not item['evidence']:
                raise M2VError('关闭问题必须有复查证据')
            for entry in item['evidence']:
                fields(entry, {'path', 'sha256', 'gate'})
                from m2v.core.delivery import digest
                if digest(local(outputs(root), entry['path'])) != entry['sha256']:
                    raise M2VError('问题复查证据摘要不匹配')
            if item['catchableAt'] < item['caughtAt'] and not item.get('uncatchableReason'):
                if not any(e['gate'] == item['catchableAt'] for e in item['evidence']):
                    raise M2VError('迟到缺陷必须附最早可拦截门的回归证据')


def update(root: Path, item: dict) -> None:
    path = outputs(root) / 'visual-notes.md'
    source = path.read_text(encoding='utf-8') if path.exists() else '# 制作问题与复查\n'
    items = load(root)
    items = [x for x in items if x['id'] != item['id']] + [item]
    validate(root, items)
    block = '```m2v-issues\n' + json.dumps(items, ensure_ascii=False, indent=2) + '\n```'
    source = BLOCK.sub(lambda _: block, source) if BLOCK.search(source) else source.rstrip() + '\n\n' + block + '\n'
    atomic_text(path, source)
