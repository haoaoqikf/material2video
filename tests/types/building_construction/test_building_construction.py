"""三维空间建筑来源：v2 数据、构件、步骤与镜头边界。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.types.building_construction import materials
from m2v.types.building_construction.components import build_components, expand_selector


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/sources/construction"


def init_project(tmp_path):
    root = tmp_path / "construction"
    shutil.copytree(FIXTURE, root)
    return root, {"type": "spatial-3d"}


def edit(path, mutate):
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def step(data, step_id):
    return next(item for item in data["steps"] if item["id"] == step_id)


def test_component_ids_are_stable_and_unique(tmp_path):
    root, _ = init_project(tmp_path)
    docs = materials.load_project(root)
    identities = [item["id"] for item in docs["components"]]
    assert len(identities) == len(set(identities)) == 77
    assert docs["components"][0] == {"id": "site", "kind": "site", "floor": 0}
    assert "column-1-0-front" in identities and "column-2-3-back" in identities
    assert "wall-2-front-0" in identities and "roof-ridge" in identities
    assert "opening-door-entry" in identities and "finish-door-entry" in identities
    first = materials.load_project(root)
    assert first["components"] == docs["components"], "重复准备必须保持构件身份"


def test_selector_expansion_rules():
    house = {
        "floors": 2, "bayCount": 3,
        "roof": {"type": "gable"},
        "openings": [{"id": "door-entry", "floor": 1}],
    }
    components = build_components(house)
    assert expand_selector(components, "column-1-*") == [
        "column-1-0-front", "column-1-0-back",
        "column-1-1-front", "column-1-1-back",
        "column-1-2-front", "column-1-2-back",
        "column-1-3-front", "column-1-3-back",
    ]
    assert expand_selector(components, "site") == ["site"]
    with pytest.raises(ValueError, match="末尾"):
        expand_selector(components, "column-*front")


def test_opening_must_stay_inside_wall(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "building.json", lambda data: data["house"]["openings"][0].update(offset=99))
    with pytest.raises(M2VError, match="开口超出"):
        materials.load_project(root)


def test_sill_plus_height_must_fit_floor(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "building.json",
         lambda data: data["house"]["openings"][1].update(sill=2.0, height=1.4))
    with pytest.raises(M2VError, match="窗台加洞高"):
        materials.load_project(root)


def test_duplicate_opening_id_is_rejected(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "building.json", lambda data: data["house"]["openings"][1].update(
        id=data["house"]["openings"][0]["id"]))
    with pytest.raises(M2VError, match="ID 重复"):
        materials.load_project(root)


def test_invalid_roof_and_stairs_are_rejected(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "building.json", lambda data: data["house"]["roof"].update(type="dome"))
    with pytest.raises(M2VError):
        materials.load_project(root)
    edit(root / "building.json", lambda data: data["house"]["roof"].update(type="gable"))
    edit(root / "building.json", lambda data: data["house"]["stairs"].update(offset=8, width=2.5))
    with pytest.raises(M2VError, match="楼梯超出"):
        materials.load_project(root)


def test_v1_material_is_rejected_with_upgrade_hint(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "building.json", lambda data: data.update(schemaVersion=1))
    with pytest.raises(M2VError, match="v2"):
        materials.load_project(root)
    edit(root / "building.json", lambda data: data.update(schemaVersion=2))
    edit(root / "construction.json", lambda data: data.update(schemaVersion=1))
    with pytest.raises(M2VError, match="v2"):
        materials.load_project(root)


def test_unknown_schema_is_rejected(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "building.json", lambda data: data.update(schemaVersion=3))
    with pytest.raises(M2VError, match="schemaVersion"):
        materials.load_project(root)


def test_stages_must_cover_duration(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "construction.json", lambda data: data["stages"].pop())
    with pytest.raises(M2VError, match="完整覆盖"):
        materials.load_project(root)


def test_shots_must_cover_duration_without_overlap(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "construction.json", lambda data: data["shots"][1].update(startSeconds=7))
    with pytest.raises(M2VError, match="镜头"):
        materials.load_project(root)


def test_unknown_hidden_component_is_rejected(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "construction.json", lambda data: data["shots"][0]["hide"].append("wall-9-*"))
    with pytest.raises(M2VError, match="没有匹配"):
        materials.load_project(root)


def test_unknown_selector_is_rejected(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "construction.json", lambda data: step(data, "columns-1")["select"].append(
        "column-9-*"))
    with pytest.raises(M2VError, match="没有匹配"):
        materials.load_project(root)


def test_overlapping_selectors_are_rejected(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "construction.json", lambda data: step(data, "columns-1")["select"].append(
        "column-1-0-*"))
    with pytest.raises(M2VError, match="重叠"):
        materials.load_project(root)


def test_component_cannot_be_built_twice(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "construction.json", lambda data: step(data, "beams-1")["select"].append(
        "column-1-0-front"))
    with pytest.raises(M2VError, match="重复建成"):
        materials.load_project(root)


def test_dependency_cycle_is_rejected(tmp_path):
    root, _ = init_project(tmp_path)
    def mutate(data):
        step(data, "slab-1")["after"] = ["beams-1"]
    edit(root / "construction.json", mutate)
    with pytest.raises(M2VError, match="依赖环"):
        materials.load_project(root)


def test_step_cannot_start_before_dependency_ends(tmp_path):
    root, _ = init_project(tmp_path)
    def mutate(data):
        step(data, "beams-1")["after"] = ["columns-1"]
        step(data, "beams-1")["startSeconds"] = 23
    edit(root / "construction.json", mutate)
    with pytest.raises(M2VError, match="不能早于依赖"):
        materials.load_project(root)


def test_step_must_stay_inside_stage(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "construction.json", lambda data: step(data, "yard").update(endSeconds=65))
    with pytest.raises(M2VError, match="阶段内"):
        materials.load_project(root)


def test_every_non_initial_component_is_built_once(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "construction.json", lambda data: data["steps"].remove(step(data, "yard")))
    with pytest.raises(M2VError, match="没有被任何步骤建成"):
        materials.load_project(root)


def test_asset_digest_is_required_when_registered(tmp_path):
    root, _ = init_project(tmp_path)
    (root / "asset.bin").write_bytes(b"x")
    edit(root / "manifest.json", lambda data: data["assets"].append({
        "path": "asset.bin", "sha256": "0" * 64, "source": "test", "license": "test"}))
    with pytest.raises(M2VError, match="摘要不匹配"):
        materials.load_project(root)
