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

BUILTINS = ("ding", "ding-dong", "click", "transition")


def validate(data: dict, root: Path) -> None:
    from m2v.core.validate import number, obj
    from .explainer import local_file
    track = obj(data.get("soundtrack", {}), "soundtrack", {"music", "effects"})
    scenes = {s["id"]: s for s in data["scenes"]}
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
    for effect in effects:
        obj(effect, "effect", {"builtin", "sourceRef", "sceneId", "segmentId", "offsetMs", "gainDb"})
        if ("builtin" in effect) == ("sourceRef" in effect): raise M2VError("音效 builtin/sourceRef 必须二选一")
        if "builtin" in effect:
            if effect["builtin"] not in BUILTINS: raise M2VError(f"未知内置音效，可选 {BUILTINS}")
        else: local_file(root, effect["sourceRef"], "effect.sourceRef")
        scene = scenes.get(effect.get("sceneId")) if isinstance(effect.get("sceneId"), str) else None
        if scene is None: raise M2VError("音效引用未知 sceneId")
        if "segmentId" in effect and effect["segmentId"] not in [s["id"] for s in scene.get("narrationSegments", [])]:
            raise M2VError("音效引用未知 segmentId")
        offset = effect.get("offsetMs", 0)
        if type(offset) is not int: raise M2VError("offsetMs 必须为整数")
        number(offset, -60000, 60000, "offsetMs")
        number(effect.get("gainDb", -18), -60, 0, "effect.gainDb")


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
        cues: list[dict], duration: float, work: Path, inputs: dict) -> None:
    from .explainer import local_file
    fps = general_fps({}, source)
    track = source.get("soundtrack", {})
    music = None
    if "music" in track:
        settings = track["music"]
        file = local_file(root, settings["sourceRef"], "music")
        inputs["file:" + file.relative_to(root).as_posix()] = asset_digest(file)
        music = (file, settings)
    effects = []
    scenes = {scene["id"]: scene for scene in compiled}
    for index, effect in enumerate(track.get("effects", [])):
        scene = scenes[effect["sceneId"]]
        start = scene["segmentWindows"][effect["segmentId"]]["startFrame"] if "segmentId" in effect else scene["startFrame"]
        start = start / fps + effect.get("offsetMs", 0) / 1000
        if not 0 <= start < duration: raise M2VError(f"音效 {index} 起点越界：{start:.3f}s")
        if "builtin" in effect:
            file = work / f"builtin-{index}.wav"
            synthesize(effect["builtin"], file)
        else:
            file = local_file(root, effect["sourceRef"], "effect")
            inputs["file:" + file.relative_to(root).as_posix()] = asset_digest(file)
        effects.append((file, start, effect.get("gainDb", -18)))
    if music or effects:
        audio.mix(raw, target, duration,
                  [{"start": c["startFrame"]/ fps, "end": c["endFrame"]/ fps} for c in cues], music, effects, work)
    else:
        audio.normalize(raw, target)
