"""按场景缓存 TTS，生成不可变媒体资源，最后原子更新媒体清单。"""
from __future__ import annotations

import json
import logging
import math
import os
import tempfile
import time
import uuid
from pathlib import Path


import m2v.engine.audio as audio
import m2v.core.security as security
import m2v.engine.beats as beat_mod
import m2v.engine.tts as shared_tts
from m2v.core.errors import M2VError
from m2v.types.article.media import MANIFEST_VERSION, fingerprint
from m2v.engine.subtitles import segment_windows, srt
import m2v.engine.sound as sound

logger = logging.getLogger(__name__)
MEDIA_CONTRACT_VERSION = MANIFEST_VERSION


def _standard_duration_check(total_frames: int, fps: int) -> dict:
    seconds = total_frames / fps
    return {"actualDurationInFrames": total_frames, "actualDurationSeconds": seconds,
            "durationStatus": "pass" if 35 * fps <= total_frames <= 45 * fps else "fail",
            "durationLimitSeconds": [35, 45]}


def _actual_speech_stage_frames(duration: float, fps: int) -> int:
    """Round actual speech up to frames and preserve only the fixed reading tail."""
    return math.ceil(duration * fps) + beat_mod.STABLE_READING_FRAMES


def synthesize(text: str, voice: str, rate: str, output: Path):
    return shared_tts.synthesize(text, voice, rate, output)


def _scene_audio(text: str, voice: str, rate: str, cache: Path, force: bool, *,
                 contract_version: int = 3, rhythm: dict | None = None):
    return shared_tts.scene_audio(text, voice, rate, cache, force=force,
                                  contract_version=contract_version, rhythm=rhythm,
                                  synthesizer=synthesize)


def _scene_cache_key(text: str, voice: str, rate: str, contract_version: int) -> str:
    return shared_tts.scene_cache_key(text, voice, rate, contract_version)


def prepare(storyboard_path: str | Path, out_dir: str | Path,
            voice: str | None = None, rate: str | None = None, force: bool = False,
            rhythm: dict | None = None) -> Path:
    """为 v4 分镜准备配音与派生时间轴；旧分镜在这里就被拒绝。"""
    started = time.monotonic()
    voice, rate = voice or shared_tts.DEFAULT_VOICE, rate or shared_tts.DEFAULT_RATE
    source_path, root = Path(storyboard_path), Path(out_dir)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    import m2v.types.article.storyboard_v4 as storyboard_v4
    report = storyboard_v4.validate(source)
    if not report.ok:
        raise M2VError("\n".join(i.format() for i in report.errors))
    if not sound.valid_rate(rate): raise M2VError("语速必须是 −50% 至 +50% 的有符号百分比")
    return _prepare_v4(source_path, root, source, voice, rate, force,
                       sound.sound_assets(source, source_path), started, rhythm)


def _prepare_v4(source_path: Path, root: Path, source: dict, voice: str, rate: str,
                force: bool, assets: dict[str, Path], started: float,
                rhythm: dict | None = None) -> Path:
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
                    text, voice, rate, cache, force, contract_version=MEDIA_CONTRACT_VERSION,
                    rhythm=rhythm,
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
        # `soundtrack` 缺省、显式 null（校验器都接受）都表示没有声音素材，
        # 这里统一收敛成空配置，避免后面按对象取键崩在 None 上。
        track = source.get("soundtrack") or {}
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
                raise M2VError(f"音效起点越出 stage {effect['stageId']}")
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
                    "soundAssets": {ref: {"path": os.path.relpath(path, source_path.parent).replace("\\", "/"),
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

