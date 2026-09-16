"""配音和字幕回归：服务替身提供真实可解码音频，常规测试不访问网络。"""
from __future__ import annotations

import json
import math
import re
import struct
import wave
from pathlib import Path

import pytest

from a2v import audio, cli, prepare as prep, storyboard as sb
from a2v.errors import A2VError
from a2v.media import load_media, media_url
from a2v.subtitles import cues_from_words, srt
from a2v.static_server import LocalServer
from a2v.browser import open_animated_page
from a2v.render import render, _resolve_page_url, _verify_output
from conftest import EXAMPLES_DIR


def tone(path, duration=2):
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        samples = (int(2000 * math.sin(2 * math.pi * 440 * n / 24000)) for n in range(round(duration * 24000)))
        stream.writeframes(b"".join(struct.pack("<h", n) for n in samples))


@pytest.fixture
def speech(monkeypatch):
    calls = []
    async def fake(text, voice, rate, output):
        calls.append((text, voice, rate))
        tone(output)
        tokens = re.findall(r"[\w\u4e00-\u9fff]", text)
        return [{"text": token, "start": .1 + i * .025, "end": .12 + i * .025} for i, token in enumerate(tokens)]
    monkeypatch.setattr(prep, "synthesize", fake)
    return calls


@pytest.fixture
def prepared(tmp_path, valid_script, speech):
    valid_script["scenes"][0]["narration"] = "你好，世界。"
    source = tmp_path / "storyboard.json"
    source.write_text(json.dumps(valid_script, ensure_ascii=False), encoding="utf-8")
    path = prep.prepare(source, tmp_path / "media")
    return source, path


def test_extension_silence_and_fingerprint(prepared):
    source, path = prepared
    media = load_media(path, source)
    assert media.storyboard.scenes[0].duration_in_frames == 69
    assert media.storyboard.scenes[1].duration_in_frames == 60
    assert media.data["scenes"][1]["audio"] is None
    assert json.loads(source.read_text(encoding="utf-8"))["scenes"][0]["durationInFrames"] == 30
    assert audio.wav_duration(media.audio) == 4.3
    with wave.open(str(media.audio), "rb") as stream:
        stream.setpos(24000 * 3)
        assert not any(stream.readframes(24000))
    assert [c["text"] for c in media.data["cues"]] == ["你好，", "世界。"]


def test_cache_reuse_text_voice_rate_and_force(prepared, speech):
    source, path = prepared
    prep.prepare(source, path.parent)
    assert len(speech) == 1
    data = json.loads(source.read_text(encoding="utf-8"))
    data["scenes"][1]["narration"] = "结束。"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    prep.prepare(source, path.parent)
    assert len(speech) == 2
    prep.prepare(source, path.parent, voice="another-voice")
    assert len(speech) == 4
    prep.prepare(source, path.parent, rate="+10%")
    assert len(speech) == 6
    prep.prepare(source, path.parent, force=True)
    assert len(speech) == 8


def test_corrupt_cache_regenerated(prepared, speech):
    source, path = prepared
    cache = next((path.parent / "cache").glob("*.wav"))
    cache.write_bytes(b"broken")
    prep.prepare(source, path.parent)
    assert len(speech) == 2


def test_stale_manifest_rejected(prepared):
    source, path = prepared
    data = json.loads(source.read_text(encoding="utf-8"))
    data["title"] = "changed"
    source.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(A2VError, match="重新 prepare"):
        load_media(path, source)
    assert cli.main_render(["--page", "absent", "--out", "out.mp4", "--media", str(path), "--storyboard", str(source)]) == 1


@pytest.mark.parametrize("change", ["duration", "cues", "audio"])
def test_invalid_manifest(prepared, change):
    source, path = prepared
    data = json.loads(path.read_text(encoding="utf-8"))
    if change == "duration":
        data["scenes"][0]["durationInFrames"] = -1
    elif change == "cues":
        data["cues"][0]["end"] = 100
    else:
        data["audio"] = "../escape.wav"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(A2VError):
        load_media(path, source)


