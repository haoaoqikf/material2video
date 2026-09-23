from __future__ import annotations
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
    first["transition"] = {"kind": "transform", "meaning": "把开场文字转为下一幕的路径"}
    report = storyboard.validate(valid_script)
    assert report.ok
