"""DESIGN.md 的唯一可解析合同；不依赖场景源码或 prepared.json。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from m2v.core.errors import M2VError
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
    fields(c, {'version', 'fps', 'width', 'height', 'structureRisk', 'scenes'}, {'constraints', 'retrospective'})
    if type(c['version']) is not int or c['version'] != 1 or type(c['structureRisk']) is not bool:
        raise M2VError('合同 version 必须为 1，structureRisk 必须为布尔值')
    if any(type(c[k]) is not int or c[k] <= 0 for k in ('fps', 'width', 'height')):
        raise M2VError('合同 fps/width/height 必须为正整数')
    if c['fps'] not in (30, 60) or (c['width'], c['height']) not in ((1920,1080),(1080,1920)):
        raise M2VError('合同画幅与帧率必须使用当前 general 契约')
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
            if shot['tier'] == 'A':
                fields(shot.get('timeStructure'), set(TIME_PARTS), name='A 级时间结构')
                cursor = shot['window'][0]
                for key in TIME_PARTS:
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
                        raise M2VError('A 级时间结构必须连续覆盖镜头帧窗')
                    cursor = window[1]
                if cursor != shot['window'][1]:
                    raise M2VError('A 级时间结构未覆盖镜头结尾')
            shots[qid] = shot
        if not isinstance(scene['checkpoints'], list) or not scene['checkpoints']:
            raise M2VError('每个场景必须声明检查点')
        covered = set()
        for cp in scene['checkpoints']:
            fields(cp, {'id', 'shotId', 'frame', 'window', 'expected', 'textPlan', 'claims', 'forbidden'},
                   {'measurement', 'sampleStep', 'minEventFrames', 'manualEvidence'})
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
            if not isinstance(cp['expected'], list) or not cp['expected']:
                raise M2VError('检查点必须包含可观察断言')
            for item in cp['expected']:
                fields(item, {'role', 'count'}, {'state', 'color', 'visible', 'tolerance'})
                text(item['role'])
                frame(item['count'], '对象数量')
                if 'visible' in item and type(item['visible']) is not bool:
                    raise M2VError('visible 必须为布尔值')
                if 'tolerance' in item:
                    frame(item['tolerance'], '计数容差')
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
            if 'measurement' in cp:
                fields(cp['measurement'], set(), {'bodyRoles', 'thresholdSource', 'minFont393',
                       'allowedOverlaps', 'maxTextCharacters', 'subtitleTop'}, name='量测规则')
                rules = cp['measurement']
                for key in ('minFont393', 'maxTextCharacters', 'subtitleTop'):
                    if key in rules and (type(rules[key]) not in (int, float) or rules[key] < 0):
                        raise M2VError('量测阈值必须为非负数')
            if any(not isinstance(v, str) or not v.strip() for v in cp['forbidden']):
                raise M2VError('禁止项必须为非空文字')
        if set(shots) - covered:
            raise M2VError(f'镜头缺少默认检查点：{sorted(set(shots) - covered)}')


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
    return fingerprint({'global': {k: v for k, v in c.items() if k != 'scenes'}, 'selected': selected})


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
