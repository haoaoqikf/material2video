"""制作门的有序定义；执行和文档投影共用，状态计算仍属于 ledger。"""
from __future__ import annotations

from dataclasses import dataclass

from m2v.core.errors import M2VError


@dataclass(frozen=True)
class Gate:
    id: str
    phase: str
    scope: str
    checker: str | None
    evidence: str
    review_round: str


GATES = (
    Gate('G0', '方案确定', 'project', None, '当前输入、事实与许可审查及不适用项', 'core'),
    Gate('G1', '方案确定', 'project', 'declaration', 'v2 合同、审核计划与设计声明一致性', 'core'),
    Gate('G2', '方案确定', 'project', 'design', '适用风险的独立目标关键帧及观察', 'core'),
    Gate('G3', '方案确定', 'project', 'mapping', '分镜映射自动检查；适用风险的 animatic 观察', 'core'),
    Gate('G4', '制作与迭代', 'checkpoint', 'capture', '每场检查点断言、量测与状态边界；完整试制窗固定独立盲审后再扩展', 'core'),
    Gate('G5', '制作与迭代', 'project', 'internal', '制作助手的全片内部粗片检查，覆盖结构、衔接、节奏与已知风险', 'internal'),
    Gate('G6', '最终验收', 'project', None, '当前候选技术 QA、完整全片证据与计划要求的终审', 'final'),
)
GATE_IDS = tuple(g.id for g in GATES)
_BY_ID = {g.id: g for g in GATES}


def gate(gate_id: str) -> Gate:
    try:
        return _BY_ID[gate_id]
    except KeyError as exc:
        raise M2VError(f"未知制作门：{gate_id}") from exc


def prerequisites(gate_id: str) -> tuple[str, ...]:
    """当前契约按门序推进，返回全部前置门。"""
    return GATE_IDS[:GATE_IDS.index(gate_id)]


def phase(current_gate: str | None) -> str:
    return gate(current_gate).phase if current_gate else '最终验收'
