"""配音和字幕回归：服务替身提供真实可解码音频，常规测试不访问网络。

入口只接受分镜 v4，因此本模块的夹具与清单断言都按 v4 契约构造与校验：
顶层 ``stages`` / ``resolvedBeats`` / ``cues`` / ``standardCheck``，
阶段帧数由 prepare 按**实际语音时长**派生。
"""
from __future__ import annotations

import json
import math
import re
import struct
import wave
from pathlib import Path

import pytest

import a2v.types.article.media as media_mod
import a2v.engine.audio as audio
import a2v.engine.beats as beats
import a2v.types.article.cli as cli
import a2v.types.article.prepare as prep
import a2v.types.article.storyboard_v4 as storyboard_v4
from a2v.core.errors import A2VError
from a2v.types.article.media import load_media
from a2v.engine.subtitles import cues_from_words, srt
from a2v.engine.http_server import LocalServer
from conftest import make_project, v4_storyboard

#: v4 示例夹具；共享测试数据本身仍由 v4_storyboard 构造
V4_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "darts-trial-and-error" / "storyboard.json"

#: v4 骨架里每个阶段声明的帧数；实际时长由 prepare 重新派生
DECLARED_STAGE_FRAMES = 400


def tone(path, duration=2.0):
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        samples = (int(2000 * math.sin(2 * math.pi * 440 * n / 24000)) for n in range(round(duration * 24000)))
        stream.writeframes(b"".join(struct.pack("<h", n) for n in samples))


@pytest.fixture
def speech(monkeypatch):
    """替换 edge-tts：记录调用并生成可解码音轨，时长口径与 conftest 一致。

    语速按中文标准口播的常见节奏（每字约 0.25 秒）折算：v4 的 prepare 用
    **实际语音时长**派生每个阶段，太快会让合规的 130～170 字口播落进
    35 秒以下的实际时长不合格。这里单独定义而不是直接用 conftest 的同名
    夹具，是因为本模块还要按调用次数断言「哪种变化让缓存失效」。
    """
    calls = []
    async def fake(text, voice, rate, output):
        calls.append((text, voice, rate))
        tokens = re.findall(r"[\w\u4e00-\u9fff]", text)
        tone(output, 0.3 + len(tokens) * 0.25)
        return [{"text": token, "start": .1 + i * .25, "end": .2 + i * .25} for i, token in enumerate(tokens)]
    monkeypatch.setattr(prep, "synthesize", fake)
    return calls


@pytest.fixture
def prepared(tmp_path, valid_script_v4, speech):
    """规范项目结构里的 v4 分镜，prepare 一次后返回（源分镜, 媒体清单）。"""
    article = make_project(tmp_path, "videos", "demo", valid_script_v4)
    source = article / "storyboard.json"
    path = prep.prepare(source, tmp_path / "media")
    return source, path


def test_stage_frames_derive_from_actual_speech(prepared):
    """阶段帧数按实际语音时长派生，源分镜声明的时长不被改写。"""
    source, path = prepared
    media = load_media(path, source)
    declared = json.loads(source.read_text(encoding="utf-8"))["stages"]
    assert [stage["durationInFrames"] for stage in declared] == [DECLARED_STAGE_FRAMES] * 3
    for stage_data, stage in zip(media.data["stages"], media.storyboard.stages):
        # 实际时长 = ceil(语音秒数 × fps) + 固定阅读余量
        speech_seconds = audio.wav_duration(path.parent / stage_data["audio"])
        assert stage.duration_in_frames == math.ceil(speech_seconds * media.storyboard.fps) + beats.STABLE_READING_FRAMES
    assert media.storyboard.total_frames == sum(s["durationInFrames"] for s in media.data["stages"])
    assert media.data["standardCheck"]["actualDurationInFrames"] == media.storyboard.total_frames
    assert media.data["standardCheck"]["durationStatus"] == "pass"
    assert audio.wav_duration(media.audio) == pytest.approx(
        media.storyboard.total_frames / media.storyboard.fps, abs=1 / 24000
    )
    # 阶段尾部多出的阅读余量是静音：全片音轨不得靠拉长口播凑时长
    with wave.open(str(media.audio), "rb") as stream:
        total = stream.getnframes()
        stream.setpos(total - 4800)
        assert not any(stream.readframes(4800))
        stream.setpos(total - 12000)
        assert any(stream.readframes(4000))
    # 字幕文本与源分镜的分段口播逐字一致
    assert "".join(cue["text"] for cue in media.data["cues"]) == "".join(
        segment["text"] for stage in declared for segment in stage["narrationSegments"]
    )


