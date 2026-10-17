"""cinematic 档位：档位解析与可选字段契约。"""
import pytest

from m2v.core.errors import M2VError
from m2v.types.general import cinematic


def hero(identity: str, start: int, end: int) -> dict:
    return {"id": identity, "target": identity, "tier": "hero", "startFrame": start, "endFrame": end}


def test_profile_defaults_to_standard_and_records_source():
    assert cinematic.resolve_profile({}) == ("standard", "default")
    assert cinematic.resolve_profile({"productionProfile": "cinematic"}) == ("cinematic", "project")
    assert cinematic.resolve_profile({"productionProfile": "standard"}, "cinematic") == ("cinematic", "command-line")
    assert cinematic.validate_project({}) == "standard"
    assert cinematic.validate_project({"productionProfile": "cinematic"}) == "cinematic"


@pytest.mark.parametrize("value", ["epic", "", "STANDARD", 1, None, True])
def test_profile_rejects_unknown_or_ill_typed_values(value):
    project = {"productionProfile": value}
    if value is None:
        assert cinematic.validate_project(project) == "standard"
        return
    with pytest.raises(M2VError):
        cinematic.validate_project(project)


def test_profile_override_rejects_unknown_value():
    with pytest.raises(M2VError):
        cinematic.resolve_profile({}, "epic")


def test_shots_absent_keeps_standard_behaviour():
    assert cinematic.validate_shots({}, "props") == []
    cinematic.validate_work([])


def test_shots_accept_declared_fields_and_hero_rule():
    props = {"shots": [hero("earth", 0, 480), hero("saturn", 480, 960), hero("oort", 960, 1440),
                       {"id": "sun", "target": "sun", "tier": "minor", "startFrame": 1440, "endFrame": 1500}]}
    shots = cinematic.validate_shots(props, "props")
    assert [shot["id"] for shot in shots] == ["earth", "saturn", "oort", "sun"]
    cinematic.validate_work(shots)


def test_shots_reject_unknown_field_with_shot_location():
    props = {"shots": [{**hero("earth", 0, 480), "zoom": 2}]}
    with pytest.raises(M2VError) as error:
        cinematic.validate_shots(props, "props")
    assert "shots[0]" in str(error.value) and "zoom" in str(error.value)


def test_shots_reject_duplicate_id_and_bad_tier_and_window():
    with pytest.raises(M2VError):
        cinematic.validate_shots({"shots": [hero("earth", 0, 480), hero("earth", 480, 960)]}, "props")
    with pytest.raises(M2VError):
        cinematic.validate_shots({"shots": [{**hero("earth", 0, 480), "tier": "epic"}]}, "props")
    with pytest.raises(M2VError):
        cinematic.validate_shots({"shots": [{"id": "a", "target": "a", "tier": "minor",
                                             "startFrame": 480, "endFrame": 480}]}, "props")


def test_work_requires_three_heroes():
    with pytest.raises(M2VError) as error:
        cinematic.validate_work([hero("earth", 0, 480), hero("saturn", 480, 960)])
    assert "hero" in str(error.value)


@pytest.mark.parametrize("length", [7 * 60, 13 * 60])
def test_hero_must_be_eight_to_twelve_seconds(length):
    shots = [hero("earth", 0, length), hero("saturn", 1000, 1000 + 480), hero("oort", 2000, 2000 + 480)]
    with pytest.raises(M2VError) as error:
        cinematic.validate_work(shots)
    assert "hero" in str(error.value)


