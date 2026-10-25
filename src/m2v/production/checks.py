"""前置合同、关键帧、分镜及场景检查点的证据生成。"""
from __future__ import annotations

import json
import subprocess
import tempfile
import uuid
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from . import contract, ledger, measure
from .storage import local, read, receipt, write


def ffmpeg(args: list[str]) -> None:
    result = subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-y', *args], capture_output=True, text=True)
    if result.returncode:
        raise M2VError('检查点媒体处理失败：' + result.stderr[-2000:])


def save_report(root: Path, c: dict, gate, checks, *, scene_id=None, checkpoint_id=None, evidence=None) -> Path:
    directory = outputs(root) / 'production/reports'
    path = directory / f'{gate}-{uuid.uuid4().hex}.json'
    states = {check['status'] for check in checks}
    state = 'fail' if 'fail' in states else 'unverified' if 'unverified' in states or not checks else 'pass'
    report = dict(gate=gate, sceneId=scene_id, checkpointId=checkpoint_id, status=state, checks=checks,
                  evidence=evidence or [], upstream=ledger.upstream(root, c, gate, scene_id, checkpoint_id),
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
    checks = []
    for _, shot, cp in contract.checkpoints(c):
        if shot['tier'] != 'A' and not shot.get('core'):
            continue
        frames = [x for x in manifest['frames'] if x.get('checkpointId') == cp['id']]
        required_phases = {'establish', 'result'}
        if shot.get('timeStructure', {}).get('reveal', {}).get('window') is not None:
            required_phases.add('reveal')
        shot_checkpoint_ids = {point['id'] for _, q, point in contract.checkpoints(c) if q['id'] == shot['id']}
        phases = {x.get('phase') for x in manifest['frames'] if x.get('checkpointId') in shot_checkpoint_ids}
        checks.append(dict(name=f'{shot["id"]}:建立揭示结果', status='pass' if required_phases <= phases else 'unverified',
                           detail={'required': sorted(required_phases), 'actual': sorted(x for x in phases if x)}))
        for width in (c['width'], 852, 393):
            width_phases = {x.get('phase') for x in manifest['frames']
                            if x.get('checkpointId') in shot_checkpoint_ids and x.get('width') == width}
            checks.append(dict(name=f'{shot["id"]}:{width}:阶段覆盖',
                status='pass' if required_phases <= width_phases else 'unverified', detail=sorted(required_phases)))
            item = next((x for x in frames if x.get('width') == width), None)
            valid = bool(item and item.get('source') == 'independent-design' and item.get('tool') and item.get('createdAt')
                         and item.get('verifiedBy') and item.get('verificationBasis') and item.get('sourceRecord'))
            if item and any(marker in (str(item.get('path', '')) + str(item.get('tool', ''))).lower()
                            for marker in ('lookdev', 'code-cache', 'scene-capture')):
                valid = False
            if valid:
                # PNG 头直接核尺寸，避免为每张设计图启动 ffprobe。
                import struct
                path = local(base, item['path'])
                header = path.read_bytes()[:24]
                actual = struct.unpack('>II', header[16:24]) if header[:8] == b'\x89PNG\r\n\x1a\n' else None
                expected = (width, round(c['height'] * width / c['width']))
                valid = actual == expected and ledger.evidence_valid(root, [item['sourceRecord'], {'path': item['path'], 'sha256': item['sha256']}])
            checks.append(dict(name=f'{cp["id"]}:{width}', status='pass' if valid else 'unverified', detail='独立来源记录、核验及尺寸'))
    return checks


def run(root: Path, manifest: dict, gate: str, *, checkpoint_id=None) -> list[Path]:
    c = contract.load(root)
    if gate == 'G1':
        path = save_report(root, c, gate, [{'name': '合同声明与帧窗', 'status': 'pass', 'detail': contract.scope_digest(c)}])
        return [path]
    if gate == 'G2':
        if not any(q['tier'] == 'A' or q.get('core') for _, q, _ in contract.checkpoints(c)):
            path = save_report(root, c, gate, [])
            value = read(path)
            value.update(status='not-applicable', notApplicableReason='没有 A 级或核心段落')
            write(path, value)
            return [path]
        checks = design_frames(root, c)
        evidence = [receipt(outputs(root), outputs(root) / 'production/design-frames.json')]
        for entry in read(outputs(root) / 'production/design-frames.json')['frames']:
            evidence.extend([receipt(outputs(root), local(outputs(root), entry['path'])), entry['sourceRecord']])
        path = save_report(root, c, gate, checks, evidence=evidence)
        if not checks:
            value = read(path)
            value.update(status='not-applicable', notApplicableReason='没有 A 级或核心段落')
            write(path, value)
        return [path]
    if gate == 'G3':
        errors = contract.mapping(c, read(root / 'storyboard.json'))
        checks = [{'name': '分镜映射', 'status': 'fail' if errors else 'pass', 'detail': errors}]
        need = c['structureRisk'] or any(q['tier'] == 'A' for _, q, _ in contract.checkpoints(c))
        evidence = []
        if need:
            animatic = make_animatic(root, c)
            evidence.append(receipt(outputs(root), animatic))
            checks.append({'name': 'animatic', 'status': 'pass', 'detail': '仅验证结构时序，非交付物；待独立评审'})
        return [save_report(root, c, gate, checks, evidence=evidence)]
    if gate == 'G4':
        return capture(root, c, checkpoint_id)
    raise M2VError('G0/G5/G6 使用 register 登记事实、全片和技术验收报告；不自动产生审美通过')


def make_animatic(root: Path, c: dict) -> Path:
    manifest = read(outputs(root) / 'production/design-frames.json')
    target = outputs(root) / 'production/animatic'
    target.mkdir(parents=True, exist_ok=True)
    segments, coverage = [], []
    for scene in c['scenes']:
        for shot in scene['shots']:
            points = [cp for cp in scene['checkpoints'] if cp['shotId'] == shot['id']]
            point_ids = {cp['id'] for cp in points}
            native = [x for x in manifest['frames'] if x['checkpointId'] in point_ids and x['width'] == c['width']]
            parts = [(key, part['window']) for key, part in shot.get('timeStructure', {}).items() if part['window'] is not None]
            if not parts:
                parts = [('result', shot['window'])]
            parts.sort(key=lambda item:item[1][0])
            cursor = shot['window'][0]
            for key, window in parts:
                if window[0] != cursor:
                    raise M2VError('animatic 时间结构不连续或重叠')
                cursor = window[1]
                phase = 'reveal' if key == 'reveal' else 'result' if key in ('result','hold') else 'establish'
                match = next((x for x in native if x.get('phase') == phase), None)
                if match is None and shot['tier'] != 'A' and not shot.get('core'):
                    match = native[0] if native else None
                copy = target / f'{len(segments):04d}.png'
                if match:
                    source = local(outputs(root), match['path'])
                    import shutil
                    shutil.copyfile(source, copy)
                    source_record = receipt(outputs(root), source)
                elif shot['tier'] == 'A' or shot.get('core'):
                    raise M2VError(f'animatic 缺独立 {phase} 设计图：{shot["id"]}')
                else:
                    # B/C 允许没有独立图，用显著占位标明覆盖空缺，不能据此判断最终美术。
                    ffmpeg(['-f','lavfi','-i',f'color=c=black:s={c["width"]}x{c["height"]}',
                            '-vf',"drawtext=text='NO DESIGN FRAME - TIMING ONLY':x=20:y=80:fontsize=28:fontcolor=white",'-frames:v','1',str(copy)])
                    source_record = {'placeholder':True}
                seconds = (window[1] - window[0]) / c['fps']
                segments.append((copy, seconds))
                coverage.append({'sceneId':scene['id'],'shotId':shot['id'],'phase':phase,
                                 'checkpointIds':sorted(point_ids),'window':window,'source':source_record})
            if cursor != shot['window'][1]:
                raise M2VError('animatic 未覆盖完整镜头')
    listing = target / 'frames.txt'
    listing.write_text(''.join(f"file '{p.name}'\nduration {duration:.9f}\n" for p, duration in segments)
                       + f"file '{segments[-1][0].name}'\n", encoding='utf-8')
    video = target / 'animatic.mp4'
    ffmpeg(['-f', 'concat', '-safe', '0', '-i', str(listing), '-vf',
            "drawtext=text='ANIMATIC - NON DELIVERY':x=16:y=16:fontsize=22:fontcolor=white,format=yuv420p",
            '-r', str(c['fps']), '-c:v', 'libx264', str(video)])
    write(target / 'manifest.json', {'nonDelivery': True, 'coverage': coverage, 'sha256': receipt(outputs(root), video)['sha256']})
    return video


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
            step = cp.get('sampleStep', 1)
            frames = sorted({cp['frame'], cp['window'][0], cp['window'][1] - 1,
                             *range(cp['window'][0], cp['window'][1], step),
                             *[part['window'][0] for part in shot.get('timeStructure', {}).values()
                               if part['window'] is not None and cp['window'][0] <= part['window'][0] < cp['window'][1]]})
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
                    checks.extend(measure.evaluate(raw['elements'], cp, width=c['width'], height=c['height'], frame=n))
                    for width in (c['width'], 852, 393):
                        path = directory / f'{n:06d}-{width}.png'
                        ffmpeg(['-i', str(work / f'frame-{n:06d}.png'), '-vf', f'scale={width}:{round(c["height"] * width / c["width"])}', '-frames:v', '1', str(path)])
                        evidence.append(receipt(base, path))
                    if n == cp['frame'] and raw.get('probe'):
                        checks.extend(measure.evaluate_probe(raw['probe'], cp))
                write(directory / 'measurements.json', {'frames': measurements, 'step': step, 'window': cp['window'],
                     'capture': 'browser-selected-frames', 'cachedFullRender': False,
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
                if step > cp.get('minEventFrames', 1):
                    checks.append({'name': '动态证据密度', 'status': 'unverified', 'detail': '步长大于最短事件，需补片段或逐帧证据'})
                design = base / 'production/design-frames.json'
                if design.exists():
                    for item in read(design)['frames']:
                        if item['checkpointId'] == cp['id']:
                            actual = directory / f'{cp["frame"]:06d}-{item["width"]}.png'
                            compare = directory / f'compare-{item["width"]}.png'
                            ffmpeg(['-i', str(local(base, item['path'])), '-i', str(actual),
                                    '-filter_complex', 'hstack=inputs=2', '-frames:v', '1', str(compare)])
                            evidence.append(receipt(base, compare))
                path = save_report(root, c, 'G4', checks, scene_id=s['id'], checkpoint_id=cp['id'], evidence=evidence)
                report = read(path)
                if report['status'] == 'fail':
                    from . import issues
                    issue_id = 'G4-' + cp['id']
                    existing = next((x for x in issues.load(root) if x['id'] == issue_id), None)
                    if not existing or existing['status'] != 'open':
                        issues.update(root, {'id': issue_id, 'status': 'open', 'required': True, 'gate': 'G4',
                            'sceneId': s['id'], 'checkpointId': cp['id'], 'caughtAt': 'G4', 'catchableAt': 'G4',
                            'evidence': [], 'versionRefs': []})
                    notes = base / 'visual-notes.md'
                    failures = sorted({x['name'].split(':')[0] for x in checks if x['status'] == 'fail'})
                    with notes.open('a', encoding='utf-8') as stream:
                        stream.write('\n### ' + issue_id + '\n\n检查点 ' + cp['id'] + '：' + '、'.join(failures)
                            + '。修复后在同检查点复查；独立评审尚未由本报告完成。报告：[' + path.name + ']('
                            + path.relative_to(base).as_posix() + ')\n')
                result.append(path)
    return result
