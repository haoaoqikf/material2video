import copy
import json
from pathlib import Path

from a2v.types.article.inspect import scene_windows, v4_stages_as_dicts, verify_v4_world_probe
from a2v.types.article.timeline_v4 import resolve_v4

STORYBOARD = json.loads((Path(__file__).parent / "fixtures" / "storyboard-v4-vectors.json").read_text(encoding="utf-8"))["valid"]


class FakePage:
    def __init__(self, value):
        self.value = value

    def evaluate(self, _script):
        return self.value


def _probe(storyboard, frame):
    timeline = resolve_v4(storyboard)
    stage = next(item for item in timeline.stages if item.start_frame <= frame < item.end_frame)
    current = next((beat["id"] for beat in timeline.beats if beat["startFrame"] <= frame < beat["endFrame"]), None)
    return {
        "id": storyboard["world"]["id"], "renderer": storyboard["world"]["renderer"]["kind"],
        "stage": {"id": stage.id, "startFrame": stage.start_frame, "endFrame": stage.end_frame},
        "objectStates": {}, "treeIds": [node["id"] for node in storyboard["world"]["sceneTree"]["children"]] + ["root"],
        "codeIds": [], "camera": {"kind": "hold", "focus": storyboard["world"]["camera"]["focus"], "x": 0, "y": 0, "scale": 1, "velocity": 0},
        "beats": {"current": current, "completed": [beat["id"] for beat in timeline.beats if beat["endFrame"] <= frame],
                  "plan": [beat["id"] for beat in timeline.beats], "estimated": True},
    }


def test_v4_probe_accepts_matching_world_stage_states_camera_and_beats():
    storyboard = copy.deepcopy(STORYBOARD)
    assert verify_v4_world_probe(FakePage(_probe(storyboard, 0)), storyboard, 0) == []


def test_v4_code_review_fails_when_referenced_world_objects_are_unprobed():
    storyboard = copy.deepcopy(STORYBOARD)
    storyboard["world"]["renderer"] = {"kind": "code", "module": "darts"}
    probe = _probe(storyboard, 100)
    probe["renderer"] = "code"
    probe["treeIds"] = []
    probe["codeIds"] = ["player", "dart"]
    issues = verify_v4_world_probe(FakePage(probe), storyboard, 100)
    assert any("缺少 world object DOM 探针：target" in issue for issue in issues)


def test_v4_probe_fails_stage_and_beat_state_drift():
    storyboard = copy.deepcopy(STORYBOARD)
    probe = _probe(storyboard, 100)
    probe["stage"]["id"] = "unrelated-stage"
    probe["beats"]["current"] = None
    issues = verify_v4_world_probe(FakePage(probe), storyboard, 100)
    assert any("stage 探针不符" in issue for issue in issues)
    assert any("当前 beat" in issue for issue in issues)


def test_v4_inspection_windows_keep_global_frame_offsets_for_later_stages():
    storyboard = copy.deepcopy(STORYBOARD)
    first = storyboard["stages"][0]
    first["durationInFrames"] = 500
    first["narrationSegments"][0]["text"] = first["narrationSegments"][0]["text"][:65]
    second = copy.deepcopy(first)
    second.update(id="ending", durationInFrames=550)
    second["narrationSegments"][0].update(id="line-ending", beatId="throw-ending",
                                           text=STORYBOARD["stages"][0]["narrationSegments"][0]["text"][65:])
    second["beats"][0]["id"] = "throw-ending"
    storyboard["stages"].append(second)
    windows = scene_windows(v4_stages_as_dicts(storyboard))
    assert windows == [("opening", 0, 500), ("ending", 500, 1050)]
