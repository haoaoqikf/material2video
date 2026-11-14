"""模型登记、显式恢复与只读诊断；不联网、不安装、不真实推理。"""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

import pytest

from m2v.materials import diagnostics
from m2v.materials.errors import MaterialError
from m2v.materials.model_manager import ModelManager


def _registry(tmp_path: Path, *, path='weights.bin', payload=b'fixed-model-bytes') -> Path:
    import hashlib
    record = {'schemaVersion': 1,
              'models': {'toy': {'repoId': 'example/toy', 'revision': 'a' * 40, 'license': 'MIT',
                                 'extra': 'asr', 'preprocessing': 'cpu',
                                 'files': [{'path': path, 'sha256': hashlib.sha256(payload).hexdigest(),
                                            'bytes': len(payload)}]}},
              'software': {'faster-whisper': {'version': '1.2.1', 'license': 'MIT'}}}
    target = tmp_path / 'registry.json'
    target.write_text(json.dumps(record), encoding='utf-8')
    return target


def test_registry_rejects_bad_identity_and_path_traversal(tmp_path):
    broken = tmp_path / 'broken.json'
    for value in ({'schemaVersion': 2}, {'schemaVersion': 1, 'models': {}, 'software': {}},
                  {'schemaVersion': 1, 'software': {},
                   'models': {'toy': {'repoId': 'x', 'revision': 'short', 'license': 'MIT',
                                      'files': [{'path': 'a', 'sha256': 'b' * 64, 'bytes': 1}]}}}):
        broken.write_text(json.dumps(value), encoding='utf-8')
        with pytest.raises(MaterialError):
            ModelManager(tmp_path / 'models', registry_path=broken)
    with pytest.raises(MaterialError):
        ModelManager(tmp_path / 'models', registry_path=_registry(tmp_path, path='../escape.bin'))


def test_verify_detects_missing_and_corrupt_bytes_and_prepare_repairs(tmp_path):
    registry = _registry(tmp_path)
    payload = b'fixed-model-bytes'
    manager = ModelManager(tmp_path / 'models', registry_path=registry)
    assert manager.list()[0]['present'] is False
    with pytest.raises(MaterialError) as missing:
        manager.verify('toy')
    assert missing.value.code == 'model-missing'

    def downloader(spec, item, destination: Path):
        destination.write_bytes(payload)

    assert manager.prepare('toy', downloader=downloader)['verified'] is True
    assert manager.verify('toy')['verified'] is True
    target = manager.path('toy') / 'weights.bin'
    target.write_bytes(b'corrupted-model!?')
    assert manager.list()[0]['sizeValid'] is True  # 大小相同不等于摘要正确
    with pytest.raises(MaterialError) as corrupt:
        manager.verify('toy')
    assert corrupt.value.code == 'hash-mismatch'
    with pytest.raises(MaterialError):
        manager.prepare('toy', downloader=downloader)
    assert manager.prepare('toy', downloader=downloader, repair=True)['verified'] is True
    with pytest.raises(MaterialError):
        manager.verify('unknown-model')


def test_prepare_never_publishes_wrong_downloaded_bytes(tmp_path):
    registry = _registry(tmp_path)
    manager = ModelManager(tmp_path / 'models', registry_path=registry)

    def wrong(spec, item, destination: Path):
        destination.write_bytes(b'wrong-bytes-wrong-bytes')

    with pytest.raises(MaterialError) as failure:
        manager.prepare('toy', downloader=wrong)
    assert failure.value.code == 'hash-mismatch'
    assert not (manager.root / 'toy' / 'weights.bin').exists()


def test_doctor_reports_verification_gaps_without_leaking_or_claiming(tmp_path, monkeypatch):
    registry = _registry(tmp_path)
    monkeypatch.setenv('PIXABAY_API_KEY', 'secret-key-value')
    monkeypatch.setenv('PEXELS_API_KEY', 'another-secret')
    report = diagnostics.doctor(tmp_path / 'models', registry_path=registry)
    text = json.dumps(report, ensure_ascii=False)
    assert 'secret-key-value' not in text and 'another-secret' not in text
    assert report['performed'] == {'network': False, 'install': False, 'inference': False, 'download': False}
    assert report['models'][0]['present'] is False
    assert report['sources']['pexels']['api'] == 'disabled'
    assert report['sources']['pixabay']['configured'] is True
    assert 'tools' in report and 'device' in report


def test_doctor_reports_dependency_mismatch_and_missing_ffprobe(tmp_path, monkeypatch):
    registry = _registry(tmp_path)
    original = importlib.metadata.version

    def fake_version(name):
        if name == 'faster-whisper':
            return '0.0.1'
        return original(name)

    monkeypatch.setattr(importlib.metadata, 'version', fake_version)
    monkeypatch.delenv('M2V_FFPROBE', raising=False)
    monkeypatch.setattr('m2v.materials.diagnostics.shutil.which', lambda name: None)
    report = diagnostics.doctor(tmp_path / 'models', registry_path=registry)
    assert report['dependencies']['faster-whisper']['matches'] is False
    assert report['tools']['ffprobe']['available'] is False
    assert 'M2V_FFPROBE' in report['tools']['ffprobe']['note']
