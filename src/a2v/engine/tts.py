"""Shared deterministic speech synthesis and cache for video types."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import tempfile
import time
from importlib.metadata import version
from pathlib import Path
from collections.abc import Callable

import edge_tts

from a2v.core.errors import A2VError
from a2v.core.fingerprints import fingerprint
from a2v.core.security import grant_inherited_access
from a2v.engine import audio
from a2v.engine.subtitles import cues_from_words

logger = logging.getLogger(__name__)
GENERATOR_VERSION = 1


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
                raise A2VError("缓存音频校验和不匹配")
            cues = cues_from_words(text, stored["words"], duration)
            logger.info("配音缓存命中 %s", key[:12])
            return wav, cues, stored["words"], duration, True
        except (A2VError, ValueError, KeyError, TypeError):
            logger.warning("配音缓存损坏，重新生成 %s", key[:12])
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        work = Path(temporary)
        for attempt in range(3):
            try:
                words = asyncio.run(synthesizer(text, voice, rate, work / "speech.mp3"))
                break
            except (ValueError, TypeError) as exc:
                raise A2VError(f"配音参数错误: {exc}") from exc
            except Exception as exc:
                if attempt == 2:
                    raise A2VError(f"配音请求失败（共 3 次）: {exc}") from exc
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
