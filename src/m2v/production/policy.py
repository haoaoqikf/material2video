"""制作审核要求的唯一策略；镜头等级与代理人数无关。"""
from __future__ import annotations

from dataclasses import dataclass

from m2v.core.errors import M2VError
from . import contract, workflow


@dataclass(frozen=True)
class Risk:
    kind: str
    gate: str
    evidence: str
    excluded: str
    final_focuses: tuple[str, ...] = ()


RISK_CATALOG = (
    Risk('static-expression', 'G2', '独立目标关键帧与盲看；实际 G4 核心窗须同轮目标对照', '只是 A 级标签、普通标题或已验证布局'),
    Risk('structure-timing', 'G3', '风险 animatic 或当前实际片段的时序观察；关键运动窗口须加密证据，可与核心样片同轮', '仅因片中有动画或 A 级镜头'),
    Risk('core-event', 'G4', '完整动态窗口；静帧不能替代', '无实质动态风险的静态作品'),
    Risk('split-final', 'G6', '两名新且互相隔离的终审代理，分别负责结构与视觉文案', '时长、镜头等级或主观追求更高级本身', ('structure', 'visual-copy')),
    Risk('substantive-dispute', 'G4', '新代理先盲看，再核对中性原条件，单独保留争议结论', '纯审美偏好差异'),
    Risk('repeated-failure', 'G4', '至少两个实质不同的匿名候选，包含删短、重排或替换机制', '第一次重要返工'),
)
RISK_KINDS = frozenset(r.kind for r in RISK_CATALOG)
CORE_GATES = {r.kind: r.gate for r in RISK_CATALOG if workflow.gate(r.gate).review_round == 'core'}
DEFAULT_FOCUSES = ('comprehensive',)


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


def core_checkpoint_ids(c: dict) -> set[str]:
    return {cid for r in risks(c) if r['kind'] in CORE_GATES for cid in r['scope']['checkpointIds']}


def consistency_ids(c: dict, gate: str, checkpoint_id=None) -> set[str]:
    """目标图通过不等于实际片段兑现；仅在实际核心窗与终审要求配对。"""
    targets = checkpoint_ids(c, 'static-expression')
    if gate == 'G6':
        return targets
    if gate == 'G4':
        return targets & core_checkpoint_ids(c) & ({checkpoint_id} if checkpoint_id else targets)
    return set()


def requirement(c: dict, gate: str, checkpoint_id=None) -> dict:
    relevant = [r for r in risks(c) if (CORE_GATES.get(r['kind']) == gate
                or (gate == 'G4' and r['kind'] == 'static-expression'))
                and (checkpoint_id is None or checkpoint_id in r['scope']['checkpointIds'])]
    ids = {cid for r in relevant for cid in r['scope']['checkpointIds']}
    if checkpoint_id:
        ids &= {checkpoint_id}
    focuses = list(DEFAULT_FOCUSES) if workflow.gate(gate).review_round == 'final' or relevant else []
    for risk in RISK_CATALOG:
        if risk.gate == gate and risk.final_focuses and risks(c, risk.kind):
            focuses = list(risk.final_focuses)
    return {'count': len(focuses), 'focuses': focuses, 'checkpointIds': sorted(ids),
            'risks': [r['id'] for r in relevant],
            'reasons': [r['reason'] for r in (risks(c, 'split-final') if gate == 'G6' else relevant)]}


def round_for(gate: str) -> str:
    return workflow.gate(gate).review_round


def rounds(c: dict) -> dict:
    core = any(r['kind'] in CORE_GATES for r in risks(c))
    final = requirement(c, 'G6')['count']
    return {'core': int(core), 'rough': 0, 'final': final, 'defaultCalls': int(core) + final}
