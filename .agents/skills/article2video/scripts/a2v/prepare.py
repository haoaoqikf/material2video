"""按场景缓存 TTS，生成不可变媒体资源，最后原子更新媒体清单。"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import shutil
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
from . import sound

logger = logging.getLogger(__name__)
GENERATOR_VERSION = 1
MEDIA_CONTRACT_VERSION = 4


def _standard_duration_check(total_frames: int, fps: int) -> dict:
    seconds = total_frames / fps
    return {"actualDurationInFrames": total_frames, "actualDurationSeconds": seconds,
            "durationStatus": "pass" if 35 * fps <= total_frames <= 45 * fps else "fail",
            "durationLimitSeconds": [35, 45]}


def _actual_speech_stage_frames(duration: float, fps: int) -> int:
    """Round actual speech up to frames and preserve only the fixed reading tail."""
    return math.ceil(duration * fps) + beat_mod.STABLE_READING_FRAMES


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


def _scene_audio(text: str, voice: str, rate: str, cache: Path, force: bool, *, contract_version: int = 3) -> tuple[Path, list[dict], list[dict], float, bool]:
    """一幕的配音、字幕 cue 与**原始词边界**；后两者都从同一份缓存推导。"""
    key = _scene_cache_key(text, voice, rate, contract_version)
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


def _scene_cache_key(text: str, voice: str, rate: str, contract_version: int) -> str:
    """Keep cached speech isolated across media contract generations."""
    return fingerprint({"text": text, "voice": voice, "rate": rate,
                       "contractVersion": contract_version, "generator": GENERATOR_VERSION,
                       "edgeTts": version("edge-tts")})


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


def _segmented_audio(item: dict, voice: str, rate: str, cache: Path, force: bool, work: Path):
    parts, cues, words, windows = [], [], [], []
    cursor, hits = 0, 0
    for segment in item["narrationSegments"]:
        settings = segment.get("speech", {})
        before = settings.get("pauseBeforeMs", 0) * audio.SAMPLE_RATE // 1000
        after = settings.get("pauseAfterMs", 0) * audio.SAMPLE_RATE // 1000
        start = cursor / audio.SAMPLE_RATE
        parts.append((None, before)); cursor += before
        path, local_cues, local_words, duration, hit = _scene_audio(segment["text"], voice, settings.get("rate", rate), cache, force)
        hits += int(hit); offset = cursor / audio.SAMPLE_RATE
        samples = round(duration * audio.SAMPLE_RATE)
        parts.extend([(path, samples), (None, after)])
        cues.extend({**cue, "start": cue["start"] + offset, "end": cue["end"] + offset} for cue in local_cues)
        words.extend({**word, "start": word["start"] + offset, "end": word["end"] + offset} for word in local_words)
        cursor += samples + after
        windows.append((start, cursor / audio.SAMPLE_RATE))
    target = work / (item["id"] + ".wav")
    audio.concatenate_samples(parts, target)
    return target, cues, words, cursor / audio.SAMPLE_RATE, hits, windows


def prepare(storyboard_path: str | Path, out_dir: str | Path,
            voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+0%", force: bool = False) -> Path:
    started = time.monotonic()
    source_path, root = Path(storyboard_path), Path(out_dir)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source.get("version") == 4:
        from . import storyboard_v4
        report = storyboard_v4.validate(source)
        if not report.ok:
            raise A2VError("\n".join(i.format() for i in report.errors))
        if not sound.valid_rate(rate): raise A2VError("语速必须是 −50% 至 +50% 的有符号百分比")
        return _prepare_v4(source_path, root, source, voice, rate, force, sound.sound_assets(source, source_path), started)
    report = sb.validate(source)
    if not report.ok:
        raise A2VError("\n".join(i.format() for i in report.errors))
    if not sound.valid_rate(rate): raise A2VError("语速必须是 −50% 至 +50% 的有符号百分比")
    assets = sound.sound_assets(source, source_path)
    cache = root / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    # 段级拼接文件必须存活到全片合成；异常清理和旧清单保护由外层临时目录承担。
    with tempfile.TemporaryDirectory(dir=root) as segmented_temp:
        return _prepare_validated(source_path, root, source, voice, rate, force, assets, Path(segmented_temp), started)


def _prepare_v4(source_path: Path, root: Path, source: dict, voice: str, rate: str,
                force: bool, assets: dict[str, Path], started: float) -> Path:
    """Prepare per-stage audio, then resolve all beats on one accumulated frame axis."""
    cache = root / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    stages, cues, parts = [], [], []
    resolved_beats, cursor, hits = [], 0, 0
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        work = Path(temporary)
        for stage in source["stages"]:
            text = "".join(segment["text"] for segment in stage.get("narrationSegments", [])).strip()
            path = None
            local_cues: list[dict] = []
            local_words: list[dict] = []
            duration = 0.0
            frames = stage["durationInFrames"]
            if text:
                path, local_cues, local_words, duration, hit = _scene_audio(
                    text, voice, rate, cache, force, contract_version=MEDIA_CONTRACT_VERSION
                )
                hits += int(hit)
                # Use speech-derived time plus the fixed reading tail. Keeping a longer
                # declared stage here could silently pad short narration to 35 seconds.
                frames = _actual_speech_stage_frames(duration, source["fps"])
                segments = [segment["text"] for segment in stage["narrationSegments"]]
                windows = segment_windows(text, segments, local_words, duration)
                local = beat_mod.resolve_from_windows(stage, windows, source["fps"], frames).to_json()
                resolved_beats.extend({**beat, "stageId": stage["id"],
                                       "startFrame": beat["startFrame"] + cursor,
                                       "endFrame": beat["endFrame"] + cursor} for beat in local)
            for cue in local_cues:
                cues.append({"start": cue["start"] + cursor / source["fps"],
                             "end": cue["end"] + cursor / source["fps"], "text": cue["text"]})
            stage_audio = path.relative_to(root).as_posix() if path else None
            stages.append({"id": stage["id"], "durationInFrames": frames, "audio": stage_audio})
            parts.append((path, frames))
            cursor += frames

        duration_check = _standard_duration_check(cursor, source["fps"])
        duration_seconds = duration_check["actualDurationSeconds"]
        status = duration_check["durationStatus"]
        generation = uuid.uuid4().hex
        audio.concatenate(parts, source["fps"], work / "narration.wav")
        track = source.get("soundtrack", {})
        effects = []
        stage_ranges = {}
        stage_cursor = 0
        for item in stages:
            stage_ranges[item["id"]] = (stage_cursor, stage_cursor + item["durationInFrames"])
            stage_cursor += item["durationInFrames"]
        for effect in track.get("effects", []):
            beat = next(item for item in resolved_beats if item["id"] == effect["beatId"] and item["stageId"] == effect["stageId"])
            start = (beat["startFrame"] + effect.get("offsetMs", 0) * source["fps"] / 1000) / source["fps"]
            stage_start, stage_end = stage_ranges[effect["stageId"]]
            if not stage_start / source["fps"] <= start < stage_end / source["fps"]:
                raise A2VError(f"音效起点越出 stage {effect['stageId']}")
            effects.append((assets[effect["sourceRef"]], start, effect.get("gainDb", -12)))
        music = track.get("music")
        audio.mix(work / "narration.wav", work / "audio.wav", duration_seconds, cues,
                  (assets[music["sourceRef"]], music) if music else None, effects, work)
        (work / "subtitles.srt").write_text(srt(cues), encoding="utf-8")
        manifest = {"version": MEDIA_CONTRACT_VERSION, "source": source,
                    "sourceFingerprint": fingerprint(source), "voice": voice, "rate": rate,
                    "stages": stages, "resolvedBeats": resolved_beats, "cues": cues,
                    "audio": f"{generation}.wav", "narration": f"{generation}.narration.wav",
                    "subtitles": f"{generation}.srt",
                    "soundFingerprint": fingerprint(sound.configuration(source)),
                    "soundAssets": {ref: {"path": os.path.relpath(path, root).replace("\\", "/"),
                                           "sha256": sound.asset_digest(path)} for ref, path in assets.items()},
                    "standardCheck": duration_check}
        (work / "audio.wav").replace(root / manifest["audio"])
        (work / "narration.wav").replace(root / manifest["narration"])
        (work / "subtitles.srt").replace(root / manifest["subtitles"])
        (work / "media.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (work / "media.json").replace(root / "media.json")
    for name in (manifest["audio"], manifest["narration"], manifest["subtitles"], "media.json"):
        security.grant_inherited_access(root / name)
    logger.info("v4 配音准备完成：%d stages，缓存命中 %d，%.2fs，时长状态 %s，耗时 %.1fs",
                len(stages), hits, duration_seconds, status, time.monotonic() - started)
    if status != "pass":
        logger.warning("实际时长 %.2f 秒超出 35～45 秒；调整口播措辞、正常语速或有意义的停顿后重新 prepare；不会截断口播或补空白",
                       duration_seconds)
    return root / "media.json"


def _prepare_validated(source_path, root, source, voice, rate, force, assets, segment_work, started):
    cache = root / "cache"
    scenes, parts, cues = [], [], []
    cursor, hits = 0, 0
    for item in source["scenes"]:
        text = beat_mod.scene_narration(item).strip()
        frames, path, local_cues, words, duration = item["durationInFrames"], None, [], [], 0.0
        if text:
            logger.info("准备场景配音 %s", item["id"])
            if any("speech" in segment for segment in item.get("narrationSegments", [])):
                path, local_cues, words, duration, hit, windows = _segmented_audio(item, voice, rate, cache, force, segment_work)
                hits += hit
                frames = max(frames, math.ceil(duration * source["fps"]) + beat_mod.STABLE_READING_FRAMES)
                resolved = beat_mod.resolve_from_windows(item, windows, source["fps"], frames).to_json()
            else:
                path, local_cues, words, duration, hit = _scene_audio(text, voice, rate, cache, force)
                hits += int(hit)
                frames = max(frames, math.ceil((duration + 0.3) * source["fps"]))
                resolved = _resolved_beats(item, words, duration, source["fps"], frames)
        else:
            resolved = []
        offset = cursor / source["fps"]
        cues.extend({"start": c["start"] + offset, "end": c["end"] + offset, "text": c["text"]} for c in local_cues)
        scenes.append({"id": item["id"], "durationInFrames": frames,
                       "audio": path.relative_to(root).as_posix() if path else None,
                       "resolvedBeats": resolved})
        parts.append((path, frames))
        cursor += frames
    # 每次准备写入新资源名，只有清单切换时新版本才对读者可见。
    generation = uuid.uuid4().hex
    with tempfile.TemporaryDirectory(dir=root) as temp:
        work = Path(temp)
        audio.concatenate(parts, source["fps"], work / "narration.wav")
        track = source.get("soundtrack", {})
        music = track.get("music")
        effects = []; scene_cursor = 0
        for scene in scenes:
            for effect in track.get("effects", []):
                if effect["sceneId"] != scene["id"]: continue
                beat = next(b for b in scene["resolvedBeats"] if b["id"] == effect["beatId"])
                start = beat["startFrame"] / source["fps"] + effect.get("offsetMs", 0) / 1000
                if not 0 <= start < scene["durationInFrames"] / source["fps"]:
                    raise A2VError(f"音效起点越出场景 {scene['id']}")
                effects.append((assets[effect["sourceRef"]], scene_cursor / source["fps"] + start, effect.get("gainDb", -12)))
            scene_cursor += scene["durationInFrames"]
        audio.mix(work / "narration.wav", work / "audio.wav", cursor / source["fps"], cues,
                  (assets[music["sourceRef"]], music) if music else None, effects, work)
        (work / "subtitles.srt").write_text(srt(cues), encoding="utf-8")
        manifest = {"version": MANIFEST_VERSION, "source": source, "sourceFingerprint": fingerprint(source),
                    "voice": voice, "rate": rate, "scenes": scenes, "cues": cues,
                    "audio": f"{generation}.wav", "narration": f"{generation}.narration.wav", "subtitles": f"{generation}.srt",
                    "soundFingerprint": fingerprint(sound.configuration(source)),
                    "soundAssets": {ref: {"path": os.path.relpath(path, root).replace('\\', '/'), "sha256": sound.asset_digest(path)} for ref, path in assets.items()}}
        # 按段生成的音频存为版本化资源，不能留下已删除的临时路径。
        for scene, (path, _) in zip(scenes, parts):
            if path and path.parent == segment_work:
                filename = f"{generation}.{scene['id']}.wav"
                shutil.copyfile(path, root / filename)
                scene["audio"] = filename
        (work / "media.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (work / "audio.wav").replace(root / manifest["audio"])
        (work / "narration.wav").replace(root / manifest["narration"])
        (work / "subtitles.srt").replace(root / manifest["subtitles"])
        (work / "media.json").replace(root / "media.json")
    for name in (manifest["audio"], manifest["narration"], manifest["subtitles"], "media.json"):
        security.grant_inherited_access(root / name)
    logger.info("配音准备完成：%d 幕，缓存命中 %d，%.2fs，耗时 %.1fs", len(scenes), hits,
                cursor / source["fps"], time.monotonic() - started)
    return root / "media.json"
