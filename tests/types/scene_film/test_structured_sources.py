"""金融、建筑、汽车进入统一分镜来源后的材料与边界。"""
from __future__ import annotations

import hashlib
import json
import shutil

import pytest

from helpers.financial import project as financial_fixture
from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_project
from m2v.types.scene_film import explainer_prepare, sources
from m2v.types.building_construction.components import build_components


def write(root, name, value):
    (root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def board(root, kind, source_kind, files, *, width, height, duration):
    if root.exists() and any(root.iterdir()):
        # 夹具目录已有来源文件；直接写 v3 工程描述，不重复覆盖或清空。
        (root / "project.json").write_text(json.dumps({
            "schemaVersion": 3, "id": root.name, "type": kind,
            "materials": {"storyboard": "storyboard.json"},
            "output": {"width": width, "height": height, "fps": 30, "audio": "optional"}},
            ensure_ascii=False), encoding="utf-8")
    else:
        create_project(root, kind, {"storyboard": "storyboard.json"},
                       output={"width": width, "height": height, "fps": 30, "audio": "optional"})
    (root / "scenes").mkdir(exist_ok=True)
    entry = {"financial-series": "FinancialSeriesScene", "construction": "ConstructionScene",
             "vehicle-model": "VehicleScene"}[source_kind]
    (root / "scenes/opening.tsx").write_text(
        f"import {{{entry}}} from 'm2v/code-scene/sources';\nexport default function Opening() {{ return <{entry} id=\"source\"/>; }}\n",
        encoding="utf-8")
    value = {"version": 9, "schemaVersion": 9, "fps": 30, "width": width, "height": height,
             "title": "来源测试", "input": {"kind": "topic", "topic": "来源"}, "targetSeconds": duration // 30,
             "sources": {"source": {"kind": source_kind, "files": files}},
             "scenes": [{"id": "opening", "template": "code", "durationFrames": duration,
                         "keywords": ["来源"], "content": {"entry": "scenes/opening.tsx", "sourceIds": ["source"]},
                         "narrationSegments": []}]}
    write(root, "storyboard.json", value)
    return value


def test_financial_source_is_validated_and_fingerprinted(tmp_path):
    root = financial_fixture(tmp_path)
    story = board(root, "data-evolution", "financial-series",
                  {"request": "request.json", "prices": "prices.json", "plan": "animation-plan.json"},
                  width=1080, height=1920, duration=450)
    result, inputs = sources.prepare(root, story, "data-evolution")
    assert result["source"]["data"]["plan"]["durationSeconds"] == 15
    assert "file:raw-prices.csv" in inputs
    explainer_prepare.prepare(root, load_project(root)[1])
    prepared = json.loads((root / "outputs/prepared.json").read_text(encoding="utf-8"))
    assert prepared["props"]["compiledScenes"][0]["content"]["preparedSources"]["source"]["kind"] == "financial-series"
    (root / "animation-plan.json").unlink()
    assert main(["data", "financial-plan", "--project", str(root), "--duration-seconds", "15"]) == 0
    assert json.loads((root / "animation-plan.json").read_text(encoding="utf-8"))["schemaVersion"] == 8


def test_source_rejects_escape_wrong_type_and_unknown_id(tmp_path):
    root = tmp_path / "work"
    root.mkdir()
    (root / "request.json").write_text("{}", encoding="utf-8")
    (root / "prices.json").write_text("{}", encoding="utf-8")
    (root / "animation-plan.json").write_text("{}", encoding="utf-8")
    story = board(root, "data-evolution", "financial-series",
                  {"request": "request.json", "prices": "prices.json", "plan": "animation-plan.json"},
                  width=1080, height=1920, duration=120)
    with pytest.raises(M2VError, match="不适用于"):
        sources.validate(root, story, "text-motion")
    story["scenes"][0]["content"]["sourceIds"] = ["missing"]
    with pytest.raises(M2VError, match="sourceIds"):
        sources.validate(root, story, "data-evolution")
    story["scenes"][0]["content"]["sourceIds"] = ["source"]
    story["sources"]["source"]["files"]["prices"] = "../prices.json"
    with pytest.raises(M2VError, match="越界"):
        sources.validate(root, story, "data-evolution")


def test_construction_steps_are_available_to_spatial_scene(tmp_path):
    root = tmp_path / "construction"
    shutil.copytree('tests/fixtures/sources/construction', root)
    story = board(root, "spatial-3d", "construction",
                  {"building": "building.json", "construction": "construction.json", "assets": "manifest.json"},
                  width=1920, height=1080, duration=1800)
    result, inputs = sources.prepare(root, story, "spatial-3d")
    data = result["source"]["data"]
    assert len(data["components"]) == 77
    assert data["construction"]["steps"]
    assert inputs["file:construction.json"] == hashlib.sha256((root / "construction.json").read_bytes()).hexdigest()
    explainer_prepare.prepare(root, load_project(root)[1])


def test_vehicle_model_is_embedded_for_spatial_scene(tmp_path):
    root = tmp_path / "vehicle"
    root.mkdir()
    assets = root / "assets"
    (assets / "studio").mkdir(parents=True)
    for name, data in {"data.bin": b"bin", "img.bin": b"img", "studio/env.hdr": b"env",
                       "studio/ao.jpg": b"ao", "studio/floor_n.webp": b"normal",
                       "studio/floor_r.webp": b"rough"}.items():
        (assets / name).write_bytes(data)
    gltf = {"asset": {"version": "2.0"}, "buffers": [{"uri": "data.bin", "byteLength": 3}],
            "images": [{"uri": "img.bin"}], "nodes": [{"name": "Wheel.001"}, {"name": "Wheel.002"}],
            "scenes": [{"nodes": [0, 1]}], "scene": 0}
    write(assets, "car.gltf", gltf)
    studio = {"environment": "assets/studio/env.hdr", "bodyAo": "assets/studio/ao.jpg",
              "floorNormal": "assets/studio/floor_n.webp", "floorRoughness": "assets/studio/floor_r.webp"}
    write(root, "showcase.json", {"schemaVersion": 2, "canvas": {"width": 1920, "height": 1080},
          "durationSeconds": 30, "fps": 30, "model": "assets/car.gltf", "wheelNodes": ["Wheel.001", "Wheel.002"],
          "camera": {"distance": 8, "height": 2, "orbitStartDegrees": 0, "orbitEndDegrees": 360},
          "effects": {"speedStartSeconds": 19, "speedEndSeconds": 26, "fadeOutSeconds": 4}, "studio": studio})
    manifest = [{"path": p.relative_to(root).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                 "source": "test", "license": "test"} for p in assets.rglob('*') if p.is_file()]
    write(root, "manifest.json", {"schemaVersion": 1, "assets": manifest})
    story = board(root, "spatial-3d", "vehicle-model", {"showcase": "showcase.json", "assets": "manifest.json"},
                  width=1920, height=1080, duration=900)
    result, inputs = sources.prepare(root, story, "spatial-3d")
    assert "data:application/octet-stream;base64," in result["source"]["data"]["modelGltf"]
    assert "file:assets/car.gltf" in inputs
    explainer_prepare.prepare(root, load_project(root)[1])
