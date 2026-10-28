"""文章声音契约与程序生成提示音；编排决定由助手保存，渲染不猜测。"""
from __future__ import annotations

from m2v.core.video_config import general_fps

import math
import struct
import wave
from pathlib import Path
from m2v.core.errors import M2VError
from m2v.engine import audio
from m2v.engine.sound import asset_digest
from m2v.core.validate import integer
from . import sound_library, scene_events

BUILTINS = ("ding", "ding-dong", "click", "transition")


def validate(data: dict, root: Path) -> None:
    from m2v.core.validate import number, obj
    from .explainer import local_file
    track = obj(data.get("soundtrack", {}), "soundtrack", {"music", "effects", "envelopes", "silence"})
    scenes = {s["id"]: s for s in data["scenes"]}
    library, _ = sound_library.resolve(root)
    if "music" in track:
        music = obj(track["music"], "soundtrack.music", {"sourceRef", "gainDb", "loop", "fadeInMs", "fadeOutMs"})
        local_file(root, music.get("sourceRef"), "soundtrack.music.sourceRef")
        number(music.get("gainDb", -24), -60, 0, "music.gainDb")
        if type(music.get("loop", False)) is not bool: raise M2VError("music.loop 必须是布尔值")
        for key in ("fadeInMs", "fadeOutMs"):
            if type(music.get(key, 500)) is not int: raise M2VError(f"music.{key} 必须为整数")
            number(music.get(key, 500), 0, 60000, "music." + key)
    effects = track.get("effects", [])
    if not isinstance(effects, list) or len(effects) > 128: raise M2VError("effects 必须为最多 128 项的数组")
    event_tables = {sid: scene_events.validate(scene) for sid, scene in scenes.items()}
    for effect in effects:
        obj(effect, "effect", {"builtin", "sourceRef", "assetId", "sceneId", "segmentId", "eventId", "offsetMs", "offsetFrames", "gainDb",
                               "trimStartMs", "durationMs", "loop", "fadeInMs", "fadeOutMs", "pan"})
        if sum(key in effect for key in ("builtin", "sourceRef", "assetId")) != 1:
            raise M2VError("音效 builtin/sourceRef/assetId 必须三选一（原 builtin/sourceRef 二选一）")
        if "builtin" in effect:
            if effect["builtin"] not in BUILTINS: raise M2VError(f"未知内置音效，可选 {BUILTINS}")
        elif "assetId" in effect:
            if not isinstance(effect["assetId"], str) or effect["assetId"] not in library:
                raise M2VError("音效引用未知 assetId")
        else: local_file(root, effect["sourceRef"], "effect.sourceRef")
        scene = scenes.get(effect.get("sceneId")) if isinstance(effect.get("sceneId"), str) else None
        if scene is None: raise M2VError("音效引用未知 sceneId")
        scene_events.validate_reference(effect, event_tables[scene["id"]])
        if "segmentId" in effect and effect["segmentId"] not in [s["id"] for s in scene.get("narrationSegments", [])]:
            raise M2VError("音效引用未知 segmentId")
        offset = effect.get("offsetMs", 0)
        if type(offset) is not int: raise M2VError("offsetMs 必须为整数")
        number(offset, -60000, 60000, "offsetMs")
        number(effect.get("gainDb", -18), -60, 0, "effect.gainDb")
        if "offsetFrames" in effect:
            integer(effect["offsetFrames"], -36000, 36000, "effect.offsetFrames")
            if "offsetMs" in effect or "segmentId" in effect:
                raise M2VError("offsetFrames 相对幕起点，不可与 offsetMs/segmentId 同时声明")
        for field in ("trimStartMs", "fadeInMs", "fadeOutMs"):
            integer(effect.get(field, 0), 0, 600000, "effect." + field)
        if "durationMs" in effect:
            integer(effect["durationMs"], 1, 600000, "effect.durationMs")
        if type(effect.get("loop", False)) is not bool:
            raise M2VError("effect.loop 必须为布尔值")
        if effect.get("loop") and "durationMs" not in effect:
            raise M2VError("循环音效必须指定 durationMs")
        number(effect.get("pan", 0), -1, 1, "effect.pan")

    envelopes = track.get("envelopes", [])
    if not isinstance(envelopes, list) or len(envelopes) > 2:
        raise M2VError("soundtrack.envelopes 必须为最多 2 项的数组")
    targets = set()
    max_frame = 600 * general_fps({}, data)
    for envelope in envelopes:
        obj(envelope, "soundtrack.envelope", {"track", "curve", "keyframes"})
        target = envelope.get("track")
        if target not in ("music", "effects") or target in targets:
            raise M2VError("每种声音轨只能声明一条包络，track 为 music 或 effects")
        targets.add(target)
        if envelope.get("curve", "linear") not in ("linear", "smooth"):
            raise M2VError("soundtrack.envelope.curve 只能为 linear 或 smooth")
        points = envelope.get("keyframes")
        if not isinstance(points, list) or not 2 <= len(points) <= 256:
            raise M2VError("soundtrack.envelope.keyframes 必须为 2～256 个关键帧")
        previous = -1
        for point in points:
            obj(point, "soundtrack.envelope.keyframe", {"frame", "gainDb"})
            frame = integer(point.get("frame"), 0, max_frame, "soundtrack.envelope.frame")
            if frame <= previous:
                raise M2VError("soundtrack.envelope 关键帧必须按帧严格递增")
            previous = frame
            number(point.get("gainDb"), -60, 0, "soundtrack.envelope.gainDb")
    if "music" in targets and "music" not in track:
        raise M2VError("music 包络需要声明 soundtrack.music")
    if "effects" in targets and not effects:
        raise M2VError("effects 包络需要声明 soundtrack.effects")
    silence = track.get("silence", [])
    if not isinstance(silence, list) or len(silence) > 128:
        raise M2VError("soundtrack.silence 必须为最多 128 项的数组")
    if silence and not ("music" in track or effects):
        raise M2VError("soundtrack.silence 需要 music 或 effects 声音轨")
    previous_end = -1
    for window in silence:
        obj(window, "soundtrack.silence.window", {"startFrame", "endFrame", "fadeFrames"})
        start = integer(window.get("startFrame"), 0, max_frame, "silence.startFrame")
        end = integer(window.get("endFrame"), 1, max_frame, "silence.endFrame")
        fade = integer(window.get("fadeFrames"), 1, max_frame, "silence.fadeFrames")
        if end <= start or start < previous_end:
            raise M2VError("静音窗口必须按时间排序且互不重叠")
        if fade * 2 > end - start:
            raise M2VError("静音窗口淡化长度不得超过窗口的一半")
        previous_end = end


