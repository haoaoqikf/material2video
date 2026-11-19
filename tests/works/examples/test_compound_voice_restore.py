"""用合成占位数据验证本地音色恢复，测试不读取私人音色档案。"""
from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path

import pytest

from helpers.examples import EXAMPLE_PATHS


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


@pytest.fixture
def voice_materials(tmp_path):
    model = tmp_path / 'example/models/qwen3-tts'
    model.mkdir(parents=True)
    audio = tmp_path / 'reference.wav'
    audio.write_bytes(b'RIFF reference test bytes')
    transcript = '合成测试参考文本'
    profile = {'voice': 'clone_test', 'refAudio': 'qwen3-tts/voices/test.wav',
               'language': 'Chinese', 'bytes': audio.stat().st_size,
               'sha256': hashlib.sha256(audio.read_bytes()).hexdigest()}
    profile.update(refText=transcript, authorization={'userAuthorized': True})
    canonical = json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    write_json(model / 'voice-requirements.json', {
        **{key: profile[key] for key in ('voice', 'refAudio', 'bytes', 'sha256')},
        'profileSha256': hashlib.sha256(canonical).hexdigest(),
    })
    source = tmp_path / 'source-registry.json'
    write_json(source, {'voices': [profile]})
    write_json(model / 'registry.template.json', {'revision': 'public-model', 'voices': []})
    script = EXAMPLE_PATHS['compound-after-20'] / 'models/qwen3-tts/restore-voice.py'
    restore = runpy.run_path(str(script))['restore']
    return restore, model, source, audio, profile


def test_restore_matches_reference_and_preserves_existing_files(voice_materials):
    restore, model, source, audio, profile = voice_materials
    registry = model / 'registry.json'
    restored = model.parent / 'files' / profile['refAudio']
    restore(model, source, audio)
    assert restored.read_bytes() == audio.read_bytes()
    assert json.loads(registry.read_text(encoding='utf-8')) == {'revision': 'public-model', 'voices': [profile]}
    original_stat = (restored.stat().st_mtime_ns, registry.stat().st_mtime_ns)
    restore(model, source, audio)
    assert (restored.stat().st_mtime_ns, registry.stat().st_mtime_ns) == original_stat

    registry.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='目标已有不同内容'):
        restore(model, source, audio)
    assert registry.read_text(encoding='utf-8') == '{}'
    assert restored.read_bytes() == audio.read_bytes()


@pytest.mark.parametrize('change, error, message', [
    ('missing registry', FileNotFoundError, None),
    ('missing audio', FileNotFoundError, None),
    ('wrong audio', ValueError, '参考 WAV'),
    ('wrong text', ValueError, '音色档案摘要'),
])
def test_restore_rejects_invalid_inputs_before_writing(voice_materials, change, error, message):
    restore, model, source, audio, profile = voice_materials
    if change == 'missing registry':
        source.unlink()
    elif change == 'missing audio':
        audio.unlink()
    elif change == 'wrong audio':
        audio.write_bytes(b'RIFF different bytes')
    else:
        write_json(source, {'voices': [{**profile, 'refText': '错误文本'}]})

    with pytest.raises(error, match=message):
        restore(model, source, audio)
    assert not (model / 'registry.json').exists()
    assert not (model.parent / 'files').exists()
