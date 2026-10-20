"""量测示意轨迹：车距、低速带传播与密度响应。

输出是制作复核证据，不参与渲染。用法：

    uv run python examples/traffic-jam-wave/scripts/verify-trajectory.py

默认写入作品的 `outputs/verification/trajectory-report.json`（忽略目录）。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1]
DATA = EXAMPLE / "assets/traffic/traffic.json"


def slowest_index(speeds: list[float]) -> int:
    return min(range(len(speeds)), key=speeds.__getitem__)


def measure_group(group: dict, threshold: float, spacing: float, cruise: float) -> dict:
    positions = []
    slow = []
    peak = {"index": None, "ratio": 1.0, "time": None}
    probe = min(5, group["cars"] - 1)
    probe_ratio = 1.0
    for frame in group["frames"]:
        speeds = [item[1] for item in frame["cars"]]
        absolute = [-index * spacing + item[0] for index, item in enumerate(frame["cars"])]
        positions.append(absolute)
        probe_ratio = min(probe_ratio, speeds[probe] / cruise)
        index = slowest_index(speeds)
        ratio = speeds[index] / cruise
        if ratio < peak["ratio"]:
            peak = {"index": index + 1, "ratio": round(ratio, 4), "time": frame["t"]}
        if speeds[index] < threshold:
            slow.append((frame["t"], index))
    gaps = []
    for frame_positions in positions:
        gaps.extend(frame_positions[index - 1] - frame_positions[index]
                    for index in range(1, len(frame_positions)))
    first, last = slow[0], slow[-1]
    seconds = last[0] - first[0]
    backward = (last[1] - first[1]) * spacing / seconds if seconds > 0 else 0.0
    return {
        "cars": group["cars"],
        "spacingPx": round(spacing, 2),
        "minCenterGapPx": round(min(gaps), 2),
        "slowWindowSeconds": [first[0], last[0]],
        "slowestCarStart": first[1] + 1,
        "slowestCarEnd": last[1] + 1,
        "backwardPxPerSecond": round(backward, 2),
        "peakSlowdown": peak,
        "sixthCarMinSpeedRatio": round(probe_ratio, 4),
    }


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    threshold = data["cruise"] * data["thresholds"]["slowRatio"]
    high = measure_group(data["groups"]["high"], threshold, data["groups"]["high"]["spacing"], data["cruise"])
    low = measure_group(data["groups"]["low"], threshold, data["groups"]["low"]["spacing"], data["cruise"])
    table = data["loop"]["table"]
    monotonic = all(b["s"] > a["s"] for a, b in zip(table, table[1:]))
    closed = math.isclose(table[0]["x"], table[-1]["x"], abs_tol=1e-6) and \
        math.isclose(table[0]["y"], table[-1]["y"], abs_tol=1e-6)
    report = {
        "schemaVersion": 1,
        "source": "assets/traffic/traffic.json",
        "note": "预设示意轨迹，不是实测或交通预测。",
        "loop": {"perimeterPx": data["loop"]["perimeter"], "arcLengthMonotonic": monotonic,
                 "closed": closed},
        "disturbance": data["disturbance"],
        "groups": {"high": high, "low": low},
        "densityContrast": {
            "slowestCarHigh": high["peakSlowdown"],
            "slowestCarLow": low["peakSlowdown"],
            "sixthCarMinSpeedRatioHigh": high["sixthCarMinSpeedRatio"],
            "sixthCarMinSpeedRatioLow": low["sixthCarMinSpeedRatio"],
        },
    }
    target = EXAMPLE / "outputs/verification/trajectory-report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
