"""韵律整形：配置校验、停顿归类、时长重设与时间戳一致性。"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.engine import rhythm
from m2v.engine import tts

RATE = 24000


def _write(path: Path, segments: list[tuple[str, float]]) -> None:
    """按「有声/静音 + 秒数」拼一段 16 位单声道 PCM。"""
    import array

    samples = array.array("h")
    for kind, seconds in segments:
        count = int(seconds * RATE)
        if kind == "tone":
            samples.extend(12000 if index % 2 else -12000 for index in range(count))
        else:
            samples.extend([0] * count)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        stream.writeframes(samples.tobytes())


def test_configure_validates_pauses_and_head_pad() -> None:
    assert rhythm.configure({"pause": {"comma": 0.15, "period": 0.55}}) == {
        "pause": {"comma": 0.15, "period": 0.55}}
    assert rhythm.configure({"headPad": 0})["headPad"] == 0.0
    assert rhythm.configure({"pause": {"comma": 0.15}, "rate": "-6%"})["pause"] == {"comma": 0.15}

    for declared, message in (
        ({"pause": {}}, "非空对象"),
        ({"pause": {"comma": 0.5}}, "0.03 至 0.45"),
        ({"pause": {"period": 0.0}}, "0.03 至 0.9"),
        ({"pause": {"paragraph": 2.0}}, "0.03 至 1.4"),
        ({"headPad": 1.5}, "0 至 0.8"),
        ({"pause": {"sentence": 0.3}}, "未知类别"),
        ({"tempo": 0.3}, "未知字段"),
        ({}, "至少需要声明"),
        ({"pause": {"comma": "快"}}, "数值秒数"),
    ):
        with pytest.raises(M2VError, match=message):
            rhythm.configure(declared)


def test_settings_carries_validated_speech() -> None:
    assert tts.settings({"tts": {"speech": {"pause": {"comma": 0.14}}}}) == {
        "backend": "edge-tts", "speech": {"pause": {"comma": 0.14}}}
    with pytest.raises(M2VError, match="未知字段"):
        tts.settings({"tts": {"speed": "+0%"}})
    with pytest.raises(M2VError, match="至少需要声明"):
        tts.settings({"tts": {"speech": {}}})


def test_pause_is_classified_by_punctuation_between_words(tmp_path: Path) -> None:
    # 词边界事件不带标点，所以类别必须靠原文下标对齐得出。
    wav = tmp_path / "scene.wav"
    _write(wav, [("tone", 0.5), ("silence", 0.2), ("tone", 0.5)])
    words = [{"text": "甲", "start": 0.0, "end": 0.5},
             {"text": "乙", "start": 0.7, "end": 1.2}]
    rate, samples = rhythm.read_samples(wav)

    pauses = rhythm.plan("甲，乙。", words, rate, samples, {"pause": {"comma": 0.1, "period": 0.4}})
    assert [(pause.kind, pause.target) for pause in pauses] == [("comma", 0.1)]

    # 同一个停顿换成句号就按句号目标走。
    other = rhythm.plan("甲。乙。", words, rate, samples, {"pause": {"comma": 0.1, "period": 0.4}})
    assert [(pause.kind, pause.target) for pause in other] == [("period", 0.4)]


def test_reshape_resizes_pauses_and_remaps_words(tmp_path: Path) -> None:
    wav = tmp_path / "scene.wav"
    _write(wav, [("tone", 0.5), ("silence", 0.2), ("tone", 0.5)])
    rate, samples = rhythm.read_samples(wav)
    pauses = [rhythm.Pause(start=0.5, end=0.7, kind="comma", target=0.1)]

    shaped, shifts = rhythm.reshape(samples, rate, pauses, {})

    # 停顿从 0.2s 收到 0.1s，整段短了 0.1s。
    assert len(shaped) == len(samples) - int(0.1 * RATE)
    # 前一时刻不动，之后的时刻统一前移。
    assert rhythm.remap(0.3, shifts) == pytest.approx(0.3)
    assert rhythm.remap(1.0, shifts) == pytest.approx(0.9)


def test_head_pad_trims_leading_silence(tmp_path: Path) -> None:
    wav = tmp_path / "scene.wav"
    _write(wav, [("silence", 0.3), ("tone", 0.5)])
    rate, samples = rhythm.read_samples(wav)

    shaped, shifts = rhythm.reshape(samples, rate, [], {"headPad": 0.1})

    assert len(shaped) == len(samples) - int(0.2 * RATE)
    assert shifts == [(0.0, pytest.approx(-0.2))]


def test_remap_all_keeps_timestamps_monotonic_within_audio() -> None:
    # 缩短停顿会把后文前移，末词可能压到音频长度之外；必须仍落在音频内且不倒退。
    below = rhythm.remap_all([0.0, 0.5, 1.0, 1.5, 2.0], [(0.5, -0.8)], 1.3)

    assert below == sorted(below)
    assert len(set(below)) == len(below)
    assert below[-1] <= 1.3


def test_shaping_uses_cached_synthesis_and_never_calls_the_service(tmp_path: Path) -> None:
    """调参是本地派生：语音服务不可达时，改停顿目标仍能完成准备。"""
    cache = tmp_path / "cache"
    cache.mkdir()
    raw = cache / "raw.wav"
    _write(raw, [("tone", 0.5), ("silence", 0.2), ("tone", 0.5)])
    key = tts.scene_cache_key("甲，乙。", "zh-CN-XiaoxiaoNeural", "+0%", 3)
    raw.replace(cache / f"{key}.wav")
    import hashlib
    (cache / f"{key}.json").write_text(json.dumps(
        {"words": [{"text": "甲", "start": 0.0, "end": 0.5},
                   {"text": "乙", "start": 0.7, "end": 1.2}],
         "sha256": hashlib.sha256((cache / f"{key}.wav").read_bytes()).hexdigest()},
        ensure_ascii=False), encoding="utf-8")

    def refuse(*_args, **_kwargs):
        raise AssertionError("缓存命中时不应请求语音服务")

    for target in (0.10, 0.25):
        result = tts.scene_audio("甲，乙。", "zh-CN-XiaoxiaoNeural", "+0%", cache,
                                 contract_version=3, rhythm={"pause": {"comma": target}},
                                 synthesizer=refuse)
        assert result[0].name.startswith(f"{key}.rhythm-")


def test_scene_audio_applies_rhythm_without_changing_cache_key(tmp_path: Path) -> None:
    """韵律是派生层：缓存里保存原始合成，开关它不影响缓存键。"""
    cache = tmp_path / "cache"
    cache.mkdir()
    raw = cache / "raw.wav"
    _write(raw, [("tone", 0.5), ("silence", 0.2), ("tone", 0.5)])
    key = tts.scene_cache_key("甲，乙。", "zh-CN-XiaoxiaoNeural", "+0%", 3)
    raw.replace(cache / f"{key}.wav")
    import hashlib
    (cache / f"{key}.json").write_text(json.dumps(
        {"words": [{"text": "甲", "start": 0.0, "end": 0.5},
                   {"text": "乙", "start": 0.7, "end": 1.2}],
         "sha256": hashlib.sha256((cache / f"{key}.wav").read_bytes()).hexdigest()},
        ensure_ascii=False), encoding="utf-8")

    plain = tts.scene_audio("甲，乙。", "zh-CN-XiaoxiaoNeural", "+0%", cache, contract_version=3)
    shaped = tts.scene_audio("甲，乙。", "zh-CN-XiaoxiaoNeural", "+0%", cache, contract_version=3,
                             rhythm={"pause": {"comma": 0.1}})

    assert plain[0].name == f"{key}.wav"
    assert shaped[0].name.startswith(f"{key}.rhythm-")
    assert shaped[3] < plain[3]
    # 字幕与音频同源重映射：末词结束不越过音频长度，字幕也落在音频内。
    assert shaped[2][-1]["end"] <= shaped[3] + 1e-6
    assert shaped[1][-1]["end"] <= shaped[3] + 1e-6
