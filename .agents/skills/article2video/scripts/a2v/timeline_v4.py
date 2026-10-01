"""单场景分镜 v4 的全片确定性帧时间轴。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .beats import proportional_spans

PHASES = ("establish", "change", "result", "settle")


@dataclass(frozen=True)
class FrameRange:
    id: str
    start_frame: int
    end_frame: int

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "startFrame": self.start_frame, "endFrame": self.end_frame}


@dataclass(frozen=True)
class V4Timeline:
    fps: int
    total_frames: int
    stages: tuple[FrameRange, ...]
    beats: tuple[dict[str, Any], ...]
    phases: tuple[dict[str, Any], ...]
    estimated: bool = True

    def stage_at(self, frame: int) -> str | None:
        return next((item.id for item in self.stages if item.start_frame <= frame < item.end_frame), None)

    def to_json(self) -> dict[str, Any]:
        return {"fps": self.fps, "totalFrames": self.total_frames,
                "stages": [item.to_json() for item in self.stages],
                "beats": list(self.beats), "phases": list(self.phases), "estimated": self.estimated}


def _phase_spans(start: int, duration: int, beats: list[dict[str, Any]]) -> list[tuple[int, int]]:
    settle = start + max(0, duration - 12)
    if beats:
        first_end = min(settle, beats[0]["endFrame"])
        change_end = min(settle, beats[-1]["endFrame"])
    else:
        active = settle - start
        first_end = start + int(active * .35)
        change_end = start + int(active * .75)
    return [(start, first_end), (first_end, change_end), (change_end, settle), (settle, start + duration)]


def resolve_v4(storyboard: dict[str, Any], media: dict[str, Any] | None = None) -> V4Timeline:
    """Resolve all stage/beat/phase intervals to global half-open frame ranges."""
    if media is not None:
        media_stages = media.get("stages")
        if (not isinstance(media_stages, list) or len(media_stages) != len(storyboard["stages"])
                or any(item.get("id") != stage.get("id") for item, stage in zip(media_stages, storyboard["stages"]))):
            raise ValueError("v4 media stage 顺序或 ID 与分镜不匹配")
    fps = int(storyboard["fps"])
    cursor = 0
    stages: list[FrameRange] = []
    beats: list[dict[str, Any]] = []
    phases: list[dict[str, Any]] = []
    for stage_index, stage in enumerate(storyboard["stages"]):
        duration = int(media["stages"][stage_index]["durationInFrames"] if media else stage["durationInFrames"])
        stage_start, stage_end = cursor, cursor + duration
        stages.append(FrameRange(stage["id"], stage_start, stage_end))
        segments = stage.get("narrationSegments") or []
        stage_beats: list[dict[str, Any]] = []
        if media is not None:
            stage_beats = [dict(beat) for beat in media.get("resolvedBeats", []) if beat.get("stageId") == stage["id"]]
            beats.extend(stage_beats)
        elif segments:
            text = [str(segment.get("text", "")) for segment in segments]
            budget = duration - 12
            if budget < len(text):
                budget = duration
            spans = proportional_spans(budget, text)
            by_id = {beat["id"]: beat for beat in stage.get("beats", [])}
            previous: dict[str, Any] | None = None
            for segment, (local_start, local_end) in zip(segments, spans):
                beat_id = segment["beatId"]
                if previous and previous["id"] == beat_id:
                    previous["endFrame"] = stage_start + local_end
                else:
                    beat = by_id[beat_id]
                    previous = {"id": beat_id, "stageId": stage["id"], "action": beat["action"],
                                "targets": list(beat["targets"]), "meaning": beat["meaning"],
                                "startFrame": stage_start + local_start, "endFrame": stage_start + local_end}
                    beats.append(previous)
                    stage_beats.append(previous)
                if previous and previous["id"] == beat_id and previous not in stage_beats:
                    stage_beats.append(previous)
        for phase, (phase_start, phase_end) in zip(PHASES, _phase_spans(stage_start, duration, stage_beats)):
            phases.append({"stageId": stage["id"], "phase": phase, "startFrame": phase_start, "endFrame": phase_end})
        cursor = stage_end
    return V4Timeline(fps, cursor, tuple(stages), tuple(beats), tuple(phases), estimated=media is None)
