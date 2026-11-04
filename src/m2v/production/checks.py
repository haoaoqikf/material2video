"""前置合同、关键帧、分镜及场景检查点的证据生成。"""
from __future__ import annotations

import logging
import subprocess
import tempfile
import uuid
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from . import contract, ledger, measure, policy, workflow
from .storage import local, read, receipt, write
from .sampling import sample_frames, sampling_step
from .evidence_images import derive_images
from .timing import make_animatic

logger = logging.getLogger(__name__)


def ffmpeg(args: list[str]) -> None:
    result = subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-y', *args], capture_output=True, text=True)
    if result.returncode:
        raise M2VError('检查点媒体处理失败：' + result.stderr[-2000:])


def save_report(root: Path, c: dict, gate, checks, *, scene_id=None, checkpoint_id=None, evidence=None,
                timing_reports=None) -> Path:
    directory = outputs(root) / 'production/reports'
    path = directory / f'{gate}-{uuid.uuid4().hex}.json'
    states = {check['status'] for check in checks}
    state = 'fail' if 'fail' in states else 'unverified' if 'unverified' in states or not checks else 'pass'
    report = dict(gate=gate, sceneId=scene_id, checkpointId=checkpoint_id, status=state, checks=checks,
                  evidence=evidence or [], upstream=ledger.upstream(root, c, gate, scene_id, checkpoint_id,
                                                                   timing_reports=timing_reports),
                  retrospective=bool(c.get('retrospective')))
    # 报告自身也能作为证据，但不能自引用摘要；附合同摘要声明供审计。
    binding = directory / f'binding-{uuid.uuid4().hex}.json'
    write(binding, report['upstream'])
    report['evidence'].append(receipt(outputs(root), binding))
    write(path, report)
    return path


def design_frames(root: Path, c: dict) -> list[dict]:
    """manifest 明确绑定每个检查点/显示宽度，不把来源标签当核验。"""
    base = outputs(root)
    manifest_path = base / 'production/design-frames.json'
    manifest = read(manifest_path)
    contract.fields(manifest, {'frames'})
    checks, derived = [], []
    selected = policy.checkpoint_ids(c, 'static-expression')
    import struct
    for _, shot, cp in contract.checkpoints(c):
        if cp['id'] not in selected:
            continue
        required = {'establish', 'result'}
        if shot.get('timeStructure', {}).get('reveal', {}).get('window') is not None:
            required.add('reveal')
        for phase in sorted(required):
            item = next((x for x in manifest['frames'] if x.get('checkpointId') == cp['id']
                         and x.get('phase') == phase and x.get('width') == c['width']), None)
            valid = bool(item and item.get('source') == 'independent-design' and item.get('tool')
                         and item.get('createdAt') and item.get('verifiedBy') and item.get('verificationBasis')
                         and item.get('sourceRecord'))
            if valid:
                valid = not any(marker in (item['path'] + item['tool']).lower()
                                for marker in ('lookdev', 'code-cache', 'scene-capture'))
            if valid:
                valid = ledger.evidence_valid(root, [item['sourceRecord'], {'path': item['path'], 'sha256': item['sha256']}])
            if valid:
                path = local(base, item['path'])
                header = path.read_bytes()[:24]
                actual = struct.unpack('>II', header[16:24]) if header[:8] == b'\x89PNG\r\n\x1a\n' else None
                valid = actual == (c['width'], c['height'])
            checks.append(dict(name=f"{cp['id']}:{phase}:来源与尺寸", status='pass' if valid else 'unverified',
                               detail='逐阶段核验独立来源、实际原图尺寸与摘要'))
            if valid:
                targets = {width: base / 'production/design-derived' / f"{cp['id']}-{phase}-{width}.png"
                           for width in (852, 393)}
                derive_images(local(base, item['path']), targets)
                for width, path in targets.items():
                    derived.append({**item, 'width': width, **receipt(base, path), 'derivedFrom': item['sha256']})
    # 只替换机器派生图，不重写任何来源声明或许可。
    manifest['frames'] = [x for x in manifest['frames'] if not x.get('derivedFrom')] + derived
    write(manifest_path, manifest)
    return checks



