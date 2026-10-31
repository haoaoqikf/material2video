"""每日帧分配：口播优先、里程加权与确定性。"""
from __future__ import annotations

import json

import pytest

from m2v.core.errors import M2VError
from m2v.types.road_trip import layout as layout_module
from m2v.types.road_trip import materials, timeline
from road_trip_helpers import write_project


def _docs(root):
    return materials.load_project(root)


def test_allocation_is_deterministic(tmp_path):
    docs = _docs(write_project(tmp_path / "trip"))
    measured = {"day-01": [2.0], "day-02": [2.0]}
    first = timeline.allocate(docs, measured)
    second = timeline.allocate(docs, measured)
    assert first == second
    assert first["totalFrames"] == 60 * 30


def test_remainder_is_distributed_by_distance(tmp_path):
    docs = _docs(write_project(tmp_path / "trip"))
    measured = {"day-01": [2.0], "day-02": [2.0]}
    result = timeline.allocate(docs, measured)
    assert result["days"][0]["durationInFrames"] != result["days"][1]["durationInFrames"]


def test_narration_is_never_truncated(tmp_path):
    docs = _docs(write_project(tmp_path / "trip"))
    trip = docs["trip"]
    trip["targetSeconds"] = 60
    measured = {"day-01": [40.0], "day-02": [40.0]}
    result = timeline.allocate(docs, measured)
    minimum = sum(shots["durationInFrames"] for shots in result["days"])
    assert minimum > 60 * 30
    for day in result["days"]:
        window = day["segmentWindows"]
        assert window
        assert max(item["endFrame"] for item in window.values()) < day["startFrame"] + day["arrivalLocalFrame"]


def test_over_600_seconds_fails(tmp_path):
    root = write_project(tmp_path / "trip")
    docs = _docs(root)
    docs["trip"]["targetSeconds"] = 540
    measured = {"day-01": [320.0], "day-02": [320.0]}
    with pytest.raises(M2VError, match="600 秒"):
        timeline.allocate(docs, measured)


def test_narration_anchor_aligns_to_landmark(tmp_path):
    root = write_project(tmp_path / "trip")
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    day = trip["days"][0]
    day["landmarks"] = [{"id": "mid", "label": "合成中", "viaIndex": 0}]
    day["narration"] = [{"id": "day-01-a", "text": "开场。"},
                        {"id": "day-01-b", "text": "到达途中。",
                         "anchor": {"kind": "landmark", "landmarkId": "mid"}}]
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    route_path = root / "routes/day-01.json"
    route = json.loads(route_path.read_text(encoding="utf-8"))
    source = next(point for point in route["viaPoints"] if point["id"] == "via-0")
    route["viaPoints"].append({"id": "mid", "name": "合成中",
                               "location": source["location"], "point": source["point"],
                               "distanceMeters": source["distanceMeters"]})
    route_path.write_text(json.dumps(route, ensure_ascii=False), encoding="utf-8")
    docs = materials.load_project(root)
    result = timeline.allocate(docs, {"day-01": [1.0, 1.0], "day-02": [1.0]})
    day_result = result["days"][0]
    window = day_result["segmentWindows"]["day-01-b"]
    spans = layout_module.day_spans(day_result["durationInFrames"], 30)
    route_geom = layout_module.day_geometry(docs["routes"]["day-01"], trim_origin=True)
    fraction = min(1.0, source["distanceMeters"] / route_geom["length_meters"])
    target = spans["follow_start"] + fraction * (spans["arrival_frame"] - spans["follow_start"])
    # 锚点可以略早开口以让出到达停留，但不会晚于地标跨越点。
    assert window["localStart"] <= target + 2
    assert target - window["localStart"] <= 30 + 30 + 2


def test_unknown_anchor_landmark_is_rejected(tmp_path):
    root = write_project(tmp_path / "trip")
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    trip["days"][0]["narration"] = [{"id": "a", "text": "开场。"},
                                    {"id": "b", "text": "到达。",
                                     "anchor": {"kind": "landmark", "landmarkId": "missing"}}]
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="未知地标"):
        materials.load_request(root)


def test_anchor_resolution(tmp_path):
    root = write_project(tmp_path / "trip")
    docs = _docs(root)
    result = timeline.allocate(docs, {"day-01": [2.0], "day-02": [2.0]})
    assert timeline.resolve_anchor({"kind": "trip-start"}, result, docs) == 0
    assert timeline.resolve_anchor({"kind": "trip-end"}, result, docs) == result["totalFrames"] - 1
    day = result["days"][0]
    assert timeline.resolve_anchor({"kind": "day-start", "dayId": "day-01"}, result, docs) == day["startFrame"]
    assert timeline.resolve_anchor({"kind": "day-arrival", "dayId": "day-01"}, result, docs) == (
        day["startFrame"] + day["arrivalLocalFrame"])
    segment = timeline.resolve_anchor(
        {"kind": "segment-start", "dayId": "day-01", "segmentId": "day-01-opening"}, result, docs)
    assert segment == day["segmentWindows"]["day-01-opening"]["startFrame"]
    with pytest.raises(M2VError, match="未知旁白段"):
        timeline.resolve_anchor(
            {"kind": "segment-start", "dayId": "day-01", "segmentId": "missing"}, result, docs)
