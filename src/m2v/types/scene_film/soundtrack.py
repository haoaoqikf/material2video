"""创作命令读取分镜时的声音编排校验。"""
from __future__ import annotations

from m2v.core.video_config import storyboard_fps

from pathlib import Path
from m2v.core.errors import M2VError
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
    max_frame = 600 * storyboard_fps({}, data)
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
