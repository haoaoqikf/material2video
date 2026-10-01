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


def _phase_spans(start: int, duration: int) -> list[tuple[int, int]]:
    # Deterministic largest-remainder partition; the final phase ends exactly at the stage boundary.
    widths = [duration // 4] * 4
    for index in range(duration % 4):
        widths[index] += 1
    spans: list[tuple[int, int]] = []
    cursor = start
    for width in widths:
        spans.append((cursor, cursor + width))
        cursor += width
    return spans


def resolve_v4(storyboard: dict[str, Any]) -> V4Timeline:
    """Resolve all stage/beat/phase intervals to global half-open frame ranges."""
    fps = int(storyboard["fps"])
    cursor = 0
    stages: list[FrameRange] = []
    beats: list[dict[str, Any]] = []
    phases: list[dict[str, Any]] = []
    for stage in storyboard["stages"]:
        duration = int(stage["durationInFrames"])
        stage_start, stage_end = cursor, cursor + duration
        stages.append(FrameRange(stage["id"], stage_start, stage_end))
        for phase, (start, end) in zip(PHASES, _phase_spans(stage_start, duration)):
            phases.append({"stageId": stage["id"], "phase": phase, "startFrame": start, "endFrame": end})
        segments = stage.get("narrationSegments") or []
        if segments:
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
        cursor = stage_end
    return V4Timeline(fps, cursor, tuple(stages), tuple(beats), tuple(phases))
