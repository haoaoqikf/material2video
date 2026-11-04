"""隔离的 G5 可播放时间线：共用正式 composition，不编码全片粗稿。"""
from __future__ import annotations

import copy
import shutil
import subprocess
import uuid
from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from . import contract, ledger, policy, workflow
from .storage import local, receipt, write


def build(root: Path, manifest: dict) -> Path:
    from m2v.commands import _prepared
    from m2v.types.general import code_scenes
    from m2v.engine.contract_page import web_dir
    from m2v.engine.lookdev import sample_audio
    state = ledger.status(root, manifest)
    c = contract.load(root)
    if not state.get('scenes') or any(s['status'] != '通过' for s in state['scenes']):
        raise M2VError('G5 需要全部 G4 检查及审核计划指定的核心风险观察通过')
    if any(r['evidenceStatus'] not in ('通过', '不适用')
           for r in state['gates'] if r['gate'] in workflow.prerequisites('G5')
           and workflow.gate(r['gate']).checker in ('design', 'mapping')):
        raise M2VError('G5 需要先关闭适用的静态与结构风险')
    prepared = _prepared(root, manifest)
    # materialize 只补录缺区间，已有区间按现有摘要校验后复用。
    materialized = code_scenes.materialize(root, prepared, 0, prepared['durationInFrames'])
    directory = outputs(root) / 'review-pack' / uuid.uuid4().hex
    directory.mkdir(parents=True)
    props = copy.deepcopy(materialized['props'])
    for index, scene in enumerate(props['compiledScenes']):
        source = local(root, scene['mediaPath'])
        target = directory / f'evidence-{index:04d}.mp4'
        shutil.copyfile(source, target)
        scene['mediaPath'] = target.name
        # 不向盲审导出源码路径、作者 props 或实现说明。
        for key in list(scene):
            if key not in ('id', 'startFrame', 'endFrame', 'durationInFrames', 'transitionFrames', 'transition',
                           'mediaPath', 'mediaStartFrame', 'mediaDurationFrames'):
                del scene[key]
        scene['id'] = f'scene-{index:04d}'
    has_audio, audio = sample_audio(prepared, root)
    if has_audio and audio:
        target = directory / 'sound.wav'
        shutil.copyfile(audio, target)
        props['reviewAudio'] = target.name
    props['mediaBase'] = './'
    allowed = {'version', 'schemaVersion', 'fps', 'width', 'height', 'subtitle', 'durationInFrames',
               'compiledScenes', 'subtitleCues', 'reviewAudio', 'mediaBase'}
    props = {k: v for k, v in props.items() if k in allowed}
    props['title'] = ''
    write(directory / 'timeline.json', props)
    web = web_dir()
    result = subprocess.run([shutil.which('node') or 'node', str(web / 'scripts/build-review-player.mjs'), str(directory)],
                            cwd=web, capture_output=True, text=True, encoding='utf-8', timeout=120)
    if result.returncode:
        raise M2VError('粗片播放器构建失败：' + result.stderr[-2000:])
    fonts = web / 'public/fonts'
    if fonts.is_dir():
        shutil.copytree(fonts, directory / 'fonts')
    (directory / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Review</title>'
        '<div id="root"></div><script src="player.js"></script>', encoding='utf-8')
    (directory / 'questions.md').write_text('只读取本目录。按完整顺序观察理解、结构、节奏和声画承接。\n'
        '本目录是本地网页，使用本地 HTTP 服务打开 index.html；不能播放时以分场和跨场窗口补证，不推断通过。\n', encoding='utf-8')
    files = [receipt(directory, p) for p in sorted(directory.rglob('*')) if p.is_file()]
    from .reviews import build_manifest
    write(directory / 'manifest.json', build_manifest(review_id=directory.name, cycle_id=c['cycleId'], created_at=ledger.now(),
        gate='G5', scene_id=None, checkpoint_ids=[cp['id'] for _, _, cp in contract.checkpoints(c)], kind='rough-timeline',
        display_sizes=[c['width'], 852, 393], timecodes=[[0, props['durationInFrames']]], files=files))
    return directory
