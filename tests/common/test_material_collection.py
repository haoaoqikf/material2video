"""全片采样与大目录增量收集的独特失败边界。"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image
import pytest

from m2v.materials import cli, indexing, scanning
from m2v.materials.sampling import STRATEGY, spread
from m2v.materials.store import MaterialStore


def test_spread_preserves_timeline_extremes_middle_and_uneven_density():
    times = [*range(100), 1000, 5000, 10000]
    assert spread(times, 3) == [0, 5000, 10000]
    assert spread(times, 1) == [5000]
    result = spread(times, 40)
    assert len(result) == len(set(result)) == 40
    assert result[0] == 0 and result[-1] == 10000


def test_scan_diagnostic_details_are_bounded():
    details = scanning._Details()
    for number in range(1200):
        details.append({'number': number})
    assert details.total == 1200 and len(details) == 1000
    assert scanning._Details().total == 0


def _image(path: Path, color='navy'):
    Image.new('RGB', (8, 8), color).save(path, format='PNG', compress_level=0)


@pytest.mark.media
def test_incremental_scan_advances_past_500_without_reacquiring(tmp_path, monkeypatch):
    folder = tmp_path / 'inputs'
    folder.mkdir()
    for number in range(502):
        _image(folder / f'{number:04}.png')
    original = scanning.fetch_local
    calls = []
    def counted(*args, **kwargs):
        calls.append(kwargs['path'])
        return original(*args, **kwargs)
    monkeypatch.setattr(scanning, 'fetch_local', counted)
    with MaterialStore(tmp_path / 'work') as store:
        first = scanning.scan_directory(store, folder)
        assert first['acquired'] == 500 and first['hasMore']
        second = scanning.scan_directory(store, folder)
        assert second['acquired'] == 2 and second['reused'] == 500 and not second['hasMore']
        third = scanning.scan_directory(store, folder)
        assert third['acquired'] == 0 and third['reused'] == 502
        assert len(calls) == len(store.documents('material.media')) == 502


@pytest.mark.media
def test_scan_isolates_corruption_detects_hidden_content_change_and_repairs_missing_object(tmp_path):
    folder = tmp_path / 'inputs'
    folder.mkdir()
    (folder / 'broken.png').write_bytes(b'not an image')
    good = folder / 'valid.png'
    _image(good, 'red')
    with MaterialStore(tmp_path / 'work') as store:
        first = scanning.scan_directory(store, folder)
        assert first['acquired'] == 1 and len(first['failures']) == 1
        previous = first['mediaIds'][0]
        stamp = good.stat()
        _image(good, 'blue')
        assert good.stat().st_size == stamp.st_size
        os.utime(good, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        changed = scanning.scan_directory(store, folder)
        assert changed['acquired'] == 1 and changed['mediaIds'][0] != previous
        media = store.get(changed['mediaIds'][0], kind='material.media')
        store.verify_artifact(media.data.artifact).unlink()
        repaired = scanning.scan_directory(store, folder)
        assert repaired['acquired'] == 1
        store.verify_artifact(media.data.artifact)


@pytest.mark.media
def test_long_shot_budget_keeps_tail_and_sampling_identity(tmp_path):
    from test_material_indexing import _clip
    from m2v.materials.contracts import Source, SourceData
    from m2v.materials.fetch import fetch_local
    source = Source(id='source-long', data=SourceData(provider='local', title='长镜头'))
    with MaterialStore(tmp_path / 'work') as store:
        store.put(source)
        media = fetch_local(store, source=source, path=_clip(tmp_path / 'long.mp4', seconds=12, audio=False)).media
        result = indexing.index_shots(store, media, long_shot_s=1, max_frames=3)
        frames = store.records(result[1].document.id)
        times = sorted(frame.localRange.startUs for frame in frames)
        assert len(times) == 3 and times[0] < 1_000_000 and times[-1] > 10_000_000
        assert result[1].document.data.config['sampling'] == STRATEGY
        assert any('全时间轴' in message for message in result[1].warnings)


@pytest.mark.media
def test_scan_cli_reports_partial_success_and_all_failure(tmp_path, capsys):
    folder = tmp_path / 'inputs'
    folder.mkdir()
    (folder / 'broken.png').write_bytes(b'invalid')
    _image(folder / 'good.png')
    args = ['library', 'scan', '--workspace', str(tmp_path / 'work'), '--dir', str(folder), '--json']
    assert cli.main(args) == 1
    capsys.readouterr()
    (folder / 'good.png').unlink()
    assert cli.main(args) == 2


@pytest.mark.media
def test_unreadable_failure_does_not_starve_later_files_across_budgeted_runs(tmp_path, monkeypatch):
    folder = tmp_path / 'inputs'
    folder.mkdir()
    bad, good = folder / 'a.png', folder / 'z.png'
    _image(bad)
    _image(good, 'red')
    monkeypatch.setattr(scanning, '_walk', lambda *args: iter([(bad, bad.stat()), (good, good.stat())]))
    original = scanning._digest
    def unreadable(path):
        if path == bad:
            raise PermissionError('unreadable')
        return original(path)
    monkeypatch.setattr(scanning, '_digest', unreadable)
    with MaterialStore(tmp_path / 'work') as store:
        first = scanning.scan_directory(store, folder, max_files=1)
        assert first['failures'] and first['hasMore']
        second = scanning.scan_directory(store, folder, max_files=1)
        assert second['acquired'] == 1 and second['failures'][0]['reusedFailure']
