from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from a2v import storyboard
from a2v.migration import migrate_document, migrate_file

def v2() -> dict:
    return {"version":2,"schemaVersion":2,"fps":30,"width":1080,"height":1920,"visualDirection":{"motif":"边界","compositionBias":"mixed","density":"balanced","rhythm":"steady","avoid":[]},"scenes":[{"id":"one","type":"title","durationInFrames":90,"data":{"text":"判断"},"visualIntent":{"relation":"focus","focus":"text","composition":"offset","density":"sparse","tone":"neutral"},"sceneTree":{"id":"root","type":"stack","children":[{"id":"copy","type":"text","contentRef":"data.text","role":"headline"}]},"motions":[{"target":"copy","recipe":"reveal","startFrame":0,"durationFrames":24}]}]}

def test_v2_valid(): assert storyboard.validate(v2()).ok
@pytest.mark.parametrize("field,value", [("id","root"),("contentRef","visual.text"),("style",{"color":"red"})])
def test_v2_rejects_bad_nodes(field, value):
    data=v2(); child=data["scenes"][0]["sceneTree"]["children"][0]; child[field]=value
    assert not storyboard.validate(data).ok
def test_v2_rejects_unknown_motion_target():
    data=v2(); data["scenes"][0]["motions"][0]["target"]="missing"
    assert any(i.path.endswith("target") for i in storyboard.validate(data).errors)
def legacy() -> dict:
    return {"version":1,"fps":30,"width":1080,"height":1920,"scenes":[{"id":"one","type":"title","durationInFrames":90,"data":{"text":"判断","figure":{"kind":"balance"}}}]}
def test_declarative_rejects_v1_with_migration_hint():
    report=storyboard.validate(legacy()); assert "migrate_storyboard.py" in report.errors[0].message
def test_migration_preserves_content_and_marks_review():
    source=legacy(); migrated, report=migrate_document(source); assert migrated["scenes"][0]["id"]==source["scenes"][0]["id"]; assert "figure" not in migrated["scenes"][0]["data"]; assert report["accepted"] is False

def test_migration_preserves_narration_duration_and_order(tmp_path: Path):
    source = {
        "version": 1, "fps": 30, "width": 1080, "height": 1920,
        "scenes": [
            {"id": "a", "type": "number", "durationInFrames": 90, "narration": "第一幕口播", "data": {"value": 42, "label": "次"}},
            {"id": "b", "type": "chart", "durationInFrames": 60, "narration": "第二幕口播", "data": {"values": [{"label": "一月", "value": 3}], "chart": "bar"}},
        ],
    }
    migrated, report = migrate_document(source)
    assert [s["id"] for s in migrated["scenes"]] == ["a", "b"]
    assert [s["durationInFrames"] for s in migrated["scenes"]] == [90, 60]
    assert [s["narration"] for s in migrated["scenes"]] == ["第一幕口播", "第二幕口播"]
    assert migrated["scenes"][0]["data"] == {"value": 42, "label": "次"}
    assert migrated["scenes"][1]["data"]["values"] == [{"label": "一月", "value": 3}]
    assert all(item["preservedFields"] == ["id", "type", "durationInFrames", "narration", "data"] for item in report["scenes"])
    assert storyboard.validate(migrated).ok
def test_migration_does_not_overwrite(tmp_path: Path):
    src=tmp_path/"old.json"; out=tmp_path/"new.json"; src.write_text(json.dumps(legacy()),encoding="utf-8"); migrate_file(src,out)
    with pytest.raises(FileExistsError): migrate_file(src,out)
