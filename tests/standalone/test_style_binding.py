"""从正常初始化与本地入口检查隔离运行、授权范围及准备失效。"""
import copy
import json
from pathlib import Path

import pytest

from m2v.core import project as manager
from m2v.core import style_binding as style
from m2v.core.errors import M2VError
from m2v.standalone.scaffold import create
from m2v.type_system.catalog import catalog
from film_runtime.core import project as standalone
from film_runtime.core.errors import VideoError


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


@pytest.fixture
def work(tmp_path):
    create(tmp_path, 'data-evolution')
    return tmp_path, manager.load_project(tmp_path)[1]


@pytest.mark.parametrize('kind', catalog().names())
def test_published_revision_survives_catalog_change(tmp_path, kind, monkeypatch):
    create(tmp_path, kind)
    root, manifest = manager.load_project(tmp_path)
    published = catalog().get(kind).default_style
    monkeypatch.setitem(published, 'revision', published['revision'] + 1)
    assert standalone.load_project(root)[1] == manifest
    assert style.load_binding(root, manifest)['visualStyle']['revision'] < published['revision']
    local_code = root/'runtime/python/film_runtime/core/style_binding.py'
    assert local_code.read_text('utf-8') == Path(style.__file__).read_text('utf-8')


@pytest.mark.parametrize('problem', ['missing', 'old', 'digest', 'authorization', 'escape',
                                    'unknown-scene', 'conflict', 'snapshot', 'role', 'self-reference'])
def test_both_loaders_reject_invalid_binding(work, problem):
    root, manifest = work
    path = root/style.BINDING
    data = style.load_binding(root, manifest)
    target = copy.deepcopy(data['visualStyle'])
    (root/'authorization.txt').write_text('采用此专项', encoding='utf-8')
    override = {'target': target, 'referenceDigest': data['referenceDigest'],
                'scope': {'scenes': ['opening'], 'uses': [target['references'][0]['id']]},
                'authorization': {'at': '2026-11-28T03:00:00+08:00', 'source': 'authorization.txt',
                                  'quote': '采用此专项'}}
    data['overrides'] = [override]
    save(path, data)
    assert standalone.load_project(root)[1] == manifest
    if problem == 'missing':
        path.unlink()
    else:
        if problem == 'old':
            data['schemaVersion'] = 0
        elif problem == 'digest':
            target['references'][0]['scope'] += 'changed'
        elif problem == 'authorization':
            override['authorization']['quote'] = '未授权'
        elif problem == 'self-reference':
            override['authorization']['source'] = style.BINDING
        elif problem == 'escape':
            override['authorization']['source'] = '../authorization.txt'
        elif problem == 'unknown-scene':
            override['scope']['scenes'] = ['missing']
        elif problem == 'conflict':
            data['overrides'].append(override)
        elif problem == 'role':
            target['references'] = [ref for ref in target['references'] if ref['role'] != 'overall']
            override['referenceDigest'] = style.fingerprint(target)
        elif problem == 'snapshot':
            ref = target['references'][0]
            target['snapshot'] = {ref['id']: {'path': 'authorization.txt', 'sha256': ref['evidence']['sha256']}}
            override['referenceDigest'] = style.fingerprint(target)
        save(path, data)
    for loader, error in ((manager, M2VError), (standalone, VideoError)):
        with pytest.raises(error, match='风格绑定'):
            loader.load_project(root)


def test_old_or_modified_preparation_is_rejected_by_both_consumers(work):
    root, manifest = work
    inputs = standalone.file_inputs(root, manifest)
    assert inputs == manager.file_inputs(root, manifest)
    params = dict(project=manifest, composition_id='SceneFilm', props={}, width=1920,
                  height=1080, fps=30, duration_in_frames=30)
    standalone.save_prepared(root, inputs=inputs, **params)
    for loader in (manager, standalone):
        assert loader.load_current_prepared(root, manifest)['inputs'] == inputs
    path = root/style.BINDING
    path.write_bytes(path.read_bytes()+b'\n')
    for loader, error in ((manager, M2VError), (standalone, VideoError)):
        with pytest.raises(error, match='prepare'):
            loader.load_current_prepared(root, manifest)
    del inputs['file:'+style.BINDING]
    standalone.save_prepared(root, inputs=inputs, **params)
    for loader, error in ((manager, M2VError), (standalone, VideoError)):
        with pytest.raises(error, match='风格绑定'):
            loader.load_current_prepared(root, manifest)
