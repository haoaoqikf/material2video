from __future__ import annotations
from pathlib import Path
import a2v.core.catalog as catalog
import sync_catalog

ROOT=Path(__file__).resolve().parents[1]

def test_regenerated_outputs_match_disk():
    for path, expected in sync_catalog.build_outputs(sync_catalog.load_registry()).items():
        assert path.read_text(encoding="utf-8") == expected

def test_registry_mirror_and_sources_are_complete():
    registry=sync_catalog.load_registry(); types={item["type"] for item in registry["primitives"]}
    assert types == set(catalog.PRIMITIVE_CATALOG)
    for item in registry["primitives"]:
        assert (ROOT/"web/src"/item["source"]).is_file()
        assert item["children"][0] <= item["children"][1]
        assert item["motions"]

def test_declared_props_have_runtime_mentions():
    source=(ROOT/"web/src/primitives/SceneTree.tsx").read_text(encoding="utf-8")
    for primitive in catalog.PRIMITIVE_CATALOG.values():
        for prop in primitive.props:
            assert prop in source, f"{primitive.type}.{prop} 未被渲染器消费"
