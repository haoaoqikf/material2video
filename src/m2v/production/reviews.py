"""隔离包与每轮报告；先完整校验，再绑定多个门的证据。"""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from . import workflow, acceptance, contract, ledger, policy, dependencies, media_evidence
from .dependencies import digest
from .storage import local, read, receipt, write

KINDS = {'design-keyframe', 'animatic', 'scene-window', 'rough-timeline', 'final-video'}
EXCLUDED = ['DESIGN.md', 'storyboard.json', 'scenes/', 'visual-notes.md', 'style-reference.md', 'old-verdicts', 'anonymous-key']


def package(root: Path, *, gate: str, scene_id, checkpoint_ids: list[str], files: list[str],
            kind: str, display_sizes: list, review_type='blind', timecodes=None, blind_id=None) -> Path:
    if gate not in workflow.GATE_IDS or kind not in KINDS or review_type not in ('blind', 'consistency'):
        raise M2VError('评审门、证据类型或评审类型无效')
    c = contract.load(root)
    known = {cp['id'] for _, _, cp in contract.checkpoints(c)}
    if not files or not checkpoint_ids or not set(checkpoint_ids) <= known:
        raise M2VError('评审包缺证据或检查点绑定无效')
    base = outputs(root)
    if review_type == 'consistency':
        events, diagnostics = ledger.history(root)
        prior = [e for e in events if e['type'] == 'review' and e['upstream'].get('cycle') == c['cycleId']
                 and e['data'].get('reportId') == blind_id and e['data'].get('reviewType') == 'blind'
                 and ledger.evidence_valid(root, e['evidence'])]
        if diagnostics or not prior:
            raise M2VError('对照包必须在本轮独立盲审落盘导入之后创建，需 blind_id')
    sources = [local(base, f) for f in files]
    # 对照只接收目标媒体；中性条件投影由工具生成，不复制任意设计说明。
    allowed = {'.png', '.jpg', '.jpeg', '.webp', '.mp4', '.webm', '.wav', '.mp3'}
    if any(p.suffix.lower() not in allowed for p in sources):
        raise M2VError('评审只接受中性媒体证据；不复制任意 HTML、设计文档或源码')
    identifier = uuid.uuid4().hex
    target = base / 'review-pack' / identifier
    target.mkdir(parents=True)
    entries = []
    for index, source in enumerate(sources):
        path = target / f'evidence-{index:04d}{source.suffix.lower()}'
        from .checks import ffmpeg
        if source.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
            ffmpeg(['-i', str(source), '-map_metadata', '-1', '-frames:v', '1', str(path)])
        else:
            ffmpeg(['-i', str(source), '-map_metadata', '-1', '-map_chapters', '-1', '-c', 'copy', str(path)])
        entries.append(receipt(target, path))
    manifest = dict(reviewId=identifier, cycleId=c['cycleId'], createdAt=ledger.now(), gate=gate, sceneId=scene_id,
                    checkpointIds=checkpoint_ids, scope='scene' if scene_id else 'whole-film', evidenceType=kind,
                    reviewType=review_type, displaySizes=display_sizes, timecodes=timecodes or [],
                    files=entries, excluded=EXCLUDED, blindId=blind_id)
    if review_type == 'consistency':
        projection = target / 'conditions.json'
        write(projection, [{'checkpointId': cp['id'], 'window': cp['window'], 'expected': cp['expected'],
                            'textPlan': cp['textPlan']} for _, _, cp in contract.checkpoints(c) if cp['id'] in checkpoint_ids])
        entries.append(receipt(target, projection))
    questions = target / 'questions.md'
    questions.write_text('只读取本目录。按时间顺序先记录实际看到的内容、变化与理解，再判断表现、可读性和证据不足。\n'
                         '不能确认帧间运动或听感时如实限定覆盖，不用作者意图补全画面。\n'
                         '核心风险覆盖项须分别判断 understanding、presentation、representativeness，'
                         '每项写 status 与 observations；占位证据不能授权正式视觉实现。\n', encoding='utf-8')
    entries.append(receipt(target, questions))
    write(target / 'manifest.json', manifest)
    return target


