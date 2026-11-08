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
