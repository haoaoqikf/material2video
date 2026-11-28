"""准备和候选身份属于作品；外部工具只复核本地记录和真实输入。"""
import importlib
import json
from pathlib import Path
import shutil
import os
import subprocess

import pytest

from m2v.core import delivery, project as projects
from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from m2v.production import dependencies


def prepared_work(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'storyboard.json').write_text('{"fps":30}', encoding='utf-8')
    (root / 'owned.py').write_text('original', encoding='utf-8')
    project = {'schemaVersion': 3, 'id': 'binding-test', 'type': 'text-motion',
               'materials': {'storyboard': 'storyboard.json'}, 'output': {'fps': 30}}
    from m2v.standalone.scaffold import install_default_style
    install_default_style(root, project)
    inputs = {**projects.file_inputs(root, project), 'file:owned.py': delivery.digest(root / 'owned.py'),
              'implementation': 'own-python', 'renderer': 'own-node'}
    prepared = projects.save_prepared(root, project=project, composition_id='SceneFilm', props={'version': 9},
        width=1920, height=1080, fps=30, duration_in_frames=90, inputs=inputs)
    (root / 'project.json').write_text(json.dumps(project), encoding='utf-8')
    return project, prepared


@pytest.mark.parametrize('module,error', [('m2v.core.project', M2VError),
    ('film_runtime.core.project', importlib.import_module('film_runtime.core.errors').VideoError)])
def test_actual_adopted_input_change_invalidates_preparation(tmp_path, module, error):
    project, prepared = prepared_work(tmp_path)
    reader = importlib.import_module(module).load_current_prepared
    assert reader(tmp_path, project) == prepared
    (tmp_path / 'owned.py').write_text('updated', encoding='utf-8')
    with pytest.raises(error, match='变化'):
        reader(tmp_path, project)


@pytest.mark.parametrize('version', [1, 2, 3.0, True])
def test_main_rejects_old_or_non_integer_project_version(tmp_path, version):
    project, _ = prepared_work(tmp_path)
    project['schemaVersion'] = version
    (tmp_path / 'project.json').write_text(json.dumps(project), encoding='utf-8')
    with pytest.raises(M2VError, match='schemaVersion'):
        projects.load_project(tmp_path)


@pytest.mark.parametrize('kind', ['old-contract', 'absolute-input'])
def test_signed_but_old_or_nonportable_prepared_is_rejected(tmp_path, kind):
    project, prepared = prepared_work(tmp_path)
    if kind == 'old-contract':
        prepared['contractVersion'] = 2
    else:
        prepared['inputs']['file:' + (tmp_path / 'owned.py').as_posix()] = delivery.digest(tmp_path / 'owned.py')
        prepared['materialFingerprint'] = fingerprint({'project': project, 'inputs': prepared['inputs']})
    prepared.pop('preparedFingerprint')
    prepared['preparedFingerprint'] = fingerprint(prepared)
    (tmp_path / projects.PREPARED_FILE).write_text(json.dumps(prepared), encoding='utf-8')
    with pytest.raises(M2VError):
        projects.load_current_prepared(tmp_path, project)


@pytest.mark.parametrize('field,value', [('inputs', {'file:a': 123}), ('props', []),
    ('width', True), ('fps', 30.0), ('durationInFrames', 0), ('audio', None)])
def test_self_consistent_but_malformed_prepared_is_rejected(tmp_path, field, value):
    project, prepared = prepared_work(tmp_path)
    prepared[field] = value
    prepared.pop('preparedFingerprint')
    prepared['preparedFingerprint'] = fingerprint(prepared)
    (tmp_path / projects.PREPARED_FILE).write_text(json.dumps(prepared), encoding='utf-8')
    with pytest.raises(M2VError, match='准备记录'):
        projects.load_current_prepared(tmp_path, project)


def test_moved_candidate_keeps_identity_without_global_renderer(tmp_path, monkeypatch):
    root = tmp_path / 'original'
    project, prepared = prepared_work(root)
    video = root / 'outputs/candidate.mp4'
    video.write_bytes(b'complete-candidate')
    binding = delivery.binding(root, prepared, {'crf': 18})
    record = {**binding, 'key': fingerprint(binding), 'status': 'delivered',
              'path': 'outputs/candidate.mp4', 'sha256': delivery.digest(video)}
    projects._write_json(root / 'outputs/delivery.json', record)
    moved = tmp_path / 'renamed folder'
    shutil.copytree(root, moved)
    shutil.rmtree(root)
    # 身份来自作品的已绑定实现，检查器不读取任何全局渲染入口。
    assert projects.load_current_prepared(moved, project) == prepared
    assert Path(delivery.candidate(moved, prepared)['path']) == moved / 'outputs/candidate.mp4'
    record['width'] = 720  # 记录不能借用原key隐藏不同技术参数。
    projects._write_json(moved / 'outputs/delivery.json', record)
    with pytest.raises(M2VError, match='参数'):
        delivery.candidate(moved, prepared)


