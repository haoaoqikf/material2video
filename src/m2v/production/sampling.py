"""风险步长与强制边界；采样结果不代表帧间运动已经通过。"""
from __future__ import annotations


def sampling_step(cp: dict, *, fps: int = 30, dynamic: bool = False) -> int:
    if 'sampleStep' in cp:
        return cp['sampleStep']
    # 未声明运动节拍时不能把动态风险降为普通保持段。
    if dynamic:
        return cp.get('minEventFrames', 1)
    return min(cp.get('minEventFrames', max(1, fps // 2)), max(1, fps // 2))


def sample_frames(cp: dict, shot: dict, *, fps: int = 30, dynamic: bool = False,
                  event_frames=()) -> list[int]:
    start, end = cp['window']
    step = sampling_step(cp, fps=fps, dynamic=dynamic)
    frames = {cp['frame'], start, end - 1, *range(start, end, step)}
    plans = [*cp['textPlan'], *cp.get('statePlan', []), *shot.get('timeStructure', {}).values()]
    boundaries = [boundary for plan in plans if plan['window'] is not None for boundary in plan['window']]
    for boundary in [*boundaries, *event_frames]:
        frames.update(boundary + offset for offset in (-1, 0, 1) if start <= boundary + offset < end)
    return sorted(frames)
