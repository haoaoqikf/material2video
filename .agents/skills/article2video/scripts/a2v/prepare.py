"""按场景缓存 TTS，生成不可变媒体资源，最后原子更新媒体清单。"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import tempfile
import time
import uuid
from importlib.metadata import version
from pathlib import Path

import edge_tts

from . import audio, security, storyboard as sb
from . import beats as beat_mod
from .errors import A2VError
from .media import MANIFEST_VERSION, fingerprint
from .subtitles import cues_from_words, segment_windows, srt

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


def _scene_audio(text: str, voice: str, rate: str, cache: Path, force: bool) -> tuple[Path, list[dict], list[dict], float, bool]:
    """一幕的配音、字幕 cue 与**原始词边界**；后两者都从同一份缓存推导。"""
    key = fingerprint({"text": text, "voice": voice, "rate": rate,
                       "generator": GENERATOR_VERSION, "edgeTts": version("edge-tts")})
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
    with tempfile.TemporaryDirectory(dir=cache) as temp:
        root = Path(temp)
        for attempt in range(3):
            try:
                words = asyncio.run(synthesize(text, voice, rate, root / "speech.mp3"))
                break
            except (ValueError, TypeError) as exc:
                raise A2VError(f"配音参数错误: {exc}") from exc
            except Exception as exc:
                if attempt == 2:
                    raise A2VError(f"配音请求失败（共 3 次）: {exc}") from exc
                logger.warning("配音请求失败，重试 %d/2: %s", attempt + 1, exc)
                time.sleep(attempt + 1)
        duration = audio.decode(root / "speech.mp3", root / "speech.wav")
        cues = cues_from_words(text, words, duration)
        (root / "words.json").write_text(json.dumps({"words": words,
            "sha256": hashlib.sha256((root / "speech.wav").read_bytes()).hexdigest()}, ensure_ascii=False), encoding="utf-8")
        (root / "speech.wav").replace(wav)
        (root / "words.json").replace(metadata)
        # 经临时目录转手的文件会带上「关闭继承」的 ACL，交回父目录的继承规则
        security.grant_inherited_access(wav)
        security.grant_inherited_access(metadata)
    return wav, cues, words, duration, False


def _resolved_beats(item: dict, words: list[dict], duration: float, fps: int, frames: int) -> list[dict]:
    """一幕的 ``resolvedBeats``：分段口播才有，字符串口播返回空表。

    真实词边界是唯一真源：先把每段解析成秒区间，再按 fps 向外取整成场景内
    帧区间。字幕、配音与画面共用这批边界，因此三者不可能各自漂移。
    """
    segments = item.get("narrationSegments")
    if not isinstance(segments, list) or not segments:
        return []
    text = beat_mod.scene_narration(item)
    windows = segment_windows(text, [str(segment.get("text", "")) for segment in segments], words, duration)
    timeline = beat_mod.resolve_from_windows(item, windows, fps, frames)
    return timeline.to_json()


def prepare(storyboard_path: str | Path, out_dir: str | Path,
            voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+0%", force: bool = False) -> Path:
    started = time.monotonic()
    source_path, root = Path(storyboard_path), Path(out_dir)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    report = sb.validate(source)
    if not report.ok:
        raise A2VError("\n".join(i.format() for i in report.errors))
    cache = root / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    scenes, parts, cues = [], [], []
    cursor, hits = 0, 0
    for item in source["scenes"]:
        text = beat_mod.scene_narration(item).strip()
        frames, path, local_cues, words, duration = item["durationInFrames"], None, [], [], 0.0
        if text:
            logger.info("准备场景配音 %s", item["id"])
            path, local_cues, words, duration, hit = _scene_audio(text, voice, rate, cache, force)
            hits += int(hit)
            frames = max(frames, math.ceil((duration + 0.3) * source["fps"]))
        offset = cursor / source["fps"]
        cues.extend({"start": c["start"] + offset, "end": c["end"] + offset, "text": c["text"]} for c in local_cues)
        scenes.append({"id": item["id"], "durationInFrames": frames,
                       "audio": path.relative_to(root).as_posix() if path else None,
                       "resolvedBeats": _resolved_beats(item, words, duration, source["fps"], frames)})
        parts.append((path, frames))
        cursor += frames
    # 每次准备写入新资源名，只有清单切换时新版本才对读者可见。
    generation = uuid.uuid4().hex
    with tempfile.TemporaryDirectory(dir=root) as temp:
        work = Path(temp)
        audio.concatenate(parts, source["fps"], work / "audio.wav")
        (work / "subtitles.srt").write_text(srt(cues), encoding="utf-8")
        manifest = {"version": MANIFEST_VERSION, "source": source, "sourceFingerprint": fingerprint(source),
                    "voice": voice, "rate": rate, "scenes": scenes, "cues": cues,
                    "audio": f"{generation}.wav", "subtitles": f"{generation}.srt"}
        (work / "media.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (work / "audio.wav").replace(root / manifest["audio"])
        (work / "subtitles.srt").replace(root / manifest["subtitles"])
        (work / "media.json").replace(root / "media.json")
    for name in (manifest["audio"], manifest["subtitles"], "media.json"):
        security.grant_inherited_access(root / name)
    logger.info("配音准备完成：%d 幕，缓存命中 %d，%.2fs，耗时 %.1fs", len(scenes), hits,
                cursor / source["fps"], time.monotonic() - started)
    return root / "media.json"
