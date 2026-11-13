"""作品直接入口及可选制作工具协议；所有执行路径均属于当前工程。"""
from __future__ import annotations

import argparse
import json
import logging
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from playwright.sync_api import Error as BrowserError

from .core.assets import REPOSITORY_ROOT as ROOT
from .core.errors import VideoError
from .core.project import _write_json, load_project

logger = logging.getLogger(__name__)


def _run(argv: list[str], *, timeout: int = 600) -> None:
    """本地构建／恢复失败必须退出；不借用主项目命令或父工作区。"""
    from .engine.remotion.process import _run as execute
    execute(argv, cwd=ROOT, timeout_s=timeout, what='作品本地命令')


def _node() -> str:
    node = shutil.which('node')
    if not node:
        raise VideoError('缺少Node.js，请按本作品README安装运行环境')
    return node


def _build() -> None:
    _run([_node(), 'scripts/sync-fonts.mjs'])
    _run([_node(), 'node_modules/typescript/bin/tsc', '--noEmit'])
    _run([_node(), 'node_modules/vite/bin/vite.js', 'build'])


def _setup(options) -> dict:
    _run([sys.executable, 'fonts/fetch.py', *(['--download'] if options.download else [])])
    _run([_node(), 'scripts/sync-fonts.mjs'])
    media = ROOT / 'assets/fetch.py'
    if media.is_file():
        _run([sys.executable, str(media)])
    sound = ROOT / 'assets/sound-recipe.json'
    if sound.is_file():
        from .types.scene_film.sound_library import import_assets
        import_assets(ROOT, json.loads(sound.read_text(encoding='utf-8-sig')), base=sound.parent)
    if options.install_browser:
        _run([sys.executable, '-m', 'playwright', 'install', 'chromium'])
    return {'status': 'ready', 'root': '.'}


def _validate(project: dict) -> dict:
    # 登记字体尚未恢复时不得报告 pass：构建会因缺字失败，validate 必须提前暴露。
    _run([sys.executable, 'fonts/fetch.py', '--check'])
    from .types.scene_film import cinematic, explainer
    cinematic.validate_project(project)
    board = explainer.load(ROOT, project)
    if not explainer.topic_input(board):
        explainer.source_file(ROOT, project)
    return {'status': 'pass', 'scenes': len(board['scenes'])}


def _prepare(project: dict, options) -> dict:
    from .types.scene_film import explainer_prepare
    return explainer_prepare.prepare(ROOT, project, voice=options.voice, rate=options.rate,
                                    rhythm=json.loads(options.rhythm))


def _current(project: dict, options) -> dict:
    from .types.scene_film import explainer_render
    try:
        return explainer_render.current(ROOT, project)
    except VideoError:
        logger.info('准备记录缺失或输入已改变，使用作品本地实现重新准备')
        return _prepare(project, options)


def _sample(project: dict, options) -> dict:
    from .core import security
    from .engine import design_sample
    from .core.delivery import digest
    import uuid
    from .engine.browser import configure
    configure()
    if not options.entry:
        raise VideoError('sample需要--entry指定作品内场景')
    props = json.loads(options.props)
    from .core.project import _local_reference
    destination = (_local_reference(ROOT, options.destination) if options.destination else
                   ROOT / 'outputs/samples' / uuid.uuid4().hex[:16])
    if (not destination.is_relative_to(ROOT / 'outputs/samples')
            or destination.exists() and (not destination.is_dir() or any(destination.iterdir()))):
        raise VideoError('sample目标须为outputs/samples内尚不存在或为空的目录')
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.sample-', dir=parent) as temporary:
        stage = Path(temporary) / 'capture'
        _run([_node(), 'scripts/sync-fonts.mjs'])
        result = design_sample.render(ROOT, project, stage, entry=options.entry, props=props,
                                     duration_seconds=options.duration_seconds, still_frames=options.frame,
                                     props_source=options.props_source)
        result['artifacts'] = {p.relative_to(stage).as_posix(): digest(p)
                               for p in sorted(stage.rglob('*')) if p.is_file()}
        _write_json(stage / 'capture.json', result)
        if destination.exists():
            destination.rmdir()  # 只接受空目标；并发写入会使rmdir失败，不覆盖内容。
        security.deliver_directory(stage, destination)
    return {'status': 'captured', 'path': destination.relative_to(ROOT).as_posix(), **result}