def _invocation(base: Path, report: dict, pack_path: Path, pack: dict) -> dict:
    entry = report['invocation']
    if not ledger.evidence_valid_at(base, [entry]):
        raise M2VError('缺少有效独立调用记录')
    invocation = read(local(base, entry['path']))
    contract.fields(invocation, {'id', 'reviewerId', 'freshContext', 'startedAt', 'completedAt', 'inputPaths', 'readReportIds'})
    for name in ('id', 'reviewerId'):
        contract.text(invocation[name], name)
    if invocation['reviewerId'] != report['reviewerId']:
        raise M2VError('调用身份与评审者不一致')
    if report['isolation'] == 'independent-subagent' and invocation['freshContext'] is not True:
        raise M2VError('独立代理必须使用新建上下文')
    try:
        start, end = [datetime.fromisoformat(invocation[k].replace('Z', '+00:00')) for k in ('startedAt', 'completedAt')]
        created = datetime.fromisoformat(pack['createdAt'].replace('Z', '+00:00'))
        if not start.tzinfo or not end.tzinfo or not created.tzinfo or not created <= start <= end:
            raise ValueError('调用时间早于包或顺序错误')
    except (ValueError, TypeError, AttributeError) as exc:
        raise M2VError('调用时间必须为有时区的有效时间，且包先于调用') from exc
    inputs = invocation['inputPaths']
    if (not isinstance(inputs, list) or not inputs or
            any(not isinstance(p, str) or not local(base, p).is_relative_to(pack_path.parent) for p in inputs)):
        raise M2VError('独立调用输入必须来自当前隔离包')
    read_ids = invocation['readReportIds']
    if not isinstance(read_ids, list) or read_ids != ([] if report['reviewType'] == 'blind' else [pack['blindId']]):
        raise M2VError('盲审不得读旧报告；对照只能读同一轮自身盲看记录')
    return invocation


def import_report(root: Path, manifest: dict, report_path: Path) -> dict:
    with dependencies.snapshot(), media_evidence.snapshot():
        return _import_report(root, manifest, report_path)


