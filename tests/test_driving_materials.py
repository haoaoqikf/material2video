"""自驾路线材料：请求绑定、真实路线几何、授权前置与渲染 props。"""
from __future__ import annotations

import json

import pytest

from m2v.core.errors import M2VError
from m2v.core.project import load_project as load_manifest
from m2v.types.driving_route import adapter, materials
from driving_helpers import (
    DESTINATION, MIDDLE, ORIGIN, edit, request_document, route_document, write_project,
)


def test_valid_synthetic_route_loads_and_builds_render_props(tmp_path):
    root = write_project(tmp_path)
    docs = materials.load_project(root)
    assert docs["request"]["origin"]["label"] == "上海"
    props = materials.build_render_props(docs)
    assert props["durationInFrames"] == 1800
    assert (props["width"], props["height"], props["fps"]) == (1080, 1920, 60)
    assert props["totalDistanceMeters"] == 5000
    assert [step["road"] for step in props["steps"]] == ["合成高速", "合成高速"]


def test_render_props_remove_consecutive_duplicate_points(tmp_path):
    request = request_document()
    steps = [
        {"road": "合成高速", "distanceMeters": 1000,
         "points": [list(ORIGIN), list(ORIGIN), list(MIDDLE[0]), list(MIDDLE[0]), list(MIDDLE[1])]},
        {"road": "合成高速", "distanceMeters": 1000,
         "points": [list(MIDDLE[1]), list(DESTINATION)]},
    ]
    root = write_project(tmp_path, request=request, route=route_document(request, steps=steps))
    props = materials.build_render_props(materials.load_project(root))
    assert props["steps"][0]["points"] == [list(ORIGIN), list(MIDDLE[0]), list(MIDDLE[1])]
    assert props["steps"][1]["points"] == [list(MIDDLE[1]), list(DESTINATION)]


@pytest.mark.parametrize("field,value,match", [
    ("strategy", "shortest", "highway-first"),
    ("durationSeconds", 6, "大于 6"),
    ("durationSeconds", 6.5, "大于 6"),
    ("durationSeconds", True, "大于 6"),
    ("canvas", {"width": 1920, "height": 1080}, "固定为 1080×1920"),
])
def test_request_contract_is_enforced(tmp_path, field, value, match):
    request = request_document()
    request[field] = value
    root = write_project(tmp_path, request=request)
    with pytest.raises(M2VError, match=match):
        materials.load_project(root)


def test_request_placeholders_are_rejected(tmp_path):
    root = write_project(tmp_path)
    edit(root / "request.json", lambda data: data["origin"].update(city="填写城市"))
    with pytest.raises(M2VError, match="占位"):
        materials.load_project(root)


def test_source_usage_must_be_verified_for_every_scope(tmp_path):
    request = request_document()
    request["sourceUsage"]["offlineStorage"] = False
    root = write_project(tmp_path, request=request)
    with pytest.raises(M2VError, match="offlineStorage"):
        materials.load_project(root)


def test_source_usage_requires_document_reference(tmp_path):
    request = request_document()
    request["sourceUsage"]["documents"] = []
    root = write_project(tmp_path, request=request)
    with pytest.raises(M2VError, match="1～8 份"):
        materials.load_project(root)


def test_request_change_invalidates_saved_route(tmp_path):
    root = write_project(tmp_path)
    edit(root / "request.json", lambda data: data["destination"].update(label="郑州"))
    with pytest.raises(M2VError, match="重新运行 m2v driving-route fetch"):
        materials.load_project(root)


@pytest.mark.parametrize("value", [-200, float("nan"), float("inf"), True, 200])
def test_coordinates_must_be_finite_and_in_range(tmp_path, value):
    request = request_document()
    route = route_document(request)
    route["origin"]["location"][0] = value
    root = write_project(tmp_path, request=request, route=route)
    with pytest.raises(M2VError, match="location"):
        materials.load_project(root)


@pytest.mark.parametrize("value", ["x", True])
def test_route_distance_must_be_a_positive_number(tmp_path, value):
    request = request_document()
    route = route_document(request)
    route["route"]["distanceMeters"] = value
    root = write_project(tmp_path, request=request, route=route)
    with pytest.raises(M2VError, match="distanceMeters"):
        materials.load_project(root)


def test_step_gap_beyond_tolerance_names_the_segment(tmp_path):
    request = request_document()
    steps = [
        {"road": "合成高速", "distanceMeters": 1000, "points": [list(ORIGIN), list(MIDDLE[0])]},
        {"road": "合成高速", "distanceMeters": 1000, "points": [list(DESTINATION), list(DESTINATION)]},
    ]
    root = write_project(tmp_path, request=request, route=route_document(request, steps=steps))
    with pytest.raises(M2VError, match=r"steps\[1\].*超过 25 米"):
        materials.load_project(root)


def test_route_endpoints_must_stay_within_one_kilometre_of_geocode(tmp_path):
    request = request_document()
    far = (ORIGIN[0] + 0.02, ORIGIN[1])
    route = route_document(request, origin_location=far)
    root = write_project(tmp_path, request=request, route=route)
    with pytest.raises(M2VError, match="超过 1 公里"):
        materials.load_project(root)


def test_route_start_point_must_match_first_coordinate(tmp_path):
    request = request_document()
    route = route_document(request)
    route["route"]["startPoint"] = [DESTINATION[0] + 1, DESTINATION[1]]
    root = write_project(tmp_path, request=request, route=route)
    with pytest.raises(M2VError, match="首.*第一个坐标|startPoint"):
        materials.load_project(root)