def _serve(project: dict, options) -> dict:
    """预览播放已准备的本地composition；与导出使用同一素材和字幕。"""
    from .engine import contract_page
    from .engine.http_server import LocalServer
    from .types.scene_film import code_scenes
    from .engine.browser import configure
    configure()
    prepared = _current(project, options)
    _build()
    prepared = code_scenes.materialize(ROOT, prepared, 0, prepared['durationInFrames'])
    page_props = ROOT / 'outputs/preview-props.json'
    with LocalServer(ROOT, cors=True) as server:
        audio = prepared.get('audio', {}).get('segments', [])
        from .core.audio_policy import declared_audio
        _write_json(page_props, {**prepared['props'], 'mediaBase': server.base_url + '/',
            **({'previewAudio': server.url_for(ROOT / audio[0]['path'])}
               if declared_audio(prepared) and audio else {})})
        url = contract_page.with_storyboard_query(server.url_for(contract_page.contract_page_path()),
                                                 '/outputs/preview-props.json') + '&video-preview=1'
        print(json.dumps({'status': 'serving', 'url': url}, ensure_ascii=False), flush=True)
        # 服务仅由明确的preview --serve持续持有；Ctrl+C在main统一处理。
        import threading
        threading.Event().wait()
    return {'status': 'stopped'}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='本作品独立准备、预览、采集与导出')
    parser.add_argument('command', choices=['setup', 'validate', 'prepare', 'build', 'preview', 'render', 'qa', 'sample',
                              'inspect', 'lookdev', 'materialize'])
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--install-browser', action='store_true')
    parser.add_argument('--voice')
    parser.add_argument('--rate')
    parser.add_argument('--rhythm', default='{}')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--limit-frames', type=int)
    parser.add_argument('--start-seconds', type=float, default=0)
    parser.add_argument('--end-seconds', type=float)
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--video')
    parser.add_argument('--step', type=int, default=30)
    parser.add_argument('--entry')
    parser.add_argument('--props', default='{}')
    parser.add_argument('--props-source')
    parser.add_argument('--destination')
    parser.add_argument('--duration-seconds', type=float, default=3)
    parser.add_argument('--frame', type=int, action='append')
    parser.add_argument('--scale', type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s', stream=sys.stderr)
    options = _parser().parse_args(argv)
    try:
        _, project = load_project(ROOT)
        if not 1 <= options.jobs <= 4:
            raise VideoError('--jobs必须为1至4的整数')
        if options.command == 'setup':
            result = _setup(options)
        elif options.command == 'validate':
            result = _validate(project)
        elif options.command == 'prepare':
            prepared = _prepare(project, options)
            result = {'status': 'prepared', 'path': 'outputs/prepared.json',
                      'preparedFingerprint': prepared['preparedFingerprint']}
        elif options.command == 'build':
            _build()
            result = {'status': 'built'}
        elif options.command == 'sample':
            sample = _sample(project, options)
            result = {'status': sample['status'], 'path': sample['path'] + '/capture.json'}
        elif options.command == 'inspect':
            from .types.scene_film.explainer_render import current
            prepared = current(ROOT, project)
            result = {'status': 'current', 'path': 'outputs/prepared.json',
                      'preparedFingerprint': prepared['preparedFingerprint']}
        elif options.command == 'lookdev':
            from .engine import lookdev
            if not options.frame:
                raise VideoError('lookdev需要至少一个--frame')
            destination = options.destination or 'outputs/lookdev'
            manifest = lookdev.render_stills(ROOT, project, options.frame, Path(destination),
                                             scale=options.scale)
            result = {'status': 'captured', 'path': destination + '/lookdev.json',
                      'stills': manifest['stills'], 'preparedFingerprint': manifest['preparedFingerprint']}
        elif options.command == 'materialize':
            from .engine import lookdev
            value = lookdev.materialize_all(ROOT, project)
            result = {'status': 'materialized', 'path': 'outputs/materialized.json',
                      'preparedFingerprint': value['preparedFingerprint']}
        elif options.command == 'qa':
            from .engine import qa
            report = qa.run(ROOT, _current(project, options), video=Path(options.video) if options.video else None, step=options.step)
            result = {'status': report['status'], 'path': 'outputs/qa.json'}
        elif options.command == 'preview' and options.serve:
            result = _serve(project, options)
        else:
            from .types.scene_film import explainer_render
            from .engine.browser import configure
            configure()
            _current(project, options)
            _build()
            output = explainer_render.render(ROOT, project, preview=options.command == 'preview',
                limit_frames=options.limit_frames, start_seconds=options.start_seconds,
                end_seconds=options.end_seconds, jobs=options.jobs)
            prepared = explainer_render.current(ROOT, project)
            result = {'status': 'candidate', 'path': output.relative_to(ROOT).as_posix(),
                      'preparedFingerprint': prepared['preparedFingerprint']}
        if 'path' in result:
            from .core.delivery import digest
            result['sha256'] = digest(ROOT / result['path'])
        result['environment'] = {'python': platform.python_version(), 'platform': sys.platform,
                                 'pythonEnvironment': 'local' if Path(sys.prefix).resolve().is_relative_to(ROOT) else 'system'}
        print('__VIDEO_RESULT__' + json.dumps({'version': 1, 'command': options.command, 'result': result}, ensure_ascii=False), flush=True)
        return 1 if options.command == 'qa' and result.get('status') == 'fail' else 0
    except KeyboardInterrupt:
        logger.info('作品执行已取消')
        return 130
    except (VideoError, OSError, ValueError, subprocess.SubprocessError, BrowserError) as exc:
        logger.error('%s', exc)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
