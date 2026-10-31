"""链式取数：起点衔接、via 定位、原子写入与凭据门禁。"""
from __future__ import annotations

import json

import pytest

from m2v.core.errors import M2VError
from m2v.types.road_trip import fetch as fetch_module
from m2v.types.road_trip import materials
from road_trip_helpers import (DAY1_END, FIXED_NOW, amap_transport, trip_document,
                               write_project)


def _fetch(root, **options):
    return fetch_module.fetch(root, transport=amap_transport, now=FIXED_NOW,
                              district_delay=0, **options)


def test_fetch_chains_days_and_records_via(tmp_path, monkeypatch):
    monkeypatch.setenv("M2V_AMAP_KEY", "test-key")
    root = write_project(tmp_path / "trip", trip_document(map_tiles=True))
    targets = _fetch(root)
    assert len(targets) == 2
    first = json.loads((root / "routes/day-01.json").read_text(encoding="utf-8"))
    second = json.loads((root / "routes/day-02.json").read_text(encoding="utf-8"))
    assert first["route"]["endPoint"] == second["route"]["startPoint"]
    assert first["viaPoints"][0]["id"] == "via-0"
    assert second["origin"] is None
    assert second["start"]["kind"] == "previous-end"
    materials.load_project(root, require_basemap=False)


def test_fetch_requires_gate_before_network(tmp_path, monkeypatch):
    monkeypatch.setenv("M2V_AMAP_KEY", "test-key")
    calls = []

    def transport(url, timeout):
        calls.append(url)
        return 500, b""

    root = write_project(tmp_path / "trip", trip_document(map_tiles=False))
    with pytest.raises(M2VError, match="mapTiles"):
        fetch_module.fetch(root, transport=transport, district_delay=0)
    assert calls == []


def test_fetch_requires_key_before_network(tmp_path, monkeypatch):
    monkeypatch.delenv("M2V_AMAP_KEY", raising=False)
    calls = []

    def transport(url, timeout):
        calls.append(url)
        return 500, b""

    root = write_project(tmp_path / "trip", trip_document(map_tiles=True))
    with pytest.raises(M2VError, match="M2V_AMAP_KEY"):
        fetch_module.fetch(root, transport=transport, district_delay=0)
    assert calls == []


def test_failed_write_restores_all_old_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("M2V_AMAP_KEY", "test-key")
    root = write_project(tmp_path / "trip", trip_document(map_tiles=True))
    before = {path: path.read_bytes() for path in (root / "routes").glob("*.json")}
    original = fetch_module._write_atomic
    writes = {"count": 0}

    def flaky(path, value):
        writes["count"] += 1
        if writes["count"] == 2:
            raise OSError("合成写入失败")
        original(path, value)

    monkeypatch.setattr(fetch_module, "_write_atomic", flaky)
    with pytest.raises(OSError):
        _fetch(root)
    after = {path: path.read_bytes() for path in (root / "routes").glob("*.json")}
    assert after == before


def test_acquisition_records_no_key(tmp_path, monkeypatch):
    monkeypatch.setenv("M2V_AMAP_KEY", "secret-value")
    root = write_project(tmp_path / "trip", trip_document(map_tiles=True))
    _fetch(root)
    for path in (root / "routes").glob("*.json"):
        assert "secret-value" not in path.read_text(encoding="utf-8")


def _gap_transport(url, timeout):
    payload = {
        "status": "1",
        "route": {"paths": [{
            "distance": "4000",
            "cost": {"duration": "600", "tolls": "0", "toll_distance": "0",
                     "traffic_lights": "0"},
            "steps": [
                {"road_name": "城市路", "step_distance": "2000",
                 "polyline": "121.47,31.23;121.475,31.235", "cities": []},
                {"road_name": "G318", "step_distance": "2000",
                 "polyline": "121.4754,31.2354;121.49,31.25", "cities": []},
            ],
        }]},
    }
    return 200, json.dumps(payload).encode()


def test_service_gap_is_bridged_with_connector_step():
    from m2v.core.errors import M2VError
    from m2v.types.driving_route.amap import AmapClient
    client = AmapClient("test", transport=_gap_transport)
    with pytest.raises(M2VError, match="25 米容差"):
        client.drive((121.47, 31.23), (121.49, 31.25))
    result = client.drive((121.47, 31.23), (121.49, 31.25), bridge_gaps=60)
    assert any(step["road"] == "路口连接" for step in result["steps"])
    previous = None
    from m2v.types.route_common import haversine_meters
    for step in result["steps"]:
        first = tuple(step["points"][0])
        if previous is not None:
            assert haversine_meters(previous, first) <= 25
        previous = tuple(step["points"][-1])


def test_trip_change_during_fetch_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("M2V_AMAP_KEY", "test-key")
    root = write_project(tmp_path / "trip", trip_document(map_tiles=True))
    before = {path: path.read_bytes() for path in (root / "routes").glob("*.json")}

    def transport(url, timeout):
        trip_path = root / "trip.json"
        trip = json.loads(trip_path.read_text(encoding="utf-8"))
        trip["days"][0]["narration"][0]["text"] = "取数期间改过的旁白。"
        trip_path.write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
        return amap_transport(url, timeout)

    with pytest.raises(M2VError, match="trip.json 已变化"):
        fetch_module.fetch(root, transport=transport, now=FIXED_NOW, district_delay=0)
    after = {path: path.read_bytes() for path in (root / "routes").glob("*.json")}
    assert after == before
