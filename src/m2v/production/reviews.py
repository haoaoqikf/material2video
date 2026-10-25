"""分门隔离评审包和独立结论导入，不自动生成审美结论。"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from m2v.core.delivery import digest, outputs
from m2v.core.errors import M2VError
from . import contract, ledger
from .storage import local, read, receipt, write

KINDS = {'design-keyframe', 'animatic', 'scene-window', 'rough-timeline', 'final-video'}
EXCLUDED = ['DESIGN.md', 'storyboard.json', 'scenes/', 'visual-notes.md', 'style-reference.md', 'old-verdicts', 'anonymous-key']


def package(root: Path, *, gate: str, scene_id, checkpoint_ids: list[str], files: list[str],
            kind: str, display_sizes: list, review_type='blind', timecodes=None) -> Path:
    if gate not in ledger.GATES or kind not in KINDS or review_type not in ('blind', 'consistency'):
        raise M2VError('评审门、证据类型或评审类型无效')
    c = contract.load(root)
    known = {cp['id'] for _, _, cp in contract.checkpoints(c)}
    if not files or not checkpoint_ids or not set(checkpoint_ids) <= known:
        raise M2VError('评审包缺证据或检查点绑定无效')
    base = outputs(root)
    sources = [local(base, f) for f in files]
    allowed = {'.png', '.jpg', '.jpeg', '.webp', '.mp4', '.webm', '.wav', '.mp3'}
    if review_type == 'consistency':
        allowed |= {'.json', '.md'}
    if any(p.suffix.lower() not in allowed for p in sources):
        raise M2VError('盲审只接受中性媒体证据；时间线依赖须展开为媒体，不复制任意 HTML/源码')
    identifier = uuid.uuid4().hex
    target = base / 'review-pack' / identifier
    target.mkdir(parents=True)
    entries = []
    for index, source in enumerate(sources):
        path = target / f'evidence-{index:04d}{source.suffix.lower()}'
        if source.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
            from .checks import ffmpeg
            ffmpeg(['-i', str(source), '-map_metadata', '-1', '-frames:v', '1', str(path)])
        elif source.suffix.lower() in {'.mp4', '.webm', '.wav', '.mp3'}:
            from .checks import ffmpeg
            ffmpeg(['-i', str(source), '-map_metadata', '-1', '-map_chapters', '-1', '-c', 'copy', str(path)])
        else:
            shutil.copyfile(source, path)
        entries.append(receipt(target, path))
    manifest = dict(reviewId=identifier, gate=gate, sceneId=scene_id, checkpointIds=checkpoint_ids,
                    scope='scene' if scene_id else 'whole-film', evidenceType=kind, reviewType=review_type,
                    displaySizes=display_sizes, timecodes=timecodes or [], files=entries, excluded=EXCLUDED)
    if review_type == 'consistency':
        projection = target / 'contract-scope.json'
        write(projection, [{'sceneId': s['id'], 'shot': q, 'checkpoint': cp}
                           for s, q, cp in contract.checkpoints(c) if cp['id'] in checkpoint_ids])
        entries.append(receipt(target, projection))
    write(target / 'manifest.json', manifest)
    (target / 'questions.md').write_text('只读取本目录。先描述看到的内容与变化，再记录理解、表现、可读性及证据不足。\n不得读取包外设计或旧结论。不能确认连续运动时明确记录证据不足。\n', encoding='utf-8')
    return target


def import_report(root: Path, manifest: dict, report_path: Path) -> dict:
    report = read(report_path)
    contract.fields(report, {'gate', 'sceneId', 'checkpointIds', 'packPath', 'packSha256', 'reviewerId',
                            'isolation', 'reviewType', 'verdict', 'observations', 'checkIds'}, {'focus'})
    if report['gate'] not in ledger.GATES or report['verdict'] not in ('pass', 'fail', 'insufficient'):
        raise M2VError('评审结论无效')
    if not report['observations'] or not report['reviewerId'] or report['reviewType'] not in ('blind', 'consistency'):
        raise M2VError('评审缺观察或身份')
    if not isinstance(report['checkpointIds'], list) or not isinstance(report['checkIds'], list) or not report['checkpointIds']:
        raise M2VError('评审覆盖范围与检查 ID 必须为非空列表')
    if report['gate'] == 'G6' and report.get('focus') not in ('structure', 'visual-copy'):
        raise M2VError('G6 必须声明 structure 或 visual-copy 隔离终审职责')
    base = outputs(root)
    pack_path = local(base, report['packPath'])
    if digest(pack_path) != report['packSha256']:
        raise M2VError('评审包摘要不匹配')
    pack = read(pack_path)
    for key in ('gate', 'sceneId', 'checkpointIds', 'reviewType'):
        if pack[key] != report[key]:
            raise M2VError(f'评审包绑定不一致：{key}')
    if not ledger.evidence_valid_at(pack_path.parent, pack['files']):
        raise M2VError('评审包媒体已变化')
    c = contract.load(root)
    events, diagnostics = ledger.history(root)
    if diagnostics:
        raise M2VError('; '.join(diagnostics))
    results = []
    for check_id in report['checkIds']:
        check = next((e for e in events if e['id'] == check_id and e['type'] == 'check'), None)
        if not check or not (check['gate'] == report['gate'] or (check['gate'] == 'G4' and report['gate'] == 'G5')):
            raise M2VError('评审引用未知检查，或门不匹配')
        if report['sceneId'] is not None and report['sceneId'] != check['sceneId']:
            raise M2VError('评审场景范围不匹配')
        if check['checkpointId'] and check['checkpointId'] not in report['checkpointIds']:
            raise M2VError('批量报告未覆盖检查点')
        current = ledger.upstream(root, c, check['gate'], check['sceneId'], check['checkpointId'])
        if current != check['upstream'] or not ledger.evidence_valid(root, check['evidence']):
            raise M2VError('评审绑定的检查已过期')
        results.append(ledger.append(root, manifest, 'review', gate=check['gate'], scene_id=check['sceneId'],
            checkpoint_id=check['checkpointId'], upstream=current,
            evidence=[receipt(base, report_path), receipt(base, pack_path),
                      *[receipt(base, local(pack_path.parent, e['path'])) for e in pack['files']]],
            data={**{k: report[k] for k in ('reviewerId', 'isolation', 'reviewType', 'verdict', 'focus') if k in report}, 'checkId': check_id},
            event_id=digest(report_path) + '-' + check_id))
        if report['verdict'] == 'fail':
            from . import issues
            identifier = 'REVIEW-' + check_id
            issues.update(root, {'id': identifier, 'status': 'open', 'required': True,
                'gate': check['gate'], 'sceneId': check['sceneId'], 'checkpointId': check['checkpointId'],
                'caughtAt': report['gate'], 'catchableAt': check['gate'], 'evidence': [], 'versionRefs': []})
            with (base / 'visual-notes.md').open('a', encoding='utf-8') as stream:
                stream.write('\n### ' + identifier + '\n\n' + str(report['observations']) + '\n')
    if not results:
        raise M2VError('评审必须绑定至少一个检查事件')
    return {'events': [e['id'] for e in results]}
