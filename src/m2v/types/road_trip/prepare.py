"""多日地图游记准备：旁白、字幕、音效、程序化音床与母版。

旁白逐段合成并缓存；失败不写准备记录。时间轴按实测口播长度编译，音效锚点
解析到全局帧后混入母版。准备记录只保存底图路径与摘要，不内嵌任何 data URI。
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import tempfile
from pathlib import Path
from typing import Any

from m2v.core import security
from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint, module_files
from m2v.core.project import save_prepared
from m2v.engine import audio, remotion, tts
from m2v.engine.audio import Effect

from m2v.types.road_trip import ambient, materials, timeline as timeline_module
from m2v.types.road_trip import layout as layout_module

logger = logging.getLogger(__name__)

COMPOSITION_ID = "RoadTrip"
MEDIA_DIR = "outputs/media"
AMBIENT_PATH = "outputs/road-trip/ambient.wav"


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def implementation_digest() -> str:
    from m2v.engine import render_pipeline, subtitles
    from m2v.types.driving_route import geometry
    from m2v.types.driving_route import layout as driving_layout
    from m2v.types.road_trip import adapter, render
    modules = (materials, layout_module, timeline_module, ambient, adapter, render,
               geometry, driving_layout, audio, tts, subtitles, render_pipeline, remotion)
    files = [file for module in modules for file in module_files(module)]
    return fingerprint({path.as_posix(): digest_file(path) for path in files})


def _rhythm(project: dict, option: dict | None) -> dict | None:
    from m2v.engine import rhythm as rhythm_engine
    declared = tts.settings(project).get("speech")
    if not declared and not option:
        return None
    return rhythm_engine.configure({**(declared or {}), **(option or {})})


def _cue_frames(local_cues: list[dict], start_frame: int, frames: int, fps: int) -> list[dict]:
    result = []
    for cue in local_cues:
        start = max(0, min(frames - 1, round(cue["start"] * fps)))
        end = max(start + 1, min(frames, round(cue["end"] * fps)))
        result.append({"startFrame": start_frame + start, "endFrame": start_frame + end,
                       "text": cue["text"]})
    return result


def _effect_source(root: Path, effect: dict, work: Path, index: int,
                   library: dict) -> tuple[Path, dict]:
    if "builtin" in effect:
        from m2v.types.general import soundtrack
        name = effect["builtin"]
        if name not in soundtrack.BUILTINS:
            raise M2VError(f"未知内置音效：{name}")
        target = work / f"builtin-{index}.wav"
        soundtrack.synthesize(name, target)
        from m2v.types.general import sound_library
        return target, sound_library.probe(target)
    if "synthesis" in effect:
        from m2v.types.general import sound_synthesis, sound_library
        target = work / f"synthesis-{index}.wav"
        sound_synthesis.synthesize(effect["synthesis"], target)
        return target, sound_library.probe(target)
    if "assetId" in effect:
        identity = effect["assetId"]
        if identity not in library:
            raise M2VError(f"音效引用未知 assetId：{identity}")
        info = library[identity]
        return info["file"], info
    from m2v.types.general import explainer, sound_library
    source = explainer.local_file(root, effect.get("sourceRef"), "effect.sourceRef")
    target = work / f"local-{index}.wav"
    return target, sound_library.decode(source, target)


def _build_effects(root: Path, docs: dict[str, Any], timeline: dict[str, Any],
                   work: Path, fps: int) -> tuple[list[Effect], dict[str, str]]:
    from m2v.types.general import sound_library
    library, library_inputs = sound_library.resolve(root)
    effects: list[Effect] = []
    total = timeline["totalFrames"]
    for index, effect in enumerate(docs["effects"]):
        start = timeline_module.resolve_anchor(effect["anchor"], timeline, docs) + effect.get("offsetMs", 0) / 1000 * fps
        start = max(0, start)
        if start >= total:
            raise M2VError(f"音效 {effect['id']} 起点越界：第 {start} 帧，全片 {total} 帧")
        file, info = _effect_source(root, effect, work, index, library)
        trim = effect.get("trimStartMs", 0) / 1000
        available = info["durationSeconds"] - trim
        if available <= 0:
            raise M2VError(f"音效 {effect['id']} trimStartMs 超出素材范围")
        length = effect.get("durationMs", round(available * 1000)) / 1000
        if not effect.get("loop", False) and length > available + 1 / audio.SAMPLE_RATE:
            raise M2VError(f"音效 {effect['id']} durationMs 超出素材剩余时长；需要重复时声明 loop")
        for field in ("fadeInMs", "fadeOutMs"):
            if effect.get(field, 0) > length * 1000:
                raise M2VError(f"音效 {effect['id']} {field} 超出播放时长")
        effects.append(Effect(file, start / fps, effect.get("gainDb", -18), trim, length,
                              effect.get("loop", False), effect.get("fadeInMs", 0) / 1000,
                              effect.get("fadeOutMs", 0) / 1000, None))
    return effects, library_inputs


def _verify_basemap_coverage(docs: dict[str, Any], timeline: dict[str, Any]) -> None:
    """编译后的逐帧相机只能使用已保存的瓦片；缺块在准备阶段失败。"""
    if docs["basemap"] is None:
        return
    for index, day in enumerate(docs["days"]):
        record = docs["basemap"]["days"][day["id"]]
        follow = record["followTiles"]
        stored = {(tile["x"], tile["y"]) for tile in follow["tiles"]}
        timing = timeline["days"][index]
        missing: set[tuple[int, int]] = set()
        for local_frame in range(timing["durationInFrames"]):
            missing |= layout_module.visible_tiles_for_frame(
                docs["routes"][day["id"]], day["id"], index, local_frame,
                timing["durationInFrames"], materials.FPS, follow["zoom"])
        missing -= stored
        if missing:
            x, y = sorted(missing)[0]
            raise M2VError(f"{day['id']} 缺少 {len(missing)} 块相机走廊瓦片（首块 {x}:{y}，"
                           f"z{follow['zoom']}）；请重新运行 m2v road-trip basemap")


def _ambient(root: Path, seed: int = ambient.DEFAULT_SEED) -> tuple[Path, dict]:
    target = root / AMBIENT_PATH
    metadata_path = target.with_suffix(".json")
    if target.is_file() and metadata_path.is_file():
        try:
            stored = json.loads(metadata_path.read_text(encoding="utf-8"))
            if (stored.get("sha256") == digest_file(target)
                    and stored.get("seed") == seed
                    and stored.get("version") == ambient.VERSION
                    and abs(audio.wav_duration(target) - ambient.LOOP_SECONDS) < 1 / audio.SAMPLE_RATE):
                return target, stored
        except (OSError, ValueError, M2VError):
            logger.warning("音床缓存损坏，重新生成")
    target.parent.mkdir(parents=True, exist_ok=True)
    record = ambient.synthesize(target, seed=seed)
    metadata_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return target, record


def prepare(root: Path, project: dict, *, voice: str | None = None, rate: str | None = None,
            rhythm: dict | None = None) -> dict:
    docs = materials.load_project(root)
    trip = docs["trip"]
    fps = materials.FPS
    texts = [segment["text"] for day in docs["days"] for segment in day["narration"]]
    actual_tts = tts.preparation(project, texts, voice=voice, rate=rate, rhythm=rhythm)
    cache = root / "outputs/audio-cache"
    cache.mkdir(parents=True, exist_ok=True)

    measured: dict[str, list[float]] = {}
    speech: dict[str, list[tuple[Path | None, int, list[dict]]]] = {}
    hits = 0
    total_chars = 0
    for day in docs["days"]:
        seconds: list[float] = []
        entries = []
        for segment in day["narration"]:
            wav, cues, _words, length, hit = tts.scene_audio(
                segment["text"], actual_tts["voice"], actual_tts["rate"], cache,
                contract_version=1)
            if not math.isfinite(length) or length <= 0:
                raise M2VError(f"旁白 {segment['id']} 音频时长无效")
            seconds.append(length)
            entries.append((wav, max(1, math.ceil(length * fps)), cues))
            total_chars += len(segment["text"])
            hits += int(hit)
        measured[day["id"]] = seconds
        speech[day["id"]] = entries

    timeline = timeline_module.allocate(docs, measured)
    _verify_basemap_coverage(docs, timeline)
    cues: list[dict] = []
    # 字幕必须按段顺序取对应的本地 cue，不能把同一天所有 cue 塞进每个窗口。
    for position, day in enumerate(timeline["days"]):
        source_day = docs["days"][position]
        entries = speech[day["dayId"]]
        for segment, (wav, frames, local_cues) in zip(source_day["narration"], entries):
            window = day["segmentWindows"][segment["id"]]
            start = window["startFrame"]
            cues.extend(_cue_frames(local_cues, start, frames, fps))

    windows = timeline["segmentWindows"]
    props = materials.build_render_props(docs, timeline, cues, windows)

    parts: list[tuple[Path | None, int]] = []
    cursor = 0
    for position, day in enumerate(timeline["days"]):
        day_cursor = 0
        entries = speech[day["dayId"]]
        for index, segment in enumerate(docs["days"][position]["narration"]):
            window = day["segmentWindows"][segment["id"]]
            start = window["startFrame"] - day["startFrame"]
            if start < day_cursor:
                raise M2VError(f"{day['dayId']} 的旁白段重叠：{segment['id']}")
            if start > day_cursor:
                parts.append((None, start - day_cursor))
                day_cursor = start
            wav, frames, _cues = entries[index]
            parts.append((wav, frames))
            day_cursor += frames
        tail = day["durationInFrames"] - day_cursor
        if tail < 0:
            raise M2VError(f"{day['dayId']} 的音频超出当天时间轴；拒绝截断口播")
        if tail:
            parts.append((None, tail))
            day_cursor += tail
        cursor += day_cursor
    if cursor != timeline["totalFrames"]:
        raise M2VError(f"音轨帧数 {cursor} 与全片 {timeline['totalFrames']} 不一致")

    media_dir = root / MEDIA_DIR
    media_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="road-trip-audio-", dir=media_dir) as temporary:
        work = Path(temporary)
        raw = work / "narration.wav"
        audio.concatenate(parts, fps, raw)
        bed, bed_record = _ambient(root)
        effects, library_inputs = _build_effects(root, docs, timeline, work, fps)
        music = (bed, {"loop": True, "gainDb": -27, "fadeInMs": 1200, "fadeOutMs": 1600})
        cue_seconds = [{"start": cue["startFrame"] / fps, "end": cue["endFrame"] / fps}
                       for cue in cues]
        mixed = work / "mixed.wav"
        audio.mix(raw, mixed, timeline["totalFrames"] / fps, cue_seconds, music, effects, work,
                  fps=fps)
        mastered = work / "mastered.wav"
        audio.master(mixed, mastered, integrated=-14.0, true_peak=-1.2)
        sha = digest_file(mastered)
        master = media_dir / f"{sha}.wav"
        security.deliver(mastered, master)

    inputs: dict[str, str] = {
        "trip": digest_file(root / materials.MATERIALS["trip"]),
        "tts": json.dumps(actual_tts, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        "implementation": implementation_digest(),
        "productionContract": "road-trip-v1",
        "frame": f"{materials.WIDTH}x{materials.HEIGHT}",
        "subtitle": json.dumps(props["subtitle"], ensure_ascii=False, sort_keys=True,
                              separators=(",", ":")),
        "ambient": json.dumps(bed_record, ensure_ascii=False, sort_keys=True,
                              separators=(",", ":")),
        "file:" + master.relative_to(root).as_posix(): sha,
        "file:" + bed.relative_to(root).as_posix(): digest_file(bed),
    }
    for day in docs["days"]:
        route = root / day["route"]
        inputs["file:" + day["route"]] = digest_file(route)
    if docs["basemap"] is not None:
        inputs["file:" + materials.BASEMAP_INDEX] = digest_file(root / materials.BASEMAP_INDEX)
        for day in docs["days"]:
            manifest = docs["basemap"]["days"][day["id"]]["followTiles"]["manifest"]
            inputs["file:" + manifest] = digest_file(root / manifest)
    inputs.update(library_inputs)
    inputs["renderer"] = remotion.build_input_fingerprint(workspace_root=root.parent)["digest"]

    prepared = save_prepared(
        root, project=project, composition_id=COMPOSITION_ID, props=props,
        width=materials.WIDTH, height=materials.HEIGHT, fps=fps,
        duration_in_frames=timeline["totalFrames"], inputs=inputs,
        subtitles=cues,
        audio={"segments": [{"sceneId": "master", "path": master.relative_to(root).as_posix(),
                             "startFrame": 0, "durationInFrames": timeline["totalFrames"],
                             "sha256": sha}], "cacheHits": hits},
    )
    size = (root / "outputs/prepared.json").stat().st_size
    if size > 80 * 1024 * 1024:
        raise M2VError(f"准备记录 {size / 1024 / 1024:.1f} MB，超过 80 MB；"
                       "请检查是否误把瓦片内嵌进 props")
    if size > 50 * 1024 * 1024:
        logger.warning("准备记录 %.1f MB，超过 50 MB 预算", size / 1024 / 1024)
    logger.info("多日地图游记准备：%d 天，%d 帧，旁白 %d 字，TTS 缓存命中 %d",
                len(docs["days"]), timeline["totalFrames"], total_chars, hits)
    return prepared
