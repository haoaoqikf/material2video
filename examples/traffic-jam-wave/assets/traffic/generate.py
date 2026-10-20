"""生成交通拥堵波示例的确定性示意轨迹。

这不是交通仿真产品，也不是经过标定的预测模型。它只构造一条闭合环路上
「一辆车轻点刹车、后车依次响应」的预设速度曲线，用来解释一种机制：
所有车辆都在向前行驶，低速区域却沿车队向后移动。

输出 `traffic.json` 同时供画面与图表采样，任何一次生成都应与仓库内文件
逐字节一致；脚本末尾会做以下硬检查，失败即退出：

* 速度不为负；
* 任意两车中心距大于车身长度并保留安全余量；
* 两组只有车辆数量不同，首车减速幅度、起始时刻与持续时间完全相同；
* 低速区域（相对速度低于阈值）确实沿车队向后传播。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

FPS = 60
SAMPLE_HZ = 10  # 关键帧频率；画面按弧长与速度线性插值
DURATION_SECONDS = 60
LOOP = {"rx": 360.0, "ry": 520.0}
CAR = {"length": 46.0, "width": 26.0}
CRUISE = 95.0  # 示意速度，单位是画布像素/秒，不是真实车速
DISTURBANCE = {"start": 7.0, "duration": 2.6, "leaderAmplitude": 0.78}
DELAY_STEP = 0.85  # 每向后退一辆车的响应延迟
BRAKE_RATIO = 0.94  # 相对速度低于此值视为制动灯亮起
SLOW_RATIO = 0.72  # 低速区域阈值
SAFE_GAP = 18.0  # 中心距减去车身长度的最小余量

GROUPS = {
    "high": {"cars": 16, "amplitude": lambda index: min(0.94, 0.78 + 0.012 * index)},
    "low": {"cars": 8, "amplitude": lambda index: 0.78 * (0.78 ** index)},
}


def ellipse_table(samples: int = 1440) -> list[dict]:
    """按累计弧长采样环路：s → 中心线坐标与切线方向。"""
    points = []
    s = 0.0
    previous = None
    for index in range(samples + 1):
        t = 2 * math.pi * index / samples
        x = LOOP["rx"] * math.cos(t)
        y = -LOOP["ry"] * math.sin(t)
        if previous is not None:
            s += math.hypot(x - previous[0], y - previous[1])
        dx, dy = -LOOP["rx"] * math.sin(t), -LOOP["ry"] * math.cos(t)
        points.append({"s": round(s, 4), "x": round(x, 4), "y": round(y, 4),
                       "heading": round(math.atan2(dy, dx), 6)})
        previous = (x, y)
    # 最后一点回到起点，弧长闭合。
    return points


def bump(u: float) -> float:
    """平滑减速脉冲：区间内为 0→1→0 的余弦包络，区间外为 0。"""
    if u <= 0.0 or u >= 1.0:
        return 0.0
    return 0.5 - 0.5 * math.cos(2 * math.pi * u)


def speed_of(group: str, index: int, seconds: float) -> float:
    amplitude = GROUPS[group]["amplitude"](index)
    start = DISTURBANCE["start"] + index * DELAY_STEP
    u = (seconds - start) / DISTURBANCE["duration"]
    return CRUISE * (1.0 - amplitude * bump(u))


def simulate(group: str) -> dict:
    spec = GROUPS[group]
    count = spec["cars"]
    perimeter = ellipse_table()[-1]["s"]
    spacing = perimeter / count
    # 车辆 0 在最前，i 号车位于其后方 i 个间距处；位置使用未取模的累计位移，
    # 便于检查车距。画面上再对环路周长取模。
    positions = [-index * spacing for index in range(count)]
    start_positions = list(positions)
    frames = []
    total_frames = int(DURATION_SECONDS * FPS)
    next_sample = 0.0
    min_gap = float("inf")
    min_speed = float("inf")
    slow_track = []
    for frame in range(total_frames + 1):
        seconds = frame / FPS
        # 以 1/60 秒步长做中点积分，保证速度与位移共用同一时钟。
        for index in range(count):
            mid = seconds + 0.5 / FPS
            positions[index] += speed_of(group, index, mid) / FPS
        for index in range(1, count):
            gap = (positions[index - 1] - positions[index]) - CAR["length"]
            min_gap = min(min_gap, gap)
        speeds = [speed_of(group, index, seconds) for index in range(count)]
        min_speed = min(min_speed, min(speeds))
        slow = [index for index, value in enumerate(speeds) if value < CRUISE * SLOW_RATIO]
        slow_track.append(len(slow) > 0)
        if seconds + 1e-9 >= next_sample:
            frames.append({
                "t": round(seconds, 3),
                # 每辆车：[沿路累计位移（相对第 0 帧），速度]
                "cars": [[round(positions[index] - start_positions[index], 3), round(speeds[index], 3)]
                         for index in range(count)],
            })
            next_sample = round(next_sample + 1 / SAMPLE_HZ, 6)
    return {
        "cars": count,
        "spacing": round(spacing, 3),
        "frames": frames,
        "checks": {
            "minGap": round(min_gap, 3),
            "minSpeed": round(min_speed, 3),
            "slowFrames": sum(slow_track),
        },
    }


def slow_zone_moves_backwards(frames: list[dict]) -> bool:
    """最低速车辆的编号应随响应延迟逐步增大，也就是向车队后方移动。"""
    visited = []
    for frame in frames:
        speeds = [item[1] for item in frame["cars"]]
        minimum = min(range(len(speeds)), key=speeds.__getitem__)
        if speeds[minimum] < CRUISE * SLOW_RATIO:
            visited.append((frame["t"], minimum))
    return bool(visited) and visited[-1][1] > visited[0][1]


def document() -> dict:
    table = ellipse_table()
    perimeter = table[-1]["s"]
    high = simulate("high")
    low = simulate("low")
    for name, data in (("high", high), ("low", low)):
        checks = data["checks"]
        if checks["minGap"] <= SAFE_GAP:
            raise SystemExit(f"{name} 组最小车距不足：{checks['minGap']} ≤ {SAFE_GAP}")
        if checks["minSpeed"] < 0:
            raise SystemExit(f"{name} 组出现负速度：{checks['minSpeed']}")
        if not slow_zone_moves_backwards(data["frames"]):
            raise SystemExit(f"{name} 组低速区域没有向后传播")
    # 两组必须共享同一道路、初速、扰动幅度与持续时间。
    if high["frames"][-1]["cars"][0][1] == 0 or low["frames"][-1]["cars"][0][1] == 0:
        raise SystemExit("轨迹没有回到巡航速度")
    return {
        "schemaVersion": 1,
        "kind": "schematic-preset",
        "note": "预设示意轨迹：车辆向前、低速区域向后；不是测量数据或经过标定的交通预测。",
        "fps": FPS,
        "sampleHz": SAMPLE_HZ,
        "durationSeconds": DURATION_SECONDS,
        "cruise": CRUISE,
        "car": {"length": CAR["length"], "width": CAR["width"]},
        "loop": {"rx": LOOP["rx"], "ry": LOOP["ry"], "perimeter": round(perimeter, 3), "table": table},
        "disturbance": {"start": DISTURBANCE["start"], "duration": DISTURBANCE["duration"],
                        "leaderAmplitude": DISTURBANCE["leaderAmplitude"],
                        "delayPerCar": DELAY_STEP},
        "thresholds": {"brakeRatio": BRAKE_RATIO, "slowRatio": SLOW_RATIO},
        "groups": {"high": high, "low": low},
    }


def main() -> None:
    target = Path(__file__).with_name("traffic.json")
    text = json.dumps(document(), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    target.write_text(text + "\n", encoding="utf-8")
    print(f"写出 {target}（{target.stat().st_size} 字节）")


if __name__ == "__main__":
    main()
