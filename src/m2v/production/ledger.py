"""追加式事件与当前证据派生；查询不修改快照或历史。"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from . import contract, issues, policy, dependencies
from .dependencies import digest
from .storage import local, read, receipt, write

logger = logging.getLogger(__name__)
GATES = [f'G{i}' for i in range(7)]
PHASES = ['方案确定'] * 4 + ['粗片验证'] * 2 + ['最终验收']


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def history(root: Path) -> tuple[list[dict], list[str]]:
    path = outputs(root) / 'production/history.jsonl'
    if not path.exists():
        return [], []
    events, diagnostics, seen = [], [], set()
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        try:
            event = json.loads(line)
            contract.fields(event, {'id', 'projectId', 'versionId', 'type', 'time', 'gate', 'sceneId', 'checkpointId',
                                    'evidence', 'upstream', 'data'})
            if event['id'] in seen or event['gate'] not in [None, *GATES]:
                raise ValueError('重复事件 ID 或未知门')
            if (any(not isinstance(event[k], str) or not event[k] for k in ('id', 'projectId', 'versionId', 'type', 'time'))
                    or not isinstance(event['data'], dict) or not isinstance(event['upstream'], dict)
                    or not isinstance(event['evidence'], list)
                    or any(event[k] is not None and not isinstance(event[k], str) for k in ('sceneId', 'checkpointId'))):
                raise ValueError('事件字段类型无效')
            seen.add(event['id'])
            events.append(event)
        except (ValueError, TypeError, M2VError) as exc:
            diagnostics.append(f'历史第 {number} 行损坏：{exc}')
            break  # 不完整历史只能展示有效前缀，不支持通过。
    return events, diagnostics


def append(root: Path, manifest: dict, kind: str, *, gate=None, scene_id=None, checkpoint_id=None,
           evidence=None, upstream=None, data=None, event_id=None) -> dict:
    events, diagnostics = history(root)
    if any(e['projectId'] != manifest['id'] for e in events):
        diagnostics.append('历史含其他作品事件，不能据此判定通过')
    if diagnostics:
        raise M2VError('; '.join(diagnostics) + '；请显式 repair')
    eid = event_id or uuid.uuid4().hex
    prior = next((e for e in events if e['id'] == eid), None)
    if prior:
        return prior
    event = dict(id=eid, projectId=manifest['id'], versionId=(upstream or {}).get('cycle', 'legacy'),
                 type=kind, time=now(), gate=gate, sceneId=scene_id, checkpointId=checkpoint_id,
                 evidence=evidence or [], upstream=upstream or {}, data=data or {})
    directory = outputs(root) / 'production'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'history.jsonl'
    prefix = ''
    if path.exists() and path.stat().st_size:
        with path.open('rb') as existing:
            existing.seek(-1, 2)
            prefix = '' if existing.read(1) == b'\n' else '\n'
    with path.open('a', encoding='utf-8', newline='\n') as stream:
        import os
        stream.write(prefix + json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    logger.info('制作事件 %s gate=%s scene=%s id=%s', kind, gate, scene_id, eid)
    return event


def upstream(root: Path, c: dict, gate: str, scene_id=None, checkpoint_id=None) -> dict:
    result = {'cycle': c['cycleId'], 'contract': contract.scope_digest(c, scene_id, checkpoint_id)}
    if gate == 'G0':
        project_path = root / 'project.json'
        if project_path.exists():
            project = read(project_path)
            result['input'] = fingerprint({name: digest(local(root, name)) for name in project.get('materials', {}).values()})
    design = outputs(root) / 'production/design-frames.json'
    if gate in ('G2', 'G3', 'G4', 'G5', 'G6') and design.exists():
        selected_ids = {cp['id'] for s, _, cp in contract.checkpoints(c)
                        if (not scene_id or s['id'] == scene_id) and (not checkpoint_id or cp['id'] == checkpoint_id)}
        selected = [x for x in read(design).get('frames', []) if x.get('checkpointId') in selected_ids]
        source_digests = {}
        for item in selected:
            for reference in (item.get('path'), (item.get('sourceRecord') or {}).get('path')):
                if reference:
                    try:
                        source_digests[reference] = digest(local(outputs(root), reference))
                    except M2VError:
                        source_digests[reference] = 'missing'
        result['keyframes'] = fingerprint({'records': selected, 'files': source_digests})
    board_path = root / 'storyboard.json'
    if gate in ('G3', 'G4', 'G5', 'G6') and board_path.exists():
        board = read(board_path)
        if scene_id:
            board = {**{k: v for k, v in board.items() if k != 'scenes'},
                     'scenes': [s for s in board['scenes'] if s['id'] == scene_id]}
        result['storyboard'] = fingerprint(board)
    if gate in ('G4', 'G5', 'G6'):
        board = read(board_path)
        selected_scenes = [s for s in board['scenes'] if not scene_id or s['id'] == scene_id]
        bound = {s['id']: dependencies.scene_sources(root, s) for s in selected_scenes}
        result['sources'] = fingerprint(bound)
        result['conservativeReasons'] = sorted({reason for item in bound.values() for reason in item['conservativeReasons']})
        prepared = outputs(root) / 'prepared.json'
        if prepared.exists():
            value = read(prepared)
            # 场景选择后的输入不包括全局 preparedFingerprint，避免误伤无关场景。
            selected = [s for s in value.get('props', {}).get('compiledScenes', []) if not scene_id or s['id'] == scene_id]
            result['preparedInputs'] = fingerprint({'scenes': selected, 'fps': value.get('fps'),
                                                   'width': value.get('width'), 'height': value.get('height')})
    if gate == 'G6':
        delivery = outputs(root) / 'delivery.json'
        if delivery.exists():
            value = read(delivery)
            path = Path(value.get('path', ''))
            result['video'] = digest(path) if path.is_file() else 'missing'
    return result


def evidence_valid(root: Path, entries: list) -> bool:
    return evidence_valid_at(outputs(root), entries)


def evidence_valid_at(base: Path, entries: list) -> bool:
    try:
        return bool(entries) and all(digest(local(base, e['path'])) == e['sha256'] for e in entries)
    except (M2VError, OSError, KeyError, TypeError):
        return False


def register(root: Path, manifest: dict, report_path: Path) -> dict:
    report = read(report_path)
    contract.fields(report, {'gate', 'sceneId', 'checkpointId', 'status', 'checks', 'evidence', 'upstream'},
                    {'notApplicableReason', 'reviewRequired', 'coverage', 'retrospective'})
    gate = report['gate']
    if gate not in GATES or report['status'] not in ('pass', 'fail', 'unverified', 'not-applicable'):
        raise M2VError('未知门或报告状态')
    c = contract.load(root)
    current = upstream(root, c, gate, report['sceneId'], report['checkpointId'])
    if report['upstream'] != current or not evidence_valid(root, report['evidence']):
        raise M2VError('报告上游或证据摘要已过期')
    if report['status'] == 'pass' and (not report['checks'] or any(x.get('status') != 'pass' for x in report['checks'])):
        raise M2VError('通过报告必须有全部通过的检查')
    if report['status'] == 'not-applicable' and (gate not in ('G2',) or not report.get('notApplicableReason') or
            bool(policy.risks(c, 'static-expression'))):
        raise M2VError('此门不满足不适用条件')
    return append(root, manifest, 'check', gate=gate, scene_id=report['sceneId'], checkpoint_id=report['checkpointId'],
                  evidence=[receipt(outputs(root), report_path), *report['evidence']], upstream=current,
                  data={k: report[k] for k in ('status', 'reviewRequired') if k in report})


def status(root: Path, manifest: dict, *, full_history=False) -> dict:
    with dependencies.snapshot():
        return _status(root, manifest, full_history=full_history)


def _status(root: Path, manifest: dict, *, full_history=False) -> dict:
    if manifest['type'] != 'general':
        return {'applicability': '专用类型契约', 'gates': []}
    events, diagnostics = history(root)
    if any(e['projectId'] != manifest['id'] for e in events):
        diagnostics.append('历史含其他作品事件，不能据此判定通过')
    displayed_history = events if full_history else [{k: e[k] for k in
        ('id', 'type', 'time', 'gate', 'sceneId', 'checkpointId', 'evidence')} for e in events[-5:]]
    try:
        c = contract.load(root)
    except M2VError as exc:
        return {'applicability': '缺少制作合同或旧流程', 'diagnostics': [str(exc), *diagnostics], 'gates': [],
                'next': '补齐当前 v2 制作合同；旧记录仅作历史，不自动迁移或继承通过', 'history': displayed_history}
    try:
        problem_list = issues.load(root, required=True)
    except (M2VError, OSError) as exc:
        problem_list = []
        diagnostics.append(str(exc))
    rows, scenes = [], []
    indexed = {}
    current_events = [e for e in events if e['upstream'].get('cycle') == c['cycleId']]
    for event in current_events:
        indexed.setdefault((event['gate'], event['sceneId'], event['checkpointId']), []).append(event)
    for gate in GATES:
        scopes = [(s['id'], cp['id']) for s, _, cp in contract.checkpoints(c)] if gate == 'G4' else [(None, None)]
        results = []
        for sid, cid in scopes:
            scoped = indexed.get((gate, sid, cid), [])
            checks = [e for e in scoped if e['type'] == 'check']
            last = checks[-1] if checks else None
            opened = [p['id'] for p in problem_list if p['required'] and p['status'] != 'closed' and
                      (p['gate'] == gate or (gate == 'G4' and p['catchableAt'] == 'G4')) and
                      (not sid or not p['sceneId'] or p['sceneId'] == sid) and
                      (not cid or not p['checkpointId'] or p['checkpointId'] == cid)]
            state, degraded, check_state = '未开始', False, '未开始'
            missing_acceptance = []
            if last:
                try:
                    current = upstream(root, c, gate, sid, cid)
                except (M2VError, OSError, ValueError, TypeError, KeyError) as exc:
                    current = None
                    diagnostics.append(f'{gate}/{cid or "all"} 上游不可读：{exc}')
                valid = evidence_valid(root, last['evidence']) and last['upstream'] == current
                if not valid:
                    state = check_state = '过期'
                else:
                    raw = last['data']['status']
                    check_state = {'pass': '通过', 'fail': '阻断', 'unverified': '进行中', 'not-applicable': '不适用'}[raw]
                    state = check_state
                    if raw == 'pass':
                        requirement = policy.requirement(c, gate, cid)
                        reviews = [e for e in scoped if e['type'] == 'review' and e['upstream'] == last['upstream'] and
                                   e['data'].get('checkId') == last['id'] and evidence_valid(root, e['evidence'])]
                        degraded = any(e['data'].get('isolation') != 'independent-subagent' for e in reviews)
                        latest = {(e['data'].get('reviewerId'), e['data'].get('reviewType')): e for e in reviews}
                        blind = [e for (who, kind), e in latest.items() if kind == 'blind']
                        passed = [e for e in blind if e['data'].get('isolation') == 'independent-subagent'
                                  and e['data'].get('verdict') == 'pass']
                        focuses = {e['data'].get('focus') for e in passed}
                        if not set(requirement['focuses']) <= focuses:
                            state = '待评审'
                        if any(e['data'].get('verdict') == 'fail' for e in latest.values()):
                            state = '阻断'
                        # 对照必须与同一独立观察绑定，不新增人数要求。
                        if gate == 'G6' and policy.risks(c, 'static-expression'):
                            paired = {e['data'].get('blindId') for e in latest.values()
                                      if e['data'].get('reviewType') == 'consistency' and e['data'].get('verdict') == 'pass'}
                            if not any(e['data'].get('reportId') in paired for e in passed):
                                missing_acceptance = ['同轮设计对照']
                                if state != '阻断':
                                    state = '待评审'
            if state != '过期' and opened:
                state = '阻断'
            if diagnostics and state in ('通过', '不适用'):
                state = '阻断'
            row = dict(gate=gate, sceneId=sid, checkpointId=cid, status=state, checkStatus=check_state,
                       issues=opened, degraded=degraded, missingAcceptance=missing_acceptance,
                       lastEvidence=last['evidence'] if last else [],
                       reviewRequirement=policy.requirement(c, gate, cid))
            results.append(row)
            if sid:
                scenes.append(row)
        order = ['过期', '阻断', '待评审', '进行中', '未开始']
        aggregate = next((x for x in order if any(r['status'] == x for r in results)), '通过')
        if all(x['status'] == '不适用' for x in results):
            aggregate = '不适用'
        rows.append({'gate': gate, 'status': aggregate,
                     'missingAcceptance': sorted({item for r in results for item in r['missingAcceptance']})})
    # 前置未完成不意味着本门证据损坏；保留自身结果，单列可继续工作的条件。
    for index, row in enumerate(rows):
        earlier = [r for r in rows[:index] if r['status'] not in ('通过', '不适用')]
        row.update(evidenceStatus=row['status'], prerequisites=[r['gate'] for r in earlier],
                   ready=not earlier and row['status'] in ('通过', '不适用'))
        if row['status'] == '通过' and earlier:
            row['status'] = '等待前置'
        for scene in scenes if row['gate'] == 'G4' else []:
            scene.update(evidenceStatus=scene['status'], prerequisites=row['prerequisites'],
                         ready=not earlier and scene['status'] == '通过')
    current = next((r['gate'] for r in rows if r['status'] not in ('通过', '不适用')), None)
    next_action = f'm2v gates check --project {root} --gate {current}' if current else '全部门证据有效，可报告制作复核完成'
    if current:
        current_row = next(r for r in rows if r['gate'] == current)
        if current_row['evidenceStatus'] == '待评审':
            next_action = f'完成 {policy.round_for(current)} 轮缺失覆盖并导入报告（{current}）'
        elif current in ('G0', 'G5', 'G6'):
            next_action = f'登记 {current} 当前检查证据，再导入适用独立报告'
    phase = PHASES[int(current[1])] if current else '最终验收'
    g5 = next(r for r in rows if r['gate'] == 'G5')
    if g5['evidenceStatus'] == '通过' and current in ('G4', 'G5'):
        phase = '精制修订'
    scene_summary = []
    for scene in c['scenes']:
        checkpoints = [row for row in scenes if row['sceneId'] == scene['id']]
        scene_summary.append({'sceneId': scene['id'], 'passedCheckpoints': sum(x['status'] == '通过' for x in checkpoints),
            'totalCheckpoints': len(checkpoints), 'blockedCheckpoints': [x['checkpointId'] for x in checkpoints if x['status'] == '阻断'],
            'issues': sorted({issue for x in checkpoints for issue in x['issues']})})
    return dict(applicability='后验回归' if c.get('retrospective') else '检查点流程', phase=phase,
                cycleId=c['cycleId'], reviewRounds=policy.rounds(c), currentGate=current, gates=rows, scenes=scenes, sceneSummary=scene_summary, next=next_action, diagnostics=diagnostics,
                renders={'requests': sum(e['type'] == 'render-request' for e in events),
                         'generationAttempts': sum(e['type'] == 'generation-attempt' for e in events),
                         'generationSuccesses': sum(e['type'] == 'generation-succeeded' for e in events)},
                history=displayed_history)


def rebuild(root: Path, manifest: dict) -> dict:
    result = status(root, manifest)
    write(outputs(root) / 'production/gates.json', result)
    return result


def repair(root: Path) -> dict:
    events, diagnostics = history(root)
    if not diagnostics:
        return {'repaired': False}
    path = outputs(root) / 'production/history.jsonl'
    backup = path.with_name(f'history-damaged-{uuid.uuid4().hex}.jsonl')
    backup.write_bytes(path.read_bytes())
    from .storage import atomic_text
    atomic_text(path, ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in events))
    return {'repaired': True, 'backup': str(backup), 'diagnostics': diagnostics}
