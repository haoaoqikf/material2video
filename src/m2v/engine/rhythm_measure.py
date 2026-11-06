"""交付音轨的节奏测量：静音区间与准备时间轴对账。

本模块只做两件事：

- **纯区间运算**：半开区间裁剪、排序合并、交集计时。全片按并集、逐场按交集，
  跨场不重复计时。
- **报告生成**：读取 `qa_inspection.audio_signals` 已经完成的静音候选与
  `prepared` 时间轴，输出字数、旁白窗口、平均字速、静音分布与归因限制。

它不再次解码音轨、不调用 ffmpeg，也不参与审美通过与否：没有最低字速、最长静音
或静音占比阈值。字幕阅读上限仍由 `types/scene_film/reading_pace.py` 独立报告。
"""
from __future__ import annotations

from typing import Iterable

from m2v.core.text import count_characters
from m2v.core.video_config import READING_TAIL_SECONDS

Interval = tuple[float, float]
HoldKind = str
HOLD_KINDS = ("leadIn", "segmentHold", "readingHold", "tail")
#: 区间比较的浮点容差；只用于避免相邻区间因为舍入被判成重叠或缝隙。
EPSILON = 1e-9

UNITS = {
    "seconds": "seconds",
    "characters": "characters",
    "charactersPerSecond": "charactersPerSecond",
    "ratio": "ratio",
}

_LIMITATIONS = [
    "静音来自交付音轨的自动信号检测；音乐、音效与编码噪声可能进入候选，不能证明口播停顿来源。",
    "旁白窗口内的静音只表示位置，不声称由标点造成；无法归因的剩余部分记为 unknown。",
    "测量不参与审美通过与否，不设最低字速、最长静音或静音占比阈值；字幕阅读上限另行报告。",
    "全片静音按区间并集计时，逐场按交集计时；淡化/交叉淡化造成的相邻场景重叠，边界部分分配给后一幕，不重复计时。",
    "声明留白（storyboardHoldSeconds）与时间轴实际落地留白（declaredHoldSeconds）分开报告；不一致时以实际时间轴计时并提示复查。",
    "交付音轨短于旁白窗口时字速不适用，不强行计算或补零。",
]


# ---------------------------------------------------------------------------
# 纯区间运算
# ---------------------------------------------------------------------------

def clip(intervals: Iterable[Interval], limit: float) -> list[Interval]:
    """裁到 `[0, limit]` 的半开区间；丢弃零长或倒置区间。"""
    result: list[Interval] = []
    for start, end in intervals:
        a, b = max(0.0, float(start)), min(float(limit), float(end))
        if b - a > EPSILON:
            result.append((a, b))
    return result


def merge(intervals: Iterable[Interval]) -> list[Interval]:
    """排序并合并重叠或首尾相接的区间；输入应已裁到同一范围。"""
    ordered = sorted((a, b) for a, b in intervals if b - a > EPSILON)
    merged: list[Interval] = []
    for start, end in ordered:
        if merged and start <= merged[-1][1] + EPSILON:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def total(intervals: Iterable[Interval]) -> float:
    return sum(end - start for start, end in intervals)


def intersections(intervals: Iterable[Interval], windows: Iterable[Interval]) -> list[Interval]:
    """两组区间的交集片段；不做合并，调用方可继续 `merge`。"""
    result: list[Interval] = []
    for start, end in intervals:
        for window_start, window_end in windows:
            a, b = max(start, window_start), min(end, window_end)
            if b - a > EPSILON:
                result.append((a, b))
    return result


def intersect_seconds(intervals: Iterable[Interval], windows: Iterable[Interval]) -> float:
    return total(intersections(intervals, windows))


# ---------------------------------------------------------------------------
# 准备时间轴
# ---------------------------------------------------------------------------

def narration_windows(prepared: dict) -> list[dict]:
    """全片旁白窗口的绝对秒数；与音频候选的 `narrationOverlap` 共用一份口径。"""
    result = []
    fps = prepared.get("fps")
    if not isinstance(fps, (int, float)) or fps <= 0:
        return result
    for scene in (prepared.get("props") or {}).get("compiledScenes") or []:
        for segment in scene.get("narrationSegments") or []:
            if not str(segment.get("text") or "").strip():
                continue
            window = (scene.get("segmentWindows") or {}).get(segment.get("id"))
            if not window:
                continue
            result.append({"id": segment["id"], "startSeconds": window["startFrame"] / fps,
                           "endSeconds": window["endFrame"] / fps})
    return result


