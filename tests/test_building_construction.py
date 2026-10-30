"""建筑建造类型：初始化、材料校验与准备边界。"""
from __future__ import annotations

import json

import pytest

from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.core.project import load_current_prepared, load_project
from m2v.types.building_construction import materials


def init_project(tmp_path):
    assert main(["init", "--type", "building-construction", "--project", "demo",
                 "--content-root", str(tmp_path)]) == 0
    root, manifest = load_project(tmp_path / "videos/building-construction/demo")
    return root, manifest


def edit(path, mutate):
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_init_and_prepare_frames(tmp_path):
    root, manifest = init_project(tmp_path)
    assert manifest["type"] == "building-construction"
    assert manifest["output"]["fps"] == 30
    assert (manifest["output"]["width"], manifest["output"]["height"]) == (1920, 1080)
    assert manifest["materials"] == materials.MATERIALS
    assert main(["prepare", "--project", str(root)]) == 0
    prepared = load_current_prepared(root, manifest)
    assert prepared["durationInFrames"] == 1200
    assert prepared["fps"] == 30
    assert prepared["compositionId"] == "BuildingConstruction"


def test_opening_must_stay_inside_wall(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "building.json", lambda data: data["house"]["openings"][0].update(offset=99))
    with pytest.raises(M2VError, match="开口超出"):
        materials.load_project(root)


def test_duplicate_opening_id_is_rejected(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "building.json", lambda data: data["house"]["openings"][1].update(
        id=data["house"]["openings"][0]["id"]))
    with pytest.raises(M2VError, match="ID 重复"):
        materials.load_project(root)


def test_stages_must_cover_duration(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "construction.json", lambda data: data["stages"].pop())
    with pytest.raises(M2VError, match="完整覆盖"):
        materials.load_project(root)


def test_asset_digest_is_required_when_registered(tmp_path):
    root, _ = init_project(tmp_path)
    (root / "asset.bin").write_bytes(b"x")
    edit(root / "manifest.json", lambda data: data["assets"].append({
        "path": "asset.bin", "sha256": "0" * 64, "source": "test", "license": "test"}))
    with pytest.raises(M2VError, match="摘要不匹配"):
        materials.load_project(root)


def test_unknown_schema_is_rejected(tmp_path):
    root, _ = init_project(tmp_path)
    edit(root / "building.json", lambda data: data.update(schemaVersion=2))
    with pytest.raises(M2VError, match="schemaVersion"):
        materials.load_project(root)
