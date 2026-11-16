"""显式复用完全相同的 trial 视觉观察；当前来源仍由当前包和采集验证。"""
from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from . import ledger, reviews
from .model import fields, identifier, now
from .storage import local, read, receipt, write

logger = logging.getLogger(__name__)
_resolving = ContextVar('visual_reuse_resolving', default=frozenset())


def signature(root, project, pack_path, pack_sha, *, historical=False):
    """排除来源内容和路径偶然性；所有完整媒体、观察条件保持严格相同。"""
    from . import samples

    pack, private = (reviews.historical_package(root, project, pack_path, pack_sha)
                     if historical else reviews.load_package(root, project, pack_path, pack_sha))
    req, binding = private['request'], private['binding']
    if req['round'] != 'trial':
        raise M2VError('视觉复用仅限同周期独立评审')
    return dict(round=req['round'], purpose=req['purpose'], blindReason=req.get('blindReason'),
                fps=req['fps'], displaySizes=sorted(req['displaySizes']),
                sceneIds=req['sceneIds'], sources=samples.scope_sources(root, req),
                conditions=req.get('conditions', []), references=binding['references'],
                items=[{**{k: item[k] for k in ('id', 'window', 'dynamic')},
                        'sha256': media['sha256']}
                       for item, media in zip(req['items'], binding['media'], strict=True)],
                sampleStep=req.get('sampleStep', 1)), pack, private


def _pair(root, project, record):
    blind, comparison = [reviews.sealed_report(root, project, identifier(record[key]), historical=True)
                         for key in ('blindId', 'comparisonId')]
    if (blind['round'] != 'trial' or comparison['round'] != 'trial'
            or blind['reviewType'] != 'blind' or comparison['reviewType'] != 'consistency'
            or comparison.get('blindId') != blind['id']
            or any(r['verdict'] != 'pass' or r['isolation'] != 'independent-subagent'
                   or r['focus'] != 'comprehensive' for r in (blind, comparison))
            or blind['reviewerId'] != comparison['reviewerId']):
        raise M2VError('复用须为原同轮同评审者的 trial 独立双通过')
    current, pack, private = signature(root, project, record['packPath'], record['packSha256'])
    if pack['reviewType'] != 'blind':
        raise M2VError('复用须绑定当前有效盲包')
    for report in (blind, comparison):
        original, _, _ = signature(root, project, report['packPath'], report['packSha256'], historical=True)
        if original != current:
            raise M2VError('完整媒体、观察窗口、目标或显示条件不同，不能复用')
    return blind, comparison, pack, private


def _conflicts(root, project, blind):
    """仅真实独立关闭解除冲突；递归复用同一收据会由 resolve 的栈拒绝。"""
    from . import issues

    original, _, _ = signature(root, project, blind['packPath'], blind['packSha256'], historical=True)
    problems = {item['reportId']: item for item in issues.load(root, required=True, check_closures=False)}
    events, errors = ledger.history(root)
    if errors:
        raise M2VError('; '.join(errors))
    for event in events:
        if event['type'] != 'review':
            continue
        # 所有记录的封存身份均须完好；不能以来源过期跳过同媒体 fail。
        if not ledger.evidence_valid(root, event['data']['receipts']):
            raise M2VError('复用历史评审记录损坏')
        candidate = read(local(outputs(root), event['data']['reportPath']))
        if (candidate['verdict'] != 'fail' or candidate['round'] != 'trial'
                or candidate['isolation'] != 'independent-subagent'
                or candidate['focus'] != blind['focus']):
            continue
        target, _, _ = signature(root, project, candidate['packPath'], candidate['packSha256'], historical=True)
        if target != original:
            continue
        problem = problems.get(candidate['id'])
        if not problem or problem['status'] != 'closed':
            raise M2VError('相同媒体存在未解决独立失败，不能挑选旧 pass 复用')
        issues.validate_closure(root, problem)


def register(root, project, request):
    fields(request, {'version', 'blindId', 'comparisonId', 'packPath', 'packSha256'})
    if type(request['version']) is not int or request['version'] != 1:
        raise M2VError('视觉复用收据须为 version=1')
    blind, _, _, _ = _pair(root, project, request)
    _conflicts(root, project, blind)
    identity = uuid.uuid4().hex
    value = dict(request, id=identity, cycleId=ledger.cycle(root)['cycleId'],
                 projectId=project['id'], createdAt=now())
    path = ledger.directory(root) / 'visual-reuse' / f'{identity}.json'
    write(path, value)
    record = receipt(outputs(root), path)
    ledger.append(root, project, 'visual-reused', data={'receipt': record})
    logger.info('复用 trial 视觉结论 %s；保留原观察时间，未执行新评审', identity)
    return {'id': identity, 'receipt': record, 'blindId': value['blindId'],
            'comparisonId': value['comparisonId'], 'newObservation': False}


def resolve(root, project, report_id):
    """返回原报告与当前观察包；不改变报告身份、原始时间或失败关闭顺序。"""
    identifier(report_id)
    key = (str(root), report_id)
    if key in _resolving.get():
        raise M2VError('视觉复用关闭证据循环依赖，不能授权')
    token = _resolving.set(_resolving.get() | {key})
    try:
        events, errors = ledger.history(root)
        if errors:
            raise M2VError('; '.join(errors))
        for event in reversed(events):
            if event['type'] != 'visual-reused':
                continue
            record_receipt = event['data']['receipt']
            if not ledger.evidence_valid(root, [record_receipt]):
                raise M2VError('视觉复用收据摘要失配')
            value = read(local(outputs(root), record_receipt['path']))
            fields(value, {'version', 'blindId', 'comparisonId', 'packPath', 'packSha256',
                           'id', 'cycleId', 'projectId', 'createdAt'})
            if (value['version'] != 1 or value['cycleId'] != ledger.cycle(root)['cycleId']
                    or value['projectId'] != project['id']):
                raise M2VError('视觉复用收据周期或身份无效')
            if report_id not in (value['blindId'], value['comparisonId']):
                continue
            blind, comparison, pack, private = _pair(root, project, value)
            _conflicts(root, project, blind)
            return (blind if report_id == blind['id'] else comparison), pack, private, record_receipt
        raise M2VError('评审已过期，缺少有效完整媒体视觉复用收据')
    finally:
        _resolving.reset(token)


def has_record(root, report_id):
    events, errors = ledger.history(root)
    if errors:
        raise M2VError('; '.join(errors))
    for event in reversed(events):
        if event['type'] != 'visual-reused':
            continue
        sealed = event['data']['receipt']
        if not ledger.evidence_valid(root, [sealed]):
            raise M2VError('视觉复用收据摘要失配')
        value = read(local(outputs(root), sealed['path']))
        if report_id in (value.get('blindId'), value.get('comparisonId')):
            return True
    return False


def evidence(root, project, report_id):
    """交付等调用方须获得当前包；原报告本体永不改写。"""
    if has_record(root, report_id):
        return resolve(root, project, report_id)
    report = reviews.sealed_report(root, project, report_id)
    pack, private = reviews.load_package(root, project, report['packPath'], report['packSha256'])
    return report, pack, private, None
