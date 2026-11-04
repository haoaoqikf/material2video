"""DESIGN.md 的唯一可解析合同；不依赖场景源码或 prepared.json。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.core import frames
from m2v.core.video_config import validate_general_fps
from m2v.core.fingerprints import fingerprint

FENCE = re.compile(r'^```m2v-checkpoints\s*\n(.*?)^```\s*$', re.M | re.S)
TIME_PARTS = ('establish', 'pause', 'change', 'reveal', 'result', 'hold')


def fields(value, required: set[str], optional: set[str] = frozenset(), name='合同'):
    if not isinstance(value, dict) or required - value.keys() or value.keys() - required - optional:
        raise M2VError(f'{name} 字段缺失或未知；必需字段：{sorted(required)}')


def frame(value, name='帧'):
    if type(value) is not int or value < 0:
        raise M2VError(f'{name} 必须为非负整数')
    return value


def text(value, name='文本'):
    if not isinstance(value, str) or not value.strip():
        raise M2VError(f'{name} 必须为非空文字')
    return value


def identifier(value):
    text(value, 'ID')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', value):
        raise M2VError('ID 只能包含字母、数字、下划线及连字符，长度最多 96')
    return value


def interval(value, duration):
    if not isinstance(value, list) or len(value) != 2:
        raise M2VError('帧窗必须为 [start, end)')
    begin, end = (frame(v) for v in value)
    if not 0 <= begin < end <= duration:
        raise M2VError(f'非法帧窗：{value} / {duration}')


def expected(value):
    if not isinstance(value, list):
        raise M2VError('可观察断言必须为列表')
    for item in value:
        fields(item, {'role', 'count'}, {'state', 'color', 'visible', 'tolerance'})
        text(item['role'])
        frame(item['count'], '对象数量')
        for key in ('state', 'color'):
            if key in item:
                text(item[key], key)
        if 'visible' in item and type(item['visible']) is not bool:
            raise M2VError('visible 必须为布尔值')
        if 'tolerance' in item:
            frame(item['tolerance'], '计数容差')


def load(root: Path) -> dict:
    try:
        source = (root / 'DESIGN.md').read_text(encoding='utf-8')
        matches = FENCE.findall(source)
        if len(matches) != 1:
            raise M2VError('DESIGN.md 必须包含且仅包含一个 m2v-checkpoints JSON 合同块')
        contract = json.loads(matches[0])
    except (OSError, ValueError) as exc:
        raise M2VError(f'检查点合同不可读：{exc}') from exc
    validate(contract)
    return contract


def validate(c: dict) -> None:
    if not isinstance(c, dict) or type(c.get('version')) is not int or c['version'] != 2:
        raise M2VError('制作合同仅支持 version=2；旧合同须重新编排，不自动迁移或继承通过')
    fields(c, {'version', 'cycleId', 'fps', 'width', 'height', 'reviewPlan', 'scenes'}, {'constraints', 'retrospective'})
    identifier(c['cycleId'])
    if any(type(c[k]) is not int or c[k] <= 0 for k in ('fps', 'width', 'height')):
        raise M2VError('合同 fps/width/height 必须为正整数')
    validate_general_fps(c['fps'], '合同 fps')
    frames.normalize(c['width'], c['height'])
    if 'retrospective' in c and type(c['retrospective']) is not bool:
        raise M2VError('retrospective 必须为布尔值')
    if not isinstance(c['scenes'], list) or not c['scenes']:
        raise M2VError('合同 scenes 不得为空')
    seen, scene_ids, shot_ids = set(), set(), set()
    for scene in c['scenes']:
        fields(scene, {'id', 'durationFrames', 'shots', 'checkpoints'})
        sid = identifier(scene['id'])
        if sid in scene_ids:
            raise M2VError(f'重复场景 ID：{sid}')
        scene_ids.add(sid)
        duration = frame(scene['durationFrames'])
        if not duration or not isinstance(scene['shots'], list) or not scene['shots']:
            raise M2VError('场景时长与 shots 不得为空')
        shots = {}
        for shot in scene['shots']:
            fields(shot, {'id', 'tier', 'window'}, {'timeStructure', 'core'})
            qid = identifier(shot['id'])
            if qid in shot_ids or shot['tier'] not in ('A', 'B', 'C'):
                raise M2VError(f'重复镜头 ID 或非法 tier：{qid}')
            shot_ids.add(qid)
            interval(shot['window'], duration)
            if 'core' in shot and type(shot['core']) is not bool:
                raise M2VError('镜头 core 必须为布尔值')
            if 'timeStructure' in shot:
                fields(shot['timeStructure'], set(), set(TIME_PARTS), name='风险窗时间结构')
                cursor = shot['window'][0]
                for key in TIME_PARTS:
                    if key not in shot['timeStructure']:
                        continue
                    part = shot['timeStructure'][key]
                    fields(part, {'window', 'audience', 'visible', 'attention', 'toleranceFrames', 'failure'},
                           {'notApplicableReason', 'alternative'})
                    if part['window'] is None:
                        if not part.get('notApplicableReason') or not part.get('alternative'):
                            raise M2VError('时间结构不适用须说明原因及替代节奏')
                        continue
                    window = part['window']
                    interval(window, duration)
                    for k in ('audience', 'visible', 'attention', 'failure'):
                        text(part[k])
                    frame(part['toleranceFrames'], '时机容差')
                    if window[0] != cursor:
                        raise M2VError('时间结构必须连续覆盖镜头帧窗')
                    cursor = window[1]
                if cursor != shot['window'][1]:
                    raise M2VError('时间结构未覆盖镜头结尾')
            shots[qid] = shot
        if not isinstance(scene['checkpoints'], list) or not scene['checkpoints']:
            raise M2VError('每个场景必须声明检查点')
        covered = set()
        for cp in scene['checkpoints']:
            fields(cp, {'id', 'shotId', 'frame', 'window', 'expected', 'textPlan', 'claims', 'forbidden'},
                   {'measurement', 'sampleStep', 'minEventFrames', 'manualEvidence', 'statePlan'})
            cid = identifier(cp['id'])
            if cid in seen:
                raise M2VError(f'重复检查点 ID：{cid}')
            seen.add(cid)
            if cp['shotId'] not in shots:
                raise M2VError(f'未知镜头：{cp["shotId"]}')
            shot = shots[cp['shotId']]
            covered.add(cp['shotId'])
            interval(cp['window'], duration)
            n = frame(cp['frame'])
            if not shot['window'][0] <= cp['window'][0] <= n < cp['window'][1] <= shot['window'][1]:
                raise M2VError(f'检查点不在镜头帧窗内：{cid}')
            expected(cp['expected'])
            for key in ('textPlan', 'claims', 'forbidden'):
                if not isinstance(cp[key], list):
                    raise M2VError(f'{key} 必须为列表')
            for item in cp['textPlan']:
                fields(item, {'role', 'text', 'window'})
                text(item['role'])
                text(item['text'])
                interval(item['window'], duration)
            for claim in cp['claims']:
                fields(claim, {'id', 'value', 'unit', 'basis'}, {'role'})
                text(claim['basis'])
                # 同一口径主张必须唯一，避免标题与数量各说各话。
                values = [x['value'] for x in cp['claims'] if x['id'] == claim['id']]
                if any(v != claim['value'] for v in values):
                    raise M2VError(f'定量主张矛盾：{claim["id"]}')
                if claim.get('role'):
                    plans = [p for p in cp['textPlan'] if p['role'] == claim['role']]
                    for plan in plans:
                        numbers = re.findall(r'-?\d+(?:\.\d+)?', plan['text'].replace(',', ''))
                        if isinstance(claim['value'], (int, float)) and not any(float(v) == claim['value'] for v in numbers):
                            raise M2VError(f'文字与定量主张矛盾：{claim["id"]}')
            for key in ('sampleStep', 'minEventFrames'):
                if key in cp and (type(cp[key]) is not int or cp[key] < 1):
                    raise M2VError(f'{key} 必须为正整数')
            plans = cp.get('statePlan', [])
            if not isinstance(plans, list):
                raise M2VError('statePlan 必须为列表')
            by_role = {}
            for plan in plans:
                fields(plan, {'window', 'expected'})
                interval(plan['window'], duration)
                if not shot['window'][0] <= plan['window'][0] < plan['window'][1] <= shot['window'][1]:
                    raise M2VError('状态计划必须位于镜头窗口内')
                expected(plan['expected'])
                if not plan['expected']:
                    raise M2VError('状态计划必须包含断言')
                for item in plan['expected']:
                    windows = by_role.setdefault(item['role'], [])
                    if any(max(a, plan['window'][0]) < min(b, plan['window'][1]) for a, b in windows):
                        raise M2VError('同角色状态计划窗口不得重叠')
                    windows.append(plan['window'])
            if 'measurement' in cp:
                fields(cp['measurement'], set(), {'bodyRoles', 'thresholdSource', 'minFont393',
                       'allowedOverlaps', 'maxTextCharacters', 'subtitleTop', 'subtitleRoles'}, name='量测规则')
                rules = cp['measurement']
                for key in ('minFont393', 'maxTextCharacters', 'subtitleTop'):
                    if key in rules and (type(rules[key]) not in (int, float) or rules[key] < 0):
                        raise M2VError('量测阈值必须为非负数')
                roles = rules.get('subtitleRoles')
                if roles is not None and (not isinstance(roles, list)
                                          or any(not isinstance(value, str) or not value.strip() for value in roles)):
                    raise M2VError('subtitleRoles 必须为非空字符串列表')
            if any(not isinstance(v, str) or not v.strip() for v in cp['forbidden']):
                raise M2VError('禁止项必须为非空文字')
    from .policy import validate_plan
    validate_plan(c)


def checkpoints(c: dict):
    for scene in c['scenes']:
        for cp in scene['checkpoints']:
            shot = next(x for x in scene['shots'] if x['id'] == cp['shotId'])
            yield scene, shot, cp


def scope_digest(c: dict, scene_id: str | None = None, checkpoint_id: str | None = None) -> str:
    selected = []
    for scene, shot, cp in checkpoints(c):
        if (not scene_id or scene['id'] == scene_id) and (not checkpoint_id or cp['id'] == checkpoint_id):
            selected.append({'scene': scene['id'], 'duration': scene['durationFrames'], 'shot': shot, 'checkpoint': cp})
    global_values = {k: v for k, v in c.items() if k not in ('scenes', 'reviewPlan')}
    from .policy import risks
    ids = {item['checkpoint']['id'] for item in selected}
    plan = c['reviewPlan'] if not scene_id and not checkpoint_id else {
        'risks': [risk for risk in risks(c) if ids.intersection(risk['scope']['checkpointIds'])]}
    return fingerprint({'global': global_values, 'plan': plan, 'selected': selected})


def mapping(c: dict, board: dict) -> list[str]:
    failures = []
    actual = {s['id']: s for s in board['scenes']}
    for scene in c['scenes']:
        target = actual.get(scene['id'])
        if not target or target.get('durationFrames') != scene['durationFrames']:
            failures.append(f'场景映射或时长不一致：{scene["id"]}')
    if set(actual) != {s['id'] for s in c['scenes']}:
        failures.append('合同与分镜场景集合不一致')
    for key in ('width', 'height', 'fps'):
        if board.get(key) != c[key]:
            failures.append(f'合同与分镜 {key} 不一致')
    return failures