def test_camera_focus_post_and_exposure_ranges():
    shot = {**hero("earth", 0, 480),
            "camera": {"path": [[0, 0, 9], [0, 0, 3]], "fov": 32, "roll": -2, "easing": "quintInOut",
                       "keyframes": [{"frame": 0, "position": [0, 0, 9]}, {"frame": 480, "position": [0, 0, 3]}]},
            "focus": {"target": "earth", "distance": 3.2, "aperture": 2.8},
            "exposure": {"ev": -0.3},
            "post": {"bloom": 0.7, "dof": 0.6, "grain": 0.35, "vignette": 0.45, "chromaticAberration": 0.12}}
    cinematic.validate_shots({"shots": [shot]}, "props")
    for broken in ({**shot, "camera": {"fov": 200}}, {**shot, "camera": {"easing": "bounce"}},
                   {**shot, "focus": {"aperture": 0}}, {**shot, "post": {"bloom": 3}},
                   {**shot, "exposure": {"ev": 9}}, {**shot, "camera": {"path": [[0, 0, 1]]}}):
        with pytest.raises(M2VError):
            cinematic.validate_shots({"shots": [broken]}, "props")


def test_look_requires_profile_and_bounded_numbers():
    cinematic.validate_look({"profile": "deep-space", "grain": 0.3, "exposure": {"ev": -0.3}}, "look")
    with pytest.raises(M2VError):
        cinematic.validate_look({"grain": 0.3}, "look")
    with pytest.raises(M2VError):
        cinematic.validate_look({"profile": "deep-space", "dof": 2}, "look")
    with pytest.raises(M2VError):
        cinematic.validate_look({"profile": "deep-space", "lut": 3}, "look")


def test_claims_are_non_empty_unique_and_bounded():
    cinematic.validate_claims({}, "segment")
    cinematic.validate_claims({"claims": ["大红斑", "云带流动"]}, "segment")
    with pytest.raises(M2VError):
        cinematic.validate_claims({"claims": ["大红斑", "大红斑"]}, "segment")
    with pytest.raises(M2VError):
        cinematic.validate_claims({"claims": [""]}, "segment")
    with pytest.raises(M2VError):
        cinematic.validate_claims({"claims": ["x" * 81]}, "segment")


def test_shot_windows_follow_declared_segment():
    shots = cinematic.validate_shots({"shots": [{**hero("earth", 120, 600), "segment": "home-0"}]}, "props")
    windows = {"home-0": {"startFrame": 120, "endFrame": 600}}
    cinematic.validate_shot_windows("home", shots, windows, 720)
    with pytest.raises(M2VError) as error:
        cinematic.validate_shot_windows("home", shots, {"home-0": {"startFrame": 180, "endFrame": 600}}, 720)
    assert "shots[earth]" in str(error.value)
    with pytest.raises(M2VError):
        cinematic.validate_shot_windows("home", shots, {"home-1": {"startFrame": 120, "endFrame": 600}}, 720)


def test_shot_windows_allow_silent_lead_in_and_tail_only():
    lead = cinematic.validate_shots({"shots": [{**hero("sun", 0, 120), "tier": "minor"}]}, "props")
    windows = {"sun-0": {"startFrame": 300, "endFrame": 900}}
    cinematic.validate_shot_windows("cold-open", lead, windows, 1200)
    tail = cinematic.validate_shots({"shots": [{**hero("oort", 1000, 1120), "tier": "minor"}]}, "props")
    cinematic.validate_shot_windows("edge", tail, windows, 1200)
    inside = cinematic.validate_shots({"shots": [{**hero("sun", 320, 500), "tier": "minor"}]}, "props")
    with pytest.raises(M2VError):
        cinematic.validate_shot_windows("edge", inside, windows, 1200)
    with pytest.raises(M2VError):
        cinematic.validate_shot_windows("edge", cinematic.validate_shots(
            {"shots": [{**hero("sun", 200, 400), "tier": "minor"}]}, "props"), windows, 1200)


def test_shot_windows_must_fit_scene_duration():
    shots = cinematic.validate_shots({"shots": [{**hero("sun", 0, 480), "tier": "minor"}]}, "props")
    with pytest.raises(M2VError):
        cinematic.validate_shot_windows("cold-open", shots, {}, 300)
