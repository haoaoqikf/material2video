"""road-trip 类型身份、固定帧率与程序化音床。"""
from __future__ import annotations

import hashlib
import json

from m2v.cli import main
from m2v.core.video_config import default_fps
from m2v.type_system import catalog, registry
from m2v.types.road_trip import ambient


def test_type_is_registered_and_documented():
    assert main(["types"]) == 0
    entry = catalog.catalog().get("road-trip")
    assert entry.description == "多日地图游记"
    assert entry.material_map() == {"trip": "trip.json"}
    assert registry.get("road-trip").name == "road-trip"


def test_fixed_fps_is_30():
    assert default_fps("road-trip") == 30
    assert default_fps("driving-route") == 30


def test_init_project_output_is_vertical_30fps(tmp_path):
    assert main(["init", "--type", "road-trip", "--project", str(tmp_path / "demo")]) == 0
    project = json.loads((tmp_path / "demo/project.json").read_text(encoding="utf-8"))
    assert project["output"] == {"width": 1080, "height": 1920, "fps": 30, "audio": "optional"}
    trip = json.loads((tmp_path / "demo/trip.json").read_text(encoding="utf-8"))
    assert trip["schemaVersion"] == 1
    assert trip["days"][0]["route"] == "routes/day-01.json"


def test_ambient_bed_is_deterministic_and_seamless(tmp_path):
    first = tmp_path / "a.wav"
    second = tmp_path / "b.wav"
    record_one = ambient.synthesize(first)
    record_two = ambient.synthesize(second)
    assert hashlib.sha256(first.read_bytes()).hexdigest() == \
        hashlib.sha256(second.read_bytes()).hexdigest()
    assert record_one == record_two
    assert record_one["loopSeconds"] == 30.0
    assert record_one["license"].startswith("CC0")
    assert ambient.verify(first)["sha256"] == record_one["sha256"]