def test_dependency_snapshot_only_tracks_owned_reachable_sources(tmp_path, monkeypatch):
    root = tmp_path / 'work'
    (root / 'scenes').mkdir(parents=True)
    (root / 'components').mkdir()
    (root / 'scenes/main.tsx').write_text('import {value} from "../components/math"; export default value;', encoding='utf-8')
    (root / 'components/math.ts').write_text('export const value=1;', encoding='utf-8')
    unused = root / 'components/unused.ts'
    unused.write_text('unused', encoding='utf-8')
    scene = {'content': {'entry': 'scenes/main.tsx'}}
    before = dependencies.scene_sources(root, scene)
    assert set(before['files']) == {'work/scenes/main.tsx', 'work/components/math.ts'}
    unused.write_text('irrelevant update', encoding='utf-8')
    assert dependencies.scene_sources(root, scene) == before
    (root / 'components/math.ts').write_text('export const value=2;', encoding='utf-8')
    assert dependencies.scene_sources(root, scene) != before


def test_legacy_sdk_reference_is_rejected_instead_of_resolved_from_main(tmp_path):
    scene = tmp_path / 'main.tsx'
    scene.write_text('import {Chart} from "m2v/code-scene";', encoding='utf-8')
    with pytest.raises(M2VError, match='主项目运行时'):
        dependencies.scene_sources(tmp_path, {'content': {'entry': 'main.tsx'}})


@pytest.mark.parametrize('argument,conservative', [("'earth'", False), ('bodyId', True)])
def test_media_hook_declaration_does_not_turn_static_calls_into_dynamic_bindings(tmp_path, argument, conservative):
    """真实动态调用仍保守绑定；SDK函数声明不会把无关声音和缓存绑进样品。"""
    (tmp_path / 'assets').mkdir()
    for name in ('earth.png', 'unused.wav'):
        (tmp_path / 'assets' / name).write_bytes(name.encode())
    (tmp_path / 'assets/media-sources.json').write_text(json.dumps({'assets': [
        {'id': 'earth', 'path': 'assets/earth.png'}]}), encoding='utf-8')
    (tmp_path / 'main.tsx').write_text(
        'export function\nuseMediaAsset(id: string) { return id; }\n'
        f'export const asset = useMediaAsset({argument});', encoding='utf-8')
    result = dependencies.scene_sources(tmp_path, {'content': {'entry': 'main.tsx'}})
    assert bool(result['conservativeReasons']) is conservative
    assert ('work/assets/unused.wav' in result['files']) is conservative
    assert 'work/assets/earth.png' in result['files']


@pytest.mark.skipif(os.name != 'nt', reason='Windows目录联接边界')
def test_font_junction_is_rejected_before_external_directory_is_read(tmp_path, monkeypatch):
    root = tmp_path / 'work'
    outside = tmp_path / 'external'
    outside.mkdir()
    (outside / 'secret.ttf').write_bytes(b'font')
    (root / 'fonts').mkdir(parents=True)
    (root / 'scene.ts').write_text('export default 1;', encoding='utf-8')
    link = root / 'fonts/files'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)], capture_output=True)
    assert result.returncode == 0
    original = os.scandir
    def no_external_scan(path):
        if Path(path).resolve().is_relative_to(outside):
            pytest.fail('external directory was read before boundary check')
        return original(path)
    monkeypatch.setattr(os, 'scandir', no_external_scan)
    try:
        with pytest.raises(M2VError, match='越过作品'):
            dependencies.scene_sources(root, {'content': {'entry': 'scene.ts'}})
    finally:
        link.rmdir()  # 仅删除联接本身，不递归触碰目标。


def test_success_cleanup_preserves_current_relative_candidate_and_receipt(tmp_path):
    from m2v.core.output_cleanup import cleanup_after_render
    base = tmp_path / 'outputs'
    current = base / 'video.mp4'
    candidate_file = base / 'candidates/current.mp4'
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_bytes(b'current')
    current.write_bytes(b'current')
    old = base / 'candidates/old.mp4'
    old.write_bytes(b'old')
    receipt = candidate_file.with_suffix('.delivery.json')
    receipt.write_text('{}', encoding='utf-8')
    (base / 'delivery.json').write_text(json.dumps({'path': 'outputs/candidates/current.mp4'}), encoding='utf-8')
    assert not cleanup_after_render(base, current)
    assert candidate_file.exists() and receipt.exists()
    assert not old.exists()


@pytest.mark.skipif(os.name != 'nt', reason='Windows素材目录联接边界')
@pytest.mark.parametrize('module,error', [('m2v.types.scene_film.media_assets', M2VError),
    ('film_runtime.types.scene_film.media_assets', importlib.import_module('film_runtime.core.errors').VideoError)])
@pytest.mark.parametrize('kind', ['media', 'record', 'import'])
def test_media_helpers_reject_external_junction_before_read_or_write(tmp_path, monkeypatch, module, error, kind):
    helper = importlib.import_module(module)
    root, outside = tmp_path / 'work', tmp_path / 'external'
    root.mkdir()
    outside.mkdir()
    (outside / 'media-sources.json').write_text('{"schemaVersion":1,"assets":[]}', encoding='utf-8')
    if kind == 'record':
        link = root / 'assets'
    else:
        (root / 'assets').mkdir()
        link = root / 'assets/media'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)], capture_output=True)
    assert result.returncode == 0
    original = Path.read_text
    def no_external_read(path, *args, **kwargs):
        if path.resolve().is_relative_to(outside):
            pytest.fail('external registry was read')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', no_external_read)
    try:
        with pytest.raises(error, match='越过作品'):
            if kind == 'record':
                helper.load_record(root)
            elif kind == 'import':
                helper.import_assets(root, {'schemaVersion': 1, 'assets': [{}]}, base=root)
            else:
                helper.resolve(root)
    finally:
        link.rmdir()
