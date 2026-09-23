from __future__ import annotations
from copy import deepcopy
from a2v import storyboard

def test_v3_timeline_loads(valid_script, tmp_path):
    import json
    path=tmp_path/"storyboard.json"; path.write_text(json.dumps(valid_script),encoding="utf-8")
    model, report=storyboard.load(path)
    assert report.ok and model is not None
    assert model.total_frames == 180

def test_old_format_is_rejected_by_new_entry():
    old={"version":1,"fps":30,"scenes":[]}
    report=storyboard.validate(old)
    assert not report.ok and "不支持 v3 之前分镜" in report.errors[0].message

def test_directing_contract_requires_brief_when_enabled(valid_script):
    valid_script["directingBrief"] = None
    report = storyboard.validate(valid_script)
    assert not report.ok
    assert any(item.path == "directingBrief" for item in report.errors)

def test_directing_contract_accepts_camera_transition_and_beat_states(valid_script):
    valid_script["directingBrief"] = {
        "thesis": "反馈决定努力是否有效",
        "audienceShift": "从投入不足转向方向错误",
        "emotionalArc": ["困惑", "理解"],
        "visualMotif": "不断回到原点的路径",
        "stylePack": "editorial",
        "avoid": [],
    }
    first = valid_script["scenes"][0]
    first["camera"] = {"shot": "close", "composition": "left", "depth": "layered", "focus": "copy", "segments": [{"kind": "hold", "phase": "establish", "intensity": 0}, {"kind": "push-in", "phase": "change", "focus": "copy", "intensity": 0.5}]}
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
    # 新增树节点后，将段焦点和 beat 目标重定向到当前场景真实节点。
    parts["camera"]["focus"] = "part-a"
    parts["camera"]["segments"] = [{"kind": "hold", "phase": "establish", "focus": "part-a", "intensity": 0}]
    parts.pop("beats", None)
    parts.pop("narrationSegments", None)
    parts.pop("narration", None)
    whole["camera"]["focus"] = "whole-shape"
    whole["camera"]["segments"] = [{"kind": "hold", "phase": "establish", "focus": "whole-shape", "intensity": 0}]
    whole.pop("beats", None)
    whole.pop("narrationSegments", None)
    whole.pop("narration", None)
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


def test_v2_is_rejected_before_field_validation(valid_script):
    valid_script["version"] = 2
    valid_script["schemaVersion"] = 2
    report = storyboard.validate(valid_script)
    assert not report.ok
    assert "不支持 v3 之前分镜" in report.errors[0].message


def test_v3_rejects_string_narration(valid_script):
    valid_script["scenes"][0]["narration"] = "旧式整段口播"
    report = storyboard.validate(valid_script)
    assert any(item.path.endswith(".narration") for item in report.errors)


def test_v3_requires_renderer_and_complete_directing(valid_script):
    del valid_script["scenes"][0]["renderer"]
    del valid_script["scenes"][0]["visualIntent"]["motionMeaning"]
    report = storyboard.validate(valid_script)
    assert any(item.path.endswith(".renderer") for item in report.errors)
    assert any("缺少视觉论证字段" in item.message for item in report.errors)


def test_v3_rejects_absolute_motion_time(valid_script):
    valid_script["scenes"][0]["motions"][0]["startFrame"] = 12
    report = storyboard.validate(valid_script)
    assert any(item.path.endswith(".startFrame") for item in report.errors)
