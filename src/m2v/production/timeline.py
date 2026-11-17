"""隔离的全片可播放时间线：共用正式 composition，不编码全片粗稿。"""
from __future__ import annotations

import copy
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from .model import VERSION
from .storage import local, receipt, write


def build(root: Path, manifest: dict) -> Path:
    from m2v.commands import _prepared
    from m2v.standalone import executor
    prepared = _prepared(root, manifest)
    # 由作品本地入口物化片段并返回带本地媒体路径的 props。
    result = executor.execute(root, project=manifest, action='materialize', arguments=[], timeout=3600)
    value = executor.read_json(executor.local_artifact(root, result['path']))
    if value.get('preparedFingerprint') != prepared['preparedFingerprint']:
        raise M2VError('时间线物化结果与当前准备身份不符')
    directory = outputs(root) / 'review-pack' / uuid.uuid4().hex
    directory.mkdir(parents=True)
    props = copy.deepcopy(value['props'])
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
    audio_value = value.get('audio')
    if audio_value:
        target = directory / 'sound.wav'
        shutil.copyfile(local(root, audio_value), target)
        props['reviewAudio'] = target.name
    props['mediaBase'] = './'
    allowed = {'version', 'schemaVersion', 'fps', 'width', 'height', 'subtitle', 'durationInFrames',
               'compiledScenes', 'subtitleCues', 'reviewAudio', 'mediaBase'}
    props = {k: v for k, v in props.items() if k in allowed}
    props['title'] = ''
    write(directory / 'timeline.json', props)
    result = subprocess.run([shutil.which('node') or 'node', str(root / 'scripts/build-review-player.mjs'),
                             str(directory)], cwd=root, capture_output=True, text=True,
                            encoding='utf-8', timeout=120)
    if result.returncode:
        raise M2VError('粗片播放器构建失败：' + result.stderr[-2000:])
    fonts = root / 'public/fonts'
    if (not fonts.is_dir() or fonts.is_symlink()
            or (hasattr(fonts, 'is_junction') and fonts.is_junction())
            or not fonts.resolve().is_relative_to(root.resolve())):
        raise M2VError('作品字体目录缺失或经链接指向作品外；请先修复并重新 build')
    def _reject_links(base: Path) -> None:
        for parent, children, names in os.walk(base, followlinks=False):
            for name in [*children, *names]:
                path = Path(parent) / name
                if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
                    raise M2VError(f'作品字体目录含链接：{path}')
                if not path.resolve().is_relative_to(root.resolve()):
                    raise M2VError(f'作品字体目录越过作品：{path}')
    _reject_links(fonts)
    shutil.copytree(fonts, directory / 'fonts')
    (directory / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Review</title>'
        '<div id="root"></div><script src="player.js"></script>', encoding='utf-8')
    (directory / 'questions.md').write_text(
        '只读取本目录。按完整顺序观察理解、结构、节奏和声画承接。\n'
        '本目录是本地网页，使用本地 HTTP 服务打开 index.html；制作复核使用分场与跨场窗口的抽帧和适用信号，无需播放观看或试听。\n',
        encoding='utf-8')
    files = [receipt(directory, p) for p in sorted(directory.rglob('*')) if p.is_file()]
    write(directory / 'manifest.json', {'version': VERSION, 'kind': 'internal-timeline',
        'fps': prepared['fps'], 'window': [0, prepared['durationInFrames']], 'files': files})
    return directory
