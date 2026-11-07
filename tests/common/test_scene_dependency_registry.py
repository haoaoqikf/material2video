"""登记可扩展，但错误版本、缺失依据和资源加载越界必须明确失败。"""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

REPO = Path(__file__).resolve().parents[2]
HELPER = REPO / 'web/scripts/code-scene-dependencies.mjs'


def run(web, body):
    if not shutil.which('node'):
        pytest.skip('需要Node')
    return subprocess.run(['node', '--input-type=module', '-e',
        f'import {{readSceneDependencies,requireRegisteredDependency}} from {json.dumps(HELPER.as_uri())};'
        f'const web={json.dumps(str(web))};const registry=readSceneDependencies(web);' + body],
        capture_output=True, text=True, encoding='utf-8', timeout=30)


def setup(web, **changes):
    entry = {'version': '1.2.3', 'source': 'https://example.org/native-widget',
             'license': 'MIT', 'integration': '外部组件已适配受控时间'}
    entry.update(changes)
    web.mkdir()
    registry = {'schemaVersion': 1, 'packages': {'native-widget': entry}, 'loaders': {'.glb': 'file'}}
    (web / 'code-scene-dependencies.json').write_text(json.dumps(registry), encoding='utf-8')
    package = web / 'node_modules/native-widget'
    package.mkdir(parents=True)
    (package / 'package.json').write_text(json.dumps({'name': 'native-widget', 'version': '1.2.3'}), encoding='utf-8')
    return registry


def test_new_local_package_is_accepted_from_registry_without_changing_loader(tmp_path):
    web = tmp_path / 'web'
    setup(web)
    result = run(web, "console.log(requireRegisteredDependency(web,registry,'native-widget'));")
    assert result.returncode == 0, result.stderr
    assert 'native-widget' in result.stdout


@pytest.mark.parametrize('changes', [{'version': '^1.2.3'}, {'source': 'file://untracked'},
                                    {'integration': ''}, {'license': ''}, {'unknown': True}])
def test_incomplete_or_unpinned_registration_is_rejected(tmp_path, changes):
    web = tmp_path / 'web'
    setup(web, **changes)
    result = run(web, '')
    assert result.returncode != 0 and '登记无效' in result.stderr


def test_registered_package_version_and_missing_package_are_not_silently_replaced(tmp_path):
    web = tmp_path / 'web'
    setup(web, version='2.0.0')
    result = run(web, "requireRegisteredDependency(web,registry,'native-widget');")
    assert result.returncode != 0 and '版本失配' in result.stderr
    result = run(web, "requireRegisteredDependency(web,registry,'other-widget');")
    assert result.returncode != 0 and '未登记' in result.stderr


def test_asset_loaders_cannot_override_executable_source_parsing(tmp_path):
    web = tmp_path / 'web'
    registry = setup(web)
    registry['loaders']['.tsx'] = 'file'
    (web / 'code-scene-dependencies.json').write_text(json.dumps(registry), encoding='utf-8')
    result = run(web, '')
    assert result.returncode != 0 and '加载登记无效' in result.stderr
