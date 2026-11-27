"""Kokoro 后端的配置校验、缓存隔离与失败前置；不加载模型。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.engine import kokoro_tts, tts


def test_settings_pair_backend_with_voice_format() -> None:
    assert tts.settings({"tts": {"backend": "kokoro", "voice": "zf_027"}})[
        "backend"] == "kokoro"
    assert tts.settings({"tts": {"backend": "edge-tts", "voice": "zh-CN-YunxiNeural"}})[
        "voice"] == "zh-CN-YunxiNeural"
    for config in (
        {"backend": "kokoro", "voice": "zh-CN-XiaoxiaoNeural"},
        {"backend": "edge-tts", "voice": "zf_027"},
    ):
        with pytest.raises(M2VError, match="音色名必须形如"):
            tts.settings({"tts": config})


def test_preparation_records_actual_backend() -> None:
    project = {"tts": {"backend": "kokoro", "voice": "zf_027", "rate": "+20%"}}
    record = tts.preparation(project, ["你好。"])
    assert record["backend"] == "kokoro"
    assert record["voice"] == "zf_027"
    assert record["rate"] == "+20%"
    # 命令行覆盖后端时，音色仍按覆盖后的后端校验。
    assert tts.preparation({"tts": {"voice": "zh-CN-XiaoxiaoNeural"}}, ["你好。"],
                           backend="edge-tts")["backend"] == "edge-tts"
    with pytest.raises(M2VError, match="音色名必须形如"):
        tts.preparation({"tts": {"voice": "zh-CN-XiaoxiaoNeural"}}, ["你好。"],
                        backend="kokoro")


def test_narration_defaults_to_edge_and_allows_kokoro_override() -> None:
    project = {"type": "text-motion", "tts": {"voice": "zh-CN-XiaoxiaoNeural"}}
    assert tts.preparation(project, ["你好。"])["backend"] == "edge-tts"
    assert tts.preparation(project, ["你好。"], backend="kokoro",
                           voice="zf_027")["backend"] == "kokoro"
    assert tts.preparation({"type": "text-motion"}, []) == {}
    with pytest.raises(M2VError, match="voices --backend edge-tts"):
        tts.preparation({"type": "text-motion"}, ["你好。"])


def test_cache_key_separates_backends() -> None:
    edge = tts.scene_cache_key("旁白", "zh-CN-XiaoxiaoNeural", "+0%", 9)
    kokoro = tts.scene_cache_key("旁白", "zf_027", "+20%", 9, backend="kokoro")
    assert edge != kokoro
    assert edge == tts.scene_cache_key("旁白", "zh-CN-XiaoxiaoNeural", "+0%", 9,
                                       backend="edge-tts")


def test_rate_maps_to_kokoro_speed() -> None:
    assert kokoro_tts.speed_for_rate("+20%") == 1.2
    assert kokoro_tts.speed_for_rate("-2%") == 0.98
    assert kokoro_tts.speed_for_rate("+0%") == 1.0
    with pytest.raises(ValueError, match="语速"):
        kokoro_tts.speed_for_rate("20%")


def test_voice_list_is_chinese_only() -> None:
    voices = kokoro_tts.voice_names()
    assert len(voices) == 100
    assert all(voice["voice"].startswith(("zf_", "zm_")) for voice in voices)
    assert {voice["gender"] for voice in voices} == {"Female", "Male"}


def test_unsupported_text_fails_before_loading(tmp_path: Path) -> None:
    for text in ("2024 年的故事。", "Hello，世界。"):
        with pytest.raises(ValueError, match="不支持"):
            kokoro_tts.synthesize(text, "zf_027", "+0%", tmp_path / "a.wav",
                                  models_dir=tmp_path)


def test_missing_model_fails_with_action(tmp_path: Path) -> None:
    with pytest.raises(M2VError, match="models/fetch.py"):
        kokoro_tts.ensure_assets(tmp_path, "zf_027")


def test_kokoro_voice_json_is_valid_package_data() -> None:
    path = Path(kokoro_tts.__file__).with_name("kokoro_voices.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schemaVersion"] == 1
    assert data["voices"][0]["voice"].startswith(("zf_", "zm_"))
