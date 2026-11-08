"""look-dev 的取点与接触表：只验证可判定的部分，渲染本身由真实制作验证。"""
import subprocess
from pathlib import Path

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


@pytest.mark.media
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


# ---------------------------------------------------------------- 任意时刻预览

def two_scene_prepared():
    """两个首尾相接的幕，便于验证跨幕取帧与归属校验。"""
    return {"durationInFrames": 300, "fps": 30,
            "props": {"compiledScenes": [{"id": "a", "startFrame": 0, "endFrame": 150},
                                          {"id": "b", "startFrame": 150, "endFrame": 300}]}}


def test_seconds_to_frame_rounds_and_clamps():
    assert lookdev.seconds_to_frame(2.0, 30, 300) == 60
    # 四舍五入而不是向下取整：作者按秒指定的是最近的那一帧。
    assert lookdev.seconds_to_frame(2.02, 30, 300) == 61
    assert lookdev.seconds_to_frame(-5, 30, 300) == 0
    assert lookdev.seconds_to_frame(999, 30, 300) == 299


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), "2"])
def test_seconds_to_frame_rejects_non_finite(value):
    with pytest.raises(M2VError, match="时刻必须是有限数值|时刻必须是秒数"):
        lookdev.seconds_to_frame(value, 30, 300)


def test_check_frames_runs_before_any_browser_work():
    """归属校验必须先于采集：非法帧不该白跑一遍浏览器。"""
    prepared = two_scene_prepared()
    lookdev.check_frames(prepared, [0, 149, 299])
    with pytest.raises(M2VError, match="超出全片范围"):
        lookdev.check_frames(prepared, [300])
    with pytest.raises(M2VError, match="超出全片范围"):
        lookdev.check_frames(prepared, [-1])
    with pytest.raises(M2VError, match="没有可采集的时刻"):
        lookdev.check_frames(prepared, [])


def test_check_frames_rejects_frame_outside_every_scene():
    prepared = two_scene_prepared()
    prepared["props"]["compiledScenes"][1]["startFrame"] = 200
    with pytest.raises(M2VError, match="不属于任何已准备场景"):
        lookdev.check_frames(prepared, [180])


def test_uniform_frames_includes_both_ends():
    assert lookdev.uniform_frames(0, 100, 3) == [0, 50, 100]
    assert lookdev.uniform_frames(7, 7, 5) == [7]
    assert lookdev.uniform_frames(0, 100, 1) == [0]
    with pytest.raises(M2VError, match="早于起点"):
        lookdev.uniform_frames(50, 10, 3)
    with pytest.raises(M2VError, match="至少为 1"):
        lookdev.uniform_frames(0, 10, 0)


def test_sheet_frames_accepts_times_and_uniform_count():
    prepared = two_scene_prepared()
    assert lookdev.sheet_frames(["1", "3.5"], prepared) == [30, 105]
    # 重复时刻只采一次。
    assert lookdev.sheet_frames(["1", "1.0"], prepared) == [30]
    uniform = lookdev.sheet_frames(["4"], prepared)
    assert len(uniform) == 4 and uniform == sorted(uniform) and uniform[-1] < 300
    with pytest.raises(M2VError, match="1～24"):
        lookdev.sheet_frames(["99"], prepared)
    with pytest.raises(M2VError, match="时刻必须是秒数"):
        lookdev.sheet_frames(["abc"], prepared)


def test_motion_frames_rejects_bad_windows():
    prepared = two_scene_prepared()
    frames = lookdev.motion_frames(1.0, 2.0, 5, prepared)
    assert len(frames) == 5 and frames[0] == 30 and frames[-1] == 60
    with pytest.raises(M2VError, match="早于起点"):
        lookdev.motion_frames(2.0, 1.0, 5, prepared)
    with pytest.raises(M2VError, match="超出成片时长"):
        lookdev.motion_frames(0, 100, 5, prepared)


