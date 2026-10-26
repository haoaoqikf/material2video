"""表达检查的结构完整性；只验证覆盖和来源，不自动判断审美。"""
from __future__ import annotations

from m2v.core.errors import M2VError
from . import contract

DIMENSIONS = {'composition-scale', 'spatial-hierarchy', 'impact', 'attention', 'timing'}
STATES = {'pass', 'fail', 'insufficient'}


def required(c: dict, gate: str, checkpoint_id=None) -> set[tuple[str, str]]:
    if not c.get('acceptanceChecks') or gate not in ('G4', 'G6'):
        return set()
    kind = 'visual-event' if gate == 'G4' else 'design-fulfillment'
    return {(cp['id'], kind) for _, shot, cp in contract.checkpoints(c)
            if (shot['tier'] == 'A' or shot.get('core')) and
            (checkpoint_id is None or cp['id'] == checkpoint_id)}


def validate(items, c: dict, report: dict, base, evidence_valid) -> list[dict]:
    """导入前核对覆盖和全部证据，先完整验证再追加任何事件。"""
    if not isinstance(items, list):
        raise M2VError('acceptance 必须为列表')
    points = {cp['id']: cp for _, _, cp in contract.checkpoints(c)}
    seen, evidence = set(), []
    for item in items:
        contract.fields(item, {'checkpointId', 'kind', 'window', 'status', 'observations', 'evidence'},
                        {'dimensions', 'design'})
        for field in ('checkpointId', 'kind', 'status'):
            contract.text(item[field], field)
        key = (item['checkpointId'], item['kind'])
        if key in seen or key[0] not in points or key[0] not in report['checkpointIds']:
            raise M2VError('完成凭据重复或未绑定当前检查点')
        seen.add(key)
        if item['status'] not in STATES:
            raise M2VError('完成凭据状态无效')
        contract.text(item['observations'], '实际观察')
        if item['window'] != points[key[0]]['window']:
            raise M2VError('完成凭据须覆盖完整检查窗')
        if item['kind'] == 'visual-event':
            if report['gate'] not in ('G4', 'G5') or report['reviewType'] != 'blind':
                raise M2VError('visual-event 必须来自 G4/G5 独立盲审视图')
        elif item['kind'] == 'design-fulfillment':
            if report['gate'] != 'G6' or report['reviewType'] != 'consistency':
                raise M2VError('design-fulfillment 必须来自 G6 隔离对照视图')
            dimensions = item.get('dimensions', {})
            contract.fields(dimensions, DIMENSIONS, name='设计兑现五维')
            for value in dimensions.values():
                contract.fields(value, {'status', 'observations'})
                if not isinstance(value['status'], str) or value['status'] not in STATES:
                    raise M2VError('兑现维度状态无效')
                contract.text(value['observations'])
            states = {value['status'] for value in dimensions.values()}
            aggregate = 'fail' if 'fail' in states else 'insufficient' if 'insufficient' in states else 'pass'
            if item['status'] != aggregate:
                raise M2VError('兑现总状态必须与五维结果一致')
            design = item.get('design', {})
            contract.fields(design, {'direction', 'keyframes', 'animation'}, name='三方对照来源')
            for entries in design.values():
                if not evidence_valid(base, entries):
                    raise M2VError('三方对照来源缺失或过期')
                evidence.extend(entries)
        else:
            raise M2VError('未知完成凭据类型')
        if not evidence_valid(base, item['evidence']):
            raise M2VError('完成凭据证据缺失或过期')
        if report['verdict'] == 'pass' and item['status'] != 'pass':
            raise M2VError('报告通过与完成凭据状态矛盾')
        evidence.extend(item['evidence'])
    return evidence


def coverage(c: dict, gate: str, checkpoint_id, reviews: list[dict]) -> tuple[list[str], bool]:
    needed = required(c, gate, checkpoint_id)
    latest, by_reviewer = {}, {}
    for event in reviews:
        data = event['data']
        by_reviewer[(data.get('reviewerId'), data.get('reviewType'))] = event
    for event in by_reviewer.values():
        data = event['data']
        if data.get('isolation') != 'independent-subagent':
            continue
        for item in data.get('acceptance', []):
            key = (item['checkpointId'], item['kind'])
            latest[(data['reviewerId'], key)] = item
    failed = any(item['status'] == 'fail' for (_, key), item in latest.items() if key in needed)
    passed = {key for (_, key), item in latest.items() if item['status'] == 'pass'}
    return [f'{cid}:{kind}' for cid, kind in sorted(needed - passed)], failed
