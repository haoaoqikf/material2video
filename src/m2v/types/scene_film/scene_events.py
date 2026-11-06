"""幕内事件的唯一时间规则；准备、混音与场景配置共享解析结果。"""
from __future__ import annotations

from m2v.core.errors import M2VError
from m2v.core.validate import integer, obj, text

MAX_EVENTS = 1024


def validate(scene: dict, duration: int | None = None) -> dict[str, int]:
    path = f"scene[{scene['id']}].events"
    events = scene.get("events", [])
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise M2VError(f"{path} 必须为最多 {MAX_EVENTS} 项的数组")
    frames = {}
    for event in events:
        obj(event, path, {"id", "frame"})
        identity = text(event.get("id"), path + ".id")
        frame = integer(event.get("frame"), 0, 36000, path + ".frame")
        if identity in frames:
            raise M2VError(f"{path} 重复事件 ID：{identity}")
        if duration is not None and frame >= duration:
            raise M2VError(f"{path}.{identity} 帧 {frame} 超出本幕时长 {duration}")
        frames[identity] = frame
    return frames


def validate_reference(effect: dict, event_frames: dict[str, int]) -> None:
    if "eventId" not in effect:
        return
    identity = text(effect["eventId"], "effect.eventId")
    if identity not in event_frames:
        raise M2VError(f"音效引用未知 eventId：{identity}")
    if "segmentId" in effect or "offsetMs" in effect:
        raise M2VError("eventId 不可与 segmentId/offsetMs 同时声明")


def resolve(scenes: list[dict]) -> list[dict]:
    """实际幕长确定后解析，幕内帧表直接作为录制配置输入。"""
    entries = []
    for scene in scenes:
        frames = validate(scene, scene["durationInFrames"])
        scene["eventFrames"] = frames
        entries.extend({"sceneId": scene["id"], "id": identity, "frame": frame,
                        "globalFrame": scene["startFrame"] + frame}
                       for identity, frame in frames.items())
    return entries


def effect_starts(effects: list[dict], scenes: list[dict], fps: int, total_frames: int) -> list[float]:
    """毫秒定位保留分数帧精度，事件定位始终使用整数帧。"""
    by_id = {scene["id"]: scene for scene in scenes}
    starts = []
    for index, effect in enumerate(effects):
        scene = by_id[effect["sceneId"]]
        if "eventId" in effect:
            frames = scene["eventFrames"]
            validate_reference(effect, frames)
            local = frames[effect["eventId"]] + effect.get("offsetFrames", 0)
            if not 0 <= local < scene["durationInFrames"]:
                raise M2VError(f"音效 {index} 事件偏移后起点越界：{local} 帧（所属幕 {scene['id']}）")
            start = scene["startFrame"] + local
        else:
            start = (scene["segmentWindows"][effect["segmentId"]]["startFrame"]
                     if "segmentId" in effect else scene["startFrame"])
            start += effect["offsetFrames"] if "offsetFrames" in effect else effect.get("offsetMs", 0) * fps / 1000
        if not 0 <= start < total_frames:
            raise M2VError(f"音效 {index} 起点越界：{start / fps:.3f}s")
        starts.append(start)
    return starts
