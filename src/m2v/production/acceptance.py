"""每轮覆盖凭据：核验范围与来源，不自动判断审美。"""
from __future__ import annotations

from pathlib import Path
from m2v.core.errors import M2VError
from . import contract, policy, media_evidence

DIMENSIONS = ('understanding', 'presentation', 'representativeness')


def validate_assessment(item: dict, *, required=False) -> None:
    """核验分别作出判断，不代替评审者判断美术质量。"""
    assessment = item.get('assessment')
    if assessment is None and not required:
        return
    contract.fields(assessment, set(DIMENSIONS), name='核心 assessment')
    for name in DIMENSIONS:
        value = assessment[name]
        contract.fields(value, {'status', 'observations'}, name=name)
        if value['status'] not in ('pass', 'fail', 'insufficient'):
            raise M2VError('核心判断状态无效')
        contract.text(value['observations'], name + ' 具体观察')
    states = {v['status'] for v in assessment.values()}
    expected = 'fail' if 'fail' in states else 'insufficient' if 'insufficient' in states else 'pass'
    if item['status'] != expected:
        raise M2VError('覆盖状态必须反映理解、表现与代表性，不得合并为通过')


def core_coverage_passed(coverage: list, checkpoint_ids: set[str]) -> bool:
    """历史报告缺少分别判断时只作历史；不能继续授权扩展。"""
    try:
        selected = [item for item in coverage if item['checkpointId'] in checkpoint_ids]
        if {item['checkpointId'] for item in selected} != checkpoint_ids:
            return False
        for item in selected:
            validate_assessment(item, required=True)
            if item['status'] != 'pass':
                return False
        return True
    except (M2VError, KeyError, TypeError):
        return False


def validate(items, c: dict, report: dict, base: Path, evidence_valid) -> list[dict]:
    if not isinstance(items, list) or not items:
        raise M2VError('每轮报告必须有非空 coverage 覆盖表')
    points = {cp['id']: cp for _, _, cp in contract.checkpoints(c)}
    seen, evidence = set(), []
    for item in items:
        contract.fields(item, {'checkpointId', 'window', 'status', 'observations', 'evidence', 'issues'}, {'assessment'})
        cid = item['checkpointId']
        if not isinstance(cid, str) or cid in seen or cid not in points or cid not in report['checkpointIds']:
            raise M2VError('覆盖范围未知、重复或不在评审包内')
        seen.add(cid)
        if item['window'] != points[cid]['window']:
            raise M2VError('覆盖表必须覆盖完整检查窗口')
        if item['status'] not in ('pass', 'fail', 'insufficient'):
            raise M2VError('覆盖状态无效')
        validate_assessment(item, required=report['round'] == 'core' and report['reviewType'] == 'blind'
                            and cid in policy.core_checkpoint_ids(c))
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
    if report.get('gate') == 'G4' and report['round'] == 'core' and report['reviewType'] == 'blind':
        # 只有实际动态核心轮才要求过程片段；同一检查点上绑定的 G2 关键帧等静态轮不探测视频。
        dynamic = policy.checkpoint_ids(c, 'core-event') & seen
        media_evidence.validate(items, c, base, dynamic)
    return evidence
