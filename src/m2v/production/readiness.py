"""从当前制作证据投影扩展资格；不阻断渲染，也不重新采集证据。"""
from __future__ import annotations


def expansion(gates: list[dict], scenes: list[dict], diagnostics: list[str], *, trial_ids=frozenset()) -> list[dict]:
    preparation = [g['gate'] for g in gates if g['gate'] in ('G0', 'G1', 'G2', 'G3')
                   and not g['ready']]
    result = []
    pending = sorted(row['checkpointId'] for row in scenes
                     if row['checkpointId'] in trial_ids and row['evidenceStatus'] != '通过')
    for scene in scenes:
        reasons = [f'全局准备门未完成：{", ".join(preparation)}'] if preparation else []
        if pending:
            reasons.append(f'试制独立验证未完成：{", ".join(pending)}')
        if scene['evidenceStatus'] != '通过':
            reasons.append(f'G4 {scene["evidenceStatus"]}')
        reasons.extend(scene['missingAcceptance'])
        reasons.extend(f'必改项未关闭：{issue}' for issue in scene['issues'])
        if diagnostics:
            reasons.append('制作记录或证据存在诊断错误')
        result.append({'sceneId': scene['sceneId'], 'checkpointId': scene['checkpointId'],
                       'allowed': not reasons, 'reasons': reasons})
    return result


def summary(result: dict) -> str:
    complete = result['production'].get('complete', False)
    if result.get('candidate', {}).get('status') == 'delivered':
        return '候选已生成，制作复核完成' if complete else '候选已生成，制作未完成'
    return '制作证据已齐，候选尚未交付' if complete else '制作未完成，候选尚未交付'
