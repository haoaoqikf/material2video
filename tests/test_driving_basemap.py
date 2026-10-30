"""普通道路底图：概览拼接、跟随瓦片走廊、授权门禁、原子保存与离线绑定。"""
from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.types.driving_route import basemap, layout, materials
from driving_helpers import FIXED_NOW, request_document, write_project


def tile_bytes(color=(238, 236, 230)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (256, 256), color).save(buffer, format="PNG")
    return buffer.getvalue()


class TileTransport:
    def __init__(self, *, fail_at: int | None = None, fail_all: bool = False,
                 color=(238, 236, 230)):
        self.urls: list[str] = []
        self.fail_at = fail_at
        self.fail_all = fail_all
        self.color = color

    def __call__(self, url: str, timeout: float) -> tuple[int, bytes]:
        self.urls.append(url)
        if self.fail_all or (self.fail_at is not None and len(self.urls) == self.fail_at):
            return 500, b""
        return 200, tile_bytes(self.color)


def test_fetch_basemap_stitches_overview_and_corridor_tiles(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    transport = TileTransport()
    result = basemap.fetch_basemap(root, transport=transport, now=FIXED_NOW, delay=0)
    assert result["reused"] is False
    assert transport.urls and all("style=8" in url for url in transport.urls)
    route = json.loads((root / "route.json").read_text(encoding="utf-8"))
    block = route["basemap"]
    assert block["provider"] == "amap"
    assert block["service"] == "road-tiles"
    assert block["layoutVersion"] == layout.layout_version() == 4
    assert block["overview"]["zoom"] >= 8
    assert block["followTiles"]["zoom"] >= 9
    overview = root / block["overview"]["image"]["path"]
    assert overview.is_file()
    assert block["overview"]["image"]["width"] > 0
    assert block["overview"]["projected"]["width"] > 0
    tiles = block["followTiles"]["tiles"]
    assert len(tiles) == block["followTiles"]["tileCount"] >= 1
    for tile in tiles:
        image = root / tile["path"]
        assert image.is_file()
        assert tile["width"] == tile["height"] == 256
        with Image.open(image) as opened:
            assert opened.format == "JPEG"
    docs = materials.load_project(root)
    assert set(docs["basemapDataUris"]) == {"overview", "followTiles"}
    assert len(docs["basemapDataUris"]["followTiles"]) == len(tiles)
    props = materials.build_render_props(docs)
    assert props["basemap"]["overview"]["dataUri"].startswith("data:image/jpeg;base64,")
    assert len(props["basemap"]["followTiles"]["tiles"]) == len(tiles)
    assert props["basemap"]["followTiles"]["tiles"][0]["dataUri"].startswith("data:image/jpeg;base64,")


def test_repeated_basemap_reuses_without_network(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    assert basemap.fetch_basemap(root, transport=TileTransport(), now=FIXED_NOW, delay=0)["reused"] is False
    second = TileTransport(fail_at=1)
    result = basemap.fetch_basemap(root, transport=second, now=FIXED_NOW, delay=0)
    assert result["reused"] is True
    assert second.urls == []


def test_basemap_requires_map_tile_authorization(tmp_path):
    request = request_document(map_tiles=True)
    request["sourceUsage"]["mapTiles"] = False
    root = write_project(tmp_path, request=request)
    transport = TileTransport()
    with pytest.raises(M2VError, match="mapTiles"):
        basemap.fetch_basemap(root, transport=transport, now=FIXED_NOW, delay=0)
    assert transport.urls == []


def test_basemap_failure_preserves_old_route_and_has_no_temp_tiles(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    before = (root / "route.json").read_bytes()
    with pytest.raises(M2VError, match="HTTP 500"):
        basemap.fetch_basemap(root, transport=TileTransport(fail_all=True),
                              now=FIXED_NOW, delay=0)
    assert (root / "route.json").read_bytes() == before
    directory = root / "assets" / "basemap"
    assert not directory.exists() or not list(directory.glob("follow-tiles-*"))
    assert not list(directory.glob(".follow-tiles-tmp-*")) if directory.exists() else True
    assert not list(root.glob("*.tmp"))


def test_basemap_rejects_v1_route(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    route = json.loads((root / "route.json").read_text(encoding="utf-8"))
    route["schemaVersion"] = 2
    (root / "route.json").write_text(json.dumps(route), encoding="utf-8")
    with pytest.raises(M2VError, match="必须为 3"):
        basemap.fetch_basemap(root, transport=TileTransport(), now=FIXED_NOW, delay=0)


def test_basemap_overview_hash_drift_is_rejected(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    basemap.fetch_basemap(root, transport=TileTransport(), now=FIXED_NOW, delay=0)
    route = json.loads((root / "route.json").read_text(encoding="utf-8"))
    image = root / route["basemap"]["overview"]["image"]["path"]
    image.write_bytes(tile_bytes((1, 2, 3)))
    with pytest.raises(M2VError, match="摘要不匹配"):
        materials.load_project(root)


def test_follow_tile_hash_drift_is_rejected(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    basemap.fetch_basemap(root, transport=TileTransport(), now=FIXED_NOW, delay=0)
    route = json.loads((root / "route.json").read_text(encoding="utf-8"))
    tile = route["basemap"]["followTiles"]["tiles"][0]
    (root / tile["path"]).write_bytes(tile_bytes((1, 2, 3)))
    with pytest.raises(M2VError, match="瓦片摘要不匹配"):
        materials.load_project(root)


def test_layer_plan_stays_within_tile_and_width_limits():
    route_box = (12_600_000.0, 3_600_000.0, 13_500_000.0, 4_050_000.0)
    zoom, x0, y0, x1, y1, bbox = basemap.layer_plan(
        route_box, half_x=520_000.0, half_y=680_000.0, scale=0.0012, minimum_zoom=8)
    assert zoom >= 8
    assert (x1 - x0 + 1) * (y1 - y0 + 1) <= basemap.MAX_TILES
    assert (x1 - x0 + 1) * basemap.TILE_SIZE <= basemap.MAX_WIDTH
    assert bbox[0] < bbox[2] and bbox[1] < bbox[3]


def test_prepare_with_basemap_is_offline(tmp_path, monkeypatch):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    basemap.fetch_basemap(root, transport=TileTransport(), now=FIXED_NOW, delay=0)
    monkeypatch.delenv("M2V_AMAP_KEY", raising=False)
    assert main(["prepare", "--project", str(root)]) == 0
    prepared = json.loads((root / "outputs" / "prepared.json").read_text(encoding="utf-8"))
    assert prepared["props"]["basemap"]["overview"]["dataUri"].startswith("data:image/jpeg;base64,")
    assert prepared["props"]["basemap"]["followTiles"]["tiles"]
    assert prepared["durationInFrames"] == 900


def test_cli_basemap_wires_the_command(tmp_path, monkeypatch):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    monkeypatch.setattr(basemap, "default_transport", TileTransport())
    assert main(["driving-route", "basemap", "--project", str(root)]) == 0
    route = json.loads((root / "route.json").read_text(encoding="utf-8"))
    assert route["basemap"]["service"] == "road-tiles"


def test_refresh_failure_keeps_old_basemap_images(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    basemap.fetch_basemap(root, transport=TileTransport(), now=FIXED_NOW, delay=0)
    route_before = (root / "route.json").read_bytes()
    route = json.loads(route_before)
    old_images = [root / route["basemap"]["overview"]["image"]["path"]]
    old_images.extend(root / tile["path"] for tile in route["basemap"]["followTiles"]["tiles"])
    with pytest.raises(M2VError, match="HTTP 500"):
        basemap.fetch_basemap(root, transport=TileTransport(fail_all=True),
                              now=FIXED_NOW, delay=0, refresh=True)
    assert (root / "route.json").read_bytes() == route_before
    assert all(image.is_file() for image in old_images)
    assert materials.load_project(root)["route"]["basemap"]["service"] == "road-tiles"


def test_follow_tile_set_must_match_the_corridor_plan(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    basemap.fetch_basemap(root, transport=TileTransport(), now=FIXED_NOW, delay=0)
    route = json.loads((root / "route.json").read_text(encoding="utf-8"))
    follow = route["basemap"]["followTiles"]
    removed = follow["tiles"].pop()
    follow["tileCount"] -= 1
    (root / removed["path"]).unlink()
    (root / "route.json").write_text(json.dumps(route), encoding="utf-8")
    with pytest.raises(M2VError, match="瓦片集合|缺少"):
        materials.load_project(root)


def test_request_change_during_basemap_aborts(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    before = (root / "route.json").read_bytes()

    class MutatingTransport(TileTransport):
        def __call__(self, url: str, timeout: float) -> tuple[int, bytes]:
            data = json.loads((root / "request.json").read_text(encoding="utf-8"))
            data["destination"]["label"] = "郑州"
            (root / "request.json").write_text(json.dumps(data), encoding="utf-8")
            return super().__call__(url, timeout)

    with pytest.raises(M2VError, match="request.json 已变化"):
        basemap.fetch_basemap(root, transport=MutatingTransport(), now=FIXED_NOW, delay=0)
    assert (root / "route.json").read_bytes() == before


def test_route_change_during_basemap_aborts(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))

    class MutatingTransport(TileTransport):
        def __call__(self, url: str, timeout: float) -> tuple[int, bytes]:
            route_path = root / "route.json"
            data = json.loads(route_path.read_text(encoding="utf-8"))
            data["route"]["distanceMeters"] += 1
            route_path.write_text(json.dumps(data), encoding="utf-8")
            return super().__call__(url, timeout)

    with pytest.raises(M2VError, match="route.json 已变化"):
        basemap.fetch_basemap(root, transport=MutatingTransport(), now=FIXED_NOW, delay=0)


def test_layout_version_mismatch_is_rejected(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    basemap.fetch_basemap(root, transport=TileTransport(), now=FIXED_NOW, delay=0)
    route = json.loads((root / "route.json").read_text(encoding="utf-8"))
    route["basemap"]["layoutVersion"] = 3
    (root / "route.json").write_text(json.dumps(route), encoding="utf-8")
    with pytest.raises(M2VError, match="布局版本不匹配"):
        materials.load_project(root)


def test_old_layout_is_not_reused(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    basemap.fetch_basemap(root, transport=TileTransport(), now=FIXED_NOW, delay=0)
    route = json.loads((root / "route.json").read_text(encoding="utf-8"))
    route["basemap"]["layoutVersion"] = 3
    (root / "route.json").write_text(json.dumps(route), encoding="utf-8")
    transport = TileTransport()
    result = basemap.fetch_basemap(root, transport=transport, now=FIXED_NOW, delay=0)
    assert result["reused"] is False
    assert transport.urls


def test_satellite_basemap_uses_style_6_and_validates(tmp_path):
    root = write_project(tmp_path, request=request_document(map_tiles=True))
    transport = TileTransport()
    result = basemap.fetch_basemap(root, transport=transport, now=FIXED_NOW, delay=0,
                                   style="satellite")
    assert result["reused"] is False
    assert transport.urls and all("style=6" in url for url in transport.urls)
    route = json.loads((root / "route.json").read_text(encoding="utf-8"))
    assert route["basemap"]["service"] == "satellite-tiles"
    assert route["basemap"]["overview"]["request"]["params"]["style"] == "6"
    assert route["basemap"]["followTiles"]["request"]["params"]["style"] == "6"
    materials.load_project(root)
