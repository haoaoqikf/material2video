from __future__ import annotations
from copy import deepcopy
from a2v import storyboard

def test_v2_timeline_loads(valid_script, tmp_path):
    import json
    path=tmp_path/"storyboard.json"; path.write_text(json.dumps(valid_script),encoding="utf-8")
    model, report=storyboard.load(path)
    assert report.ok and model is not None
    assert model.total_frames == 90

def test_old_format_is_rejected_by_new_entry():
    old={"version":1,"fps":30,"scenes":[]}
    report=storyboard.validate(old)
    assert not report.ok and "migrate_storyboard.py" in report.errors[0].message

def test_directing_contract_requires_brief_when_enabled(valid_script):
    valid_script["directingVersion"] = 1
    report = storyboard.validate(valid_script)
    assert not report.ok
    assert any(item.path == "directingBrief" for item in report.errors)

def test_directing_contract_accepts_camera_transition_and_beat_states(valid_script):
    valid_script["directingVersion"] = 1
    valid_script["directingBrief"] = {
        "thesis": "反馈决定努力是否有效",
        "audienceShift": "从投入不足转向方向错误",
        "emotionalArc": ["困惑", "理解"],
        "visualMotif": "不断回到原点的路径",
        "stylePack": "editorial",
        "avoid": [],
    }
    first = valid_script["scenes"][0]
    first["camera"] = {"shot": "close", "composition": "left", "depth": "layered", "focus": "copy", "movement": "push-in"}
    second = deepcopy(first)
    second["id"] = "next"
    second["transition"] = {"kind": "transform", "source": "copy", "target": "copy", "meaning": "把开场文字连续带入下一幕"}
    valid_script["scenes"].append(second)
    report = storyboard.validate(valid_script)
    assert report.ok

def test_transition_rejects_missing_cross_scene_nodes(valid_script):
    valid_script["scenes"].append({
        **valid_script["scenes"][0],
        "id": "next",
        "transition": {"kind": "transform", "source": "missing", "target": "missing", "meaning": "连续变化"},
    })
    report = storyboard.validate(valid_script)
    assert not report.ok
    assert any("source 节点 missing" in item.message for item in report.errors)

def test_transition_accepts_decompose_and_recompose(valid_script):
    parts = deepcopy(valid_script["scenes"][0])
    parts["id"] = "parts"
    parts["sceneTree"]["children"] = [
        {"id": "part-a", "type": "shape", "shape": "circle"},
        {"id": "part-b", "type": "shape", "shape": "rect"},
    ]
    parts["motions"] = []
    parts["transition"] = {"kind": "decompose", "source": "copy", "targets": ["part-a", "part-b"], "meaning": "拆成两部分"}
    whole = deepcopy(valid_script["scenes"][0])
    whole["id"] = "whole"
    whole["sceneTree"]["children"] = [{"id": "whole-shape", "type": "shape", "shape": "ring"}]
    whole["motions"] = []
    whole["transition"] = {"kind": "recompose", "sources": ["part-a", "part-b"], "target": "whole-shape", "meaning": "重新组合"}
    valid_script["scenes"].extend([parts, whole])
    assert storyboard.validate(valid_script).ok

def test_transition_rejects_first_scene_and_unregistered_transform(valid_script):
    valid_script["scenes"][0]["transition"] = {"kind": "break", "source": "copy", "meaning": "没有上一幕"}
    report = storyboard.validate(valid_script)
    assert any("第一幕不能声明" in item.message for item in report.errors)
    del valid_script["scenes"][0]["transition"]
    second = deepcopy(valid_script["scenes"][0])
    second["id"] = "next"
    second["sceneTree"]["children"] = [{"id": "image", "type": "image", "sourceRef": "data.image"}]
    second["data"]["image"] = "local.png"
    second["transition"] = {"kind": "transform", "source": "copy", "target": "image", "meaning": "未登记变形"}
    valid_script["scenes"].append(second)
    report = storyboard.validate(valid_script)
    assert any("未登记的跨幕变形" in item.message for item in report.errors)

def test_transition_rejects_ambiguous_mapping_fields(valid_script):
    second = deepcopy(valid_script["scenes"][0])
    second["id"] = "next"
    second["transition"] = {"kind": "break", "source": "copy", "target": "copy", "meaning": "有意断裂"}
    valid_script["scenes"].append(second)
    report = storyboard.validate(valid_script)
    assert any("break 转场不接受 target" in item.message for item in report.errors)
