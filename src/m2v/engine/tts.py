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
    unknown = set(declared) - {"backend", "voice", "rate", "speech"}
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
    if "speech" in declared:
        from m2v.engine import rhythm as rhythm_engine
        result["speech"] = rhythm_engine.configure(declared["speech"])
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
                contract_version: int = 3, rhythm: dict | None = None,
                synthesizer: Callable = synthesize) -> tuple[Path, list[dict], list[dict], float, bool]:
    """Return cached WAV, subtitle cues, word boundaries, duration, and cache hit.

    `rhythm` 为真时对停顿做整形。缓存里始终保存**未整形**的原始合成，
    所以整形开关与参数不改变缓存键，也不会让已有缓存失效。
    """
    key = scene_cache_key(text, voice, rate, contract_version)
    wav, metadata = cache / f"{key}.wav", cache / f"{key}.json"
    if not force and wav.is_file() and metadata.is_file():
        try:
            duration = audio.wav_duration(wav)
            stored = json.loads(metadata.read_text(encoding="utf-8"))
            if stored["sha256"] != hashlib.sha256(wav.read_bytes()).hexdigest():
                raise M2VError("缓存音频校验和不匹配")
            shaped, words, duration = _shape(text, wav, stored["words"], duration, rhythm, cache, key)
            cues = cues_from_words(text, words, duration)
            logger.info("配音缓存命中 %s", key[:12])
            return shaped, cues, words, duration, True
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
        digest = hashlib.sha256((work / "speech.wav").read_bytes()).hexdigest()
        (work / "words.json").write_text(json.dumps({"words": words, "sha256": digest}, ensure_ascii=False), encoding="utf-8")
        (work / "speech.wav").replace(wav)
        (work / "words.json").replace(metadata)
        grant_inherited_access(wav)
        grant_inherited_access(metadata)
    shaped, words, duration = _shape(text, wav, words, duration, rhythm, cache, key)
    cues = cues_from_words(text, words, duration)
    return shaped, cues, words, duration, False


def _shape(text: str, wav: Path, words: list[dict], duration: float, rhythm: dict | None,
           cache: Path, key: str) -> tuple[Path, list[dict], float]:
    """按韵律声明整形停顿。未声明时原样返回，不做任何多余读写。"""
    if not rhythm:
        return wav, words, duration
    import m2v.engine.rhythm as rhythm_engine

    target = cache / f"{key}.rhythm-{hashlib.sha256(rhythm_engine.fingerprint_of(rhythm).encode()).hexdigest()[:16]}.wav"
    # 同一作品重复准备时直接复用整形结果：缓存保存的是原始合成，整形是派生物。
    if target.is_file() and target.stat().st_size > 44:
        try:
            stored = json.loads(target.with_suffix(".json").read_text(encoding="utf-8"))
            if (stored["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
                    and stored["rhythm"] == rhythm):
                return target, stored["words"], audio.wav_duration(target)
        except (OSError, ValueError, KeyError, TypeError):
            logger.warning("韵律缓存损坏，重新整形 %s", key[:12])
    sample_rate, samples = rhythm_engine.read_samples(wav)
    pauses = rhythm_engine.plan(text, words, sample_rate, samples, rhythm)
    shaped, shifts = rhythm_engine.reshape(samples, sample_rate, pauses, rhythm)
    rhythm_engine.write_samples(target, sample_rate, shaped)
    shaped_duration = audio.wav_duration(target)
    # 词边界与音频同源重映射，字幕与时间轴因此自动跟随，不需要第二处补丁。
    # 缩短停顿会把后文前移，末词可能压到音频末尾；按原顺序保持单调再夹到音频内。
    moments = rhythm_engine.remap_all(
        [value for word in words for value in (float(word["start"]), float(word["end"]))],
        shifts, shaped_duration)
    moved = [{**word, "start": moments[2 * index], "end": moments[2 * index + 1]}
             for index, word in enumerate(words)]
    grant_inherited_access(target)
    (target.with_suffix(".json")).write_text(json.dumps(
        {"words": moved, "rhythm": rhythm,
         "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}, ensure_ascii=False), encoding="utf-8")
    return target, moved, shaped_duration