def test_unknown_fields_are_rejected(tmp_path):
    request = request_document()
    request["extra"] = 1
    root = write_project(tmp_path, request=request)
    with pytest.raises(M2VError, match="未知字段"):
        materials.load_project(root)


def test_duplicate_json_keys_are_rejected(tmp_path):
    root = write_project(tmp_path)
    raw = (root / "request.json").read_text(encoding="utf-8")
    (root / "request.json").write_text(raw.replace('"schemaVersion": 2,',
                                                   '"schemaVersion": 2, "schemaVersion": 2,', 1),
                                       encoding="utf-8")
    with pytest.raises(M2VError, match="重复键"):
        materials.load_project(root)


def test_geocode_level_must_be_a_specific_place(tmp_path):
    request = request_document()
    route = route_document(request)
    route["origin"]["level"] = "城市"
    root = write_project(tmp_path, request=request, route=route)
    with pytest.raises(M2VError, match="不是具体地点"):
        materials.load_project(root)


def test_geocoded_city_must_match_the_request(tmp_path):
    request = request_document()
    route = route_document(request)
    route["origin"]["city"] = "郑州市"
    root = write_project(tmp_path, request=request, route=route)
    with pytest.raises(M2VError, match="不一致"):
        materials.load_project(root)


def test_huge_integer_distance_is_rejected_without_overflow(tmp_path):
    request = request_document()
    route = route_document(request)
    route["route"]["distanceMeters"] = 10 ** 400
    root = write_project(tmp_path, request=request, route=route)
    with pytest.raises(M2VError, match="有限"):
        materials.load_project(root)


def test_route_source_usage_must_match_the_request(tmp_path):
    request = request_document()
    route = route_document(request)
    route["sourceUsage"]["attribution"] = "另一个署名"
    root = write_project(tmp_path, request=request, route=route)
    with pytest.raises(M2VError, match="必须与当前 request.json.sourceUsage 一致"):
        materials.load_project(root)


def test_acquisition_cannot_record_a_credential(tmp_path):
    request = request_document()
    route = route_document(request)
    route["acquisition"]["requests"][0]["params"]["key"] = "SECRET"
    root = write_project(tmp_path, request=request, route=route)
    with pytest.raises(M2VError, match="不得保存凭据"):
        materials.load_project(root)


def test_project_canvas_must_match_the_type_contract(tmp_path):
    root = write_project(tmp_path, output={"width": 1920, "height": 1080})
    _, manifest = load_manifest(root)
    with pytest.raises(M2VError, match="1080×1920"):
        adapter.validate(root, manifest)


def test_haversine_matches_a_known_distance():
    # 同一经线上 1 度纬度约为 111.2 公里。
    assert materials.haversine_meters((121.0, 31.0), (121.0, 32.0)) == pytest.approx(111_195, rel=0.002)


def test_v1_materials_are_rejected(tmp_path):
    root = write_project(tmp_path)
    edit(root / "request.json", lambda data: data.update(schemaVersion=1))
    with pytest.raises(M2VError, match="必须为 2"):
        materials.load_project(root)


@pytest.mark.parametrize("value", [None, 1, "true"])
def test_map_tiles_must_be_boolean(tmp_path, value):
    request = request_document()
    if value is None:
        request["sourceUsage"].pop("mapTiles")
    else:
        request["sourceUsage"]["mapTiles"] = value
    root = write_project(tmp_path, request=request)
    with pytest.raises(M2VError, match="mapTiles"):
        materials.load_project(root)


@pytest.mark.parametrize("field,value,match", [
    ("durationSeconds", 0, "预计耗时"),
    ("tollsYuan", -1, "过路费"),
    ("tollDistanceMeters", 9000, "不能超过路线总距离"),
    ("trafficLights", True, "红绿灯"),
])
def test_cost_must_be_valid(tmp_path, field, value, match):
    request = request_document()
    cost = {"durationSeconds": 3600, "tollsYuan": 100,
            "tollDistanceMeters": 2000, "trafficLights": 5}
    cost[field] = value
    root = write_project(tmp_path, request=request, route=route_document(request, cost=cost))
    with pytest.raises(M2VError, match=match):
        materials.load_project(root)


def test_cities_must_not_repeat(tmp_path):
    request = request_document()
    cities = [{"name": "苏州市", "adcode": "320500", "location": [121.48, 31.24]},
              {"name": "苏州市", "adcode": "320500", "location": [121.48, 31.24]}]
    root = write_project(tmp_path, request=request, route=route_document(request, cities=cities))
    with pytest.raises(M2VError, match="城市重复"):
        materials.load_project(root)


def test_route_digest_is_stable_and_covers_request_content():
    request = request_document()
    assert materials.request_digest(request) == materials.request_digest(json.loads(json.dumps(request)))
    changed = json.loads(json.dumps(request))
    changed["destination"]["label"] = "郑州"
    assert materials.request_digest(changed) != materials.request_digest(request)


def test_map_tiles_require_a_basemap(tmp_path):
    request = request_document(map_tiles=True)
    root = write_project(tmp_path, request=request)
    with pytest.raises(M2VError, match="缺少底图材料"):
        materials.load_project(root)


def test_map_tiles_false_allows_vector_fallback(tmp_path):
    root = write_project(tmp_path)
    docs = materials.load_project(root)
    assert "basemap" not in docs["route"]
