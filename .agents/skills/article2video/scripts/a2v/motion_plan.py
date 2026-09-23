"""语义动画计划的 Python 参考实现，与 web/runtime/motionPlan.ts 共享规则。"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from . import beats

STABLE_READING_FRAMES = beats.STABLE_READING_FRAMES
PHASES = ("establish", "change", "result", "settle")

@dataclass(frozen=True)
class Span:
    start_frame: int
    end_frame: int

def phase_spans(scene: dict[str, Any]) -> dict[str, Span]:
    duration = int(scene["durationInFrames"]); settle = max(0, duration - STABLE_READING_FRAMES)
    timeline = beats.resolve_silent(scene) if scene.get("narrationSegments") else beats.BeatTimeline()
    if timeline.beats:
        first_end = min(settle, timeline.beats[0].end_frame); change_end = min(settle, timeline.beats[-1].end_frame)
    else:
        first_end = int(settle * .35); change_end = int(settle * .75)
    return {"establish": Span(0, first_end), "change": Span(first_end, change_end), "result": Span(change_end, settle), "settle": Span(settle, duration)}

def stagger_order(targets: list[str], kind: str, path: list[str] | None = None) -> list[str]:
    if kind == "reverse": return list(reversed(targets))
    if kind == "center": return [item for _, item in sorted((abs(index - (len(targets)-1)/2), item) for index, item in enumerate(targets))]
    if kind == "path":
        if not path or len(path) < 2 or any(item not in targets for item in path): raise ValueError("路径传播必须提供覆盖目标的有效 path")
        return list(path)
    return list(targets)