def _import_report(root: Path, manifest: dict, report_path: Path) -> dict:
    report = read(report_path)
    contract.fields(report, {'gate', 'round', 'roundId', 'sceneId', 'checkpointIds', 'packPath', 'packSha256', 'reviewerId',
                            'isolation', 'reviewType', 'verdict', 'observations', 'checkIds', 'focus', 'coverage', 'invocation'})
    if (report['gate'] not in workflow.GATE_IDS or report['verdict'] not in ('pass', 'fail', 'insufficient') or
            report['round'] not in ('core', 'rough', 'final') or report['reviewType'] not in ('blind', 'consistency') or
            report['isolation'] not in ('independent-subagent', 'external-review', 'self-review')):
        raise M2VError('评审轮次、结论或隔离方式无效')
    for key in ('roundId', 'reviewerId'):
        contract.identifier(report[key])
    if not isinstance(report['observations'], list) or not report['observations']:
        raise M2VError('评审必须有具体观察')
    for observation in report['observations']:
        contract.text(observation, '观察')
    for key in ('checkpointIds', 'checkIds'):
        values = report[key]
        if (not isinstance(values, list) or not values or any(not isinstance(x, str) for x in values)
                or len(set(values)) != len(values)):
            raise M2VError('评审覆盖与检查 ID 必须为非空不重复列表')
    base = outputs(root)
    report_id = digest(report_path)
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
    if pack['cycleId'] != c['cycleId']:
        raise M2VError('旧制作周期不能授权当前候选')
    invocation = _invocation(base, report, pack_path, pack)
    events, diagnostics = ledger.history(root)
    if diagnostics:
        raise M2VError('; '.join(diagnostics))
    events = [e for e in events if e['upstream'].get('cycle') == c['cycleId']]
    earlier = [e for e in events if e['type'] == 'review' and e['data'].get('reportId') != report_id]
    if report['round'] == 'final':
        if any(e['data'].get('reviewerId') == report['reviewerId'] and e['data'].get('round') != 'final' for e in earlier):
            raise M2VError('终审须使用未参与该作品前期评审的新代理')
        if report['focus'] not in policy.requirement(c, 'G6')['focuses']:
            raise M2VError('最终职责与当前审核计划不一致')
    elif report['focus'] != 'comprehensive':
        raise M2VError('核心与粗片轮使用综合职责')
    if report['reviewType'] == 'consistency':
        prior = [e for e in earlier if e['data'].get('reportId') == pack.get('blindId')
                 and e['data'].get('reviewType') == 'blind' and e['data'].get('reviewerId') == report['reviewerId']
                 and e['data'].get('roundId') == report['roundId'] and e['data'].get('round') == report['round']
                 and e['data'].get('isolation') == report['isolation']
                 and e['data'].get('checkId') in report['checkIds']
                 and ledger.evidence_valid(root, e['evidence'])]
        if not prior or any(e['time'] >= pack['createdAt'] for e in prior):
            raise M2VError('对照须在同一代理本轮独立盲看落盘后创建并绑定')
        if {e['data']['checkId'] for e in prior} != set(report['checkIds']):
            raise M2VError('对照必须绑定同轮盲审的相同检查事件')
    coverage_evidence = acceptance.validate(report['coverage'], c, report, base, ledger.evidence_valid_at)
    allowed_evidence = {receipt(base, local(pack_path.parent, e['path']))['path'] for e in pack['files']}
    if any(e['path'] not in allowed_evidence for e in coverage_evidence):
        raise M2VError('覆盖引用必须来自投喂评审包，不能引用未观看证据')
    bound = []
    for check_id in report['checkIds']:
        check = next((e for e in events if e['id'] == check_id and e['type'] == 'check'), None)
        if not check or policy.round_for(check['gate']) != report['round']:
            raise M2VError('评审引用未知检查或跨轮绑定')
        if check['gate'] in ('G0', 'G1'):
            raise M2VError('事实与合同自动检查不登记审美通过')
        if report['sceneId'] is not None and check['sceneId'] is not None and report['sceneId'] != check['sceneId']:
            raise M2VError('评审场景范围不匹配')
        required = policy.requirement(c, check['gate'], check['checkpointId'])['checkpointIds']
        if check['checkpointId']:
            required = [check['checkpointId']]
        if not set(required) <= set(report['checkpointIds']):
            raise M2VError('报告未覆盖被绑定门的必要检查点')
        current = ledger.upstream(root, c, check['gate'], check['sceneId'], check['checkpointId'])
        if current != check['upstream'] or not ledger.evidence_valid(root, check['evidence']):
            raise M2VError('评审绑定检查已过期')
        bound.append(check)
    # 同一调用只能代表同一观察者，不能复制ID伪装第二名终审。
    if any(e['data'].get('invocationId') == invocation['id'] and e['data'].get('reviewerId') != report['reviewerId'] for e in earlier):
        raise M2VError('同一独立调用不能作为多个评审者')
    if report['round'] == 'final' and 'video' not in bound[0]['upstream']:
        raise M2VError('最终审查必须绑定实际当前候选')
    evidence = [receipt(base, report_path), receipt(base, pack_path), report['invocation'],
                *[receipt(base, local(pack_path.parent, e['path'])) for e in pack['files']], *coverage_evidence]
    results = []
    for check in bound:
        data = {k: report[k] for k in ('reviewerId', 'isolation', 'reviewType', 'verdict', 'focus', 'round', 'roundId')}
        data.update(checkId=check['id'], reportId=report_id, invocationId=invocation['id'],
                    blindId=pack.get('blindId'), coverage=report['coverage'])
        results.append(ledger.append(root, manifest, 'review', gate=check['gate'], scene_id=check['sceneId'],
            checkpoint_id=check['checkpointId'], upstream=check['upstream'], evidence=evidence,
            data=data, event_id=report_id + '-' + check['id']))
    if report['verdict'] == 'fail':
        from . import issues
        # 每轮只登记一次问题，细项覆盖表保留代理自己的问题ID。
        identifier = 'REVIEW-' + report['roundId'] + '-' + report['reviewerId']
        check = bound[0]
        issues.update(root, {'id': identifier, 'status': 'open', 'required': True, 'gate': check['gate'],
            'sceneId': report['sceneId'], 'checkpointId': report['checkpointIds'][0] if len(report['checkpointIds']) == 1 else None,
            'caughtAt': report['gate'],
            'catchableAt': check['gate'], 'evidence': [], 'versionRefs': []})
        notes = base / 'visual-notes.md'
        marker = '\n### ' + identifier + '\n'
        if marker not in notes.read_text(encoding='utf-8'):
            with notes.open('a', encoding='utf-8') as stream:
                stream.write(marker + '\n' + '\n'.join(report['observations']) + '\n')
    return {'events': [e['id'] for e in results]}
