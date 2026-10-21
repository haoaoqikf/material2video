"""交通拥堵波示例的轨迹是确定性预设：可重复、无穿车、方向正确。"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/traffic-jam-wave"
GENERATOR = EXAMPLE / "assets/traffic/generate.py"
DATA = EXAMPLE / "assets/traffic/traffic.json"


def _generator():
    spec = importlib.util.spec_from_file_location("traffic_generator", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated() -> dict:
    return _generator().document()


@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_committed_data_matches_a_fresh_generation(generated: dict, committed: dict) -> None:
    """仓库里的轨迹必须能由脚本逐值重现，避免手改数据与来源脱节。"""
    assert generated == committed


def test_groups_only_differ_in_density(committed: dict) -> None:
    high, low = committed["groups"]["high"], committed["groups"]["low"]
    assert high["cars"] > low["cars"]
    assert high["spacing"] < low["spacing"]
    assert committed["disturbance"]["leaderAmplitude"] == 0.78
    assert committed["disturbance"]["duration"] == 2.6
    # 两组首车走同一条速度曲线：相同初速、幅度与持续时间。
    assert high["frames"][1]["cars"][0] == low["frames"][1]["cars"][0]


def test_no_collision_or_negative_speed(committed: dict) -> None:
    car_length = committed["car"]["length"]
    for name, group in committed["groups"].items():
        spacing = group["spacing"]
        assert group["checks"]["minSpeed"] >= 0, f"{name} 出现负速度"
        for frame in group["frames"]:
            speeds = [item[1] for item in frame["cars"]]
            # 关键帧保存的是相对第 0 帧的位移，绝对位置还要加上初始间距。
            positions = [-index * spacing + item[0] for index, item in enumerate(frame["cars"])]
            gaps = [positions[index - 1] - positions[index] for index in range(1, len(positions))]
            assert min(gaps) - car_length > 18, f"{name} 在 {frame['t']} 秒穿车"
            assert min(speeds) >= 0


def test_slow_zone_moves_backwards(committed: dict) -> None:
    threshold = committed["cruise"] * committed["thresholds"]["slowRatio"]
    visited = []
    for frame in committed["groups"]["high"]["frames"]:
        speeds = [item[1] for item in frame["cars"]]
        slowest = min(range(len(speeds)), key=speeds.__getitem__)
        if speeds[slowest] < threshold:
            visited.append((frame["t"], slowest))
    assert visited, "高密度组没有出现低速区域"
    assert visited[-1][1] > visited[0][1], "低速区域没有向车队后方移动"


def test_keyframes_follow_the_declared_cadence(committed: dict) -> None:
    """画面按固定 10 Hz 关键帧插值，时间戳必须精确对应，不能靠墙钟补齐。"""
    hz = committed["sampleHz"]
    for name, group in committed["groups"].items():
        frames = group["frames"]
        assert len(frames) == committed["durationSeconds"] * hz + 1
        assert all(frame["t"] == round(index / hz, 3) for index, frame in enumerate(frames))
        assert len(frames[130]["cars"]) == group["cars"]


def test_scene_code_derives_lights_and_curves_from_the_same_data() -> None:
    """制动灯与图表必须从速度采样派生，不能另写一套曲线或手点亮灯。"""
    traffic = (EXAMPLE / "scenes/traffic.ts").read_text(encoding="utf-8")
    assert "brake: speed < cruise * TRAFFIC.thresholds.brakeRatio" in traffic
    scenes = list((EXAMPLE / "scenes").glob("*.tsx"))
    assert scenes
    for scene in scenes:
        source = scene.read_text(encoding="utf-8")
        assert "Math.random" not in source and "Date.now" not in source
    film = (EXAMPLE / "scenes/film.tsx").read_text(encoding="utf-8")
    assert "car.brake" in film, "film.tsx 没有使用轨迹里的制动状态"
    assert "curve('high'" in film and "curve('low'" in film
    assert "sample(group" in (EXAMPLE / "scenes/traffic.ts").read_text(encoding="utf-8") \
        or "sample(group" in film, "曲线没有从统一采样生成"
