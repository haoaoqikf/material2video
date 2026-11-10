"""静态贴图需真实解码，但无需为每张图反复启动外部视频进程。"""
from pathlib import Path

from PIL import Image
import pytest

from m2v.core.errors import M2VError
from m2v.types.scene_film import media_assets

pytestmark = pytest.mark.media


@pytest.mark.parametrize('format', ['PNG', 'JPEG', 'WEBP'])
def test_image_probe_decodes_supported_bytes_without_video_process(tmp_path: Path, monkeypatch, format):
    target = tmp_path / 'texture.data'
    Image.new('RGB', (73, 41), (48, 91, 137)).save(target, format=format)
    monkeypatch.setattr(media_assets.subprocess, 'run', lambda *_a, **_k: pytest.fail('image spawned ffmpeg'))
    assert media_assets.probe(target, 'image') == {'width': 73, 'height': 41, 'durationSeconds': None}


def test_image_probe_rejects_truncated_pixel_data_and_unsupported_format(tmp_path: Path):
    target = tmp_path / 'texture.jpg'
    Image.new('RGB', (73, 41), (48, 91, 137)).save(target, format='JPEG')
    target.write_bytes(target.read_bytes()[:-40])
    with pytest.raises(M2VError, match='无法解码'):
        media_assets.probe(target, 'image')
    Image.new('RGB', (73, 41)).save(target, format='GIF')
    with pytest.raises(M2VError, match='类型不符'):
        media_assets.probe(target, 'image')
