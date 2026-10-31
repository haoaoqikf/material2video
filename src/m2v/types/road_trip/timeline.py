"""每日帧分配与旁白/卡片/音效锚点的全局帧换算。

口播永不截断：每天的最小帧数由章节卡、前导、全部旁白、段间停留、到达停留与
当天概览收束相加得到。软目标多出来的帧按当天路线里程加权，用最大余数法分成
整数帧，保证相同材料重复准备得到完全一致的帧数。
"""
from __future__ import annotations

import math
from typing import Any

from m2v.core.errors import M2VError
from m2v.types.road_trip import layout as layout_module
from m2v.types.road_trip.materials import FPS


def minimum_day_frames(speech_frames: list[int], *, chapter: int, lead_in: int,
                       inter_hold: int, arrival_hold: int, pullout: int) -> int:
    total = chapter + lead_in + sum(speech_frames) + max(0, len(speech_frames) - 1) * inter_hold
    return total + arrival_hold + pullout


def distribute_remainder(total: int, weights: list[float]) -> list[int]:
    """最大余数法分配整数余量；权重全零时平均分，不引入随机。"""
    if total < 0:
        raise M2VError("余量不能为负")
    if not weights:
        return []
    floor = [0] * len(weights)
    weight_sum = sum(max(0.0, weight) for weight in weights)
    if weight_sum <= 0:
        base, extra = divmod(total, len(weights))
        return [base + (1 if index < extra else 0) for index in range(len(weights))]
    remainders: list[tuple[float, int]] = []
    assigned = 0
    for index, weight in enumerate(weights):
        exact = total * max(0.0, weight) / weight_sum
        whole = math.floor(exact)
        floor[index] = whole
        assigned += whole
        remainders.append((exact - whole, index))
    remainders.sort(key=lambda item: (-item[0], item[1]))
    for position in range(total - assigned):
        floor[remainders[position][1]] += 1
    return floor


def _anchor_local(anchor: dict[str, Any], docs: dict[str, Any], day: dict[str, Any],
                  index: int, spans: dict[str, int], length: int) -> int | None:
    """旁白锚点 → 当天局部帧；地标按当天路线里程比例换算。"""
    kind = anchor["kind"]
    if kind == "arrival":
        # 句尾正好让出到达停留；到达点之后只留当天概览收束。
        hold = round(layout_module.layout()["camera"]["arrivalHoldSeconds"] * FPS)
        return max(spans["chapter_frames"], spans["arrival_frame"] - hold - length)
    if kind != "landmark":
        raise M2VError(f"{day['id']} 的旁白锚点类型无效：{kind}")
    landmark_id = anchor.get("landmarkId")
    route = docs["routes"][day["id"]]
    point = next((item for item in route["viaPoints"] if item["id"] == landmark_id), None)
    if point is None:
        raise M2VError(f"{day['id']} 的旁白锚点引用未知地标：{landmark_id}")
    geom = layout_module.day_geometry(route, trim_origin=index == 0)
    fraction = min(1.0, max(0.0, float(point["distanceMeters"]) / max(1.0, geom["length_meters"])))
    return round(spans["follow_start"] + fraction
                 * (spans["arrival_frame"] - spans["follow_start"]))


def _place_segments(day: dict[str, Any], docs: dict[str, Any], index: int,
                    frames: int, speech_frames: list[int], *, fps: int,
                    chapter: int, lead_in: int, inter_hold: int) -> tuple[dict[str, int], int]:
    """按锚点与顺序排布当天旁白；返回（段局部窗口，最后一个段尾）。"""
    spans = layout_module.day_spans(frames, fps)
    cursor = spans["chapter_frames"] + lead_in
    windows: dict[str, int] = {}
    for position, segment in enumerate(day["narration"]):
        length = speech_frames[position]
        start = cursor
        if "anchor" in segment:
            anchored = _anchor_local(segment["anchor"], docs, day, index, spans, length)
            if anchored is not None:
                # 地标句可以略早开口，但必须在到达停留前收尾；否则最后一段
                # 会把当天时长不断推高，形成不收敛的固定点。
                arrival_hold = round(layout_module.layout()["camera"]["arrivalHoldSeconds"] * FPS)
                latest = spans["arrival_frame"] - arrival_hold - length
                start = max(start, min(anchored, latest))
        end = start + length
        windows[segment["id"]] = start
        windows[segment["id"] + ":end"] = end
        cursor = end
        if position < len(day["narration"]) - 1:
            cursor += inter_hold
    return windows, cursor


