"""字体源损坏不能被同尺寸的正确目标副本掩盖。"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest


def test_same_size_valid_target_does_not_hide_corrupt_source(tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('需要Node.js执行实际字体同步入口')
    template = Path(__file__).resolve().parents[2] / 'templates/standalone'
    script = tmp_path / 'scripts/sync-fonts.mjs'
    script.parent.mkdir()
    shutil.copyfile(template / 'scripts/sync-fonts.mjs', script)
    for name in ['src/assets', 'fonts/files', 'fonts/licenses', 'public/fonts']:
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / 'fonts/files/test.ttf').write_bytes(b'evil')
    (tmp_path / 'public/fonts/test.ttf').write_bytes(b'good')
    (tmp_path / 'fonts/licenses/LICENSE.txt').write_text('fixture license', encoding='utf-8')
    manifest = {'sourceDirFromWeb': 'fonts/files', 'licenseDirFromWeb': 'fonts/licenses',
                'files': [{'family': 'Fixture', 'file': 'test.ttf', 'weight': '400',
                           'usage': 'fixture', 'license': 'LICENSE.txt'}]}
    registry = {'fonts': [{'file': 'test.ttf', 'bytes': 4,
                          'sha256': hashlib.sha256(b'good').hexdigest()}]}
    (tmp_path / 'src/assets/fonts.json').write_text(json.dumps(manifest), encoding='utf-8')
    (tmp_path / 'fonts/registry.json').write_text(json.dumps(registry), encoding='utf-8')
    result = subprocess.run([node, str(script)], cwd=tmp_path, capture_output=True,
                            text=True, encoding='utf-8', timeout=30)
    assert result.returncode != 0
    assert '字体源摘要与登记不符' in result.stderr
    assert (tmp_path / 'public/fonts/test.ttf').read_bytes() == b'good'


def test_font_registry_rejects_escaped_file_name(tmp_path):
    template = Path(__file__).resolve().parents[2] / 'templates/standalone'
    (tmp_path / 'fonts/licenses').mkdir(parents=True)
    shutil.copyfile(template / 'fonts/fetch.py', tmp_path / 'fonts/fetch.py')
    (tmp_path / 'fonts/licenses/LICENSE.txt').write_text('fixture', encoding='utf-8')
    (tmp_path / 'fonts/registry.json').write_text(json.dumps({'schemaVersion': 1, 'fonts': [{
        'id': 'escape', 'file': '../../../escaped.ttf', 'source': 'https://example.invalid',
        'version': '1', 'bytes': 1, 'sha256': '0' * 64, 'license': 'licenses/LICENSE.txt',
        'targets': []}]}), encoding='utf-8')
    result = subprocess.run(['python', 'fonts/fetch.py', '--check'], cwd=tmp_path,
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode != 0
    assert '纯文件名' in result.stdout + result.stderr


def test_sync_fonts_rejects_escaped_source_directory(tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('需要Node.js执行实际字体同步入口')
    template = Path(__file__).resolve().parents[2] / 'templates/standalone'
    (tmp_path / 'scripts').mkdir()
    shutil.copyfile(template / 'scripts/sync-fonts.mjs', tmp_path / 'scripts/sync-fonts.mjs')
    (tmp_path / 'src/assets').mkdir(parents=True)
    (tmp_path / 'fonts').mkdir()
    manifest = {'sourceDirFromWeb': '../../outside', 'licenseDirFromWeb': 'fonts/licenses',
                'files': []}
    (tmp_path / 'src/assets/fonts.json').write_text(json.dumps(manifest), encoding='utf-8')
    (tmp_path / 'fonts/registry.json').write_text(json.dumps({'fonts': []}), encoding='utf-8')
    result = subprocess.run([node, str(tmp_path / 'scripts/sync-fonts.mjs')], cwd=tmp_path,
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode != 0
    assert '越过作品' in result.stderr


def test_sync_fonts_rejects_escaped_license_name(tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('需要Node.js执行实际字体同步入口')
    template = Path(__file__).resolve().parents[2] / 'templates/standalone'
    (tmp_path / 'scripts').mkdir()
    shutil.copyfile(template / 'scripts/sync-fonts.mjs', tmp_path / 'scripts/sync-fonts.mjs')
    for name in ('src/assets', 'fonts/files', 'fonts/licenses', 'public/fonts'):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / 'fonts/files/test.ttf').write_bytes(b'good')
    (tmp_path / 'fonts/licenses/LICENSE.txt').write_text('fixture', encoding='utf-8')
    (tmp_path.parent / 'outside.txt').write_text('outside', encoding='utf-8')
    manifest = {'sourceDirFromWeb': 'fonts/files', 'licenseDirFromWeb': 'fonts/licenses',
                'files': [{'family': 'Fixture', 'file': 'test.ttf', 'weight': '400',
                           'usage': 'fixture', 'license': '../outside.txt'}]}
    (tmp_path / 'src/assets/fonts.json').write_text(json.dumps(manifest), encoding='utf-8')
    (tmp_path / 'fonts/registry.json').write_text(json.dumps({'fonts': [{
        'file': 'test.ttf', 'bytes': 4, 'sha256': hashlib.sha256(b'good').hexdigest()}]}),
        encoding='utf-8')
    result = subprocess.run([node, str(tmp_path / 'scripts/sync-fonts.mjs')], cwd=tmp_path,
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode != 0
    assert '许可文件名必须是纯文件名' in result.stderr


def _junction(link: Path, target: Path) -> None:
    subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                   check=True, capture_output=True, text=True)


@pytest.mark.skipif(__import__('os').name != 'nt', reason='Windows 目录联接')
def test_sync_fonts_rejects_output_directory_junction(tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('需要Node.js执行实际字体同步入口')
    template = Path(__file__).resolve().parents[2] / 'templates/standalone'
    (tmp_path / 'scripts').mkdir()
    shutil.copyfile(template / 'scripts/sync-fonts.mjs', tmp_path / 'scripts/sync-fonts.mjs')
    for name in ('src/assets', 'fonts/files', 'fonts/licenses'):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    outside = tmp_path.parent / 'outside-fonts'
    outside.mkdir()
    (tmp_path / 'public').mkdir()
    _junction(tmp_path / 'public' / 'fonts', outside)
    (tmp_path / 'fonts/files/test.ttf').write_bytes(b'good')
    (tmp_path / 'fonts/licenses/LICENSE.txt').write_text('fixture', encoding='utf-8')
    manifest = {'sourceDirFromWeb': 'fonts/files', 'licenseDirFromWeb': 'fonts/licenses',
                'files': [{'family': 'Fixture', 'file': 'test.ttf', 'weight': '400',
                           'usage': 'fixture', 'license': 'LICENSE.txt'}]}
    (tmp_path / 'src/assets/fonts.json').write_text(json.dumps(manifest), encoding='utf-8')
    (tmp_path / 'fonts/registry.json').write_text(json.dumps({'fonts': [{
        'file': 'test.ttf', 'bytes': 4, 'sha256': hashlib.sha256(b'good').hexdigest()}]}),
        encoding='utf-8')
    result = subprocess.run([node, str(tmp_path / 'scripts/sync-fonts.mjs')], cwd=tmp_path,
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode != 0
    assert not (outside / 'test.ttf').exists() and not (outside / 'manifest.json').exists()


@pytest.mark.skipif(__import__('os').name != 'nt', reason='Windows 目录联接')
def test_font_fetch_rejects_files_directory_junction(tmp_path):
    template = Path(__file__).resolve().parents[2] / 'templates/standalone'
    (tmp_path / 'fonts/licenses').mkdir(parents=True)
    shutil.copyfile(template / 'fonts/fetch.py', tmp_path / 'fonts/fetch.py')
    (tmp_path / 'fonts/licenses/LICENSE.txt').write_text('fixture', encoding='utf-8')
    outside = tmp_path.parent / 'outside-files'
    outside.mkdir()
    _junction(tmp_path / 'fonts' / 'files', outside)
    data = b'font'
    (tmp_path / 'fonts/.cache').mkdir()
    (tmp_path / 'fonts/.cache/test.ttf').write_bytes(data)
    (tmp_path / 'fonts/registry.json').write_text(json.dumps({'schemaVersion': 1, 'fonts': [{
        'id': 'test', 'file': 'test.ttf', 'source': 'https://example.invalid', 'version': '1',
        'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
        'license': 'licenses/LICENSE.txt', 'targets': []}]}), encoding='utf-8')
    result = subprocess.run(['python', 'fonts/fetch.py'], cwd=tmp_path, capture_output=True,
                            text=True, encoding='utf-8', timeout=30)
    assert result.returncode != 0
    assert '链接指向作品外' in result.stdout + result.stderr
    assert not (outside / 'test.ttf').exists()


def test_sync_fonts_rejects_file_symlink_target(tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('需要Node.js执行实际字体同步入口')
    template = Path(__file__).resolve().parents[2] / 'templates/standalone'
    (tmp_path / 'scripts').mkdir()
    shutil.copyfile(template / 'scripts/sync-fonts.mjs', tmp_path / 'scripts/sync-fonts.mjs')
    for name in ('src/assets', 'fonts/files', 'fonts/licenses', 'public/fonts'):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    outside = tmp_path.parent / 'outside-target.ttf'
    outside.write_bytes(b'outside')
    try:
        (tmp_path / 'public/fonts/test.ttf').symlink_to(outside)
    except OSError:
        pytest.skip('当前用户不能创建文件符号链接')
    (tmp_path / 'fonts/files/test.ttf').write_bytes(b'good')
    (tmp_path / 'fonts/licenses/LICENSE.txt').write_text('fixture', encoding='utf-8')
    manifest = {'sourceDirFromWeb': 'fonts/files', 'licenseDirFromWeb': 'fonts/licenses',
                'files': [{'family': 'Fixture', 'file': 'test.ttf', 'weight': '400',
                           'usage': 'fixture', 'license': 'LICENSE.txt'}]}
    (tmp_path / 'src/assets/fonts.json').write_text(json.dumps(manifest), encoding='utf-8')
    (tmp_path / 'fonts/registry.json').write_text(json.dumps({'fonts': [{
        'file': 'test.ttf', 'bytes': 4, 'sha256': hashlib.sha256(b'good').hexdigest()}]}),
        encoding='utf-8')
    result = subprocess.run([node, str(tmp_path / 'scripts/sync-fonts.mjs')], cwd=tmp_path,
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode != 0
    assert outside.read_bytes() == b'outside'
