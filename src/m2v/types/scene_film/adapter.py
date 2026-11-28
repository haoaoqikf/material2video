"""三类制作工具均委托作品本地入口，不加载主项目生产画面。"""
from pathlib import Path
import json

from m2v.core.errors import M2VError
from m2v.core.preview import window
from m2v.engine.output_validation import verify_output
from m2v.standalone import executor


def validate(root: Path, project: dict) -> None:
    result = executor.execute(root, project, 'validate', timeout=120)
    if result.get('status') != 'pass':
        raise M2VError('作品本地材料校验未通过')


def prepare(root: Path, project: dict, *, voice=None, rate=None, rhythm=None, backend=None) -> dict:
    arguments = []
    if voice is not None:
        arguments.append('--voice=' + voice)
    if rate is not None:
        arguments.append('--rate=' + rate)
    if backend is not None:
        arguments.append('--backend=' + backend)
    if rhythm:
        arguments.append('--rhythm=' + json.dumps(rhythm, ensure_ascii=False))
    return executor.prepare(root, project, arguments)


def preview(root: Path, project: dict, *, limit_frames=None, start_seconds=0, end_seconds=None, jobs=1) -> Path:
    arguments = ['--jobs', str(jobs), '--start-seconds', str(start_seconds)]
    if limit_frames is not None:
        arguments += ['--limit-frames', str(limit_frames)]
    if end_seconds is not None:
        arguments += ['--end-seconds', str(end_seconds)]
    result = executor.execute(root, project, 'preview', arguments)
    from m2v.core.project import load_current_prepared
    prepared = load_current_prepared(root, project)
    start, end = window(prepared['durationInFrames'], prepared['fps'], start_seconds=start_seconds,
                        end_seconds=end_seconds, limit_frames=limit_frames)
    return _verify(root, project, result, prepared, start, end)


def _verify(root, project, result, prepared, start, end):
    from m2v.core.audio_policy import declared_audio
    from m2v.core.delivery import digest
    from m2v.core.project import load_current_prepared
    path = executor.local_artifact(root, result['path'])
    if result.get('preparedFingerprint') != prepared['preparedFingerprint']:
        raise M2VError('视频执行结果与当前准备身份不符')
    provenance_path = path.with_suffix('.provenance.json')
    provenance = executor.read_json(executor.local_artifact(root, provenance_path.relative_to(root).as_posix()))
    expected = {'preparedFingerprint': prepared['preparedFingerprint'], 'startFrame': start,
                'durationInFrames': end-start, 'fps': prepared['fps'],
                'width': prepared['width'], 'height': prepared['height']}
    if (any(provenance.get(k) != v for k, v in expected.items())
            or not isinstance(provenance.get('delivery'), dict)
            or provenance['delivery'].get('sha256') != result['sha256']):
        raise M2VError('视频溯源与当前准备身份、窗口或文件摘要不符')
    verify_output(path, end-start, prepared['width'], prepared['height'], prepared['fps'],
                  expect_audio=declared_audio(prepared))
    if digest(path) != result['sha256']:
        raise M2VError('视频在独立技术复核期间变化')
    if load_current_prepared(root, project)['preparedFingerprint'] != prepared['preparedFingerprint']:
        raise M2VError('技术复核期间准备身份变化')
    return path


def render(root: Path, project: dict, *, jobs=1) -> Path:
    result = executor.execute(root, project, 'render', ['--jobs', str(jobs)])
    from m2v.core.project import load_current_prepared
    from m2v.core.delivery import candidate
    prepared = load_current_prepared(root, project)
    record = candidate(root, prepared)
    if (record.get('status') != 'delivered' or record['sha256'] != result['sha256']
            or executor.local_artifact(root, record.get('destination')) != executor.local_artifact(root, result['path'])):
        raise M2VError('完整导出结果与当前已交付候选不符')
    return _verify(root, project, result, prepared, 0, prepared['durationInFrames'])