def test_network_failure_retries_and_preserves_manifest(prepared, monkeypatch):
    source, path = prepared
    before = path.read_bytes()
    calls = []
    async def fail(*args):
        calls.append(1)
        raise TimeoutError("offline")
    monkeypatch.setattr(prep, "synthesize", fail)
    monkeypatch.setattr(prep.time, "sleep", lambda _: None)
    with pytest.raises(A2VError, match="3 次"):
        prep.prepare(source, path.parent, force=True)
    assert len(calls) == 3
    assert path.read_bytes() == before


@pytest.mark.parametrize("words", [[], [{"text": "好", "start": 2, "end": 1}],
    [{"text": "好", "start": float("nan"), "end": 1}], [{"text": "错", "start": 0, "end": .2}]])
def test_bad_timestamps(words):
    with pytest.raises(A2VError):
        cues_from_words("好", words, 2)


def test_long_sentence_and_clipped_srt():
    text = "字" * 60
    words = [{"text": "字", "start": i * .1, "end": (i + 1) * .1} for i in range(60)]
    cues = cues_from_words(text, words, 6)
    assert [len(c["text"]) for c in cues] == [28, 28, 4]
    assert cues[1]["start"] == pytest.approx(2.8)
    output = srt(cues, 3)
    assert "00:00:03,000" in output
    assert output.count("-->") == 2


def test_prepare_cli_invalid_input(tmp_path):
    assert cli.main_prepare(["--storyboard", str(tmp_path / "absent"), "--out-dir", str(tmp_path)]) == 1
    # 只给 --media 属于参数组合非法，按「输入无效」退出，而不是渲染失败
    assert cli.main_render(["--page", "none", "--out", "none.mp4", "--media", "none.json"]) == 2


@pytest.fixture
def example_media(tmp_path, speech):
    return load_media(prep.prepare(EXAMPLES_DIR / "storyboard.json", tmp_path / "media"))


def test_subtitle_frames_layout_playback_and_determinism(example_media):
    media = example_media
    with LocalServer(media.path.parent, cors=True) as server:
        with _resolve_page_url(EXAMPLES_DIR / "index.html", None) as url:
            with open_animated_page(media_url(url, server.base_url, media), width=1080, height=1920) as page:
                page.seek(0)
                assert page.evaluate("() => document.querySelector('[data-a2v-subtitle]').hidden")
                page.seek(4)
                assert page.evaluate("() => document.querySelector('[data-a2v-subtitle]').textContent") == media.data["cues"][0]["text"]
                bounds = page.evaluate("""() => {let el=document.querySelector('[data-a2v-subtitle]');let r=el.getBoundingClientRect();return {bottom:r.bottom,height:r.height,lines:el.scrollHeight/parseFloat(getComputedStyle(el).lineHeight)}}""")
                assert bounds["bottom"] <= 1600
                assert bounds["height"] <= 128
                page.evaluate("() => A2V.controller.play()")
                page.evaluate("() => new Promise(r => setTimeout(r, 250))")
                assert page.evaluate("() => A2V.controller.currentFrame()") > 4
                page.evaluate("() => A2V.controller.pause()")
                paused = page.evaluate("() => A2V.controller.currentFrame()")
                page.evaluate("() => new Promise(r => setTimeout(r, 100))")
                assert page.evaluate("() => A2V.controller.currentFrame()") == paused
                page.seek(600)
                assert page.evaluate("() => document.querySelector('[data-a2v-audio]').currentTime") == pytest.approx(20, abs=.04)
                page.evaluate("() => A2V.controller.replay()")
                page.evaluate("() => new Promise(r => setTimeout(r, 200))")
                assert page.evaluate("() => A2V.controller.currentFrame()") < 30
                page.evaluate("() => A2V.controller.pause()")
                page.seek(60)
                assert page.evaluate("() => document.querySelector('[data-a2v-subtitle]').hidden")
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                page.seek(4)
                first = page.capture("png")
                page.seek(60)
                page.seek(4)
                assert first == page.capture("png")
                page.evaluate("() => A2V.controller.play()")
                assert not page.evaluate("() => A2V.controller.isPlaying()")


