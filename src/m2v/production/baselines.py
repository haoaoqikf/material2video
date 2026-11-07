"""重置版本快照与可恢复清理；引用保护优先于数量目标。"""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from m2v.core.delivery import digest, outputs
from m2v.core.errors import M2VError
from . import issues, ledger
from .storage import local, read, receipt, write

MEDIA = {'.mp4', '.webm', '.mov', '.wav', '.mp3', '.flac', '.png', '.jpg', '.jpeg', '.webp'}


def _baseline_directory(root: Path) -> Path:
    directory = outputs(root) / 'baselines'
    if any(path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())
           for path in (outputs(root), directory)):
        raise M2VError('基线目录不允许符号链接或目录联接')
    directory = directory.resolve()
    # 报告摘要文件名加 records 前缀会超出 Win32 MAX_PATH；仅 IO 使用扩展路径，
    # manifest 仍登记原有相对路径，不改变系统长路径策略或基线材料格式。
    value = str(directory)
    if os.name == 'nt' and not value.startswith('\\\\?\\'):
        value = '\\\\?\\UNC\\' + value[2:] if value.startswith('\\\\') else '\\\\?\\' + value
    return Path(value)


def manifests(root: Path) -> list[dict]:
    directory = _baseline_directory(root)
    result = []
    for path in sorted(directory.glob('*/manifest.json')):
        if path.is_symlink() or path.parent.is_symlink():
            raise M2VError('基线目录不允许符号链接')
        value = read(path)
        if value.get('retention') not in ('full', 'record-only') or value.get('id') != path.parent.name:
            raise M2VError(f'基线 manifest 无效：{path}')
        result.append(value)
    return sorted(result, key=lambda x: x['createdAt'])


def references(root: Path) -> set[str]:
    protected = {v for p in issues.load(root, required=True) if p['status'] != 'closed' for v in p['versionRefs']}
    for archived in (outputs(root) / 'production/history-notes').glob('*.md'):
        # 历史问题仍保护引用；旧格式不能确认引用时拒绝清理，不猜测安全。
        value = issues.parse(archived.read_text(encoding='utf-8'))
        protected.update(v for p in value['items'] if p['status'] != 'closed' for v in p['versionRefs'])
    comparison = outputs(root) / 'production/comparisons.json'
    if not comparison.exists():
        return protected
    value = read(comparison)
    if not isinstance(value, list):
        raise M2VError('比较引用表必须为列表')
    for item in value:
        if item.get('status') not in ('active', 'closed') or not isinstance(item.get('versionRefs'), list):
            raise M2VError('比较引用表损坏')
        if item['status'] == 'active':
            protected.update(item['versionRefs'])
    return protected


def create(root: Path, manifest: dict, *, reason: str, files: list[str], reset=True) -> dict:
    if not reason.strip() or not files:
        raise M2VError('基线必须记录原因和覆盖前媒体')
    base = outputs(root)
    source = [local(base, name) for name in files]
    if any(p.suffix.lower() not in MEDIA or p.is_relative_to(base / 'baselines') for p in source):
        raise M2VError('基线媒体必须是当前输出媒体，不可复制其他基线')
    identifier = uuid.uuid4().hex
    directory = _baseline_directory(root) / identifier
    directory.mkdir(parents=True)
    media = []
    for index, path in enumerate(source):
        target = directory / 'media' / f'{index:04d}{path.suffix.lower()}'
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(path, target)
        media.append(receipt(directory, target))
    records = []
    for relative in ('prepared.json', 'delivery.json', 'visual-notes.md', 'production/workflow.json', 'production/comparisons.json'):
        path = root / 'outputs' / relative if relative == 'prepared.json' else base / relative
        if path.is_file():
            target = directory / 'records' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local(path.parent, path.name), target)
            records.append(receipt(directory, target))
    # 评审报告、manifest、台账与缩略图属于长期记录，不随媒体清理消失。
    for folder in ('review-pack', 'production'):
        for path in sorted((base / folder).rglob('*')):
            if path.is_file() and path.suffix.lower() in {'.json', '.md', '.jsonl'}:
                relative = path.relative_to(base).as_posix()
                target = directory / 'records' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local(base, relative), target)
                records.append(receipt(directory, target))
    delivery = read(base / 'delivery.json') if (base / 'delivery.json').exists() else {}
    bound_prepared = delivery.get('preparedFingerprint') if any(digest(p) == delivery.get('sha256') for p in source) else None
    value = dict(id=identifier, createdAt=ledger.now(), reason=reason, reset=reset, retention='full',
                 prunedAt=None, pruneReason=None, media=media, records=records,
                 preparedFingerprint=bound_prepared)
    write(directory / 'manifest.json', value)
    if (base / 'production/workflow.json').exists():
        ledger.append(root, manifest, 'baseline-created', data={'id': identifier, 'reset': reset})
    return value


def prune(root: Path, manifest: dict) -> dict:
    base = _baseline_directory(root)
    versions = manifests(root)
    protected = references(root)
    known = {v['id'] for v in versions}
    if protected - known - {'current'}:
        raise M2VError(f'引用了未知版本，停止清理：{sorted(protected - known - {"current"})}')
    resets = [v for v in versions if v.get('reset', True)]
    keep = protected | ({resets[0]['id'], resets[-1]['id']} if resets else set())
    removed = []
    for value in versions:
        directory = base / value['id']
        if value['id'] in keep:
            if value['retention'] != 'full':
                raise M2VError(f'被引用版本媒体已降级，无法恢复：{value["id"]}')
            continue
        for record in value['records']:
            if digest(local(directory, record['path'])) != record['sha256']:
                raise M2VError('长期记录副本损坏，停止清理')
        if value['retention'] == 'full':
            # 先验证待删路径，再持久化删除计划；进程中断后可幂等继续。
            for item in value['media']:
                path = local(directory, item['path'])
                if not path.is_relative_to(directory / 'media') or path.suffix.lower() not in MEDIA or digest(path) != item['sha256']:
                    raise M2VError('待删除媒体路径或摘要无效')
            value.update(retention='record-only', pruneReason='不在默认保留集合且无活动引用', pendingDelete=[x['path'] for x in value['media']])
            write(directory / 'manifest.json', value)
        for name in value.get('pendingDelete', []):
            path = local(directory, name, exists=False)
            if not path.is_relative_to(directory / 'media') or path.suffix.lower() not in MEDIA:
                raise M2VError('清理清单越界')
            path.unlink(missing_ok=True)
        if not value.get('prunedAt'):
            value.update(prunedAt=ledger.now(), pendingDelete=[])
            write(directory / 'manifest.json', value)
            removed.append(value['id'])
    result = summary(root)
    result['pruned'] = removed
    ledger.append(root, manifest, 'baseline-pruned', data=result)
    return result


def summary(root: Path) -> dict:
    values = manifests(root)
    full = [v for v in values if v['retention'] == 'full']
    current_count = int((outputs(root) / 'video.mp4').is_file())
    try:
        protected = sorted(references(root))
        diagnostic = []
    except M2VError as exc:
        protected, diagnostic = [], [str(exc)]
    return {'current': 'current', 'fullVersions': current_count + len(full), 'target': 3, 'excess': max(0, len(full) - 2),
            'protected': protected, 'diagnostics': diagnostic,
            'versions': [{'id': v['id'], 'retention': v['retention'], 'prunedAt': v.get('prunedAt')} for v in values]}
