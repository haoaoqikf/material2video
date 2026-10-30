"""自驾路线取数：凭据隔离、授权前置、失败不破坏旧材料与原子保存。"""
from __future__ import annotations

import json

import pytest

from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.core.project import create_project
from m2v.types.driving_route import fetch as fetch_module
from m2v.types.driving_route import materials
from driving_helpers import (
    DESTINATION, FIXED_NOW, MIDDLE, ORIGIN, edit, request_document, write_project,
)

KEY = "TEST-ONLY-FAKE-VALUE"


def geocode_payload(location, *, city="上海市", level="兴趣点", count=1):
    entry = {
        "formatted_address": "上海市黄浦区合成地点",
        "province": "上海市",
        "city": city,
        "district": "黄浦区",
        "location": f"{location[0]},{location[1]}",
        "level": level,
    }
    return {"status": "1", "info": "OK", "infocode": "10000", "count": str(count),
            "geocodes": [entry] * count}


def drive_payload(points, *, distance="5000", road="沪蓉高速", steps=None):
    if steps is None:
        polyline = ";".join(f"{point[0]},{point[1]}" for point in points)
        steps = [{"road_name": road, "step_distance": distance, "polyline": polyline}]
    return {"status": "1", "info": "OK", "infocode": "10000",
            "route": {"paths": [{"distance": distance, "steps": steps}]}}


class FakeTransport:
    def __init__(self, geocodes, drive=None):
        self.geocodes = list(geocodes)
        self.drive = drive
        self.urls: list[str] = []

    def __call__(self, url: str, timeout: float) -> tuple[int, bytes]:
        self.urls.append(url)
        if "/geocode/" in url:
            return 200, json.dumps(self.geocodes.pop(0)).encode()
        return 200, json.dumps(self.drive).encode()


def success_transport():
    return FakeTransport(
        [geocode_payload(ORIGIN), geocode_payload(DESTINATION, city="上海市")],
        drive_payload([ORIGIN, *MIDDLE, DESTINATION]),
    )


def fetch_project(tmp_path, monkeypatch, *, request=None):
    monkeypatch.setenv(fetch_module.KEY_ENV, KEY)
    return write_project(tmp_path, request=request)


def test_fetch_saves_a_request_bound_route_without_credentials(tmp_path, monkeypatch):
    root = fetch_project(tmp_path, monkeypatch)
    transport = success_transport()
    target = fetch_module.fetch(root, transport=transport, now=FIXED_NOW)
    assert target == root / "route.json"
    route = json.loads(target.read_text(encoding="utf-8"))
    assert route["coordinateSystem"] == "GCJ-02"
    assert route["requestDigest"] == materials.request_digest(materials.load_request(root))
    assert route["acquisition"]["strategy"] == 34
    assert route["acquisition"]["requestedAt"] == FIXED_NOW.isoformat(timespec="seconds")
    assert route["route"]["steps"][0]["road"] == "沪蓉高速"
    assert route["sourceUsage"] == materials.load_request(root)["sourceUsage"]
    assert KEY not in target.read_text(encoding="utf-8")
    assert materials.load_project(root)["route"]["route"]["distanceMeters"] == 5000
    assert not list(root.glob("*.tmp"))


def test_fetch_requires_the_key_environment_variable(tmp_path, monkeypatch):
    root = write_project(tmp_path)
    monkeypatch.delenv(fetch_module.KEY_ENV, raising=False)
    with pytest.raises(M2VError, match=fetch_module.KEY_ENV):
        fetch_module.fetch(root)


def test_usage_authorization_blocks_before_any_network_call(tmp_path, monkeypatch):
    request = request_document()
    request["sourceUsage"]["videoPublication"] = False
    root = fetch_project(tmp_path, monkeypatch, request=request)
    transport = success_transport()
    with pytest.raises(M2VError, match="videoPublication"):
        fetch_module.fetch(root, transport=transport, now=FIXED_NOW)
    assert transport.urls == []


def test_ambiguous_geocode_is_rejected_not_guessed(tmp_path, monkeypatch):
    root = fetch_project(tmp_path, monkeypatch)
    transport = FakeTransport([
        geocode_payload(ORIGIN, count=2),
        geocode_payload(DESTINATION),
    ], drive_payload([ORIGIN, DESTINATION]))
    with pytest.raises(M2VError, match="不唯一"):
        fetch_module.fetch(root, transport=transport, now=FIXED_NOW)


def test_coarse_geocode_level_is_rejected(tmp_path, monkeypatch):
    root = fetch_project(tmp_path, monkeypatch)
    transport = FakeTransport([
        geocode_payload(ORIGIN, level="城市"),
        geocode_payload(DESTINATION),
    ], drive_payload([ORIGIN, DESTINATION]))
    with pytest.raises(M2VError, match="不是具体地点"):
        fetch_module.fetch(root, transport=transport, now=FIXED_NOW)