# 原用例「version 2 清单去掉声音字段后仍可读」描述的是已删除的 v3 兼容行为：
# load_media 现在只接受 version 4，旧清单一律要求重新 prepare，因此该用例删除。


@pytest.mark.parametrize("version", [1, 2, 3])
def test_legacy_manifest_versions_are_rejected(prepared, version):
    """v1–v3 清单不再读取：入口只认 v4，并要求按 v4 契约重新 prepare。"""
    source, path = prepared
    original = json.loads(path.read_text(encoding="utf-8"))
    for mutate in (
        lambda data: data.update(version=version),
        lambda data: data["source"].update(version=version, schemaVersion=version),
    ):
        data = json.loads(json.dumps(original))
        mutate(data)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(A2VError, match="重新 prepare"):
            load_media(path, source)


def test_cache_reuse_text_voice_rate_and_force(prepared, speech):
    source, path = prepared
    assert len(speech) == 3  # 三个阶段各合成一次
    prep.prepare(source, path.parent)
    assert len(speech) == 3  # 文本、音色、语速都没变：全部命中缓存
    data = json.loads(source.read_text(encoding="utf-8"))
    data["stages"][1]["narrationSegments"][0]["text"] = "每次记录落点，也要顺便记下修正的方向。"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    prep.prepare(source, path.parent)
    assert len(speech) == 4  # 只有改过口播的那个阶段重新合成
    prep.prepare(source, path.parent, voice="another-voice")
    assert len(speech) == 7
    prep.prepare(source, path.parent, rate="+10%")
    assert len(speech) == 10
    prep.prepare(source, path.parent, force=True)
    assert len(speech) == 13


def test_corrupt_cache_regenerated(prepared, speech):
    source, path = prepared
    cache = next((path.parent / "cache").glob("*.wav"))
    cache.write_bytes(b"broken")
    prep.prepare(source, path.parent)
    assert len(speech) == 4  # 只有校验和不符的那个阶段重新合成


def test_stale_manifest_rejected(prepared):
    source, path = prepared
    data = json.loads(source.read_text(encoding="utf-8"))
    data["title"] = "changed"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(A2VError, match="重新 prepare"):
        load_media(path, source)
    assert cli.main_render(["--out", str(source.parent / "out.mp4"), "--media", str(path),
                            "--storyboard", str(source)]) == 1


@pytest.mark.parametrize("change", ["duration", "cues", "audio", "standardCheck", "resolvedBeats"])
def test_invalid_manifest(prepared, change):
    source, path = prepared
    data = json.loads(path.read_text(encoding="utf-8"))
    if change == "duration":
        data["stages"][0]["durationInFrames"] = -1
    elif change == "cues":
        data["cues"][0]["end"] = 100
    elif change == "audio":
        data["audio"] = "../escape.wav"
    elif change == "standardCheck":
        data["standardCheck"]["durationStatus"] = "fail"
    else:
        data["resolvedBeats"][0]["targets"] = ["nowhere"]
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
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
    assert cli.main_render(["--out", "none.mp4", "--media", "none.json"]) == 2


@pytest.fixture
def example_media(tmp_path, speech):
    return load_media(prep.prepare(V4_EXAMPLE, tmp_path / "media"))


@pytest.mark.parametrize("narration", [None, 1, {}, []])
def test_narration_field_is_rejected_in_v4(valid_script_v4, narration):
    """v4 用 narrationSegments 取代幕级 narration：声明该字段一律报错。"""
    valid_script_v4["stages"][0]["narration"] = narration
    report = storyboard_v4.validate(valid_script_v4)
    assert any(i.path == "stages[0].narration" for i in report.errors)


@pytest.mark.parametrize("narration", [None, 1, {}])
def test_narration_segments_type_is_checked(narration):
    script = v4_storyboard()
    script["stages"][0]["narrationSegments"] = narration
    report = storyboard_v4.validate(script)
    assert any("narrationSegments 与 beats 必须是数组" in i.message for i in report.errors)


def test_validate_media_command(prepared):
    source, media = prepared
    assert cli.main_validate([str(source), "--media", str(media)]) == 0


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


