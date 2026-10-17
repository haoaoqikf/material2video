"""look-dev 的取点与接触表：只验证可判定的部分，渲染本身由真实制作验证。"""
import subprocess

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError
from m2v.engine import lookdev


def scene_with_shots(shots):
    return {"durationInFrames": 3600, "fps": 60,
            "props": {"compiledScenes": [{"content": {"props": {"shots": shots}}}]}}


HEROES = [{"id": "earth", "tier": "hero", "target": "earth", "startFrame": 300, "endFrame": 780},
          {"id": "saturn", "tier": "hero", "target": "saturn", "startFrame": 1500, "endFrame": 1980},
          {"id": "oort", "tier": "hero", "target": "oort", "startFrame": 3000, "endFrame": 3400},
          {"id": "sun", "tier": "minor", "target": "sun", "startFrame": 0, "endFrame": 200}]


def test_still_frames_prefer_hero_midpoints():
    assert lookdev.still_frames(scene_with_shots(HEROES), 3) == [540, 1740, 3200]


def test_still_frames_fill_with_first_last_and_even_points():
    frames = lookdev.still_frames(scene_with_shots(HEROES), 5)
    assert frames[0] == 0 and frames[-1] == 3599 and {540, 1740, 3200} <= set(frames)
    assert len(frames) == 5


def test_still_frames_without_shots_are_spread_and_bounded():
    plain = {"durationInFrames": 3600, "fps": 60, "props": {"compiledScenes": []}}
    frames = lookdev.still_frames(plain, 4)
    assert len(frames) == 4 and frames == sorted(frames)
    assert frames[0] == 0 and frames[-1] == 3599


def test_sample_window_covers_first_hero():
    assert lookdev.sample_window(scene_with_shots(HEROES), 24) == (300, 1739)
    plain = {"durationInFrames": 900, "fps": 60, "props": {"compiledScenes": []}}
    assert lookdev.sample_window(plain, 20) == (0, 899)


def test_sample_window_rejects_impossible_request():
    with pytest.raises(M2VError):
        lookdev.sample_window({"durationInFrames": 0, "fps": 60, "props": {"compiledScenes": []}}, 20)


def test_contact_sheet_tiles_stills(tmp_path):
    stills = []
    for index in range(3):
        path = tmp_path / f"still-{index}.png"
        subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                        "-i", f"color=c=black:size=320x180", "-frames:v", "1", str(path)], check=True)
        stills.append(path)
    sheet = lookdev.contact_sheet(stills, tmp_path / "sheet.png")
    assert sheet.is_file() and sheet.stat().st_size > 0
    with pytest.raises(M2VError):
        lookdev.contact_sheet([], tmp_path / "empty.png")