def synthesize(name: str, target: Path) -> None:
    """无外部资产版权依赖的确定性正弦提示音，短包络避免点击爆音。"""
    duration = {"ding": .65, "ding-dong": 1.05, "click": .08, "transition": .3}[name]
    with wave.open(str(target), "wb") as dest:
        dest.setparams((1, 2, audio.SAMPLE_RATE, 0, "NONE", "not compressed"))
        samples = bytearray()
        for i in range(round(duration * audio.SAMPLE_RATE)):
            t = i / audio.SAMPLE_RATE
            if name == "ding-dong":
                local = t if t < .35 else t - .35
                frequency = 1046.5 if t < .35 else 784
            else:
                local = t
                frequency = {"ding": 1046.5, "click": 1800, "transition": 500}.get(name, 500)
            phase = 2 * math.pi * (frequency * local + (1500 * local**2 if name == "transition" else 0))
            envelope = min(1, local/.006) * math.exp(-local * (50 if name == "click" else 7)) * min(1, (duration-t)/.02)
            samples.extend(struct.pack("<h", round(16000 * envelope * math.sin(phase))))
        dest.writeframes(samples)


def mix(root: Path, source: dict, compiled: list[dict], raw: Path, target: Path,
        cues: list[dict], duration: float, work: Path, inputs: dict, *, effect_start_frames: list[float] | None = None) -> None:
    from .explainer import local_file
    fps = general_fps({}, source)
    track = source.get("soundtrack", {})
    total_frames = round(duration * fps)
    for envelope in track.get("envelopes", []):
        if envelope["keyframes"][-1]["frame"] > total_frames:
            raise M2VError("声音包络关键帧超过全片时长")
        if envelope["track"] == "music" and "music" not in track:
            raise M2VError("music 包络需要声明 soundtrack.music")
        if envelope["track"] == "effects" and not track.get("effects"):
            raise M2VError("effects 包络需要声明 soundtrack.effects")
    for window in track.get("silence", []):
        if window["endFrame"] > total_frames:
            raise M2VError("静音窗口超过全片时长")
    music = None
    if "music" in track:
        settings = track["music"]
        file = local_file(root, settings["sourceRef"], "music")
        inputs["file:" + file.relative_to(root).as_posix()] = asset_digest(file)
        music = (file, settings)
    effects = []
    starts = (effect_start_frames if effect_start_frames is not None else
              scene_events.effect_starts(track.get("effects", []), compiled, fps, total_frames))
    if len(starts) != len(track.get("effects", [])):
        raise M2VError("音效解析起点数量与声明不一致")
    library, library_inputs = sound_library.resolve(root)
    inputs.update(library_inputs)
    local_cache = {}
    for index, effect in enumerate(track.get("effects", [])):
        start = starts[index] / fps
        if not 0 <= start < duration: raise M2VError(f"音效 {index} 起点越界：{start:.3f}s")
        if "builtin" in effect:
            file = work / f"builtin-{index}.wav"
            synthesize(effect["builtin"], file)
            info = sound_library.probe(file)
        elif "assetId" in effect:
            info = library[effect["assetId"]]
            file = info["file"]
        else:
            source_file = local_file(root, effect["sourceRef"], "effect")
            inputs["file:" + source_file.relative_to(root).as_posix()] = asset_digest(source_file)
            if source_file not in local_cache:
                file = work / f"local-effect-{index}.wav"
                info = sound_library.decode(source_file, file)
                local_cache[source_file] = (file, info)
            file, info = local_cache[source_file]
        trim = effect.get("trimStartMs", 0) / 1000
        available = info["durationSeconds"] - trim
        if available <= 0:
            raise M2VError(f"音效 {index} trimStartMs 超出素材范围")
        length = effect.get("durationMs", available * 1000) / 1000
        if not effect.get("loop") and length > available + 1/audio.SAMPLE_RATE:
            raise M2VError(f"音效 {index} durationMs 超出素材剩余时长；需要重复时声明 loop")
        for field in ("fadeInMs", "fadeOutMs"):
            if effect.get(field, 0) > length * 1000:
                raise M2VError(f"音效 {index} {field} 超出播放时长")
        effects.append(audio.Effect(file, start, effect.get("gainDb", -18), trim, length,
                                   effect.get("loop", False), effect.get("fadeInMs", 0)/1000,
                                   effect.get("fadeOutMs", 0)/1000, effect.get("pan")))
    if music or effects:
        audio.mix(raw, target, duration,
                  [{"start": c["startFrame"]/ fps, "end": c["endFrame"]/ fps} for c in cues], music, effects, work,
                  fps=fps, envelopes=track.get("envelopes", []), silence=track.get("silence", []))
    else:
        audio.normalize(raw, target)
