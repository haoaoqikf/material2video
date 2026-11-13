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
from m2v.core import security
from m2v.engine import audio
from m2v.engine.subtitles import cues_from_words

logger = logging.getLogger(__name__)
GENERATOR_VERSION = 1

#: 合成后端是作品属性；默认仍是联网的 edge-tts。
DEFAULT_BACKEND = "edge-tts"
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_RATE = "+0%"
BACKENDS = (DEFAULT_BACKEND, "kokoro", "qwen3-tts")
_VOICE = {
    "edge-tts": re.compile(r"^[A-Za-z]{2,3}-[A-Za-z]{2,4}-[A-Za-z0-9]{2,40}Neural$"),
    #: Kokoro v1.1-zh 的中国音色；zf 女声、zm 男声。
    "kokoro": re.compile(r"^z[fm]_\d{3}$"),
    #: Qwen3-TTS 的作品内克隆音色档案；参考音频与文本登记在 models/qwen3-tts。
    "qwen3-tts": re.compile(r"^clone_[a-z0-9][a-z0-9-]*$"),
}
_RATE = re.compile(r"^[+-]\d{1,2}%$")


def voice_pattern(backend: str) -> re.Pattern:
    try:
        return _VOICE[backend]
    except KeyError as exc:
        raise M2VError(f"不支持的 TTS 后端：{backend!r}；当前可用：{'、'.join(BACKENDS)}") from exc


def _check_voice(voice: str, backend: str) -> None:
    """音色格式由后端决定；两种格式不能互相冒充。"""
    if not isinstance(voice, str) or not voice_pattern(backend).fullmatch(voice):
        example = {"edge-tts": "zh-CN-XiaoxiaoNeural", "kokoro": "zf_027",
                   "qwen3-tts": "clone_tuixiu"}[backend]
        raise M2VError(f"{backend} 的音色名必须形如 {example}，实际为 {voice!r}")


def settings(project: dict) -> dict:
    """读取并校验作品级 TTS 配置。

    配置可以尚未选音；只有准备实际旁白时才要求明确音色。
    """
    declared = project.get("tts")
    if declared is None:
        return {}
    if not isinstance(declared, dict):
        raise M2VError("project.json 的 tts 必须是对象")
    unknown = set(declared) - {"backend", "voice", "rate", "speech", "selection"}
    if unknown:
        raise M2VError(f"tts 存在未知字段：{'、'.join(sorted(unknown))}")
    result = {}
    backend = declared.get("backend", DEFAULT_BACKEND)
    if backend not in BACKENDS:
        raise M2VError(f"不支持的 TTS 后端：{backend!r}；当前可用：{'、'.join(BACKENDS)}")
    result["backend"] = backend
    if "voice" in declared:
        voice = declared["voice"]
        _check_voice(voice, backend)
        result["voice"] = voice
    if "rate" in declared:
        rate = declared["rate"]
        if not isinstance(rate, str) or not _RATE.fullmatch(rate) or not -50 <= int(rate[:-1]) <= 50:
            raise M2VError("tts.rate 必须是 −50% 至 +50% 的有符号百分比")
        result["rate"] = rate
    if "speech" in declared:
        from m2v.engine import rhythm as rhythm_engine
        result["speech"] = rhythm_engine.configure(declared["speech"])
    if "selection" in declared:
        selection = declared["selection"]
        if (not isinstance(selection, dict)
                or set(selection) != {"mode", "rationale", "narrationSha256"}
                or selection.get("mode") != "assistant"
                or not isinstance(selection.get("rationale"), str)
                or not selection["rationale"].strip()
                or not isinstance(selection.get("narrationSha256"), str)
                or not re.fullmatch(r"[a-f0-9]{64}", selection["narrationSha256"])):
            raise M2VError("tts.selection 必须包含 mode=assistant、非空 rationale 和 64 位 narrationSha256")
        if "voice" not in result:
            raise M2VError("tts.selection 必须同时声明 tts.voice")
        result["selection"] = dict(selection)
    return result


async def list_voices() -> dict[str, list[dict]]:
    """按区域列出可用音色；仅用于诊断与校验，不参与渲染。"""
    voices = await edge_tts.list_voices()
    grouped: dict[str, list[dict]] = {}
    for voice in voices:
        grouped.setdefault(voice.get("Locale", "unknown"), []).append(voice)
    return grouped


def resolve(project: dict, *, voice: str | None = None, rate: str | None = None,
            backend: str | None = None) -> tuple[str, str]:
    """音色必须显式选择；语速独立按命令行、作品、默认值解析。"""
    configured = settings(project)
    actual_backend = backend or configured.get("backend", DEFAULT_BACKEND)
    actual_voice = voice if voice is not None else configured.get("voice")
    actual_rate = rate if rate is not None else configured.get("rate", DEFAULT_RATE)
    if actual_voice is None:
        raise M2VError("尚未选择音色：请由制作助手运行 m2v voices --json 后写入 project.json 的 tts.voice，或 prepare --voice <音色名>")
    # 命令行也使用相同格式校验，不能绕过作品字段契约。
    settings({"tts": {"backend": actual_backend, "voice": actual_voice, "rate": actual_rate}})
    return actual_voice, actual_rate


