"""示例音轨恢复须拒绝已有摘要漂移，并保护原文件和固定配方。"""
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import wave

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'examples/spatial-3d/solar-system-journey/assets/sound/generate.py'


@pytest.mark.parametrize('damage', ['none', 'audio', 'missing', 'generator', 'line-endings'])
def test_sound_recipe_check_preserves_existing_files(tmp_path, monkeypatch, damage):
    folder = tmp_path / 'assets/sound'
    folder.mkdir(parents=True)
    script = folder / 'generate.py'
    shutil.copy2(SOURCE, script)
    (tmp_path / 'storyboard.json').write_text(json.dumps({'fps': 30, 'scenes': [
        {'durationFrames': 60, 'content': {'props': {'shots': []}}}]}), encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', [str(script)])
    generator = runpy.run_path(str(script), run_name='recipe_fixture')
    files = {}
    for name in generator['NAMES']:
        with wave.open(str(folder / name), 'wb') as stream:
            stream.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\0\0' * 100)
        files[name] = {'sha256': hashlib.sha256((folder / name).read_bytes()).hexdigest(),
                       'durationSeconds': 100 / 24000}
    recipe = folder / 'recipe.json'
    recipe.write_text(json.dumps({'version': 1, 'inputs': generator['source_inputs'](), 'files': files}), encoding='utf-8')
    if damage == 'audio':
        (folder / generator['NAMES'][1]).write_bytes(b'changed existing audio')
    elif damage == 'missing':
        (folder / generator['NAMES'][1]).unlink()
    elif damage == 'generator':
        script.write_text(script.read_text(encoding='utf-8') + '\n# edited generator\n', encoding='utf-8')
    elif damage == 'line-endings':
        script.write_bytes(script.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
    before = {path.name: path.read_bytes() for path in folder.iterdir() if path.is_file()}
    result = subprocess.run([sys.executable, str(script), '--check' if damage == 'missing' else '--restore'],
                            capture_output=True, timeout=20)
    assert (result.returncode == 0) is (damage in {'none', 'line-endings'})
    assert {path.name: path.read_bytes() for path in folder.iterdir() if path.is_file()} == before
