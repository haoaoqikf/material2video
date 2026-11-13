"""Qwen3-TTS 后端的配置、参考音色摘要、缓存隔离与零时长修复；不加载模型。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.engine import qwen3_tts, tts


def _voice(**overrides):
    value = {
        "voice": "clone_test",
        "refAudio": "qwen3-tts/voices/clone_test.wav",
        "refText": "参考文本。",
        "language": "Chinese",
        "sha256": "a" * 64,
        "bytes": 123,
        "authorization": {"userAuthorized": True, "statement": "用户明确要求使用该参考音色"},
    }
    value.update(overrides)
    return value


def _registry(tmp_path: Path, voices: list[dict] | None = None) -> Path:
    models = tmp_path / "models"
    directory = models / "qwen3-tts"
    (directory / "licenses").mkdir(parents=True)
    (directory / "licenses" / "Apache-2.0.txt").write_text("license", encoding="utf-8")
    (models / "files" / "qwen3-tts").mkdir(parents=True)
    data = {
        "schemaVersion": 1,
        "backend": "qwen3-tts",
        "repo": qwen3_tts.REPO_ID,
        "revision": qwen3_tts.REVISION,
        "license": "licenses/Apache-2.0.txt",
        "modelDir": "qwen3-tts/model",
        "alignerDir": "qwen3-tts/aligner",
        "files": [],
        "voices": voices if voices is not None else [_voice()],
    }
    (directory / "registry.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return models


def test_settings_pair_backend_with_voice_format() -> None:
    assert tts.settings({"tts": {"backend": "qwen3-tts", "voice": "clone_test"}})[
        "backend"] == "qwen3-tts"
    for config in (
        {"backend": "qwen3-tts", "voice": "zf_027"},
        {"backend": "qwen3-tts", "voice": "zh-CN-XiaoxiaoNeural"},
        {"backend": "kokoro", "voice": "clone_test"},
    ):
        with pytest.raises(M2VError, match="音色名必须形如"):
            tts.settings({"tts": config})


def test_speed_mapping() -> None:
    assert qwen3_tts.speed_for_rate("+20%") == 1.2
    assert qwen3_tts.speed_for_rate("-2%") == 0.98
    assert qwen3_tts.speed_for_rate("+0%") == 1.0
    with pytest.raises(ValueError, match="语速"):
        qwen3_tts.speed_for_rate("20%")


def test_voice_registry_and_digest(tmp_path: Path) -> None:
    models = _registry(tmp_path)
    assert qwen3_tts.voice_names(models)[0]["voice"] == "clone_test"
    digest = qwen3_tts.voice_digest(models, "clone_test")
    assert len(digest) == 64
    with pytest.raises(M2VError, match="没有"):
        qwen3_tts.voice_digest(models, "clone_missing")


def test_reference_voice_requires_user_authorization(tmp_path: Path) -> None:
    models = _registry(tmp_path, [_voice(authorization={"userAuthorized": False})])
    with pytest.raises(M2VError, match="用户明确要求"):
        qwen3_tts.voice_names(models)


def test_cache_key_separates_backends_and_voice_profiles(tmp_path: Path) -> None:
    models = _registry(tmp_path)
    edge = tts.scene_cache_key("旁白", "zh-CN-XiaoxiaoNeural", "+0%", 9)
    qwen = tts.scene_cache_key("旁白", "clone_test", "+20%", 9,
                               backend="qwen3-tts", models_dir=models)
    assert edge != qwen
    assert qwen == tts.scene_cache_key("旁白", "clone_test", "+20%", 9,
                                       backend="qwen3-tts", models_dir=models)
    # 参考文本变化会改变音色档案摘要，从而改变缓存键。
    data = json.loads((models / "qwen3-tts/registry.json").read_text(encoding="utf-8"))
    data["voices"][0]["refText"] = "另一段参考文本。"
    (models / "qwen3-tts/registry.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert qwen != tts.scene_cache_key("旁白", "clone_test", "+20%", 9,
                                       backend="qwen3-tts", models_dir=models)


def test_zero_duration_words_merge_without_changing_time() -> None:
    raw = [
        {"text": "为什么", "start": 0.26, "end": 0.34},
        {"text": "人", "start": 0.34, "end": 0.52},
        {"text": "越", "start": 0.52, "end": 0.7},
        {"text": "在", "start": 0.7, "end": 0.7},
        {"text": "乎", "start": 0.7, "end": 0.7},
        {"text": "别", "start": 0.7, "end": 0.92},
        {"text": "活", "start": 0.92, "end": 0.92},
        {"text": "得", "start": 0.92, "end": 1.02},
    ]
    words = qwen3_tts._repair_words(raw, 1.2)
    assert [word["text"] for word in words] == ["为什么", "人", "越", "在乎别", "活得"]
    assert [(word["start"], word["end"]) for word in words] == [
        (0.26, 0.34), (0.34, 0.52), (0.52, 0.7), (0.7, 0.92), (0.92, 1.02)]


def test_zero_duration_punctuation_merges_backward() -> None:
    raw = [
        {"text": "价", "start": 1.2, "end": 1.4},
        {"text": "，", "start": 1.4, "end": 1.4},
        {"text": "活", "start": 1.4, "end": 1.5},
    ]
    words = qwen3_tts._repair_words(raw, 2.0)
    assert [word["text"] for word in words] == ["价，", "活"]


def test_standalone_punctuation_token_merges_backward() -> None:
    # 对齐器把句末分号单独成词时，字幕链路会从原文把标点挂回前词；
    # 独立标点必须先并入前词，否则下一个词语会被跳过。
    raw = [
        {"text": "话", "start": 1.4, "end": 1.58},
        {"text": "；", "start": 1.58, "end": 1.74},
        {"text": "想", "start": 1.76, "end": 1.88},
    ]
    words = qwen3_tts._repair_words(raw, 2.0)
    assert [word["text"] for word in words] == ["话；", "想"]
    assert [(word["start"], word["end"]) for word in words] == [(1.4, 1.58), (1.76, 1.88)]


def test_punctuation_is_not_duplicated() -> None:
    raw = [
        {"text": "圈，", "start": 0.78, "end": 1.04},
        {"text": "，", "start": 1.04, "end": 1.04},
        {"text": "怕", "start": 1.12, "end": 1.22},
    ]
    words = qwen3_tts._repair_words(raw, 2.0)
    assert [word["text"] for word in words] == ["圈，", "怕"]


def test_timestamp_regression_fails() -> None:
    raw = [
        {"text": "甲", "start": 0.2, "end": 0.4},
        {"text": "乙", "start": 0.3, "end": 0.5},
    ]
    with pytest.raises(ValueError, match="倒退"):
        qwen3_tts._repair_words(raw, 1.0)


def test_unsupported_text_fails_before_loading(tmp_path: Path) -> None:
    for text in ("2024 年的故事。", "Hello，世界。"):
        with pytest.raises(ValueError, match="不支持"):
            qwen3_tts.synthesize(text, "clone_test", "+0%", tmp_path / "a.wav",
                                 models_dir=tmp_path / "models")


def test_missing_model_fails_with_action(tmp_path: Path) -> None:
    with pytest.raises(M2VError, match="qwen3-tts/fetch.py"):
        qwen3_tts.ensure_assets(tmp_path / "models", "clone_test")
