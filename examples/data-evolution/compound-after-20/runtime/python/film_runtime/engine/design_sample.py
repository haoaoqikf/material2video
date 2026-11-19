"""最小原生场景试制，复用正式构建、受控采集和视频编码。"""
from __future__ import annotations

import json
import math
import shutil
import tempfile
from pathlib import Path
import film_runtime

from film_runtime.core import frames
from film_runtime.core.assets import REPOSITORY_ROOT
from film_runtime.core.errors import VideoError
from film_runtime.core.video_config import project_fps
from film_runtime.core.fingerprints import module_files
from film_runtime.engine.contract_page import font_files
from film_runtime.types.scene_film import code_scenes, media_assets
from film_runtime.types.scene_film.code_scenes.config import WEB
from film_runtime.types.scene_film.code_scenes.config import copy_build_outputs
from film_runtime.types.scene_film.code_scenes.capture import _assert_pure_sources

VIEWER = Path(__file__).with_name('design_sample_viewer.html')


def input_path(root: Path, label: str) -> Path:
    scope, _, relative = label.partition('/')
    base = root if scope == 'work' else None
    if (base is None or not relative or Path(relative).anchor or ':' in relative
            or '\\' in relative or '..' in Path(relative).parts):
        raise VideoError(f'样品输入路径无效：{label}')
    target = (base / relative).resolve()
    if not target.is_relative_to(base.resolve()) or not target.is_file():
        raise VideoError(f'样品输入缺失或越界：{label}')
    return target


def snapshot(root: Path, paths: list[Path]) -> dict[str, str]:
    result = {}
    for path in paths:
        path = path.resolve()
        if path.is_relative_to(root.resolve()):
            label = 'work/' + path.relative_to(root.resolve()).as_posix()
        else:
            raise VideoError(f'样品构建输入越界：{path}')
        result[label] = code_scenes.digest(path)
    return result


def render(root: Path, project: dict, destination: Path, *, entry: str, props: dict,
           duration_seconds: float, still_frames: list[int] | None = None,
           props_source: str | None = None, kind: str = 'motion') -> dict:
    """destination是调用方创建的临时目录，成功前不发布有效凭据。"""
    from playwright.sync_api import sync_playwright

    if type(duration_seconds) not in (int, float) or not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise VideoError('样品时长必须为有限正数')
    code_scenes.validate_entry(root, entry, props)
    code_scenes.validate_capture(props)
    extra = [root / 'project.json']
    initial_extra = snapshot(root, extra)
    current_project = json.loads(extra[0].read_text(encoding='utf-8'))
    if current_project != project:
        raise VideoError('采集前作品配置已变化')
    if props_source:
        path = input_path(root, 'work/' + props_source)
        initial_extra.update(snapshot(root, [path]))
        if json.loads(path.read_text(encoding='utf-8')) != props:
            raise VideoError('采集前样品参数文件已变化')
        extra.append(path)
    board = root / project['materials']['storyboard']
    if board.is_file():
        extra.append(board)
        initial_extra.update(snapshot(root, [board]))
    fps = project_fps(root, project, allow_missing_storyboard=True)
    count = round(duration_seconds * fps)
    if kind not in ('static', 'motion') or count < (2 if kind == 'motion' else 1):
        raise VideoError('静态样品至少一帧，动态样品至少两帧，kind须为static/motion')
    selected = sorted(set([count - 1] if still_frames is None else still_frames))
    if not selected or any(type(n) is not int or not 0 <= n < count for n in selected):
        raise VideoError('样品静帧位置必须位于局部时长内')
    size = frames.normalize(project.get('output', {}).get('width'), project.get('output', {}).get('height'))
    frame = frames.spec(*size)
    scene = {'id': 'sample', 'startFrame': 0, 'endFrame': count, 'durationInFrames': count,
             'segmentWindows': {}, 'content': {'entry': entry, 'props': props}}
    media = media_assets.resolve(root)
    config = code_scenes.scene_config(scene, frame, media['media'], fps=fps)
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.sample-render-', dir=destination) as temporary:
        work = Path(temporary)
        implementation = code_scenes.implementation_inputs()
        code_scenes.build_scene(root, scene, work)
        settings = code_scenes.capture_settings(props)
        if settings['mode'] == 'pure-time':
            _assert_pure_sources(root, work)
        reachable = [Path(name) for name in json.loads((work / 'inputs.json').read_text(encoding='utf-8'))]
        files = [*extra, *reachable, Path(__file__), VIEWER, *font_files(),
                 *module_files(film_runtime), REPOSITORY_ROOT / 'scripts/video.py',
                 REPOSITORY_ROOT / 'scripts/sync-fonts.mjs',
                 *(REPOSITORY_ROOT / name for name in code_scenes.implementation_inputs())]
        record = root / 'assets/media-sources.json'
        if record.exists():
            files.append(record)
        files.extend(code_scenes.media_files(root, media['media']).values())
        before = snapshot(root, files)
        if any(before.get(label) != sha for label, sha in initial_extra.items()):
            raise VideoError('构建期间作品描述或样品参数发生变化，请重新采集')
        built = json.loads((work / 'input-digests.json').read_text(encoding='utf-8'))
        if (any(code_scenes.digest(Path(name)) != digest for name, digest in built.items())
                or implementation != code_scenes.implementation_inputs()):
            raise VideoError('构建至采集间来源已变化，请重新采集')
        with sync_playwright() as pw:
            probes = code_scenes._capture(pw, root, work, config, verify_frames=settings['verifyFrames'],
                                         selected_frames=selected if kind == 'static' else None)
        if kind == 'motion':
            code_scenes._encode(work, destination / 'sample.mp4', count, *size, fps=fps,
                                supersample=int((config.get('motion') or {}).get('supersample', 1)))
        web = destination / 'web'
        web.mkdir()
        copy_build_outputs(work, web)
        # 预览使用同一宿主与时钟；外部控制条在iframe之外，不进入采集帧。
        html = (work / 'index.html').read_text(encoding='utf-8')
        html = html.replace('<head>', '<head><script src="capture-clock.js"></script>', 1)
        (web / 'scene.html').write_text(html, encoding='utf-8')
        shutil.copy2(WEB / 'src/code-scene/capture-clock.js', web / 'capture-clock.js')
        (web / 'index.html').write_text(VIEWER.read_text(encoding='utf-8')
                                     .replace('__SAMPLE_CONFIG__', json.dumps(config, ensure_ascii=True).replace('<', '\\u003c')),
                                     encoding='utf-8')
        stills = []
        for index in selected:
            name = f'still-{index:06d}.png'
            from PIL import Image
            with Image.open(work / f'frame-{index:06d}.png') as image:
                if image.size != size:
                    image = image.resize(size, Image.Resampling.LANCZOS)
                image.save(destination / name)
            stills.append({'frame': index, 'path': name})
        if before != snapshot(root, files):
            raise VideoError('采集期间源码或资源发生变化，请重新采集')
    return {'kind': kind, 'entry': entry, 'props': props, 'fps': fps, 'width': size[0], 'height': size[1],
            'durationInFrames': count, 'stills': stills, 'video': 'sample.mp4' if kind == 'motion' else None,
            'inputs': before, 'config': config, 'determinism': probes,
            'project': {k: project.get(k) for k in ('id', 'type', 'output')}}