def test_effective_storyboard_uses_media_timeline(prepared):
    """有效分镜的时长必须来自媒体清单，源分镜保持声明时长不变。"""
    source, path = prepared
    media = load_media(path, source)
    effective = media_mod.effective_storyboard(media)
    source_data = json.loads(source.read_text(encoding="utf-8"))
    # v4 把派生时间轴收进 mediaTimeline：顶层仍是源分镜快照，时长不被改写
    assert effective["stages"] == source_data["stages"]
    assert [s["durationInFrames"] for s in effective["mediaTimeline"]["stages"]] == [
        s["durationInFrames"] for s in media.data["stages"]
    ]
    assert sum(s["durationInFrames"] for s in effective["mediaTimeline"]["stages"]) == media.storyboard.total_frames
    assert effective["mediaTimeline"]["resolvedBeats"] == media.data["resolvedBeats"]
    assert effective["subtitleCues"] == media.data["cues"]


def test_write_effective_storyboard_defaults_to_media_dir(prepared):
    """默认落盘到媒体目录（预览/评审的媒体服务根），文件名自证派生身份。"""
    source, path = prepared
    media = load_media(path, source)
    written = media_mod.write_effective_storyboard(media)
    assert written.parent == path.parent
    assert written.name == "storyboard.effective.json"
    data = json.loads(written.read_text(encoding="utf-8"))
    assert sum(s["durationInFrames"] for s in data["mediaTimeline"]["stages"]) == media.storyboard.total_frames
    assert data["subtitleCues"] == media.data["cues"]
    custom = path.parent / "elsewhere"
    assert media_mod.write_effective_storyboard(media, custom).parent == custom


def test_voiced_render_passes_effective_props(prepared, tmp_path, monkeypatch):
    """有声渲染的 props 必须是媒体派生分镜；打包仍用原始分镜路径。

    回归背景：props 曾一直是原始分镜，composition 按声明时长注册，
    总帧数交叉校验报「不一致」，有声渲染根本无法完成。
    """
    import a2v.engine.remotion as remotion_mod
    import a2v.types.article.render as render_mod
    from a2v.engine.remotion import BundleOutcome, CompositionMetadata

    source, path = prepared
    media = load_media(path, source)
    output = tmp_path / "out" / "voiced.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    captured: dict = {}

    def fake_bundle(**kwargs):
        captured["bundle_storyboard"] = Path(kwargs["storyboard_path"])
        return BundleOutcome(
            path=tmp_path / "bundle",
            cache_status="hit",
            cache_key="test-key",
            cache_detail="测试夹具：直接命中",
            cache_seconds=0.0,
            build_seconds=0.0,
        )

    def fake_session(**kwargs):
        # 渲染发生在临时目录存续期间：props 的内容只能在这里读
        props = Path(kwargs["props"])
        captured["props"] = props
        timeline = json.loads(props.read_text(encoding="utf-8"))["mediaTimeline"]["stages"]
        captured["props_timeline"] = timeline
        captured["render_timeline"] = timeline
        params = kwargs["on_metadata"](
            CompositionMetadata(
                fps=30, width=1080, height=1920, duration_in_frames=media.storyboard.total_frames
            )
        )
        captured["params"] = params
        return {"readySeconds": 0.5, "browsersOpened": 1}

    def fake_finalize(**kwargs):
        kwargs["output_path"].write_bytes(b"mp4")

    monkeypatch.setattr(remotion_mod, "require_environment", lambda: tmp_path)
    monkeypatch.setattr(remotion_mod, "bundle", fake_bundle)
    monkeypatch.setattr(remotion_mod, "render_session", fake_session)
    monkeypatch.setattr(render_mod, "_finalize_output", fake_finalize)
    monkeypatch.setattr(render_mod, "_write_provenance", lambda *args, **kwargs: None)

    result = render_mod.render_with_remotion(
        output=output,
        storyboard=media.storyboard,
        storyboard_path=source,
        media=media,
        bundle_cache=False,
    )

    assert result.frames == media.storyboard.total_frames
    # props 是临时目录里的派生分镜（带媒体时间轴），打包仍是原始分镜
    assert captured["props"] != source
    assert sum(s["durationInFrames"] for s in captured["props_timeline"]) == media.storyboard.total_frames
    assert captured["render_timeline"] == captured["props_timeline"]
    assert captured["bundle_storyboard"] == source
    assert captured["params"]["frames"] == f"0-{media.storyboard.total_frames - 1}"