def allocate(docs: dict[str, Any], measured: dict[str, list[float]]) -> dict[str, Any]:
    """编译每日帧数与全部锚点；返回可直接写入 props 的时间轴。"""
    trip = docs["trip"]
    spec = layout_module.layout()
    fps = FPS
    chapter = int(spec["timeline"]["chapterFrames"])
    lead_in = round(spec["camera"]["leadInSeconds"] * fps)
    inter_hold = int(spec["camera"]["interSegmentHoldFrames"])
    arrival_hold = round(spec["camera"]["arrivalHoldSeconds"] * fps)
    pullout = round(spec["camera"]["pulloutSeconds"] * fps)
    opening = round(spec["camera"]["openingSeconds"] * fps)

    speech: dict[str, list[int]] = {}
    minimums: list[int] = []
    weights: list[float] = []
    for index, day in enumerate(docs["days"]):
        seconds = measured[day["id"]]
        if len(seconds) != len(day["narration"]):
            raise M2VError(f"{day['id']} 的测量段数与旁白段数不一致")
        frames = [max(1, math.ceil(value * fps)) for value in seconds]
        for value in seconds:
            if not math.isfinite(value) or value <= 0:
                raise M2VError(f"{day['id']} 的旁白音频时长无效")
        speech[day["id"]] = frames
        minimum = minimum_day_frames(frames, chapter=chapter, lead_in=lead_in,
                                     inter_hold=inter_hold, arrival_hold=arrival_hold,
                                     pullout=pullout)
        for _attempt in range(60):
            _windows, last_end = _place_segments(day, docs, index, minimum, frames,
                                                 fps=fps, chapter=chapter, lead_in=lead_in,
                                                 inter_hold=inter_hold)
            spans = layout_module.day_spans(minimum, fps)
            required = last_end + arrival_hold + pullout
            if spans["follow_start"] >= spans["arrival_frame"]:
                required = max(required, chapter + opening + pullout + arrival_hold + 1)
            if required <= minimum:
                break
            minimum = required
        else:
            raise M2VError(f"{day['id']} 的旁白锚点无法在当天时间轴内排布")
        minimums.append(minimum)
        weights.append(float(docs["routes"][day["id"]]["route"]["distanceMeters"]))

    target = int(trip["targetSeconds"]) * fps
    extra = target - sum(minimums)
    if extra > 0:
        shares = distribute_remainder(extra, weights)
    else:
        shares = [0] * len(minimums)
    day_frames = [minimums[index] + shares[index] for index in range(len(minimums))]
    if sum(day_frames) > layout_module.layout()["timeline"]["maxTripSeconds"] * fps:
        raise M2VError(f"全片 {sum(day_frames) / fps:.1f} 秒，超过 600 秒；"
                       "请精简旁白或减少天数，不得截断口播")

    days: list[dict[str, Any]] = []
    windows: dict[str, dict[str, dict[str, int]]] = {}
    cursor = 0
    for index, day in enumerate(docs["days"]):
        frames = day_frames[index]
        spans = layout_module.day_spans(frames, fps)
        opening_frames = min(opening, spans["drive_frames"])
        follow_start = spans["chapter_frames"] + opening_frames
        arrival_local = spans["arrival_frame"]
        placed, last_end = _place_segments(day, docs, index, frames, speech[day["id"]],
                                           fps=fps, chapter=chapter, lead_in=lead_in,
                                           inter_hold=inter_hold)
        if last_end + arrival_hold > arrival_local:
            raise M2VError(f"{day['id']} 的旁白超出当天到达窗口；拒绝截断口播")
        if follow_start >= arrival_local:
            raise M2VError(f"{day['id']} 的章节卡与开场推近占满全天，无法跟随")
        segment_windows: dict[str, dict[str, int]] = {}
        for segment in day["narration"]:
            start = placed[segment["id"]]
            end = placed[segment["id"] + ":end"]
            segment_windows[segment["id"]] = {
                "startFrame": cursor + start,
                "endFrame": cursor + end,
                "localStart": start,
                "localEnd": end,
            }
        windows[day["id"]] = {segment["id"]: {
            "startFrame": segment_windows[segment["id"]]["startFrame"],
            "endFrame": segment_windows[segment["id"]]["endFrame"]}
            for segment in day["narration"]}
        days.append({
            "dayId": day["id"],
            "startFrame": cursor,
            "durationInFrames": frames,
            "chapterFrames": spans["chapter_frames"],
            "openingStart": spans["chapter_frames"],
            "openingFrames": opening_frames,
            "followStart": follow_start,
            "arrivalLocalFrame": arrival_local,
            "pulloutFrames": spans["pullout_frames"],
            "segmentWindows": segment_windows,
        })
        cursor += frames

    return {"days": days, "totalFrames": cursor, "segmentWindows": windows,
            "fps": fps, "targetFrames": target}


def resolve_anchor(anchor: dict[str, Any], timeline: dict[str, Any],
                   docs: dict[str, Any]) -> int:
    """把材料里的锚点解析成全局帧；越界或引用缺失都失败。"""
    kind = anchor["kind"]
    total = timeline["totalFrames"]
    if kind == "trip-start":
        return 0
    if kind == "trip-end":
        return max(0, total - 1)
    days = {day["dayId"]: day for day in timeline["days"]}
    if kind in {"day-start", "day-arrival", "segment-start", "segment-end", "landmark"}:
        day = days.get(anchor.get("dayId"))
        if day is None:
            raise M2VError(f"音效锚点引用未知天：{anchor.get('dayId')}")
        if kind == "day-start":
            return day["startFrame"]
        if kind == "day-arrival":
            return day["startFrame"] + day["arrivalLocalFrame"]
        if kind in {"segment-start", "segment-end"}:
            window = day["segmentWindows"].get(anchor.get("segmentId"))
            if window is None:
                raise M2VError(f"音效锚点引用未知旁白段：{anchor.get('segmentId')}")
            return window["startFrame"] if kind == "segment-start" else window["endFrame"] - 1
        landmark_id = anchor.get("landmarkId")
        trip_day = next(day for day in docs["days"] if day["id"] == anchor["dayId"])
        if landmark_id not in {item["id"] for item in trip_day["landmarks"]}:
            raise M2VError(f"音效锚点引用未知地标：{landmark_id}")
        route = docs["routes"][anchor["dayId"]]
        index = next(index for index, day in enumerate(docs["days"])
                     if day["id"] == anchor["dayId"])
        geom = layout_module.day_geometry(route, trim_origin=index == 0)
        distance = next(point["distanceMeters"] for point in route["viaPoints"]
                        if point["id"] == landmark_id)
        fraction = min(1.0, max(0.0, distance / max(1.0, geom["length_meters"])))
        return round(day["followStart"] + fraction * (day["arrivalLocalFrame"] - day["followStart"]))
    raise M2VError(f"未知音效锚点类型：{kind}")
