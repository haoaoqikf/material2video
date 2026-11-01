"""多日地图游记材料契约：编排材料、链式路线与来源绑定。"""
from __future__ import annotations

import json

import pytest

from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.types.road_trip import materials
from helpers.road_trip import DAY1_END, write_project


def _load(root):
    return materials.load_project(root)


def test_init_writes_trip_template_and_rejects_placeholders(tmp_path):
    assert main(["init", "--type", "road-trip", "--project", str(tmp_path / "demo")]) == 0
    root = tmp_path / "demo"
    manifest = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert manifest["type"] == "road-trip"
    assert manifest["materials"] == {"trip": "trip.json"}
    assert (root / "trip.json").is_file()
    assert manifest["output"]["fps"] == 30
    with pytest.raises(M2VError, match="占位"):
        materials.load_request(root)


def test_valid_two_day_material_loads(tmp_path):
    root = write_project(tmp_path / "trip")
    docs = _load(root)
    assert [day["id"] for day in docs["days"]] == ["day-01", "day-02"]
    assert docs["routes"]["day-02"]["route"]["startPoint"] == list(DAY1_END)


def test_hand_written_derived_field_is_rejected(tmp_path):
    root = write_project(tmp_path / "trip")
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    trip["totalDistanceMeters"] = 500000
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="totalDistanceMeters"):
        materials.load_request(root)


def test_fact_without_source_is_rejected(tmp_path):
    root = write_project(tmp_path / "trip")
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    trip["days"][0]["cards"] = [{"id": "card", "title": "数据", "facts": [
        {"id": "alt", "label": "海拔", "value": "4298 米"}]}]
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="没有来源"):
        materials.load_request(root)


def test_unknown_source_reference_is_rejected(tmp_path):
    root = write_project(tmp_path / "trip")
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    trip["days"][0]["cards"] = [{"id": "card", "title": "数据", "facts": [
        {"id": "alt", "label": "海拔", "value": "4298 米", "sourceId": "missing"}]}]
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="未知来源"):
        materials.load_request(root)


def test_narration_is_required(tmp_path):
    root = write_project(tmp_path / "trip")
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    trip["days"][0]["narration"] = []
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="1～24"):
        materials.load_request(root)


def test_chain_gap_over_one_meter_is_rejected(tmp_path):
    root = write_project(tmp_path / "trip")
    route = json.loads((root / "routes/day-02.json").read_text(encoding="utf-8"))
    route["route"]["steps"][0]["points"][0] = [DAY1_END[0] + 0.0002, DAY1_END[1]]
    route["route"]["startPoint"] = route["route"]["steps"][0]["points"][0]
    (root / "routes/day-02.json").write_text(json.dumps(route, ensure_ascii=False),
                                             encoding="utf-8")
    with pytest.raises(M2VError, match="1 米"):
        _load(root)


def test_narration_change_does_not_invalidate_routes(tmp_path):
    root = write_project(tmp_path / "trip")
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    trip["days"][0]["narration"][0]["text"] = "改过的旁白，仍然有效。"
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    _load(root)


def test_via_change_invalidates_route(tmp_path):
    root = write_project(tmp_path / "trip")
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    trip["days"][0]["via"][0]["address"] = "换了途经点地址"
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="via 一致"):
        _load(root)


@pytest.mark.parametrize("file,version", [("trip.json", 0), ("routes/day-01.json", 2)])
def test_unsupported_schema_version_is_rejected(tmp_path, file, version):
    root = write_project(tmp_path / "trip")
    data = json.loads((root / file).read_text(encoding="utf-8"))
    data["schemaVersion"] = version
    (root / file).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="schemaVersion"):
        _load(root)


def test_route_beyond_trip_directory_is_rejected(tmp_path):
    root = write_project(tmp_path / "trip")
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    trip["days"][0]["route"] = "../outside.json"
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="routes/day-01.json"):
        materials.load_request(root)


def test_manifest_requires_trip_material(tmp_path):
    root = write_project(tmp_path / "trip")
    manifest = json.loads((root / "project.json").read_text(encoding="utf-8"))
    manifest["materials"] = {"request": "request.json"}
    (root / "project.json").write_text(json.dumps(manifest, ensure_ascii=False),
                                      encoding="utf-8")
    from m2v.types.road_trip import adapter
    with pytest.raises(M2VError, match="trip.json"):
        adapter.validate(root, manifest)


def test_effects_must_use_exactly_one_source(tmp_path):
    root = write_project(tmp_path / "trip")
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    trip["effects"] = [{"id": "e", "anchor": {"kind": "trip-start"}, "builtin": "transition",
                        "assetId": "click"}]
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="四选一"):
        materials.load_request(root)
