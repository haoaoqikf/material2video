"""候选接触表：图片拼格、视频抽帧与索引对应。"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image

from m2v.core.errors import M2VError
from m2v.engine import assets_tools

pytestmark = pytest.mark.media


def _image(path: Path, size=(320, 200), color=(200, 30, 30)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def _video(path: Path, seconds: int = 2, size="320x240") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"color=c=0x223344:s={size}:r=10:d={seconds}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def test_images_are_tiled_in_order_with_index(tmp_path):
    first = _image(tmp_path / "a.png", (320, 200))
    second = _image(tmp_path / "b.png", (200, 320), (30, 30, 200))
    third = _image(tmp_path / "c.png", (400, 300), (30, 200, 30))
    out = tmp_path / "sheet.png"
    result = assets_tools.contact_sheet([first, second, third], columns=2, tile_width=240, out=out)
    assert out.is_file()
    index = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert result["tiles"] == index["tiles"]
    assert [item["input"] for item in index["tiles"]] == ["a.png", "b.png", "c.png"]
    assert all(item["timeSeconds"] is None for item in index["tiles"])
    assert (index["columns"], index["rows"]) == (2, 2)
    with Image.open(out) as sheet:
        cell = index["cell"]
        assert sheet.size == (2 * cell["width"] + 3 * 8, 2 * cell["height"] + 3 * 8)


def test_video_uses_explicit_times_and_writes_index(tmp_path):
    clip = _video(tmp_path / "clip.mp4")
    out = tmp_path / "clip-sheet.png"
    result = assets_tools.contact_sheet([clip], times=[0.2, 1.0, 1.8], out=out)
    assert result["output"] == str(out)
    index = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert [item["timeSeconds"] for item in index["tiles"]] == [0.2, 1.0, 1.8]
    assert all(item["input"] == "clip.mp4" for item in index["tiles"])


def test_video_without_times_samples_evenly(tmp_path):
    clip = _video(tmp_path / "clip.mp4", seconds=2)
    result = assets_tools.contact_sheet([clip], samples=3, out=tmp_path / "sheet.png")
    times = [item["timeSeconds"] for item in result["tiles"]]
    assert len(times) == 3 and times[0] < times[1] < times[2]


def test_contact_sheet_rejects_two_videos(tmp_path):
    first = _video(tmp_path / "a.mp4")
    second = _video(tmp_path / "b.mp4")
    with pytest.raises(M2VError, match="只接受一个视频"):
        assets_tools.contact_sheet([first, second], out=tmp_path / "sheet.png")


def test_contact_sheet_rejects_times_for_images(tmp_path):
    image = _image(tmp_path / "a.png")
    with pytest.raises(M2VError, match="只适用于视频"):
        assets_tools.contact_sheet([image], times=[1.0], out=tmp_path / "sheet.png")


def test_contact_sheet_rejects_out_of_range_time(tmp_path):
    clip = _video(tmp_path / "clip.mp4", seconds=1)
    with pytest.raises(M2VError, match="超出"):
        assets_tools.contact_sheet([clip], times=[0.1, 5.0], out=tmp_path / "sheet.png")


def test_contact_sheet_requires_png_output(tmp_path):
    image = _image(tmp_path / "a.png")
    with pytest.raises(M2VError, match="png"):
        assets_tools.contact_sheet([image], out=tmp_path / "sheet")
