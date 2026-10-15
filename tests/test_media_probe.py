"""媒体实测尺寸探针：留证尺寸必须来自下载文件本身，而不是图库的声明。"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError
from m2v.engine import media_probe


@pytest.fixture(scope="module")
def probe_media(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """本机生成一张竖屏图片与一段横屏视频，覆盖两种容器。"""
    directory = tmp_path_factory.mktemp("media-probe")
    ffmpeg = get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-y", "-v", "error", "-f", "lavfi",
                    "-i", "color=c=steelblue:size=1080x1920", "-frames:v", "1",
                    str(directory / "tall.jpg")], check=True, timeout=300)
    subprocess.run([ffmpeg, "-y", "-v", "error", "-f", "lavfi",
                    "-i", "testsrc=size=1920x1080:rate=30:duration=1", "-pix_fmt", "yuv420p",
                    str(directory / "wide.mp4")], check=True, timeout=300)
    return directory


def test_probe_reads_the_real_dimensions(probe_media: Path) -> None:
    assert media_probe.probe_dimensions(probe_media / "tall.jpg") == (1080, 1920)
    assert media_probe.probe_dimensions(probe_media / "wide.mp4") == (1920, 1080)


def test_probe_reports_missing_and_unreadable_files(probe_media: Path, tmp_path: Path) -> None:
    with pytest.raises(M2VError, match="不存在"):
        media_probe.probe_dimensions(tmp_path / "missing.mp4")

    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"not a media file")
    with pytest.raises(M2VError, match="无法读取素材尺寸"):
        media_probe.probe_dimensions(broken)
