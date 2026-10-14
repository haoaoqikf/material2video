"""把检索结果编译成帧精确时间轴：时长分配、幕间转场与静图运动。

自动剪辑的可复算部分全部在这里：同一份 brief 与同一批素材必须得到同一条时间轴，
因此这里不使用随机数、不读当前时间，也不依赖素材的下载顺序。

时长分配规则（写进类型参考文档）：

1. 声明口播的幕由真实语音时长决定；声明固定帧数的幕用固定帧数；
2. 其余幕均分「目标总时长 − 已确定幕」的余量，夹在
   ``provider.minClipSeconds``/``maxClipSeconds`` 与素材自身可用时长之间；
3. 余数按幕顺序逐帧补齐或扣减，使总时长尽量等于目标；
4. 最后校验全片时长与目标时长的偏差不超过 ``durationToleranceSeconds``。
"""
from __future__ import annotations

import math
from typing import Any

from m2v.core.errors import M2VError


def overlaps(brief: dict[str, Any]) -> list[int]:
    """每一幕声明的入场转场帧数（硬切为 0）。"""
    result = []
    for scene in brief["scenes"]:
        transition = scene.get("transition") or {"type": "cut"}
        kind = transition.get("type", "cut")
        result.append(int(transition.get("frames", 12 if kind == "crossfade" else 0)))
    return result


def trim_start_frames(scene: dict[str, Any], fps: int) -> int:
    return int(round(float(scene.get("trimStartSeconds", 0)) * fps))


def asset_capacity(asset: dict[str, Any], trim_frames: int, fps: int) -> int | None:
    """素材可裁剪的帧数；静图不受限（None）。"""
    if asset["kind"] != "video":
        return None
    total = int(math.floor(float(asset["durationSeconds"]) * fps))
    capacity = total - trim_frames
    if capacity < 1:
        raise M2VError(
            f"素材可用时长不足：{asset['path']} 共 {asset['durationSeconds']:.2f} 秒，"
            f"裁剪入点已到 {trim_frames / fps:.2f} 秒")
    return capacity


def allocate(brief: dict[str, Any], assets: list[dict[str, Any]], trims: list[int],
             resolved: list[int | None]) -> list[int]:
    """补全未确定时长的幕；已确定（口播或固定帧数）的幕原样保留。"""
    fps = brief["fps"]
    config = brief["provider"]
    minimum = int(round(config["minClipSeconds"] * fps))
    maximum = int(round(config["maxClipSeconds"] * fps))
    # 幕间重叠会让成片比各幕之和短，因此分配目标要把重叠加回去，
    # 编译后的总时长才会落在目标上。
    target = int(round(brief["targetSeconds"] * fps)) + sum(overlaps(brief))
    frames = list(resolved)
    auto = [index for index, value in enumerate(frames) if value is None]
    if not auto:
        return [int(value) for value in frames]
    fixed_total = sum(int(value) for value in frames if value is not None)
    remaining = target - fixed_total
    if remaining < len(auto):
        raise M2VError(
            f"已确定时长的幕占用 {fixed_total / fps:.2f} 秒，超过目标时长 "
            f"{brief['targetSeconds']} 秒；请提高 targetSeconds 或缩短口播")
    base = remaining / len(auto)
    assigned: dict[int, int] = {}
    for index in auto:
        capacity = asset_capacity(assets[index], trims[index], fps)
        cap = maximum if capacity is None else min(maximum, capacity)
        if cap < minimum:
            raise M2VError(
                f"幕 {brief['scenes'][index]['id']} 的素材可用时长只有 {cap / fps:.2f} 秒，"
                f"低于 provider.minClipSeconds={config['minClipSeconds']} 秒；请换更长的素材或调低最小时长")
        assigned[index] = max(minimum, min(cap, int(round(base))))
    diff = remaining - sum(assigned.values())
    order = list(auto)
    # 余数逐帧补齐：先按幕顺序加，直到没有余量或都到上限；不足时反向逐帧扣。
    while diff > 0:
        progressed = False
        for index in order:
            capacity = asset_capacity(assets[index], trims[index], fps)
            cap = maximum if capacity is None else min(maximum, capacity)
            if assigned[index] < cap:
                assigned[index] += 1
                diff -= 1
                progressed = True
                if diff == 0:
                    break
        if not progressed:
            break
    while diff < 0:
        progressed = False
        for index in reversed(order):
            if assigned[index] > minimum:
                assigned[index] -= 1
                diff += 1
                progressed = True
                if diff == 0:
                    break
        if not progressed:
            break
    for index, value in assigned.items():
        frames[index] = value
    return [int(value) for value in frames]


def compile_scenes(brief: dict[str, Any], frames: list[int]) -> tuple[list[dict[str, Any]], int]:
    """按幕顺序编译起止帧与转场重叠；重叠越界一律失败，不做静默裁剪。"""
    compiled: list[dict[str, Any]] = []
    cursor = 0
    for index, scene in enumerate(brief["scenes"]):
        duration = frames[index]
        transition = scene.get("transition") or {"type": "cut"}
        kind = transition.get("type", "cut")
        overlap = int(transition.get("frames", 12 if kind == "crossfade" else 0))
        if kind == "cut" and overlap:
            raise M2VError(f"幕 {scene['id']} 硬切不允许重叠帧")
        if overlap >= duration:
            raise M2VError(f"幕 {scene['id']} 的转场重叠 {overlap} 帧不小于该幕时长 {duration} 帧")
        if index == 0 and overlap:
            raise M2VError("首幕不能声明入场转场")
        if compiled and overlap >= compiled[-1]["durationInFrames"]:
            raise M2VError(f"幕 {scene['id']} 的淡化不能超过前一幕时长")
        if compiled and overlap + compiled[-1]["transitionFrames"] >= compiled[-1]["durationInFrames"]:
            raise M2VError("相邻交叉淡化导致三幕同时重叠")
        start = cursor - overlap
        compiled.append({"id": scene["id"], "durationInFrames": duration, "startFrame": start,
                         "endFrame": start + duration, "transitionFrames": overlap})
        cursor = start + duration
    return compiled, cursor


def check_total(brief: dict[str, Any], total_frames: int) -> None:
    fps = brief["fps"]
    target = brief["targetSeconds"]
    tolerance = brief["durationToleranceSeconds"]
    actual = total_frames / fps
    if abs(actual - target) > tolerance + 1e-9:
        raise M2VError(
            f"全片时长 {actual:.2f} 秒超出目标 {target} 秒的 ±{tolerance} 秒容差；"
            f"请调整 targetSeconds、逐幕口播或 provider.minClipSeconds/maxClipSeconds")


def motion_for(index: int, photo_zoom: float) -> dict[str, float]:
    """静图推拉平移：缩放方向逐幕交替，平移方向按 4 幕一轮，全部确定性。"""
    zoom_in = index % 2 == 0
    pans = ((0.0, 0.0, -0.02, 0.0), (0.0, 0.0, 0.02, 0.0),
            (0.0, -0.015, 0.0, 0.015), (0.0, 0.015, 0.0, -0.015))
    pan_x_from, pan_y_from, pan_x_to, pan_y_to = pans[index % len(pans)]
    return {"zoomFrom": 1.0 if zoom_in else photo_zoom,
            "zoomTo": photo_zoom if zoom_in else 1.0,
            "panXFrom": pan_x_from, "panXTo": pan_x_to,
            "panYFrom": pan_y_from, "panYTo": pan_y_to}