@pytest.mark.parametrize("fps,duration", [(30, 2040), (60, 2040), (30, 1), (60, 1)])
def test_out_of_range_hint_can_locate_last_frame(fps, duration):
    """越界提示里的秒数必须能原样定位末帧，不能把用户引回同一个错误。"""
    import re

    prepared = {"fps": fps, "durationInFrames": duration}
    for invalid in (
        lambda: lookdev.sheet_frames([str(duration / fps)], prepared),
        lambda: lookdev.motion_frames(0, duration / fps, 2, prepared),
    ):
        with pytest.raises(M2VError) as error:
            invalid()
        # 读取提示里最后一个秒数，不耦合整句错误文案。
        hint = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*秒", str(error.value))[-1]
        assert lookdev.sheet_frames([hint], prepared) == [duration - 1]
        assert lookdev.motion_frames(0, float(hint), 2, prepared)[-1] == duration - 1


# ---------------------------------------------------------------- 事件取点

def event_prepared():
    """两个幕、跨幕事件与同帧事件，覆盖选择器解析和窗口校验。"""
    return {"durationInFrames": 300, "fps": 30, "preparedFingerprint": "test",
            "props": {"compiledScenes": [
                {"id": "a", "startFrame": 0, "endFrame": 150, "durationInFrames": 150},
                {"id": "b", "startFrame": 150, "endFrame": 300, "durationInFrames": 150}],
                "resolvedEvents": [
                    {"sceneId": "a", "id": "contact", "frame": 30, "globalFrame": 30},
                    {"sceneId": "a", "id": "near", "frame": 33, "globalFrame": 33},
                    {"sceneId": "a", "id": "hit", "frame": 10, "globalFrame": 10},
                    {"sceneId": "b", "id": "hit", "frame": 20, "globalFrame": 170},
                    {"sceneId": "b", "id": "reveal", "frame": 40, "globalFrame": 190}]}}


def test_event_frames_declare_before_at_after_hold():
    resolved = lookdev.resolve_event_selectors(
        event_prepared(), ["a:contact"], before=6, after=6, hold=12)
    assert resolved["frames"] == [24, 30, 36, 48]
    assert resolved["labels"] == ["a.contact.b6", "a.contact.at", "a.contact.a6", "a.contact.h12"]
    event = resolved["events"][0]
    assert event["sceneId"] == "a" and event["id"] == "contact"
    assert [(phase["phase"], phase["localFrame"], phase["globalFrame"])
            for phase in event["phases"]] == [
                ("before", 24, 24), ("at", 30, 30), ("after", 36, 36), ("hold", 48, 48)]


def test_event_frames_use_global_scene_offset():
    resolved = lookdev.resolve_event_selectors(
        event_prepared(), ["b:reveal"], before=4, after=4)
    assert resolved["frames"] == [186, 190, 194]
    assert resolved["events"][0]["phases"][0]["globalFrame"] == 186


def test_event_selector_requires_scene_when_ambiguous():
    with pytest.raises(M2VError, match="多个幕"):
        lookdev.resolve_event_selectors(event_prepared(), ["hit"], before=2, after=2)
    resolved = lookdev.resolve_event_selectors(event_prepared(), ["a:hit"], before=2, after=2)
    assert resolved["frames"] == [8, 10, 12]


def test_event_frames_reject_window_outside_scene():
    with pytest.raises(M2VError, match="超出本幕范围"):
        lookdev.resolve_event_selectors(event_prepared(), ["a:contact"], before=31, after=6)
    with pytest.raises(M2VError, match="超出本幕范围"):
        lookdev.resolve_event_selectors(event_prepared(), ["a:contact"], before=6, after=130)
    with pytest.raises(M2VError, match="未找到"):
        lookdev.resolve_event_selectors(event_prepared(), ["a:missing"], before=6, after=6)


def test_event_frames_warn_about_clusters():
    resolved = lookdev.resolve_event_selectors(
        event_prepared(), ["a:contact", "a:near"], before=3, after=3)
    assert resolved["warnings"] and "事件簇" in resolved["warnings"][0]
    # 两个事件窗口重叠时，同一帧只采一次，标签合并保留来源。
    assert resolved["frames"] == [27, 30, 33, 36]
    assert resolved["labels"] == ["a.contact.b3", "a.contact.at.a.near.b3",
                                  "a.contact.a3.a.near.at", "a.near.a3"]


