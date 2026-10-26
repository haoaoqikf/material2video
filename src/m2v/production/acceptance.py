"""每轮覆盖凭据：核验范围与来源，不自动判断审美。"""
from __future__ import annotations

from pathlib import Path
from m2v.core.errors import M2VError
from . import contract, policy


def validate(items, c: dict, report: dict, base: Path, evidence_valid) -> list[dict]:
    if not isinstance(items, list) or not items:
        raise M2VError('每轮报告必须有非空 coverage 覆盖表')
    points = {cp['id']: cp for _, _, cp in contract.checkpoints(c)}
    seen, evidence = set(), []
    for item in items:
        contract.fields(item, {'checkpointId', 'window', 'status', 'observations', 'evidence', 'issues'})
        cid = item['checkpointId']
        if not isinstance(cid, str) or cid in seen or cid not in points or cid not in report['checkpointIds']:
            raise M2VError('覆盖范围未知、重复或不在评审包内')
        seen.add(cid)
        if item['window'] != points[cid]['window']:
            raise M2VError('覆盖表必须覆盖完整检查窗口')
        if item['status'] not in ('pass', 'fail', 'insufficient'):
            raise M2VError('覆盖状态无效')
        contract.text(item['observations'], '具体观察')
        if not isinstance(item['issues'], list) or any(not isinstance(x, str) or not x.strip() for x in item['issues']):
            raise M2VError('覆盖问题 ID 必须为文字列表')
        if not evidence_valid(base, item['evidence']):
            raise M2VError('覆盖证据缺失或摘要失配')
        if report['verdict'] == 'pass' and item['status'] != 'pass':
            raise M2VError('通过报告含失败或证据不足的覆盖项')
        evidence.extend(item['evidence'])
    if seen != set(report['checkpointIds']):
        raise M2VError('覆盖表与报告范围不一致')
    if report['round'] in ('rough', 'final'):
        required = set(points) if report['reviewType'] == 'blind' else policy.checkpoint_ids(c, 'static-expression')
        if not required <= seen:
            raise M2VError('全片或目标图对照报告缺少必要覆盖')
    if report['round'] == 'core' and report['reviewType'] == 'blind':
        dynamic = policy.checkpoint_ids(c, 'core-event') & seen
        for item in items:
            if item['checkpointId'] in dynamic and not any(
                    Path(e['path']).suffix.lower() in ('.mp4', '.webm') for e in item['evidence']):
                raise M2VError('动态核心需要完整过程片段，端点静帧不足')
    return evidence