def timeline(prepared: dict) -> dict | None:
    """从 v8 prepared 提取节奏对账所需的绝对时间轴。

    缺少 `compiledScenes` 或场景起止帧时返回 `None`——其他类型没有可确认的画幕时序，
    明确不适用，而不是猜测或补零。
    """
    props = prepared.get("props") or {}
    scenes = props.get("compiledScenes")
    fps = prepared.get("fps")
    if not isinstance(scenes, list) or not scenes or not isinstance(fps, (int, float)) or fps <= 0:
        return None
    result = []
    for scene in scenes:
        start_frame, end_frame = scene.get("startFrame"), scene.get("endFrame")
        if not isinstance(start_frame, (int, float)) or not isinstance(end_frame, (int, float)):
            return None
        start, end = start_frame / fps, end_frame / fps
        if end < start:
            return None
        segments = []
        windows: list[Interval] = []
        for segment in scene.get("narrationSegments") or []:
            text = str(segment.get("text") or "")
            if not text.strip():
                continue
            window = (scene.get("segmentWindows") or {}).get(segment.get("id"))
            if not window:
                # 有旁白却没有时间窗时不能跳过：那会让字数与窗口口径不一致。
                return None
            a, b = window.get("startFrame"), window.get("endFrame")
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or b < a:
                return None
            segments.append({"id": segment.get("id"), "characters": count_characters(text),
                             "startSeconds": a / fps, "endSeconds": b / fps})
            windows.append((a / fps, b / fps))
        holds = _holds(scene, fps, start, end, windows, overlap_frames=scene.get("transitionFrames") or 0)
        result.append({"sceneId": str(scene.get("id")), "startSeconds": start, "endSeconds": end,
                       "segments": segments, "windows": windows, "holds": holds,
                       "storyboardHolds": _storyboard_holds(scene, fps)})
    return {"fps": float(fps), "scenes": result}


def _storyboard_holds(scene: dict, fps: float) -> dict[str, float]:
    """分镜声明的留白秒数；与时间轴实际落地值分开报告，差异可复查。"""
    segments = scene.get("narrationSegments") or []
    segment_hold = sum(float(segment.get("holdFrames", 0) or 0)
                       for segment in segments[:-1]) / fps
    reading = scene.get("readingHoldFrames")
    if reading is None:
        reading = round(READING_TAIL_SECONDS * fps)
    return {"leadIn": (scene.get("leadInFrames") or 0) / fps,
            "segmentHold": segment_hold,
            "readingHold": float(reading) / fps,
            "tail": (scene.get("tailFrames") or 0) / fps}


def _holds(scene: dict, fps: float, start: float, end: float,
           windows: list[Interval], *, overlap_frames: float) -> dict[str, list[Interval]]:
    """声明留白窗口：引子、段间、阅读停留与幕尾。

    窗口取实际时间轴，而不是只信声明值；声明帧数在这里只决定尾部分配的先后。
    段间留白是相邻旁白窗口之间的全部空隙；阅读停留从末段结束开始，幕尾贴着场景结束。
    """
    holds: dict[str, list[Interval]] = {kind: [] for kind in HOLD_KINDS}
    lead_in = scene.get("leadInFrames") or 0
    reading = scene.get("readingHoldFrames")
    if reading is None:
        reading = round(READING_TAIL_SECONDS * fps)
    tail = scene.get("tailFrames") or 0
    visual_start = start + max(0.0, float(overlap_frames) / fps)
    if windows:
        first = windows[0][0]
        if first - visual_start > EPSILON and lead_in:
            holds["leadIn"].append((visual_start, first))
        for (_, before), (after, _) in zip(windows, windows[1:]):
            if after - before > EPSILON:
                holds["segmentHold"].append((before, after))
        last = windows[-1][1]
        if end - last > EPSILON:
            reading_end = min(end, last + reading / fps)
            if reading_end - last > EPSILON:
                holds["readingHold"].append((last, reading_end))
            tail_start = max(reading_end, end - tail / fps)
            if end - tail_start > EPSILON:
                holds["tail"].append((tail_start, end))
    else:
        if tail:
            tail_start = max(visual_start, end - tail / fps)
            if end - tail_start > EPSILON:
                holds["tail"].append((tail_start, end))
        if lead_in:
            lead_end = min(end, visual_start + lead_in / fps)
            if lead_end - visual_start > EPSILON:
                holds["leadIn"].append((visual_start, lead_end))
    return holds


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------

