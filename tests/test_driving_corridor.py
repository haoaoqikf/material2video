"""跟随瓦片走廊：计划摘要、逐帧覆盖与超限失败。"""
from __future__ import annotations

import pytest

from m2v.core.errors import M2VError
from m2v.types.driving_route import layout
from driving_helpers import request_document, route_document


def test_corridor_plan_is_stable_and_covers_every_follow_frame():
    route = route_document(request_document())
    first = layout.corridor_plan(route, 60, 30, 12)
    second = layout.corridor_plan(route, 60, 30, 12)
    assert first["tileCount"] > 0
    assert first["planDigest"] == second["planDigest"]
    assert first["tiles"] == second["tiles"]
    stored = {(tile["x"], tile["y"]) for tile in first["tiles"]}
    assert layout.missing_corridor_tiles(route, 60, 30, 12, stored) == set()
    for tile in first["tiles"]:
        assert tile["projected"] == layout.tile_projected_rect(tile["x"], tile["y"], 12)
    assert layout.MAX_CORRIDOR_TILES == 2200


def test_missing_corridor_tile_is_reported():
    route = route_document(request_document())
    plan = layout.corridor_plan(route, 60, 30, 12)
    stored = {(tile["x"], tile["y"]) for tile in plan["tiles"]}
    removed = stored.pop()
    assert layout.missing_corridor_tiles(route, 60, 30, 12, stored) == {removed}


def test_corridor_limit_fails_without_downgrading_zoom():
    route = route_document(request_document())
    with pytest.raises(M2VError, match="超过上限.*不得静默降低缩放级别"):
        layout.corridor_plan(route, 60, 30, 12, max_tiles=0)


def test_corridor_plan_depends_on_duration():
    route = route_document(request_document())
    assert layout.corridor_plan(route, 30, 30, 12)["planDigest"] != \
        layout.corridor_plan(route, 60, 30, 12)["planDigest"]
