import copy
import json
from pathlib import Path

import pytest

from a2v.types.article.timeline_v4 import resolve_v4
from a2v.types.article.state_tracks_v4 import compile_state_tracks, state_at

VECTOR = json.loads((Path(__file__).parent / "fixtures" / "storyboard-v4-timeline-vectors.json").read_text(encoding="utf-8"))


def _source():
    value = copy.deepcopy(VECTOR["storyboard"])
    value["world"] = copy.deepcopy(VECTOR["stateWorld"])
    return value


def test_v4_compiled_tracks_match_shared_random_access_samples():
    source = _source()
    tracks = compile_state_tracks(source, resolve_v4(source))
    for frame in (181, 0, 192, 20, 89, 40, 50):
        assert state_at(tracks, frame) == VECTOR["stateSamples"][str(frame)]
    assert state_at(tracks, 20) == state_at(tracks, 20)
    assert source["world"]["stateTracks"][2]["to"] == [10, 4]


def test_v4_compiler_rejects_overlapping_same_property_ranges():
    source = _source()
    source["world"]["stateTracks"].append({
        "id": "player-overlap", "target": "player", "property": "state",
        "binding": {"beatId": "beat-a"}, "to": "muted", "interpolation": "step-end",
    })
    with pytest.raises(ValueError, match="player-focus"):
        compile_state_tracks(source, resolve_v4(source))
