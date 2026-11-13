"""Kokoro 模型登记与主项目/模板配音镜像的一致性。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates/standalone"


def test_registry_covers_model_config_and_chinese_voices() -> None:
    data = json.loads((TEMPLATE / "models/registry.json").read_text(encoding="utf-8"))
    assert data["schemaVersion"] == 1
    assert data["repo"] == "hexgrad/Kokoro-82M-v1.1-zh"
    assert len(data["revision"]) == 40
    assert (TEMPLATE / "models" / data["license"]).is_file()
    roles = {entry["role"] for entry in data["files"]}
    assert roles == {"model", "config", "voice"}
    voices = {entry["voice"] for entry in data["files"] if entry["role"] == "voice"}
    assert len(voices) == 100
    assert "zf_027" in voices
    for entry in data["files"]:
        assert len(entry["sha256"]) == 64
        assert all(c in "0123456789abcdef" for c in entry["sha256"])
        assert entry["bytes"] > 0
    # m2v voices 使用包内清单；两份来源不能漂移。
    listing = json.loads(
        (ROOT / "src/m2v/engine/kokoro_voices.json").read_text(encoding="utf-8"))
    assert {voice["voice"] for voice in listing["voices"]} == voices


def test_runtime_tts_mirrors_stay_identical() -> None:
    for name in ("tts.py", "kokoro_tts.py"):
        source = (ROOT / "src/m2v/engine" / name).read_text(encoding="utf-8")
        expected = (source.replace("m2v.", "film_runtime.")
                    .replace("from m2v ", "from film_runtime ")
                    .replace("M2VError", "VideoError"))
        actual = (TEMPLATE / "runtime/python/film_runtime/engine" / name).read_text(encoding="utf-8")
        assert actual == expected, f"{name} 与主项目镜像不一致，请重新生成模板"
