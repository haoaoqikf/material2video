"""并行采集必须整组验证后才能发布缓存，失败重试不能继承未放行分块。"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from m2v.core.errors import M2VError
from m2v.types.scene_film.code_scenes import capture


def setup_capture(tmp_path, monkeypatch, *, missing_witness=False, worker_failure=False):
    cache = tmp_path / 'cache'
    work = tmp_path / 'work'
    cache.mkdir(); work.mkdir()
    (work / 'scene.js').write_text('scene', encoding='utf8')

    def worker(args, **kwargs):
        # 在所有 worker 完成前，缓存中没有可复用的 receipt。
        assert not list(cache.glob('*.json'))
        job = json.loads(Path(args[-1]).read_text(encoding='utf8'))
        output = Path(job['output'])
        assert output.is_relative_to(work)
        output.write_bytes(b'video')
        capture._clip_receipt(output, job['first'], job['last'],
                              extra={'contract': capture.PURE_CONTRACT, 'verified': True})
        for f in job['witnessFrames']:
            if not missing_witness:
                (Path(job['work']) / f'witness-{f:06d}.png').write_bytes(b'witness')
        return SimpleNamespace(returncode=1 if worker_failure else 0, stderr='failed', stdout='')

    monkeypatch.setattr(capture.subprocess, 'run', worker)
    monkeypatch.setattr(capture, '_verify_clip', lambda *_: None)
    monkeypatch.setattr(capture.security, 'deliver', lambda a, b: Path(a).replace(b))
    return cache, work


@pytest.mark.parametrize('failure', ['boundary', 'missing-witness', 'worker'])
def test_failed_group_never_publishes_reusable_blocks(tmp_path, monkeypatch, failure):
    cache, work = setup_capture(tmp_path, monkeypatch, missing_witness=failure=='missing-witness',
                                worker_failure=failure=='worker')
    monkeypatch.setattr(capture.images, 'psnr', lambda *_: 45 if failure=='boundary' else 100)
    for _ in range(2):
        with pytest.raises(M2VError):
            capture._parallel_chunks(tmp_path, work, {'durationInFrames':6}, [(0,6)], cache,
                                     'key', fps=30, jobs=2, verify_frames=2, block=2)
        assert capture._cached_ranges(cache, 'key', 0, 6, contract=capture.PURE_CONTRACT) == []
    if failure=='boundary':
        assert len(list((cache/'diagnostics').rglob('*.png'))) == 2


def test_success_publishes_only_after_all_boundaries_pass(tmp_path, monkeypatch):
    cache, work = setup_capture(tmp_path, monkeypatch)
    calls=[]
    def boundary(a,b):
        assert not list(cache.glob('*.json'))
        calls.append((a,b)); return 100
    monkeypatch.setattr(capture.images, 'psnr', boundary)
    result=capture._parallel_chunks(tmp_path,work,{'durationInFrames':6},[(0,6)],cache,
                                    'key',fps=30,jobs=2,verify_frames=2,block=2)
    assert len(calls)==2
    assert [(a,b) for a,b,_ in result]==[(0,2),(2,4),(4,6)]
    assert len(capture._cached_ranges(cache,'key',0,6,contract=capture.PURE_CONTRACT))==3


def test_previous_pure_receipts_cannot_authorize_new_capture(tmp_path):
    path=tmp_path/'clip.mp4';path.write_bytes(b'previous')
    capture._clip_receipt(path,0,2,extra={'contract':'pure-seek-png-444-v1','verified':True})
    assert not capture._valid_clip(path,path.with_suffix('.json'),contract=capture.PURE_CONTRACT)
