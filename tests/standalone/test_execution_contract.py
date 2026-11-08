"""独立工程manifest和本地委托入口的失败边界。"""
import json
from pathlib import Path

import pytest

from film_runtime.core.errors import VideoError
from film_runtime.core.execution import command
from film_runtime.core.project import load_project


def write_project(root: Path, **changes):
    root.mkdir(parents=True, exist_ok=True)
    value = {'schemaVersion': 3, 'id': 'unit-video', 'type': 'text-motion',
             'materials': {'storyboard': 'storyboard.json'}}
    value.update(changes)
    (root / 'project.json').write_text(json.dumps(value), encoding='utf-8')
    return value


@pytest.mark.parametrize('version', [1, 2, 3.0, True, '3', None])
def test_old_or_non_integer_project_contract_is_rejected(tmp_path, version):
    write_project(tmp_path, schemaVersion=version)
    with pytest.raises(VideoError, match='schemaVersion'):
        load_project(tmp_path)


def test_independent_project_does_not_need_parent_layout_or_management_protocol(tmp_path):
    root = tmp_path / 'a folder' / 'renamed-project'
    value = write_project(root)
    assert load_project(root) == (root.resolve(), value)
    assert command(root, value) is None
    with pytest.raises(VideoError, match='runtime'):
        command(root, value, required=True)


@pytest.mark.parametrize('entry', ['../external.py', '/external.py', 'scripts/missing.py', 'scripts\\video.py'])
def test_management_protocol_rejects_missing_or_external_entry(tmp_path, entry):
    value = write_project(tmp_path, runtime={'version': 1, 'command': ['python', entry]})
    with pytest.raises(VideoError, match='入口'):
        command(tmp_path, value, required=True)


def test_management_protocol_passes_argv_without_shell_interpretation(tmp_path):
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'scripts/video.py').write_text('pass', encoding='utf-8')
    args = ['uv', 'run', '--frozen', 'python', 'scripts/video.py']
    value = write_project(tmp_path, runtime={'version': 1, 'command': args})
    assert command(tmp_path, value, required=True) == args
    assert command(tmp_path, value, required=True) is not args


def test_material_reference_cannot_escape_project(tmp_path):
    root = tmp_path / 'project'
    write_project(root, materials={'storyboard': '../outside.json'})
    with pytest.raises(VideoError, match='越过'):
        load_project(root)
