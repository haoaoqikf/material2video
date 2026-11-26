"""Kokoro 模型登记与主项目/模板配音镜像的一致性。"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

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


def test_setup_checks_models_for_default_documentary_narration(monkeypatch) -> None:
    from film_runtime import cli
    from film_runtime.types.scene_film import explainer

    commands = []
    segments = []
    monkeypatch.setattr(cli, "_run", commands.append)
    monkeypatch.setattr(explainer, "load", lambda *args: {"scenes": [{"narrationSegments": segments}]})
    project = {"type": "documentary-edit", "tts": {"voice": "zf_027"}}
    cli._models(project, check=False, download=True)
    assert commands == []
    segments.append({"id": "line", "text": "试制。"})
    cli._models(project, check=False, download=True)
    assert commands[0][1:] == ["models/fetch.py", "--download", "--voice", "zf_027"]


def test_prepare_stages_fonts_before_computing_inputs(monkeypatch) -> None:
    from film_runtime import cli
    from film_runtime.types.scene_film import explainer_prepare

    calls = []
    monkeypatch.setattr(cli, "_node", lambda: "node")
    monkeypatch.setattr(cli, "_run", calls.append)
    monkeypatch.setattr(explainer_prepare, "prepare", lambda *args, **kwargs: calls.append("prepare"))
    cli._prepare({}, SimpleNamespace(voice=None, rate=None, rhythm="null", backend=None))
    assert calls == [["node", "scripts/sync-fonts.mjs"], "prepare"]


def test_qwen_restore_reuses_identical_weight_and_can_make_portable_copy(tmp_path, monkeypatch):
    import hashlib
    import importlib.util
    import os

    module_spec = importlib.util.spec_from_file_location(
        "qwen_fetch", TEMPLATE / "models/qwen3-tts/fetch.py")
    fetch = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(fetch)
    monkeypatch.setenv("M2V_QWEN3_MODEL_STORE", str(tmp_path / "shared"))
    entry = {
        "file": "qwen3-tts/model/weight.bin", "provider": "modelscope",
        "bytes": 6, "sha256": hashlib.sha256(b"shared").hexdigest(),
    }
    first = tmp_path / "first" / "files"
    second = tmp_path / "second" / "files"
    first_weight = first / entry["file"]
    second_weight = second / entry["file"]
    first_weight.parent.mkdir(parents=True)
    first_weight.write_bytes(b"shared")
    monkeypatch.setattr(fetch, "FILES", first)
    fetch.restore(entry, download=False)
    monkeypatch.setattr(fetch, "FILES", second)
    fetch.restore(entry, download=False)
    if first_weight.stat().st_nlink > 1:
        assert os.path.samefile(first_weight, second_weight)
    assert second_weight.read_bytes() == first_weight.read_bytes()

    fetch.restore(entry, download=False, portable=True)
    assert not os.path.samefile(first_weight, second_weight)
    second_weight.write_bytes(b"edited")
    assert first_weight.read_bytes() == b"shared"