def _round(value: float | None, digits: int = 5) -> float | None:
    return None if value is None else round(value, digits)


def _ratio(part: float, whole: float) -> float | None:
    return round(part / whole, 5) if whole > EPSILON else None


def _cps(characters: int, seconds: float, reason: str) -> tuple[float | None, str | None]:
    if seconds <= EPSILON:
        return None, reason
    return round(characters / seconds, 3), None


def not_applicable(detail: str) -> dict:
    return {"kind": "measurement", "status": "not-applicable", "detail": detail,
            "units": dict(UNITS), "limitations": list(_LIMITATIONS)}


def build(prepared: dict, audio: dict) -> dict:
    """把音频静音候选与准备时间轴对账；不改变既有技术 QA 判定。"""
    if audio.get("status") != "measured":
        return not_applicable("交付文件没有可测量的音轨；契约允许无声时不推算静音。")
    data = timeline(prepared)
    if data is None:
        return not_applicable("当前类型没有可确认的旁白窗口与场景时序，不进行节奏测量。")
    duration = audio.get("durationSeconds")
    if not isinstance(duration, (int, float)) or duration <= 0:
        return not_applicable("交付音轨时长无效，无法裁剪静音区间。")

    raw = [(item.get("startSeconds"), item.get("endSeconds"))
           for item in audio.get("candidates", []) if item.get("reason") == "silence"]
    raw = [(float(a), float(b)) for a, b in raw
           if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b > a]
    silences = merge(clip(raw, duration))

    scenes = data["scenes"]
    all_windows = merge(clip([w for scene in scenes for w in scene["windows"]], duration))
    narration_seconds = total(all_windows)
    characters = sum(segment["characters"] for scene in scenes for segment in scene["segments"])
    truncated = any(end > duration + EPSILON for scene in scenes for _, end in scene["windows"])
    cps, cps_reason = _cps(characters, narration_seconds, "全片没有旁白窗口，字速不适用")
    if truncated:
        cps, cps_reason = None, "交付音轨短于旁白窗口，字速不适用"

    declared: dict[str, list[Interval]] = {kind: [] for kind in HOLD_KINDS}
    for scene in scenes:
        for kind in HOLD_KINDS:
            declared[kind].extend(scene["holds"][kind])
    declared = {kind: merge(clip(intervals, duration)) for kind, intervals in declared.items()}
    declared_union = merge([interval for kind in HOLD_KINDS for interval in declared[kind]])
    storyboard = {kind: sum(scene["storyboardHolds"][kind] for scene in scenes) for kind in HOLD_KINDS}

    # 淡化/交叉淡化会让相邻两幕在 prepared 中重叠；把边界静音分配给后一幕，
    # 逐场计时因此不重复。实际时长仍按场景起点报告。
    measures: list[Interval] = []
    for index, scene in enumerate(scenes):
        start, end = scene["startSeconds"], scene["endSeconds"]
        if index + 1 < len(scenes):
            following = scenes[index + 1]["startSeconds"]
            if following > start:
                end = min(end, following)
        measures.append((start, end))

    scene_reports = []
    for scene, measure in zip(scenes, measures):
        scene_range = [measure]
        scene_windows = merge(intersections(clip(scene["windows"], duration), scene_range))
        scene_silence = merge(intersections(silences, scene_range))
        window_silence = merge(intersections(scene_silence, scene_windows))
        hold_union = merge([interval for kind in HOLD_KINDS for interval in scene["holds"][kind]])
        covered = merge([*intersections(scene_silence, scene_windows),
                         *intersections(scene_silence, hold_union)])
        scene_characters = sum(segment["characters"] for segment in scene["segments"])
        scene_narration = total(scene_windows)
        scene_truncated = any(end > duration + EPSILON for _, end in scene["windows"])
        scene_cps, scene_reason = _cps(scene_characters, scene_narration, "本场没有旁白窗口，字速不适用")
        if scene_truncated:
            scene_cps, scene_reason = None, "交付音轨短于本场旁白窗口，字速不适用"
        scene_seconds = measure[1] - measure[0]
        scene_reports.append({
            "sceneId": scene["sceneId"],
            "startSeconds": _round(scene["startSeconds"]),
            "endSeconds": _round(scene["endSeconds"]),
            "measureStartSeconds": _round(measure[0]),
            "measureEndSeconds": _round(measure[1]),
            "truncated": scene_truncated,
            "characters": scene_characters,
            "narrationWindows": len(scene["segments"]),
            "narrationSeconds": _round(scene_narration),
            "charactersPerSecond": scene_cps,
            "charactersPerSecondReason": scene_reason,
            "silenceSeconds": _round(total(scene_silence)),
            "silenceRatio": _ratio(total(scene_silence), scene_seconds),
            "narrationSilenceSeconds": _round(total(window_silence)),
            "declaredHoldSeconds": {kind: _round(total(merge(intersections(
                clip(scene["holds"][kind], duration), scene_range)))) for kind in HOLD_KINDS},
            "storyboardHoldSeconds": {kind: _round(scene["storyboardHolds"][kind])
                                      for kind in HOLD_KINDS},
            "unknownSilenceSeconds": _round(max(0.0, total(scene_silence) - total(covered))),
            "silences": [{"startSeconds": _round(a), "endSeconds": _round(b),
                          "seconds": _round(b - a)} for a, b in scene_silence],
        })

    hold_seconds = {kind: _round(total(intervals)) for kind, intervals in declared.items()}
    narration_silence = intersect_seconds(silences, all_windows)
    declared_silence = intersect_seconds(silences, declared_union)
    covered = merge([*intersections(silences, all_windows), *intersections(silences, declared_union)])
    intervals = []
    for start, end in silences:
        span = [(start, end)]
        window_ids = [segment["id"] for scene in scenes for segment in scene["segments"]
                      if min(end, segment["endSeconds"]) - max(start, segment["startSeconds"]) > EPSILON]
        kinds = [kind for kind in HOLD_KINDS
                 if intersect_seconds(span, declared[kind]) > EPSILON]
        scene_ids = [scene["sceneId"] for scene in scenes
                     if min(end, scene["endSeconds"]) - max(start, scene["startSeconds"]) > EPSILON]
        piece_covered = merge([*intersections(span, all_windows), *intersections(span, declared_union)])
        intervals.append({
            "startSeconds": _round(start), "endSeconds": _round(end), "seconds": _round(end - start),
            "sceneIds": scene_ids, "narrationWindows": window_ids, "declaredHolds": kinds,
            "unknownSeconds": _round(max(0.0, (end - start) - total(piece_covered))),
        })

    return {
        "kind": "measurement",
        "status": "measured",
        "scope": "delivery-audio-and-prepared-timeline",
        "units": dict(UNITS),
        "summary": {
            "durationSeconds": _round(duration),
            "characters": characters,
            "narrationSeconds": _round(narration_seconds),
            "charactersPerSecond": cps,
            "charactersPerSecondReason": cps_reason,
            "truncated": truncated,
            "silenceCandidates": len(raw),
            "silenceMerged": len(silences),
            "silenceSeconds": _round(total(silences)),
            "silenceRatio": _ratio(total(silences), duration),
            "narrationSilenceSeconds": _round(narration_silence),
            "declaredSilenceSeconds": _round(declared_silence),
            "unknownSilenceSeconds": _round(max(0.0, total(silences) - total(covered))),
            "declaredHoldSeconds": {**hold_seconds,
                                    "total": _round(total(declared_union))},
            "storyboardHoldSeconds": {**{kind: _round(storyboard[kind]) for kind in HOLD_KINDS},
                                      "total": _round(sum(storyboard.values()))},
        },
        "scenes": scene_reports,
        "intervals": intervals,
        "limitations": list(_LIMITATIONS),
    }
