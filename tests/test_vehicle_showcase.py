"""汽车展示类型：资产内嵌、节点校验与准备边界。"""
from __future__ import annotations

import hashlib
import json

import pytest

from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_current_prepared, load_project
from m2v.types.vehicle_showcase import materials


def write_project(tmp_path):
    root = tmp_path / "su7"
    create_project(root, "vehicle-showcase", materials.MATERIALS,
                   output={"width": 1920, "height": 1080})
    (root / "assets").mkdir()
    (root / "assets" / "data.bin").write_bytes(b"bin")
    (root / "assets" / "img.bin").write_bytes(b"img")
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{"uri": "data.bin", "byteLength": 3}],
        "images": [{"uri": "img.bin"}],
        "nodes": [{"name": "Wheel.001"}, {"name": "Wheel.002"}],
        "scenes": [{"nodes": [0, 1]}],
        "scene": 0,
    }
    (root / "assets" / "car.gltf").write_text(json.dumps(gltf), encoding="utf-8")
    showcase = {
        "schemaVersion": 1, "canvas": {"width": 1920, "height": 1080},
        "durationSeconds": 30, "fps": 30, "model": "assets/car.gltf",
        "wheelNodes": ["Wheel.001", "Wheel.002"],
        "camera": {"distance": 8, "height": 2, "orbitStartDegrees": 0,
                   "orbitEndDegrees": 360},
        "effects": {"speedStartSeconds": 19, "speedEndSeconds": 26, "fadeOutSeconds": 4},
    }
    (root / "showcase.json").write_text(json.dumps(showcase), encoding="utf-8")
    assets = []
    for path in ("assets/car.gltf", "assets/data.bin", "assets/img.bin"):
        file = root / path
        assets.append({"path": path, "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                       "source": "test", "license": "test"})
    (root / "manifest.json").write_text(json.dumps({"schemaVersion": 1, "assets": assets}),
                                        encoding="utf-8")
    return root


def test_assets_are_embedded_and_prepared(tmp_path):
    root = write_project(tmp_path)
    docs = materials.load_project(root)
    assert "data:application/octet-stream;base64," in docs["modelGltf"]
    assert "data:image/webp;base64," not in docs["modelGltf"]
    _, manifest = load_project(root)
    assert main(["prepare", "--project", str(root)]) == 0
    prepared = load_current_prepared(root, manifest)
    assert prepared["durationInFrames"] == 900
    assert prepared["props"]["modelGltf"] == docs["modelGltf"]


def test_missing_wheel_node_is_rejected(tmp_path):
    root = write_project(tmp_path)
    data = json.loads((root / "showcase.json").read_text(encoding="utf-8"))
    data["wheelNodes"].append("missing-node")
    (root / "showcase.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(M2VError, match="不存在节点"):
        materials.load_project(root)


def test_asset_hash_drift_is_rejected(tmp_path):
    root = write_project(tmp_path)
    (root / "assets" / "data.bin").write_bytes(b"changed")
    with pytest.raises(M2VError, match="摘要不匹配"):
        materials.load_project(root)


def test_unsupported_canvas_is_rejected(tmp_path):
    root = write_project(tmp_path)
    data = json.loads((root / "showcase.json").read_text(encoding="utf-8"))
    data["canvas"] = {"width": 1080, "height": 1920}
    (root / "showcase.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(M2VError, match="固定为 1920×1080"):
        materials.load_project(root)
