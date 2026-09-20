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
