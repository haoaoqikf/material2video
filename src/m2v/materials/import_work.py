"""选中片段进入作品：私有暂存、既有 import 清单、作品内 receipt 与幂等恢复。

正式登记仍是 ``assets/media-sources.json`` 与 ``assets/media/``；工作层只增加
``assets/materials/`` 下的暂存与凭据，不进入作品正式 schema，也不成为渲染依赖。
"""
from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from m2v.core.delivery import digest
from m2v.core.errors import M2VError
from m2v.core.project import load_project
from m2v.production.storage import atomic_text, locked
from m2v.types.scene_film import media_assets

from .contracts import Media, Receipt, ReceiptData, Selection, fingerprint, utc_now
from .errors import MaterialError
from .paths import no_links
from .store import MaterialStore

logger = logging.getLogger(__name__)

MAX_ASSET_BYTES = 256 * 1024 * 1024
RECEIPTS = 'assets/materials/receipts'
STAGING = 'assets/materials/staging'


@dataclass
class ImportResult:
    receipt: Receipt
    entry: dict
    resumed: bool = False


def _selection(store: MaterialStore, selection_id: str) -> Selection:
    document = store.get(selection_id, kind='material.selection')
    if document.data.decision != 'chosen' or document.data.outputArtifact is None:
        raise MaterialError('invalid-request', '只有已选中的选择才能导入作品', stage='import')
    return document


def _media(store: MaterialStore, selection: Selection) -> Media:
    media = store.get(selection.data.mediaId, kind='material.media')
    if media.data.artifact.sha256 != selection.data.mediaSha256:
        raise MaterialError('hash-mismatch', '选择引用的媒体摘要已变化', stage='import')
    return media


def _plan(store: MaterialStore, selection: Selection, media: Media, project_root: Path,
          asset_id: str, role: str) -> dict:
    if selection.data.outputArtifact is None or selection.data.outputArtifact.bytes > MAX_ASSET_BYTES:
        raise MaterialError('resource-limit', '选中片段超过作品单文件 256 MiB 上限；请缩短或重编码',
                            stage='import')
    if not isinstance(asset_id, str) or not asset_id or len(asset_id) > 80 or not all(
            char.isalnum() or char in '_-' for char in asset_id):
        raise MaterialError('invalid-request', 'asset ID 只允许字母、数字、下划线与连字符', stage='import')
    from m2v.engine.assets_audit import ROLES
    if role not in ROLES:
        raise MaterialError('invalid-request', '素材角色不在作品支持范围', stage='import')
    source = store.get(media.data.sourceId, kind='material.source')
    source_url = source.data.sourceUrl or '未知'
    return {'schemaVersion': 1, 'assets': [{'id': asset_id,
             'kind': 'image' if media.data.probe.kind == 'image' else 'video',
             'role': role, 'target': asset_id, 'localPath': None,
             'sourceUrl': source_url if source_url != '未知' else '未知',
             'author': source.data.author, 'license': source.data.license}]}


def _existing(root: Path, asset_id: str) -> dict | None:
    record = media_assets.load_record(root)
    return next((entry for entry in record['assets'] if entry.get('id') == asset_id), None)


def _stage(store: MaterialStore, selection: Selection, media: Media, root: Path,
           operation_id: str) -> tuple[Path, str]:
    artifact = selection.data.outputArtifact
    assert artifact is not None
    source = store.verify_artifact(artifact)
    directory = no_links(root / STAGING / operation_id)
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=False)
    suffix = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}.get(
        (selection.data.outputProbe.container.upper() if selection.data.outputProbe else ''), '') or '.mp4'
    target = directory / f'{artifact.sha256[:16]}{suffix}'
    shutil.copyfile(source, target)
    no_links(target)
    if target.stat().st_size != artifact.bytes or digest(target) != artifact.sha256:
        raise MaterialError('hash-mismatch', '暂存复制摘要不一致，未导入作品', stage='import')
    return target, target.relative_to(root).as_posix()


def _receipt(store: MaterialStore, selection: Selection, media: Media, *, entry: dict,
             manifest: dict, project_id: str, operation_id: str, target_path: str) -> Receipt:
    assert selection.data.outputArtifact is not None
    data = ReceiptData(operationId=operation_id, selectionId=selection.id,
        selectionDigest=fingerprint(selection), sourceId=media.data.sourceId,
        sourceUrl=store.get(media.data.sourceId, kind='material.source').data.sourceUrl,
        inputMediaSha256=selection.data.mediaSha256,
        upstreamFullSha256=media.data.upstreamFullSha256,
        localRange=selection.data.localRange, sourceRange=selection.data.sourceRange,
        timeline=media.data.probe.timeline,
        outputArtifactSha256=selection.data.outputArtifact.sha256,
        manifestSha256=fingerprint(manifest), targetProjectId=project_id,
        targetAssetId=entry['id'], targetAssetPath=target_path,
        targetAssetSha256=entry.get('sha256'), registeredEntryDigest=fingerprint(entry),
        status='committed', committedAt=utc_now(), failure=None)
    document_id = f'receipt-{fingerprint(data.model_dump(mode="json"))[:32]}'
    try:
        previous = store.get(document_id, kind='material.receipt')
    except MaterialError as exc:
        if exc.code != 'not-found':
            raise
    else:
        if previous.data != data:
            raise MaterialError('conflict', '凭据身份对应不同登记结果', stage='import')
        return previous
    return store.put(Receipt(id=document_id, data=data))


