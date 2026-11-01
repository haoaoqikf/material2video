"""每日底图：全局/每日概览、走廊、复用与样式切换。"""
from __future__ import annotations

import json

import pytest

from m2v.core.errors import M2VError
from m2v.types.road_trip import basemap, materials
from helpers.road_trip import FIXED_NOW, amap_transport, tile_transport, trip_document, write_project


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("M2V_AMAP_KEY", "test-key")
    root = write_project(tmp_path / "trip", trip_document(map_tiles=True))
    from m2v.types.road_trip.fetch import fetch
    fetch(root, transport=amap_transport, now=FIXED_NOW, district_delay=0)
    return root


def _basemap(root, **options):
    return basemap.fetch_basemap(root, transport=tile_transport, now=FIXED_NOW,
                                 delay=0, **options)


def test_basemap_generates_global_and_daily_layers(project):
    result = _basemap(project)
    assert result["reused"] is False
    index = json.loads((project / materials.BASEMAP_INDEX).read_text(encoding="utf-8"))
    assert set(index["days"]) == {"day-01", "day-02"}
    assert index["days"]["day-01"]["followTiles"]["tileCount"] > 0
    materials.load_project(project)


def test_basemap_is_reused_without_new_tiles(project):
    _basemap(project)
    calls = []

    def transport(url, timeout):
        calls.append(url)
        return tile_transport(url, timeout)

    result = basemap.fetch_basemap(project, transport=transport, now=FIXED_NOW, delay=0)
    assert result["reused"] is True
    assert calls == []


def test_missing_tile_is_reported(project):
    _basemap(project)
    index = json.loads((project / materials.BASEMAP_INDEX).read_text(encoding="utf-8"))
    tile = index["days"]["day-01"]["followTiles"]["tiles"][0]
    (project / tile["path"]).unlink()
    with pytest.raises(M2VError, match="瓦片不存在"):
        materials.load_project(project)


def test_per_day_satellite_style(project):
    trip = json.loads((project / "trip.json").read_text(encoding="utf-8"))
    trip["days"][1]["basemapStyle"] = "satellite"
    (project / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    _basemap(project)
    index = json.loads((project / materials.BASEMAP_INDEX).read_text(encoding="utf-8"))
    assert index["days"]["day-02"]["style"] == "satellite"
    assert index["days"]["day-02"]["service"] == "satellite-tiles"
    assert index["days"]["day-01"]["style"] == "road"
    materials.load_project(project)


def test_unauthorized_tiles_fail_before_fetch(project):
    trip = json.loads((project / "trip.json").read_text(encoding="utf-8"))
    trip["sourceUsage"]["mapTiles"] = False
    (project / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    calls = []

    def transport(url, timeout):
        calls.append(url)
        return tile_transport(url, timeout)

    with pytest.raises(M2VError, match="未获授权"):
        basemap.fetch_basemap(project, transport=transport, delay=0)
    assert calls == []
