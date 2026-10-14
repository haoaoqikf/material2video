"""Shared deterministic speech synthesis and cache for video types."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import tempfile
import time
from importlib.metadata import version
from pathlib import Path
from collections.abc import Callable

import edge_tts

from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from m2v.core.security import grant_inherited_access
from m2v.engine import audio
from m2v.engine.subtitles import cues_from_words

logger = logging.getLogger(__name__)
GENERATOR_VERSION = 1

#: 当前唯一的合成后端。后端抽象首先用来让作品能声明音色与语速，
#: 而不是让每个调用点各写一份默认值。
DEFAULT_BACKEND = "edge-tts"
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_RATE = "+0%"
BACKENDS = (DEFAULT_BACKEND,)
_VOICE = re.compile(r"^[A-Za-z]{2,3}-[A-Za-z]{2,4}-[A-Za-z0-9]{2,40}Neural$")
_RATE = re.compile(r"^[+-]\d{1,2}%$")


def settings(project: dict) -> dict:
    """读取并校验作品级 TTS 配置。

    未声明 `tts` 时返回空配置，调用点必须继续使用原有的默认音色与语速——
    这样既有作品的准备记录与缓存键不会因为新增字段而变化。
    """
    declared = project.get("tts")
    if declared is None:
        return {}
    if not isinstance(declared, dict):
        raise M2VError("project.json 的 tts 必须是对象")
    unknown = set(declared) - {"backend", "voice", "rate"}
    if unknown:
        raise M2VError(f"tts 存在未知字段：{'、'.join(sorted(unknown))}")
    result = {}
    backend = declared.get("backend", DEFAULT_BACKEND)
    if backend not in BACKENDS:
        raise M2VError(f"不支持的 TTS 后端：{backend!r}；当前可用：{'、'.join(BACKENDS)}")
    result["backend"] = backend
    if "voice" in declared:
        voice = declared["voice"]
        if not isinstance(voice, str) or not _VOICE.fullmatch(voice):
            raise M2VError(f"tts.voice 必须是形如 zh-CN-XiaoxiaoNeural 的音色名，实际为 {voice!r}")
        result["voice"] = voice
    if "rate" in declared:
        rate = declared["rate"]
        if not isinstance(rate, str) or not _RATE.fullmatch(rate) or not -50 <= int(rate[:-1]) <= 50:
            raise M2VError("tts.rate 必须是 −50% 至 +50% 的有符号百分比")
        result["rate"] = rate
    return result


async def list_voices() -> dict[str, list[dict]]:
    """按区域列出可用音色；仅用于诊断与校验，不参与渲染。"""
    voices = await edge_tts.list_voices()
    grouped: dict[str, list[dict]] = {}
    for voice in voices:
        grouped.setdefault(voice.get("Locale", "unknown"), []).append(voice)
    return grouped


def resolve(project: dict, *, voice: str | None = None, rate: str | None = None) -> tuple[str, str]:
    """按「命令行 > 作品配置 > 默认值」解析实际使用的音色与语速。"""
    configured = settings(project)
    return (voice or configured.get("voice") or DEFAULT_VOICE,
            rate or configured.get("rate") or DEFAULT_RATE)


async def synthesize(text: str, voice: str, rate: str, output: Path) -> list[dict]:
    words = []
    request = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary",
                                   connect_timeout=10, receive_timeout=30)
    with output.open("wb") as stream:
        async with asyncio.timeout(90):
            async for event in request.stream():
                if event["type"] == "audio":
                    stream.write(event["data"])
                elif event["type"] == "WordBoundary":
                    words.append({"text": event["text"], "start": event["offset"] / 10_000_000,
                                  "end": (event["offset"] + event["duration"]) / 10_000_000})
    return words


def scene_cache_key(text: str, voice: str, rate: str, contract_version: int) -> str:
    return fingerprint({"text": text, "voice": voice, "rate": rate,
                       "contractVersion": contract_version, "generator": GENERATOR_VERSION,
                       "edgeTts": version("edge-tts")})


def scene_audio(text: str, voice: str, rate: str, cache: Path, *, force: bool = False,
                contract_version: int = 3,
                synthesizer: Callable = synthesize) -> tuple[Path, list[dict], list[dict], float, bool]:
    """Return cached WAV, subtitle cues, word boundaries, duration, and cache hit."""
    key = scene_cache_key(text, voice, rate, contract_version)
    wav, metadata = cache / f"{key}.wav", cache / f"{key}.json"
    if not force and wav.is_file() and metadata.is_file():
        try:
            duration = audio.wav_duration(wav)
            stored = json.loads(metadata.read_text(encoding="utf-8"))
            if stored["sha256"] != hashlib.sha256(wav.read_bytes()).hexdigest():
                raise M2VError("缓存音频校验和不匹配")
            cues = cues_from_words(text, stored["words"], duration)
            logger.info("配音缓存命中 %s", key[:12])
            return wav, cues, stored["words"], duration, True
        except (M2VError, ValueError, KeyError, TypeError):
            logger.warning("配音缓存损坏，重新生成 %s", key[:12])
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        work = Path(temporary)
        for attempt in range(3):
            try:
                words = asyncio.run(synthesizer(text, voice, rate, work / "speech.mp3"))
                break
            except (ValueError, TypeError) as exc:
                raise M2VError(f"配音参数错误: {exc}") from exc
            except Exception as exc:
                if attempt == 2:
                    raise M2VError(f"配音请求失败（共 3 次）: {exc}") from exc
                logger.warning("配音请求失败，重试 %d/2: %s", attempt + 1, exc)
                time.sleep(attempt + 1)
        duration = audio.decode(work / "speech.mp3", work / "speech.wav")
        cues = cues_from_words(text, words, duration)
        digest = hashlib.sha256((work / "speech.wav").read_bytes()).hexdigest()
        (work / "words.json").write_text(json.dumps({"words": words, "sha256": digest}, ensure_ascii=False), encoding="utf-8")
        (work / "speech.wav").replace(wav)
        (work / "words.json").replace(metadata)
        grant_inherited_access(wav)
        grant_inherited_access(metadata)
    return wav, cues, words, duration, False
