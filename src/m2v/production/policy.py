"""制作审核要求的唯一策略；镜头等级与代理人数无关。"""
from __future__ import annotations

from m2v.core.errors import M2VError
from . import contract

RISK_KINDS = {'static-expression', 'structure-timing', 'core-event', 'split-final',
              'substantive-dispute', 'repeated-failure'}
CORE_GATES = {'static-expression': 'G2', 'structure-timing': 'G3', 'core-event': 'G4',
              'substantive-dispute': 'G4', 'repeated-failure': 'G4'}


def risks(c: dict, kind=None) -> list[dict]:
    return [r for r in c['reviewPlan']['risks'] if kind is None or r['kind'] == kind]


def validate_plan(c: dict) -> None:
    plan = c['reviewPlan']
    contract.fields(plan, {'basis', 'risks'}, name='审核计划')
    contract.text(plan['basis'], '适用性依据')
    if not isinstance(plan['risks'], list):
        raise M2VError('reviewPlan.risks 必须为列表')
    points = {cp['id']: shot for _, shot, cp in contract.checkpoints(c)}
    seen = set()
    for risk in plan['risks']:
        contract.fields(risk, {'id', 'kind', 'scope', 'reason', 'requiredEvidence'}, name='审核风险')
        rid = contract.identifier(risk['id'])
        if rid in seen or risk['kind'] not in RISK_KINDS:
            raise M2VError('风险 ID 重复或未知风险类型')
        seen.add(rid)
        contract.text(risk['reason'], '具体风险依据')
        contract.fields(risk['scope'], {'checkpointIds'}, name='风险范围')
        ids = risk['scope']['checkpointIds']
        if (not isinstance(ids, list) or not ids or any(not isinstance(x, str) for x in ids)
                or len(set(ids)) != len(ids) or not set(ids) <= points.keys()):
            raise M2VError('风险必须绑定已声明检查点，不得使用未知或空范围')
        evidence = risk['requiredEvidence']
        if not isinstance(evidence, list) or not evidence:
            raise M2VError('风险必须说明所需证据')
        for value in evidence:
            contract.text(value, '所需证据')
        if risk['kind'] == 'structure-timing' and any(not points[x].get('timeStructure') for x in ids):
            raise M2VError('结构时序风险窗须声明时间结构')


def checkpoint_ids(c: dict, kind: str) -> set[str]:
    return {cid for r in risks(c, kind) for cid in r['scope']['checkpointIds']}


def requirement(c: dict, gate: str, checkpoint_id=None) -> dict:
    relevant = [r for r in risks(c) if CORE_GATES.get(r['kind']) == gate
                and (checkpoint_id is None or checkpoint_id in r['scope']['checkpointIds'])]
    ids = {cid for r in relevant for cid in r['scope']['checkpointIds']}
    if checkpoint_id:
        ids &= {checkpoint_id}
    focuses = ['comprehensive'] if gate in ('G5', 'G6') or relevant else []
    if gate == 'G6' and risks(c, 'split-final'):
        focuses = ['structure', 'visual-copy']
    return {'count': len(focuses), 'focuses': focuses, 'checkpointIds': sorted(ids),
            'risks': [r['id'] for r in relevant],
            'reasons': [r['reason'] for r in (risks(c, 'split-final') if gate == 'G6' else relevant)]}


def round_for(gate: str) -> str:
    return 'final' if gate == 'G6' else 'rough' if gate == 'G5' else 'core'


def rounds(c: dict) -> dict:
    core = any(r['kind'] in CORE_GATES for r in risks(c))
    final = requirement(c, 'G6')['count']
    return {'core': int(core), 'rough': 1, 'final': final, 'defaultCalls': int(core) + 1 + final}
