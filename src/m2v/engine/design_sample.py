"""原生样品委托及输入／产物复核；采集和编码实现由作品拥有。"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image

from m2v.core.delivery import digest
from m2v.core.errors import M2VError
from m2v.core.video_config import project_fps
from m2v.engine.output_validation import verify_output
from m2v.production.storage import local
from m2v.standalone import executor

RESULT_FIELDS = {'entry', 'props', 'fps', 'width', 'height', 'durationInFrames',
                 'stills', 'video', 'inputs', 'config', 'project', 'determinism'}


def input_path(root: Path, label: str) -> Path:
    if not isinstance(label, str) or not label.startswith('work/'):
        raise M2VError('样品输入必须属于作品，不能引用主项目或旧共享运行时')
    reference = label[len('work/'):]
    executor.local_artifact(root, reference)
    return local(root, reference)


def snapshot(root: Path, paths: list[Path]) -> dict[str, str]:
    root = root.resolve()
    result = {}
    for path in paths:
        path = path.resolve()
        if not path.is_relative_to(root):
            raise M2VError('样品输入越过作品目录')
        reference = path.relative_to(root).as_posix()
        result['work/' + reference] = digest(local(root, reference))
    return result


def media_files(root: Path, media: dict) -> dict[str, Path]:
    from m2v.types.scene_film.media_assets import load_record
    entries = {row['id']: row for row in load_record(root)['assets']}
    if not isinstance(media, dict) or set(media) != set(entries):
        raise M2VError('样品媒体白名单与作品来源登记不符')
    files = {}
    for identity, value in media.items():
        row = entries[identity]
        file = local(root, row['path'])
        if (not isinstance(value, dict) or value.get('src') != '/media/' + file.name
                or not file.is_relative_to(root / 'assets/media')):
            raise M2VError('样品媒体地址必须为本地登记的/media/地址')
        files[value['src']] = file
    return files


def visible_props(props: dict) -> dict:
    """采集调度字段不进入画面；按公开的capture契约核对实际播放器参数。"""
    value = dict(props)
    capture = value.pop('capture', None)
    if isinstance(capture, dict):
        visible = {key: item for key, item in capture.items() if key in ('mode', 'timebase')}
        if visible:
            value['capture'] = visible
    elif 'capture' in props:
        raise M2VError('样品capture必须为对象')
    return value


def source_binding(root: Path, entry: str, props: dict, *, project: dict | None = None,
                   props_source: str | None = None) -> dict:
    """独立追踪作品可达输入，不以作品回报的输入列表替代外部核验。"""
    from m2v.production import dependencies
    from m2v.types.scene_film import media_assets
    project_path = local(root, 'project.json')
    project_sha = digest(project_path)
    if project is not None and executor.read_json(project_path) != project:
        raise M2VError('样品采集前或采集期间磁盘作品描述已变化')
    extra = {'work/project.json': project_sha}
    if props_source:
        props_path = input_path(root, 'work/' + props_source)
        extra['work/' + props_source] = digest(props_path)
        if executor.read_json(props_path) != props:
            raise M2VError('样品采集前或采集期间参数文件已变化')
    with dependencies.snapshot(fresh=True):
        sources = dependencies.scene_sources(root, {'content': {'entry': entry, 'props': props}})
    files = {**sources['files'], **extra}
    media = media_assets.resolve(root)['media']
    record = root / media_assets.RECORD
    if record.exists():
        files['work/' + media_assets.RECORD] = digest(local(root, media_assets.RECORD))
        for row in media_assets.load_record(root)['assets']:
            files['work/' + row['path']] = digest(local(root, row['path']))
    return {'files': files, 'media': media, 'props': visible_props(props)}


def validate_source_binding(root: Path, value: dict, binding: dict | None = None) -> dict:
    binding = binding or source_binding(root, value['entry'], value['props'])
    if (value['config'].get('props') != binding['props']
            or value['config'].get('media') != binding['media']):
        raise M2VError('样品实际播放参数或媒体与请求／登记不符')
    if any(value['inputs'].get(name) != sha for name, sha in binding['files'].items()):
        raise M2VError('样品遗漏或改变了实际可达来源、字体、控制实现或素材绑定')
    return binding


def render(root: Path, project: dict, destination: Path, *, entry: str, props: dict,
           duration_seconds: float, still_frames: list[int] | None = None,
           props_source: str | None = None) -> dict:
    """本地执行先完成私有包；验证失败不会写入采集事件或发布正式样品。"""
    if (type(duration_seconds) not in (int, float) or not math.isfinite(duration_seconds)
            or duration_seconds <= 0):
        raise M2VError('样品时长必须为有限正数')
    root = root.resolve()
    destination = destination.resolve()
    if not destination.is_relative_to(root / 'outputs/samples'):
        raise M2VError('样品暂存目标必须位于作品outputs/samples内')
    relative = destination.relative_to(root).as_posix()
    local(root, relative, exists=False)
    fps = project_fps(root, project, allow_missing_storyboard=True)
    count = round(duration_seconds * fps)
    if count < 2 or (still_frames is not None and (not still_frames or any(
            type(frame) is not int or not 0 <= frame < count for frame in still_frames))):
        raise M2VError('样品必须至少两帧，静帧位置必须在实际窗口内')
    before = source_binding(root, entry, props, project=project, props_source=props_source)
    options = ['--entry', entry, '--props', json.dumps(props, ensure_ascii=False, allow_nan=False),
               '--duration-seconds', str(duration_seconds), '--destination', relative]
    if props_source:
        options += ['--props-source', props_source]
    for frame in still_frames or []:
        options += ['--frame', str(frame)]
    outcome = executor.execute(root, project, 'sample', options)
    capture = executor.local_artifact(root, outcome['path'])
    if capture != destination / 'capture.json':
        raise M2VError('本地样品返回了不同的采集位置')
    value = executor.read_json(capture)
    if set(value) != RESULT_FIELDS | {'artifacts'}:
        raise M2VError('样品结果字段缺失或未知')
    expected = {'entry': entry, 'props': props, 'fps': fps,
                'project': {key: project.get(key) for key in ('id', 'type', 'output')}}
    if any(value.get(key) != item for key, item in expected.items()):
        raise M2VError('样品来源、参数、帧率或作品身份不符')
    if (any(type(value.get(k)) is not int or value[k] <= 0 for k in ('width', 'height', 'durationInFrames'))
            or value['durationInFrames'] != round(duration_seconds * expected['fps'])
            or not isinstance(value.get('config'), dict)
            or not isinstance(value['config'].get('media'), dict)
            or any(value['config'].get(k) != value[k] for k in ('width', 'height', 'fps', 'durationInFrames'))
            or not isinstance(value.get('inputs'), dict) or not value['inputs']
            or not isinstance(value.get('artifacts'), dict) or not value['artifacts']
            or not isinstance(value.get('stills'), list) or not value['stills']):
        raise M2VError('样品时长、配置、输入或产物结构无效')
    if (not isinstance(value['video'], str)
            or any(project.get('output', {}).get(k, value[k]) != value[k] for k in ('width', 'height'))):
        raise M2VError('样品视频入口或画幅与作品不符')
    if any(not isinstance(row, dict) or set(row) != {'frame', 'path'}
           or type(row['frame']) is not int or not 0 <= row['frame'] < value['durationInFrames']
           for row in value['stills']):
        raise M2VError('样品静帧结构或帧号无效')
    needed_inputs = {'work/project.json', 'work/' + entry}
    if props_source:
        needed_inputs.add('work/' + props_source)
    if not needed_inputs.issubset(value['inputs']):
        raise M2VError('样品缺少作品描述、场景或参数文件绑定')
    validate_source_binding(root, value, before)
    control = props.get('capture', {})
    mode = control.get('mode', 'sequential')
    timebase = control.get('timebase', 'global' if mode == 'pure-time' else 'local')
    timeline = {'sceneStartFrame': 0, 'sceneEndFrame': count, 'durationInFrames': count}
    if (mode not in ('sequential', 'pure-time') or timebase not in ('local', 'global')
            or mode == 'pure-time' and timebase != 'global'
            or value['config'].get('captureMode', 'sequential') != mode
            or value['config'].get('timeline') != (timeline if timebase == 'global' else None)):
        raise M2VError('样品实际采集模式或时间原点与请求不符')
    for label, sha in value['inputs'].items():
        if digest(input_path(root, label)) != sha:
            raise M2VError(f'样品来源已变化：{label}')
    for name, sha in value['artifacts'].items():
        if digest(executor.local_artifact(destination, name)) != sha:
            raise M2VError(f'样品产物已变化：{name}')
    wanted = sorted(set(still_frames if still_frames is not None else [value['durationInFrames'] - 1]))
    if [row.get('frame') for row in value['stills']] != wanted:
        raise M2VError('样品静帧与实际请求位置不符')
    required = [value.get('video'), 'web/index.html', 'web/scene.html', 'web/capture-clock.js']
    for row in value['stills']:
        file = executor.local_artifact(destination, row['path'])
        required.append(row['path'])
        with Image.open(file) as picture:
            if picture.size != (value['width'], value['height']):
                raise M2VError('样品静帧尺寸与当前画幅不符')
    if any(name not in value['artifacts'] for name in required):
        raise M2VError('样品缺少绑定的同源网页、静帧或视频')
    verify_output(local(destination, value['video']), value['durationInFrames'],
                  value['width'], value['height'], value['fps'], expect_audio=False,
                  require_delivery_format=False)
    # 独立解码期间也可能发生编辑；发布前重新读取，不复用查询级摘要缓存。
    if snapshot(root, [input_path(root, label) for label in value['inputs']]) != value['inputs']:
        raise M2VError('样品验证期间来源发生变化')
    if source_binding(root, entry, props, project=project, props_source=props_source) != before:
        raise M2VError('样品采集或验证期间可达来源／素材登记发生变化')
    for name, sha in value['artifacts'].items():
        if digest(executor.local_artifact(destination, name)) != sha:
            raise M2VError('样品验证期间产物发生变化')
    value.pop('artifacts')
    return value