def run(root: Path, manifest: dict, gate: str, *, checkpoint_id=None, timing_reports=None) -> list[Path]:
    if timing_reports is not None and gate != 'G3':
        raise M2VError('--timing-reports 只适用于 G3 时序验证')
    c = contract.load(root)
    checker = workflow.gate(gate).checker
    if checker == 'declaration':
        path = save_report(root, c, gate, [{'name': '合同声明与帧窗', 'status': 'pass', 'detail': contract.scope_digest(c)}])
        return [path]
    if checker == 'design':
        if not policy.risks(c, 'static-expression'):
            path = save_report(root, c, gate, [])
            value = read(path)
            value.update(status='not-applicable', notApplicableReason='审核计划无 static-expression 风险：' + c['reviewPlan']['basis'])
            write(path, value)
            return [path]
        checks = design_frames(root, c)
        evidence = [receipt(outputs(root), outputs(root) / 'production/design-frames.json')]
        for entry in read(outputs(root) / 'production/design-frames.json')['frames']:
            evidence.extend([receipt(outputs(root), local(outputs(root), entry['path'])), entry['sourceRecord']])
        path = save_report(root, c, gate, checks, evidence=evidence)
        if not checks:
            value = read(path)
            value.update(status='not-applicable', notApplicableReason='审核计划无 static-expression 风险：' + c['reviewPlan']['basis'])
            write(path, value)
        return [path]
    if checker == 'mapping':
        errors = contract.mapping(c, read(root / 'storyboard.json'))
        checks = [{'name': '分镜映射', 'status': 'fail' if errors else 'pass', 'detail': errors}]
        need = bool(policy.risks(c, 'structure-timing'))
        evidence = []
        if timing_reports is not None:
            from .timing import reuse
            evidence = reuse(root, c, timing_reports)
            checks.append({'name': '时序过程复用', 'status': 'pass', 'detail': '当前采集过程，不继承 G4 或独立通过'})
        elif need and not errors:
            animatic = make_animatic(root, c)
            evidence.extend([receipt(outputs(root), animatic), receipt(outputs(root), animatic.with_name('manifest.json'))])
            checks.append({'name': 'animatic', 'status': 'pass', 'detail': '风险镜头及相邻上下文；待独立评审'})
        return [save_report(root, c, gate, checks, evidence=evidence, timing_reports=timing_reports)]
    if checker == 'capture':
        return capture(root, c, checkpoint_id)
    raise M2VError('G0/G5/G6 使用 register 登记事实、全片和技术验收报告；不自动产生审美通过')


def event_coverage(prepared: dict, scene: dict, cp: dict, sampled: list[int], *, step=None) -> dict | None:
    """只报告检查窗内事件是否被采样帧覆盖，不改变 checks 或门结果。

    `sampleStep` 与 `minEventFrames` 都是作者手填的；事件表已经有真实帧和间隔。
    这里把两者并排写进 `measurements.json`，让漏采可见，但不由它自动判定通过。
    """
    events = [event for event in prepared.get('props', {}).get('resolvedEvents', [])
              if event.get('sceneId') == scene['id']
              and cp['window'][0] <= event['frame'] < cp['window'][1]]
    if not events:
        return None
    frames = sorted({event['frame'] for event in events})
    sampled_set = set(sampled)
    gaps = [right - left for left, right in zip(frames, frames[1:])]
    missed = sorted(set(frames) - sampled_set)
    return {
        'events': [{'id': event['id'], 'frame': event['frame'],
                    'globalFrame': event.get('globalFrame')} for event in events],
        'eventFrames': frames,
        'sampledFrames': sorted(set(frames) & sampled_set),
        'missedFrames': missed,
        'minSpacing': min(gaps) if gaps else None,
        'sampleStep': step if step is not None else cp.get('sampleStep', 1),
        'warning': bool(missed),
        'note': '非门禁诊断：只提示采样可能漏掉事件，不改变检查结果',
    }