def test_event_mode_requires_before_after_and_is_mutually_exclusive():
    args = type("Args", (), {"sheet": None, "motion": None, "det": False, "event": ["a:contact"],
                             "before": None, "after": None, "hold": 0,
                             "stills": None, "sample_seconds": lookdev.DEFAULT_SAMPLE_SECONDS})()
    with pytest.raises(M2VError, match="--before 与 --after"):
        lookdev._reject_conflicting_modes(args)
    args.before, args.after = 6, 6
    lookdev._reject_conflicting_modes(args)
    args.sheet = ["1"]
    with pytest.raises(M2VError, match="互斥"):
        lookdev._reject_conflicting_modes(args)


def test_event_labels_must_match_frames():
    prepared = event_prepared()
    with pytest.raises(M2VError, match="标注数量"):
        lookdev.preview(Path("."), {}, prepared, mode="event", frames=[24], labels=[])


def test_sheet_columns_grows_with_count():
    assert lookdev.sheet_columns(1) == 1
    assert lookdev.sheet_columns(2) == 2
    assert lookdev.sheet_columns(3) == 3
    assert lookdev.sheet_columns(12) == lookdev.SHEET_COLUMNS


@pytest.mark.media
def test_contact_sheet_labels_are_ascii_only(tmp_path):
    """标注只用数字与冒号：缺中文字体会让整条拼图命令失败。"""
    stills = []
    for index in range(2):
        path = tmp_path / f"still-{index}.png"
        subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                        "-i", "color=c=black:size=320x180", "-frames:v", "1", str(path)], check=True)
        stills.append(path)
    sheet = lookdev.contact_sheet(stills, tmp_path / "labelled.png",
                                  columns=2, labels=["1-0.00s-f0", "中文标注"])
    assert sheet.is_file() and sheet.stat().st_size > 0


def test_preview_modes_are_mutually_exclusive():
    args = type("Args", (), {"sheet": ["1"], "motion": None, "det": False, "stills": None,
                             "sample_seconds": lookdev.DEFAULT_SAMPLE_SECONDS})()
    lookdev._reject_conflicting_modes(args)
    args.motion = [0.0, 1.0]
    with pytest.raises(M2VError, match="互斥"):
        lookdev._reject_conflicting_modes(args)
    args.motion = None
    args.stills = 4
    with pytest.raises(M2VError, match="--stills 互斥"):
        lookdev._reject_conflicting_modes(args)


@pytest.mark.media
def test_psnr_reads_identical_and_different_images(tmp_path):
    first, second, third = (tmp_path / name for name in ("a.png", "b.png", "c.png"))
    for path, color in ((first, "black"), (second, "black"), (third, "white")):
        subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                        "-i", f"color=c={color}:size=64x64", "-frames:v", "1", str(path)], check=True)
    assert lookdev.psnr(first, second) == float("inf")
    assert lookdev.psnr(first, third) < lookdev.DETERMINISM_PSNR


def test_image_size_rejects_non_png(tmp_path):
    bogus = tmp_path / "not.png"
    bogus.write_bytes(b"not a png at all")
    with pytest.raises(M2VError, match="不是 PNG"):
        lookdev._image_size(bogus)


def test_sheet_frames_rejects_out_of_range_times():
    """负时刻与超出片长的时刻必须报错，不能静默夹到边界。"""
    prepared = two_scene_prepared()
    # 单个纯整数是「均匀取多少帧」，不是秒；因此这里只用明显是时刻的写法。
    for bad in ("-1", "inf", "-0.5", "10.5"):
        with pytest.raises(M2VError, match="超出成片时长"):
            lookdev.sheet_frames([bad], prepared)
    assert lookdev.sheet_frames(["9.9"], prepared) == [297]
    # 歧义按文档语义解决：--sheet 11 是均匀取 11 帧，不是第 11 秒。
    eleven = lookdev.sheet_frames(["11"], prepared)
    assert len(eleven) == 11 and eleven[-1] < 300
