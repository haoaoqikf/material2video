"""地理数学：成熟库与项目既有口径逐值一致。"""
from __future__ import annotations

import math

import mercantile
import pytest

from m2v.core.geodesy import distance_meters
from m2v.types.driving_route import geometry


def test_web_mercator_matches_mercantile():
    lng, lat = 121.4737, 31.2304
    assert geometry.project(lng, lat) == tuple(mercantile.xy(lng, lat))
    back = geometry.unproject(*geometry.project(lng, lat))
    assert back[0] == pytest.approx(121.4737)
    assert back[1] == pytest.approx(31.2304)


def test_spherical_distance_matches_haversine_formula():
    a, b = (121.4737, 31.2304), (121.5, 31.25)
    lng1, lat1 = math.radians(a[0]), math.radians(a[1])
    lng2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    expected = 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(h)))
    assert distance_meters(a, b) == pytest.approx(expected, abs=1e-6)


def test_tile_index_is_fractional_and_ranges_are_inclusive():
    assert geometry.tile_x(121.4737, 12) == pytest.approx(3430.100764444538)
    assert geometry.tile_y(31.2304, 12) == pytest.approx(1673.640856432246)
    assert geometry.tile_range((121.3, 31.1, 121.6, 31.4), 12) == (3428, 1671, 3431, 1675)
