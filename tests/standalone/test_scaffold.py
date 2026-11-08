"""五类初始化生成完整、无开发机依赖的作品。"""
import json
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.core.project import load_project
from m2v.standalone.scaffold import create, template_files
from m2v.type_system.catalog import catalog


@pytest.mark.parametrize('video_type', catalog().names())
def test_all_types_create_complete_independent_project(tmp_path, video_type):
    root = tmp_path / 'a folder' / video_type
    create(root, video_type)
    resolved, manifest = load_project(root)
    assert resolved == root.resolve()
    assert manifest['type'] == video_type
    assert manifest['schemaVersion'] == 3
    board = json.loads((root / manifest['materials']['storyboard']).read_text(encoding='utf-8'))
    assert (root / board['scenes'][0]['content']['entry']).is_file()
    for required in ['uv.lock', 'pnpm-lock.yaml', 'package.json', 'scripts/video.py',
                     'runtime/python/film_runtime/cli.py', 'fonts/registry.json']:
        assert (root / required).is_file()
    node = json.loads((root / 'package.json').read_text(encoding='utf-8'))
    assert 'three' not in node['dependencies']
    assert 'prepare' not in node['scripts']  # 不在安装生命周期隐式准备作品。
    assert not (root / '.venv').exists()
    assert not (root / 'node_modules').exists()
    assert not (root / 'fonts/files').exists()
    for file in root.rglob('*.py'):
        assert 'from m2v' not in file.read_text(encoding='utf-8')


def test_existing_content_is_not_overwritten(tmp_path):
    marker = tmp_path / 'keep.txt'
    marker.write_text('keep', encoding='utf-8')
    with pytest.raises(M2VError, match='非空'):
        create(tmp_path, 'text-motion')
    assert marker.read_text() == 'keep'


def test_template_inventory_excludes_binaries_caches_and_links():
    files = template_files()
    assert files
    for path in files:
        assert not {'.venv', 'node_modules', 'outputs', '.cache', '__pycache__'} & set(path.parts)
        assert path.suffix not in {'.ttf', '.woff2', '.mp4', '.pyc', '.png'}


def test_explicit_init_location_does_not_require_type_in_parent_directory(tmp_path):
    from m2v import cli, commands
    root = tmp_path / 'videos' / 'renamed folder'
    assert cli.main(['init', '--type', 'text-motion', '--project', str(root)]) == 0
    assert load_project(root)[1]['type'] == 'text-motion'
