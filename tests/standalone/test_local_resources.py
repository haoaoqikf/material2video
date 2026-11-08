"""作品内资源登记不能借父目录跳到作品外。"""
from pathlib import Path

import pytest

from film_runtime.core.errors import VideoError
from film_runtime.types.scene_film import media_assets, sound_library


def test_media_local_path_cannot_escape_project(tmp_path):
    root = tmp_path / 'project'
    (root / 'assets').mkdir(parents=True)
    outside = tmp_path / 'outside.png'
    outside.write_bytes(b'not-an-image')
    manifest = {'schemaVersion': 1, 'assets': [{
        'id': 'escape', 'kind': 'image', 'localPath': '../../outside.png'}]}
    with pytest.raises(VideoError, match='本地素材缺失'):
        media_assets.import_assets(root, manifest, base=root / 'assets')


def test_sound_local_path_cannot_escape_project(tmp_path):
    root = tmp_path / 'project'
    (root / 'assets').mkdir(parents=True)
    outside = tmp_path / 'outside.wav'
    outside.write_bytes(b'not-a-wave')
    manifest = {'schemaVersion': 1, 'assets': [{
        'id': 'escape', 'localPath': '../../outside.wav', 'author': 'test', 'license': 'CC0-1.0',
        'sourceUrl': 'https://example.invalid/sound'}]}
    with pytest.raises(VideoError, match='本地音效缺失'):
        sound_library.import_assets(root, manifest, base=root / 'assets')