def _write_receipt(root: Path, receipt: Receipt) -> Path:
    target = no_links(root / RECEIPTS / f'{receipt.data.operationId}.json')
    no_links(root / RECEIPTS)
    atomic_text(target, json.dumps(receipt.model_dump(mode='json'), ensure_ascii=False,
                                  indent=2, allow_nan=False) + '\n')
    return target


def import_selection(store: MaterialStore, *, project_root: Path, selection_id: str,
                     asset_id: str, role: str = 'color', replace: bool = False) -> ImportResult:
    root = no_links(Path(project_root).expanduser().resolve())
    _, project = load_project(root)
    selection = _selection(store, selection_id)
    media = _media(store, selection)
    manifest = _plan(store, selection, media, root, asset_id, role)
    operation_id = f'import-{fingerprint({"selection": selection.id, "project": project["id"], "asset": asset_id})[:24]}'
    previous = store.operation(operation_id)
    if previous and previous['status'] == 'committed':
        payload = previous['payload']
        receipt = store.get(payload['receiptId'], kind='material.receipt')
        if not (root / RECEIPTS / f'{receipt.data.operationId}.json').is_file():
            with locked(root):
                _write_receipt(root, receipt)
        entry = _existing(root, asset_id)
        return ImportResult(receipt, entry or {}, resumed=True)
    if previous and previous['status'] == 'failed':
        # 明确失败的操作允许显式重试；记录由本次执行重新核验，不沿用旧失败结论。
        logger.info('显式重试此前失败的导入 operation=%s', operation_id)
    existing = _existing(root, asset_id)
    if (existing is not None and existing.get('sha256') != selection.data.outputArtifact.sha256
            and not replace):
        raise MaterialError('conflict', '作品已有同 ID 但不同字节的素材；如确需替换请使用 --replace', stage='import')
    staging_path = root / STAGING / operation_id
    with locked(root):
        staged, relative = _stage(store, selection, media, root, operation_id)
        manifest['assets'][0]['localPath'] = relative
        store.operation(operation_id, status='pending', payload={
            'selectionId': selection.id, 'project': project['id'], 'assetId': asset_id,
            'staged': relative, 'manifestSha256': fingerprint(manifest),
            'outputSha256': selection.data.outputArtifact.sha256})
        try:
            record = media_assets.import_assets(root, manifest, base=root)
        except (M2VError, OSError) as exc:
            store.operation(operation_id, status='failed', payload={
                'selectionId': selection.id, 'reason': 'import-failed'})
            shutil.rmtree(staging_path, ignore_errors=True)
            raise MaterialError('media-invalid', f'作品导入失败：{exc}；旧登记未被修改', stage='import') from exc
        entry = next((item for item in record['assets'] if item['id'] == asset_id), None)
        if entry is None or entry.get('sha256') != selection.data.outputArtifact.sha256:
            store.operation(operation_id, status='failed', payload={
                'selectionId': selection.id, 'reason': 'verification-failed'})
            shutil.rmtree(staging_path, ignore_errors=True)
            raise MaterialError('hash-mismatch', '作品登记未绑定选中片段的实际字节', stage='import')
        receipt = _receipt(store, selection, media, entry=entry, manifest=manifest,
                           project_id=project['id'], operation_id=operation_id,
                           target_path=entry['path'])
        # 先写作品内凭据，再把操作记为已提交：凭据写失败时可幂等重试而不误报未导入。
        _write_receipt(root, receipt)
        store.operation(operation_id, status='committed', payload={
            'selectionId': selection.id, 'project': project['id'], 'assetId': asset_id,
            'receiptId': receipt.id, 'outputSha256': selection.data.outputArtifact.sha256})
        if staging_path.exists():
            shutil.rmtree(staging_path, ignore_errors=True)
    return ImportResult(receipt, entry)


def verify_project_media(project_root: Path) -> dict:
    """只依赖作品内文件；工作库不可访问时仍可核对，且不读取共享库。"""
    root = no_links(Path(project_root).expanduser().resolve())
    _, project = load_project(root)
    record = media_assets.load_record(root)
    issues, verified = [], 0
    for entry in record['assets']:
        relative = entry.get('path')
        if not isinstance(relative, str):
            issues.append({'id': entry.get('id'), 'reason': 'missing-path'})
            continue
        path = no_links(root / relative)
        if not path.is_file():
            issues.append({'id': entry.get('id'), 'reason': 'not-found', 'path': relative})
            continue
        if digest(path) != entry.get('sha256'):
            issues.append({'id': entry.get('id'), 'reason': 'hash-mismatch', 'path': relative})
            continue
        verified += 1
    return {'projectId': project['id'], 'type': project['type'], 'verified': verified,
            'issues': issues, 'usable': not issues}
