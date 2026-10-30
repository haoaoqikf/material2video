"""作品级 TTS 配置：音色与语速的解析、校验与准备记录绑定。"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.core.project import load_project
from m2v.engine import tts
from m2v.types.general import adapter
from conftest import create_typed_project

pytestmark = pytest.mark.media


def _tone(path: Path, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        stream.writeframes(b"\0\0" * int(seconds * 24000))


def _project(tmp_path: Path, plan: dict, tts_config: dict | None = None) -> tuple[Path, dict]:
    from _helpers import project
    root, manifest = project(tmp_path, plan)
    manifest.pop("tts", None)
    if tts_config is not None:
        manifest["tts"] = tts_config
    (root / "project.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return load_project(root)


def test_settings_are_optional_but_speech_requires_voice() -> None:
    assert tts.settings({}) == {}
    with pytest.raises(M2VError, match="尚未选择音色"):
        tts.resolve({})


def test_settings_validate_backend_voice_and_rate() -> None:
    assert tts.settings({"tts": {"voice": "zh-CN-YunxiNeural"}}) == {"backend": "edge-tts", "voice": "zh-CN-YunxiNeural"}
    assert tts.settings({"tts": {"rate": "-10%"}})["rate"] == "-10%"

    for bad, message in (
        ({"tts": "zh-CN-XiaoxiaoNeural"}, "必须是对象"),
        ({"tts": {"voice": "xiaoxiao"}}, "音色名"),
        ({"tts": {"voice": "晓晓"}}, "音色名"),
        ({"tts": {"rate": "0%"}}, "有符号百分比"),
        ({"tts": {"rate": "+80%"}}, "有符号百分比"),
        ({"tts": {"backend": "cosyvoice"}}, "不支持"),
        ({"tts": {"speed": "+0%"}}, "未知字段"),
    ):
        with pytest.raises(M2VError, match=message):
            tts.settings(bad)


def test_resolve_prefers_explicit_over_project_configuration() -> None:
    project = {"tts": {"voice": "zh-CN-YunxiNeural", "rate": "-10%"}}
    assert tts.resolve(project) == ("zh-CN-YunxiNeural", "-10%")
    # 命令行显式给出的值优先，另一项仍跟随作品配置。
    assert tts.resolve(project, voice="zh-CN-YunjianNeural") == ("zh-CN-YunjianNeural", "-10%")
    assert tts.resolve(project, rate="+5%") == ("zh-CN-YunxiNeural", "+5%")


def _speaking_plan() -> dict:
    from _helpers import board
    return board()


def _prepare_with_capture(root: Path, manifest: dict, monkeypatch) -> dict:
    from _helpers import fake_tts
    calls = fake_tts(monkeypatch)
    prepared = adapter.prepare(root, manifest)
    prepared["_seen"] = {"voice": calls[0][1], "rate": calls[0][2]}
    return prepared


def test_prepare_uses_project_voice_and_records_it(tmp_path: Path, monkeypatch) -> None:
    root, manifest = _project(tmp_path, _speaking_plan(), {"voice": "zh-CN-YunxiNeural", "rate": "-6%"})
    _tone(root / "assets" / "bed.wav", 1)

    prepared = _prepare_with_capture(root, manifest, monkeypatch)

    assert prepared["_seen"] == {"voice": "zh-CN-YunxiNeural", "rate": "-6%"}
    assert json.loads(prepared["inputs"]["tts"]) == {"backend": "edge-tts", "voice": "zh-CN-YunxiNeural", "rate": "-6%", "source": "project"}


def test_prepare_without_voice_fails_before_synthesis(tmp_path: Path, monkeypatch) -> None:
    root, manifest = _project(tmp_path, _speaking_plan())
    _tone(root / "assets" / "bed.wav", 1)

    with pytest.raises(M2VError, match="尚未选择音色"):
        _prepare_with_capture(root, manifest, monkeypatch)


def test_prepare_rejects_invalid_project_voice(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, _speaking_plan(), {"voice": "xiaoxiao", "rate": "+0%"})
    with pytest.raises(M2VError, match="音色名"):
        adapter.prepare(root, manifest)