def narration_digest(texts: list[str]) -> str:
    """完整有序的自身旁白摘要；分段边界有意义，画面摘要不参与。"""
    encoded = json.dumps([text for text in texts if text.strip()], ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def preparation(project: dict, texts: list[str], *, voice: str | None = None,
                rate: str | None = None, rhythm: dict | None = None,
                backend: str | None = None) -> dict:
    """生成实际 TTS 记录；无旁白时不要求选音。"""
    configured = settings(project)
    if not any(text.strip() for text in texts):
        return {}
    actual_backend = backend or configured.get("backend", DEFAULT_BACKEND)
    actual_voice, actual_rate = resolve(project, voice=voice, rate=rate, backend=actual_backend)
    selection = configured.get("selection") if voice is None else None
    if selection and selection["narrationSha256"] != narration_digest(texts):
        raise M2VError("音色选择已过期：完整旁白已改变，请制作助手重新判断并更新 tts.selection，或用 --voice 手动指定")
    record = {"backend": actual_backend, "voice": actual_voice, "rate": actual_rate,
              "source": "command-line" if (voice is not None or backend is not None)
              else "assistant" if selection else "project"}
    if selection:
        record["selection"] = selection
    if rhythm:
        record["speech"] = rhythm
    logger.info("配音选择：%s（%s），语速 %s，来源 %s", actual_voice, actual_backend, actual_rate, record["source"])
    return record


def ensure_backend(record: dict, root: Path) -> None:
    """有本地模型的后端在合成前一次性校验，缺失时不逐段重试。"""
    backend = record.get("backend", DEFAULT_BACKEND)
    if backend == "kokoro":
        from m2v.engine import kokoro_tts
        kokoro_tts.ensure_assets(root / "models", record["voice"])
    elif backend == "qwen3-tts":
        from m2v.engine import qwen3_tts
        qwen3_tts.ensure_assets(root / "models", record["voice"])


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


def scene_cache_key(text: str, voice: str, rate: str, contract_version: int,
                    backend: str = DEFAULT_BACKEND, models_dir: Path | None = None) -> str:
    payload = {"text": text, "voice": voice, "rate": rate,
               "contractVersion": contract_version, "generator": GENERATOR_VERSION}
    if backend == DEFAULT_BACKEND:
        # 保持既有 edge 缓存键不变；新增后端不借机让旧作品重新合成。
        payload["edgeTts"] = version("edge-tts")
    elif backend == "kokoro":
        from m2v.engine import kokoro_tts
        payload["backend"] = backend
        payload.update(kokoro_tts.versions())
    elif backend == "qwen3-tts":
        from m2v.engine import qwen3_tts
        if models_dir is None:
            raise M2VError("Qwen3-TTS 缓存键需要作品模型目录")
        payload["backend"] = backend
        payload.update(qwen3_tts.versions())
        payload["voiceProfile"] = qwen3_tts.voice_digest(models_dir, voice)
    else:
        raise M2VError(f"不支持的 TTS 后端：{backend!r}；当前可用：{'、'.join(BACKENDS)}")
    return fingerprint(payload)


def scene_audio(text: str, voice: str, rate: str, cache: Path, *, force: bool = False,
                contract_version: int = 3, rhythm: dict | None = None,
                synthesizer: Callable = synthesize, backend: str = DEFAULT_BACKEND,
                models_dir: Path | None = None) -> tuple[Path, list[dict], list[dict], float, bool]:
    """Return cached WAV, subtitle cues, word boundaries, duration, and cache hit.

    `rhythm` 为真时对停顿做整形。缓存里始终保存**未整形**的原始合成，
    所以整形开关与参数不改变缓存键，也不会让已有缓存失效。
    """
    key = scene_cache_key(text, voice, rate, contract_version, backend, models_dir)
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
    if backend in {"kokoro", "qwen3-tts"} and models_dir is None:
        raise M2VError(f"{backend} 后端需要作品模型目录，准备流程未提供 models/")
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        work = Path(temporary)
        attempts = 3 if backend == DEFAULT_BACKEND else 1
        for attempt in range(attempts):
            try:
                if backend == "kokoro":
                    from m2v.engine import kokoro_tts
                    words = kokoro_tts.synthesize(text, voice, rate, work / "speech.wav",
                                                  models_dir=models_dir)
                    duration = audio.wav_duration(work / "speech.wav")
                    speech = work / "speech.wav"
                elif backend == "qwen3-tts":
                    from m2v.engine import qwen3_tts
                    words = qwen3_tts.synthesize(text, voice, rate, work / "speech.wav",
                                                 models_dir=models_dir)
                    duration = audio.wav_duration(work / "speech.wav")
                    speech = work / "speech.wav"
                else:
                    words = asyncio.run(synthesizer(text, voice, rate, work / "speech.mp3"))
                    duration = audio.decode(work / "speech.mp3", work / "speech.wav")
                    speech = work / "speech.wav"
                break
            except (ValueError, TypeError) as exc:
                raise M2VError(f"配音参数错误: {exc}") from exc
            except Exception as exc:
                if attempt == attempts - 1:
                    raise M2VError(f"配音请求失败: {exc}") from exc
                logger.warning("配音请求失败，重试 %d/%d: %s", attempt + 1, attempts - 1, exc)
                time.sleep(attempt + 1)
        digest = hashlib.sha256(speech.read_bytes()).hexdigest()
        (work / "words.json").write_text(json.dumps({"words": words, "sha256": digest}, ensure_ascii=False), encoding="utf-8")
        security.deliver(speech, wav)
        security.deliver(work / "words.json", metadata)
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
    security.grant_inherited_access(target)
    (target.with_suffix(".json")).write_text(json.dumps(
        {"words": moved, "rhythm": rhythm,
         "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}, ensure_ascii=False), encoding="utf-8")
    return target, moved, shaped_duration
