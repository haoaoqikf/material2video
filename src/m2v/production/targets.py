"""用户明确换目标的历史记录；登记本身不授权通过或关闭。"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
import logging
import uuid

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from . import ledger, reviews
from .model import fields, identifier, now, text
from .storage import local, read, receipt, write

logger = logging.getLogger(__name__)
VERSION = 1


def _structural_cover(original, current):
    from .issues import covers

    # 只有参考和中性条件可替换；其余闭环约束复用唯一范围比较。
    target = {**current, 'references': original['references'], 'conditions': original['conditions'],
              'styleDigest': original.get('styleDigest'), 'styleTargets': original.get('styleTargets', {})}
    return covers(original, target)


def effective_scope(root: Path, item: dict) -> tuple[dict, int]:
    """返回原范围或最新登记替代目标，以及最后变更的历史位置。"""
    events, errors = ledger.history(root)
    if errors:
        raise M2VError('; '.join(errors))
    selected, position = deepcopy(item['scope']), -1
    for index, event in enumerate(events):
        if event['type'] != 'targets-changed':
            continue
        record_receipt = event['data'].get('receipt')
        if not record_receipt or not ledger.evidence_valid(root, [record_receipt]):
            raise M2VError('用户目标变更记录摘要失配或缺失')
        record = read(local(outputs(root), record_receipt['path']))
        fields(record, {'version', 'id', 'cycleId', 'projectId', 'createdAt', 'source',
                        'instruction', 'reportIds', 'round', 'scope', 'package'})
        if (type(record['version']) is not int or record['version'] != VERSION or record['source'] != 'user'
                or record['cycleId'] != ledger.cycle(root)['cycleId']
                or record['projectId'] != ledger.cycle(root)['projectId']):
            raise M2VError('用户目标变更记录版本、声明或周期无效')
        identifier(record['id'])
        text(record['instruction'])
        if item['reportId'] not in record['reportIds']:
            continue
        if (record['round'] != item['round']
                or not _structural_cover(selected, record['scope'])):
            raise M2VError('用户目标变更不得缩小原问题结构范围')
        selected = record['scope']
        position = index
    return selected, position


def validate_fresh_observation(root: Path, report: dict, position: int):
    if position < 0:
        return
    events, _ = ledger.history(root)
    invocation = read(local(outputs(root), report['invocation']['path']))
    if datetime.fromisoformat(invocation['startedAt']) <= datetime.fromisoformat(events[position]['time']):
        raise M2VError('独立观察必须在失败或用户目标变更登记后重新开始')


def register(root: Path, project: dict, request: dict) -> dict:
    """调用者须已依据实际对话核实授权；机器仅核验声明和可追溯证据。"""
    from . import issues

    fields(request, {'version', 'source', 'instruction', 'reportIds', 'packPath', 'packSha256'})
    if type(request['version']) is not int or request['version'] != VERSION or request['source'] != 'user':
        raise M2VError('目标变更须使用version=1并声明source=user')
    text(request['instruction'])
    text(request['packPath'])
    text(request['packSha256'])
    ids = request['reportIds']
    if (not isinstance(ids, list) or not ids
            or any(not isinstance(value, str) for value in ids) or len(set(ids)) != len(ids)):
        raise M2VError('reportIds须为不重复的独立失败ID列表')
    for report_id in ids:
        identifier(report_id)
    pack, private = reviews.load_package(root, project, request['packPath'], request['packSha256'])
    if pack['reviewType'] not in ('blind', 'process') or not private['binding']['style']['references'] or not private['request'].get('conditions'):
        raise M2VError('目标变更须绑定有实际参考和中性条件的当前盲包或过程对照包')
    selected = {item['reportId']: item for item in issues.load(root, required=True, active_only=True)
                if item['reportId'] in ids}
    if len(selected) != len(ids):
        raise M2VError('目标变更只能指定当前周期的实际独立失败问题')
    focuses = {item['scope']['focus'] for item in selected.values()}
    if len(focuses) != 1:
        raise M2VError('一次目标变更须保持同一评审职责')
    new_scope = issues.scope(root, {'packPath': request['packPath'], 'focus': next(iter(focuses))})
    events, _ = ledger.history(root)
    reports = {event['data']['reportId']: read(local(outputs(root), event['data']['reportPath']))
               for event in events if event['type'] == 'review' and event['data']['reportId'] in ids}
    for report_id, item in selected.items():
        report = reports.get(report_id)
        if (not report or report['isolation'] != 'independent-subagent' or report['verdict'] != 'fail'
                or not item['required'] or item['status'] != 'open' or item['round'] != pack['round']):
            raise M2VError('目标变更只能指定同轮开放的独立必改失败')
        current, _ = effective_scope(root, item)
        if not _structural_cover(current, new_scope):
            raise M2VError('新目标包不得缩小窗口、改变来源、职责或显示尺寸')
        old_targets = current.get('styleTargets', {})
        new_targets = new_scope['styleTargets']
        changed_scenes = {scene for key, scenes in new_targets.items() for scene, refs in scenes.items()
                          if old_targets.get(key, {}).get(scene) != refs}
        if current.get('styleDigest') != new_scope.get('styleDigest') or changed_scenes:
            from m2v.core.style_binding import load_binding
            affected = changed_scenes or {scene for scenes in new_targets.values() for scene in scenes}
            changes = load_binding(root, project)['overrides']
            # 旧报告首次补上无覆盖的类型默认时，原实物参考仍是同一目标。
            # 此时用户可以只改观察条件，登记和随后的独立复查照常执行。
            first_default = ('styleDigest' not in current and not changes and current['references']
                             and current['references'] == new_scope['references'])
            if not first_default:
                authorized = [change['scope']['scenes'] for change in changes
                              if change['authorization']['quote'] == request['instruction']]
                if 'all' not in authorized and not affected.issubset({s for group in authorized for s in group}):
                    raise M2VError('风格改靶须能追溯到全部受影响场景的已登记用户授权')
                continue
        if all(current[key] == new_scope[key] for key in ('references', 'conditions')):
            raise M2VError('目标未改变，无需登记替代')
    identity = uuid.uuid4().hex
    value = dict(version=VERSION, id=identity, cycleId=ledger.cycle(root)['cycleId'],
                 projectId=project['id'], createdAt=now(), source='user', instruction=request['instruction'],
                 reportIds=ids, round=pack['round'], scope=new_scope,
                 package=receipt(outputs(root), local(outputs(root), request['packPath'])))
    path = ledger.directory(root) / 'target-changes' / f'{identity}.json'
    write(path, value)
    ledger.append(root, project, 'targets-changed', data={'receipt': receipt(outputs(root), path)})
    logger.info('已登记用户目标变更 %s；%s个旧失败仍须独立复查', identity, len(ids))
    return {'id': identity, 'path': str(path), 'reportIds': ids, 'issuesClosed': False}
