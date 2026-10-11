import json
from pathlib import Path

from a2v.types.article.timeline_v4 import resolve_v4


VECTOR = json.loads((Path(__file__).parent / "fixtures" / "storyboard-v4-timeline-vectors.json").read_text(encoding="utf-8"))


def test_v4_global_timeline_matches_shared_vector():
    timeline = resolve_v4(VECTOR["storyboard"])
    assert timeline.to_json() == VECTOR["expected"]
    assert timeline.stage_at(0) == "opening"
    assert timeline.stage_at(100) == "opening"
    assert timeline.stage_at(101) == "middle"
    assert timeline.stage_at(309) == "ending"
    assert timeline.stage_at(310) is None


def test_v4_phase_ranges_cover_each_stage_without_gaps():
    timeline = resolve_v4(VECTOR["storyboard"])
    for stage in timeline.stages:
        phases = [item for item in timeline.phases if item["stageId"] == stage.id]
        assert phases[0]["startFrame"] == stage.start_frame
        assert phases[-1]["endFrame"] == stage.end_frame
        assert all(left["endFrame"] == right["startFrame"] for left, right in zip(phases, phases[1:]))
