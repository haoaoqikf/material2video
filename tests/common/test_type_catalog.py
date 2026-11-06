"""五类目录与初始化模板的单一来源。"""
from __future__ import annotations

import json

import pytest

from m2v.cli import _register_builtins
from m2v.core.errors import M2VError
from m2v.type_system import catalog as directory, registry


def test_catalog_matches_registry_and_has_no_category():
    _register_builtins()
    entries = directory.catalog().entries()
    assert {entry.name for entry in entries} == {item.name for item in registry.all_types()}
    assert all(entry.workspace_parts() == (entry.name,) for entry in entries)
    assert all(entry.material_map() == {"storyboard": "storyboard.json"} for entry in entries)
    assert all(entry.starters == ("scenes/opening.tsx",) for entry in entries)


def test_catalog_rejects_category_old_schema_and_wrong_count(tmp_path):
    raw = json.loads(directory.CATALOG_PATH.read_text(encoding="utf-8"))
    path = tmp_path / "catalog.json"
    def check(change, message):
        value = json.loads(json.dumps(raw))
        change(value)
        path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(M2VError, match=message):
            directory.load(path)
    check(lambda value: value.update(categories=[]), "只允许")
    check(lambda value: value["types"][0].update(category="old"), "类别")
    check(lambda value: value.update(schemaVersion=2), "schemaVersion")
    check(lambda value: value["types"].pop(), "五类")
