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


def test_still_frames_prefer_hero_payoff():
    # hero 取 75%：土星环已展开、土卫六进入画面。
    assert lookdev.still_frames(scene_with_shots(HEROES), 3) == [660, 1860, 3300]


def test_still_frames_fill_with_first_last_and_even_points():
    frames = lookdev.still_frames(scene_with_shots(HEROES), 5)
    assert frames[0] == 0 and frames[-1] == 3599 and {660, 1860, 3300} <= set(frames)
    assert len(frames) == 5


def test_still_frames_without_shots_are_spread_and_bounded():
    plain = {"durationInFrames": 3600, "fps": 60, "props": {"compiledScenes": []}}
    frames = lookdev.still_frames(plain, 4)
    assert len(frames) == 4 and frames == sorted(frames)
    assert frames[0] == 0 and frames[-1] == 3599


def test_sample_window_covers_first_hero():
    assert lookdev.sample_window(scene_with_shots(HEROES), 24) == (300, 1739)
    plain = {"durationInFrames": 900, "fps": 60, "props": {"compiledScenes": []}}
    assert lookdev.sample_window(plain, 20) == (0, 898)


def test_sample_window_rejects_impossible_request():
    with pytest.raises(M2VError):
        lookdev.sample_window({"durationInFrames": 0, "fps": 60, "props": {"compiledScenes": []}}, 20)


def test_sample_audio_follows_story_sound_intent():
    from pathlib import Path

    base = {"audio": {"segments": [{"path": "outputs/audio.wav"}]},
            "props": {"soundtrack": {}, "compiledScenes": [{"narrationSegments": []}]}}
    assert lookdev.sample_audio(base, Path("project")) == (False, None)
    base["props"]["soundtrack"] = {"music": {"sourceRef": "assets/music.wav"}}
    assert lookdev.sample_audio(base, Path("project")) == (True, Path("project/outputs/audio.wav"))
    base["props"]["soundtrack"] = {}
    base["props"]["compiledScenes"][0]["narrationSegments"] = [{"text": "hello"}]
    assert lookdev.sample_audio(base, Path("project")) == (True, Path("project/outputs/audio.wav"))


def test_still_props_keep_only_the_captured_scene(tmp_path):
    """多幕作品只合成当前帧所在幕，未采样幕没有已物化的 mediaPath。"""
    picture = tmp_path / "frame.png"
    picture.write_bytes(b"png")
    prepared = {"props": {"compiledScenes": [{"id": "a"}, {"id": "b"}]}}
    props = lookdev.still_props(prepared, {("a", 10): picture}, 10, "http://media/")
    assert [scene["id"] for scene in props["compiledScenes"]] == ["a"]
    assert props["compiledScenes"][0]["stillPath"] == "data:image/png;base64,cG5n"
    assert props["mediaBase"] == "http://media/"
    assert [scene["id"] for scene in prepared["props"]["compiledScenes"]] == ["a", "b"]


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