def test_geocoded_city_mismatch_is_rejected(tmp_path, monkeypatch):
    root = fetch_project(tmp_path, monkeypatch)
    transport = FakeTransport([
        geocode_payload(ORIGIN, city="郑州市"),
        geocode_payload(DESTINATION),
    ], drive_payload([ORIGIN, DESTINATION]))
    with pytest.raises(M2VError, match="不一致"):
        fetch_module.fetch(root, transport=transport, now=FIXED_NOW)
    # 城市不符在算路前就失败，不多发一次驾车规划请求。
    assert not any("/direction/" in url for url in transport.urls)


@pytest.mark.parametrize("status,body,match", [
    (500, b"", "HTTP 500"),
    (200, b"not-json", "非 JSON"),
    (200, b'{"status":"0","infocode":"10001","info":"INVALID_USER_KEY"}', "10001"),
])
def test_service_failures_are_explicit_and_do_not_leak_the_key(tmp_path, monkeypatch, status, body, match):
    root = fetch_project(tmp_path, monkeypatch)
    before = (root / "route.json").read_bytes()
    transport = lambda url, timeout: (status, body)
    with pytest.raises(M2VError, match=match) as error:
        fetch_module.fetch(root, transport=transport, now=FIXED_NOW)
    assert KEY not in str(error.value)
    assert (root / "route.json").read_bytes() == before
    assert not list(root.glob("*.tmp"))


def test_drive_response_without_paths_is_rejected(tmp_path, monkeypatch):
    root = fetch_project(tmp_path, monkeypatch)
    before = (root / "route.json").read_bytes()
    transport = FakeTransport(
        [geocode_payload(ORIGIN), geocode_payload(DESTINATION)],
        {"status": "1", "info": "OK", "infocode": "10000", "route": {"paths": []}},
    )
    with pytest.raises(M2VError, match="没有返回可用路线"):
        fetch_module.fetch(root, transport=transport, now=FIXED_NOW)
    assert (root / "route.json").read_bytes() == before
    assert not list(root.glob("*.tmp"))


def test_transport_failure_does_not_expose_the_request_url(tmp_path, monkeypatch):
    root = fetch_project(tmp_path, monkeypatch)

    def failing(url, timeout):
        raise TimeoutError(f"timed out: {url}")

    with pytest.raises(M2VError) as error:
        fetch_module.fetch(root, transport=failing, now=FIXED_NOW)
    assert KEY not in str(error.value)
    assert "restapi.amap.com" not in str(error.value)


def test_broken_route_continuity_leaves_the_old_route_untouched(tmp_path, monkeypatch):
    root = fetch_project(tmp_path, monkeypatch)
    before = (root / "route.json").read_bytes()
    first = [ORIGIN, MIDDLE[0]]
    second = [DESTINATION, [DESTINATION[0] + 0.01, DESTINATION[1]]]
    transport = FakeTransport(
        [geocode_payload(ORIGIN), geocode_payload(DESTINATION)],
        drive_payload([], steps=[
            {"road_name": "合成高速", "step_distance": "1000",
             "polyline": ";".join(f"{p[0]},{p[1]}" for p in first)},
            {"road_name": "合成高速", "step_distance": "1000",
             "polyline": ";".join(f"{p[0]},{p[1]}" for p in second)},
        ]),
    )
    with pytest.raises(M2VError, match="超过 25 米"):
        fetch_module.fetch(root, transport=transport, now=FIXED_NOW)
    assert (root / "route.json").read_bytes() == before
    assert not list(root.glob("*.tmp"))


def test_request_change_during_fetch_aborts_before_saving(tmp_path, monkeypatch):
    root = fetch_project(tmp_path, monkeypatch)
    before = (root / "route.json").read_bytes()

    class MutatingTransport(FakeTransport):
        def __call__(self, url: str, timeout: float) -> tuple[int, bytes]:
            if "/direction/" in url:
                data = json.loads((root / "request.json").read_text(encoding="utf-8"))
                data["destination"]["label"] = "郑州"
                (root / "request.json").write_text(json.dumps(data), encoding="utf-8")
            return super().__call__(url, timeout)

    transport = MutatingTransport(
        [geocode_payload(ORIGIN), geocode_payload(DESTINATION)],
        drive_payload([ORIGIN, *MIDDLE, DESTINATION]),
    )
    with pytest.raises(M2VError, match="取数期间 request.json 已变化"):
        fetch_module.fetch(root, transport=transport, now=FIXED_NOW)
    assert (root / "route.json").read_bytes() == before
    assert not list(root.glob("*.tmp"))


def test_cli_fetch_wires_the_type_command(tmp_path, monkeypatch):
    root = fetch_project(tmp_path, monkeypatch)
    monkeypatch.setattr(fetch_module, "default_transport", success_transport())
    assert main(["driving-route", "fetch", "--project", str(root)]) == 0
    assert json.loads((root / "route.json").read_text(encoding="utf-8"))["requestDigest"]


def test_cli_fetch_rejects_other_project_types(tmp_path, monkeypatch, capsys):
    root = tmp_path / "general"
    create_project(root, "general", {"storyboard": "storyboard.json"})
    (root / "storyboard.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv(fetch_module.KEY_ENV, KEY)
    assert main(["driving-route", "fetch", "--project", str(root)]) == 1
    assert "仅适用于 driving-route" in capsys.readouterr().err