def _reopen_checkpoint_issue(root: Path, scene_id: str, checkpoint_id: str) -> None:
    from . import issues
    issue_id = 'G4-' + checkpoint_id
    # 本项闭环证据可能已过期；显式重开仍须保留已登记归因及受保护版本。
    existing = next((x for x in issues.load(root, _reopening_id=issue_id) if x['id'] == issue_id), None)
    if existing and existing['status'] == 'open':
        return
    item = dict(existing or {})
    item.update(id=issue_id, status='open', required=True, gate='G4', sceneId=scene_id,
                checkpointId=checkpoint_id, caughtAt='G4', catchableAt='G4', evidence=[])
    item.setdefault('versionRefs', [])
    issues.update(root, item)


def capture(root: Path, c: dict, checkpoint_id: str | None) -> list[Path]:
    from playwright.sync_api import sync_playwright
    from m2v.commands import _prepared
    from m2v.core.project import load_project
    from m2v.types.general import code_scenes, media_assets
    _, project = load_project(root)
    prepared = _prepared(root, project)
    media = media_assets.resolve(root)['media']
    base = outputs(root)
    result = []
    selected = [(s, q, cp) for s, q, cp in contract.checkpoints(c) if not checkpoint_id or cp['id'] == checkpoint_id]
    if not selected:
        raise M2VError('未知检查点')
    recordings = {}
    for s, _, cp in selected:
        scene = next(x for x in prepared['props']['compiledScenes'] if x['id'] == s['id'])
        cached = code_scenes.materialize(root, prepared, scene['startFrame'] + cp['window'][0],
                                         scene['startFrame'] + cp['window'][1])
        recordings[cp['id']] = next(x for x in cached['props']['compiledScenes'] if x['id'] == s['id'])
    with sync_playwright() as pw:
        for s, shot, cp in selected:
            scene = next(x for x in prepared['props']['compiledScenes'] if x['id'] == s['id'])
            directory = base / 'production/checkpoints' / cp['id']
            directory.mkdir(parents=True, exist_ok=True)
            # 事件窗口使用正式录制缓存；后续时间线补齐时沿用同一个区间键。
            # DOM 量测另外读取页面，不把复用视频说成能恢复 DOM。
            recorded = recordings[cp['id']]
            import shutil
            window_clip = directory / 'window.mp4'
            shutil.copyfile(local(root, recorded['mediaPath']), window_clip)
            dynamic = cp['id'] in (policy.checkpoint_ids(c, 'core-event') | policy.checkpoint_ids(c, 'structure-timing'))
            step = sampling_step(cp, fps=c['fps'], dynamic=dynamic)
            events = [e['frame'] for e in prepared.get('props', {}).get('resolvedEvents', []) if e.get('sceneId') == s['id']]
            frames = sample_frames(cp, shot, fps=c['fps'], dynamic=dynamic, event_frames=events)
            logger.info('G4 %s：窗口 %s，步长 %d，边界加密后 %d 帧，动态风险=%s',
                        cp['id'], cp['window'], step, len(frames), dynamic)
            design_path = base / 'production/design-frames.json'
            designs = [item for item in read(design_path)['frames'] if item['checkpointId'] == cp['id']] if design_path.exists() else []
            widths = sorted({c['width'], 393, *(item['width'] for item in designs)})
            coverage = event_coverage(prepared, s, cp, frames, step=step)
            measurements = {}
            def observe(page, frame):
                measurements[frame] = {'elements': page.evaluate(measure.DOM),
                    'probe': page.evaluate('window.__M2V_REVIEW_STATE__ ?? null')}
            with tempfile.TemporaryDirectory(prefix='checkpoint-', dir=directory) as temp:
                work = Path(temp)
                code_scenes.build_scene(root, scene, work)
                config = code_scenes.scene_config(scene, {'width': c['width'], 'height': c['height'],
                    'subtitle': prepared['props']['subtitle']}, media, fps=c['fps'])
                code_scenes._capture(pw, root, work, config, selected_frames=frames, observe=observe)
                evidence = [receipt(base, window_clip)]
                checks = []
                for n in frames:
                    raw = measurements[n]
                    checks.extend(measure.evaluate(raw['elements'], cp, width=c['width'], height=c['height'], frame=n,
                                                   safe_area=prepared['props']['subtitle'].get('safeArea')))
                    targets = {width: directory / f'{n:06d}-{width}.png' for width in widths}
                    derive_images(work / f'frame-{n:06d}.png', targets)
                    for path in targets.values():
                        evidence.append(receipt(base, path))
                    if raw.get('probe'):
                        checks.extend(measure.evaluate_probe(raw['probe'], cp, frame=n))
                write(directory / 'measurements.json', {'frames': measurements, 'step': step, 'window': cp['window'],
                     'capture': 'browser-selected-frames', 'cachedFullRender': False,
                     'eventCoverage': coverage,
                     'cacheSource': {'path': recorded['mediaPath'], 'startFrame': cp['window'][0], 'endFrame': cp['window'][1]}})
                evidence.append(receipt(base, directory / 'measurements.json'))
                for entry in cp.get('manualEvidence', []):
                    if not ledger.evidence_valid(root, [entry]):
                        raise M2VError('人工逐项证据摘要不匹配')
                    manual = read(local(base, entry['path']))
                    contract.fields(manual, {'checkpointId', 'upstream', 'verifiedBy', 'observations', 'checks'})
                    current = ledger.upstream(root, c, 'G4', s['id'], cp['id'])
                    if manual['checkpointId'] != cp['id'] or manual['upstream'] != current or not manual['verifiedBy'] or not manual['observations']:
                        raise M2VError('人工逐项证据缺少当前绑定或实际观察')
                    for replacement in manual['checks']:
                        contract.fields(replacement, {'name', 'status', 'detail'})
                        if replacement['status'] not in ('pass', 'fail', 'unverified'):
                            raise M2VError('人工复核状态无效')
                        # 人工证据只能补未覆盖项，不能覆盖已观察到的实际缺陷。
                        for observed in checks:
                            if observed['name'] == replacement['name'] and observed['status'] == 'unverified':
                                observed.update(status=replacement['status'], detail=replacement['detail'])
                    evidence.append(entry)
                if step > cp.get('minEventFrames', 1 if dynamic else step):
                    checks.append({'name': '动态证据密度', 'status': 'unverified', 'detail': '步长大于最短事件，需补片段或逐帧证据'})
                design = base / 'production/design-frames.json'
                if design.exists():
                    for item in read(design)['frames']:
                        if item['checkpointId'] == cp['id']:
                            actual = directory / f'{cp["frame"]:06d}-{item["width"]}.png'
                            compare = directory / f'compare-{item["phase"]}-{item["width"]}.png'
                            ffmpeg(['-i', str(local(base, item['path'])), '-i', str(actual),
                                    '-filter_complex', 'hstack=inputs=2', '-frames:v', '1', str(compare)])
                            evidence.append(receipt(base, compare))
                path = save_report(root, c, 'G4', checks, scene_id=s['id'], checkpoint_id=cp['id'], evidence=evidence)
                report = read(path)
                if report['status'] == 'fail':
                    issue_id = 'G4-' + cp['id']
                    _reopen_checkpoint_issue(root, s['id'], cp['id'])
                    notes = base / 'visual-notes.md'
                    failures = sorted({x['name'].split(':')[0] for x in checks if x['status'] == 'fail'})
                    with notes.open('a', encoding='utf-8') as stream:
                        stream.write('\n### ' + issue_id + '\n\n检查点 ' + cp['id'] + '：' + '、'.join(failures)
                            + '。修复后在同检查点复查；独立评审尚未由本报告完成。报告：[' + path.name + ']('
                            + path.relative_to(base).as_posix() + ')\n')
                result.append(path)
    return result
