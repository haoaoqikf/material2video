"""风险范围的时序试验；复用采集证据，不继承审美通过。"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from . import contract, policy
from .storage import local, read, receipt, write

logger = logging.getLogger(__name__)


def reuse(root: Path, c: dict, reports: list[str]) -> list[dict]:
    """复用当前采集过程，独立时序观察仍须另行完成。"""
    from . import ledger, media_evidence

    needed = policy.checkpoint_ids(c, 'structure-timing')
    if (not needed or not isinstance(reports, list) or not reports
            or any(not isinstance(path, str) for path in reports) or len(reports) != len(set(reports))):
        raise M2VError('时序复用需要非空、不重复的 G4 报告路径和 structure-timing 风险')
    points = {cp['id']: (scene, cp) for scene, _, cp in contract.checkpoints(c)}
    base, covered, evidence, capacity = outputs(root), set(), [], []
    for reference in reports:
        path = local(base, reference)
        report = read(path)
        cid = report.get('checkpointId') if isinstance(report, dict) else None
        if not isinstance(report, dict) or report.get('gate') != 'G4' or cid not in needed or cid in covered:
            raise M2VError('时序复用必须逐项对应风险检查点的 G4 采集报告')
        scene, cp = points[cid]
        current = ledger.upstream(root, c, 'G4', scene['id'], cid)
        if (report.get('sceneId') != scene['id'] or report.get('upstream') != current
                or not ledger.evidence_valid(root, report.get('evidence', []))):
            raise M2VError(f'{cid}：时序来源上游或证据已过期')
        entries = report['evidence']
        measurement = next((local(base, item['path']) for item in entries
                            if Path(item['path']).name == 'measurements.json'), None)
        if measurement is None:
            raise M2VError(f'{cid}：缺少实际采集的窗口量测记录')
        data = read(measurement)
        if not isinstance(data, dict) or not isinstance(data.get('cacheSource'), dict):
            raise M2VError(f'{cid}：采集窗口记录无效')
        source = data['cacheSource']
        if (data.get('capture') != 'browser-selected-frames' or data.get('window') != cp['window']
                or [source.get('startFrame'), source.get('endFrame')] != cp['window']):
            raise M2VError(f'{cid}：采集来源与完整时序窗口不一致')
        clip = receipt(base, measurement.with_name('window.mp4'))
        if clip not in entries:
            raise M2VError(f'{cid}：报告未绑定完整过程片段')
        evidence.extend([receipt(base, path), *entries])
        capacity.append({'checkpointId': cid, 'window': cp['window'], 'evidence': [clip]})
        covered.add(cid)
    if covered != needed:
        raise M2VError(f'时序复用未覆盖风险：{sorted(needed - covered)}')
    media_evidence.validate(capacity, c, base, needed)
    logger.info('复用 %d 个当前 G4 时序窗口，不生成 animatic', len(covered))
    return list({(item['path'], item['sha256']): item for item in evidence}.values())


def make_animatic(root: Path, c: dict) -> Path:
    from .checks import ffmpeg

    needed = policy.checkpoint_ids(c, 'structure-timing')
    shots = [(scene, shot) for scene in c['scenes'] for shot in scene['shots']]
    risk_shots = {cp['shotId'] for _, _, cp in contract.checkpoints(c) if cp['id'] in needed}
    selected = {index + offset for index, (_, shot) in enumerate(shots) if shot['id'] in risk_shots
                for offset in (-1, 0, 1) if 0 <= index + offset < len(shots)}
    if not selected:
        raise M2VError('animatic 仅用于 structure-timing 风险镜头')
    manifest_path = outputs(root) / 'production/design-frames.json'
    manifest = read(manifest_path) if manifest_path.exists() else {'frames': []}
    target = outputs(root) / 'production/animatic' / uuid.uuid4().hex
    target.mkdir(parents=True, exist_ok=True)
    segments, coverage, output_frame = [], [], 0
    for index, (scene, shot) in enumerate(shots):
        if index in selected:
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
                phase = key if key in ('establish', 'reveal', 'result', 'hold') else 'establish'
                match = next((x for x in native if x.get('phase') == phase), None)
                if match is None and phase == 'hold':
                    # 未提供独立 hold 图时退回 result，按结果态覆盖停留段。
                    phase = 'result'
                    match = next((x for x in native if x.get('phase') == phase), None)
                if match is None and not point_ids.intersection(policy.checkpoint_ids(c, 'static-expression')):
                    match = native[0] if native else None
                copy = target / f'{len(segments):04d}.png'
                if match:
                    source = local(outputs(root), match['path'])
                    import shutil
                    shutil.copyfile(source, copy)
                    source_record = receipt(outputs(root), source)
                elif point_ids.intersection(policy.checkpoint_ids(c, 'static-expression')):
                    raise M2VError(f'animatic 缺独立 {phase} 设计图：{shot["id"]}')
                else:
                    # 无静态风险的镜头允许时序占位，不能据此判断最终美术。
                    ffmpeg(['-f','lavfi','-i',f'color=c=black:s={c["width"]}x{c["height"]}',
                            '-vf',"drawtext=text='NO DESIGN FRAME - TIMING ONLY':x=20:y=80:fontsize=28:fontcolor=white",'-frames:v','1',str(copy)])
                    source_record = {'placeholder':True}
                seconds = (window[1] - window[0]) / c['fps']
                segments.append((copy, seconds))
                coverage.append({'sceneId':scene['id'],'shotId':shot['id'],'phase':phase,
                                 'checkpointIds':sorted(point_ids),'window':window,'source':source_record,
                                 'outputWindow': [output_frame, output_frame + window[1] - window[0]],
                                 'contextOnly': shot['id'] not in risk_shots})
                output_frame += window[1] - window[0]
            if cursor != shot['window'][1]:
                raise M2VError('animatic 未覆盖完整镜头')
    listing = target / 'frames.txt'
    listing.write_text(''.join(f"file '{p.name}'\nduration {duration:.9f}\n" for p, duration in segments)
                       + f"file '{segments[-1][0].name}'\n", encoding='utf-8')
    video = target / 'animatic.mp4'
    total = sum(seconds for _, seconds in segments)
    # 逐段把静帧循环为精确时长再用 concat 滤镜拼接；concat demuxer 在 30fps 下
    # 会按图片默认帧率重采样，时长会漂移（曾出现 29 秒素材编码成 32 秒）。
    args = []
    for path, seconds in segments:
        args += ['-loop', '1', '-framerate', str(c['fps']), '-t', f'{seconds:.9f}', '-i', str(path)]
    filters = ''.join(f'[{i}:v]trim=duration={seconds:.9f},setpts=PTS-STARTPTS[v{i}];'
                      for i, (_, seconds) in enumerate(segments))
    filters += ''.join(f'[v{i}]' for i in range(len(segments)))
    filters += (f'concat=n={len(segments)}:v=1:a=0[cat];[cat]'
                "drawtext=text='ANIMATIC - NON DELIVERY':x=16:y=16:fontsize=22:fontcolor=white,"
                'format=yuv420p[vout]')
    ffmpeg([*args, '-filter_complex', filters, '-map', '[vout]', '-r', str(c['fps']),
            '-t', f'{total:.9f}', '-c:v', 'libx264', str(video)])
    write(target / 'manifest.json', {'nonDelivery': True, 'coverage': coverage, 'sha256': receipt(outputs(root), video)['sha256']})
    return video