def test_voiced_render_and_short_clip(example_media, tmp_path):
    output = tmp_path / "clip.mp4"
    result = render(EXAMPLES_DIR / "index.html", output,
                    storyboard=sb.load(EXAMPLES_DIR / "storyboard.json")[0], media=example_media, limit_frames=9)
    assert result.frames == 9
    assert output.with_suffix(".srt").is_file()
    content = output.with_suffix(".srt").read_text(encoding="utf-8")
    assert "00:00:00,300" in content
    _verify_output(output, 9, 1080, 1920, 30, expect_audio=True)
    with pytest.raises(A2VError, match="尺寸"):
        _verify_output(output, 9, 720, 1280, 30, expect_audio=True)


@pytest.mark.parametrize("narration", [None, 1, {}, []])
def test_narration_type_is_checked(valid_script, narration):
    valid_script["scenes"][0]["narration"] = narration
    report = sb.validate(valid_script)
    assert any(i.path == "scenes[0].narration" for i in report.errors)


def test_validate_media_command(prepared):
    source, media = prepared
    assert cli.main_validate([str(source), "--media", str(media)]) == 0


def test_preview_media_starts_and_closes(prepared, monkeypatch):
    import webbrowser
    import time
    source, media = prepared
    (source.parent / "index.html").write_text("<html></html>", encoding="utf-8")
    opened = []
    monkeypatch.setattr(webbrowser, "open", opened.append)
    def interrupt(_):
        raise KeyboardInterrupt
    monkeypatch.setattr(time, "sleep", interrupt)
    assert cli.main_preview([str(source.parent), "--media", str(media)]) == 0
    assert "a2v-media=" in opened[0]


def test_media_range_requests(tmp_path):
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    path = tmp_path / "audio.wav"
    path.write_bytes(bytes(range(100)))
    with LocalServer(tmp_path, cors=True) as server:
        for value, expected in [("bytes=20-39", bytes(range(20, 40))), ("bytes=-10", bytes(range(90, 100))), ("bytes=95-", bytes(range(95, 100)))]:
            with urlopen(Request(server.base_url + "/audio.wav", headers={"Range": value})) as response:
                assert response.status == 206
                assert response.read() == expected
        with pytest.raises(HTTPError) as error:
            urlopen(Request(server.base_url + "/audio.wav", headers={"Range": "bytes=101-"}))
        assert error.value.code == 416


def test_audio_corruption_rejected(prepared):
    source, path = prepared
    media = load_media(path)
    media.audio.write_bytes(media.audio.read_bytes()[:50])
    with pytest.raises(A2VError):
        load_media(path, source)


def test_missing_timestamps_does_not_publish(prepared, monkeypatch):
    source, path = prepared
    before = path.read_bytes()
    async def incomplete(text, voice, rate, output):
        tone(output)
        return []
    monkeypatch.setattr(prep, "synthesize", incomplete)
    with pytest.raises(A2VError, match="时间戳"):
        prep.prepare(source, path.parent, force=True)
    assert path.read_bytes() == before


def test_render_rejects_mismatched_dimensions(example_media, tmp_path):
    data = json.loads((EXAMPLES_DIR / "storyboard.json").read_text(encoding="utf-8"))
    data["width"] = 720
    source = tmp_path / "small.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(A2VError, match="画面尺寸"):
        render(EXAMPLES_DIR / "index.html", tmp_path / "none.mp4", storyboard=sb.load(source)[0], limit_frames=1)
