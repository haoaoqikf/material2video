from a2v import motion_plan

def test_phase_spans_reserve_stable_tail():
    spans = motion_plan.phase_spans({"durationInFrames": 60})
    assert spans["settle"] == motion_plan.Span(48, 60)
    assert spans["result"].end_frame == 48

def test_stagger_orders_are_deterministic():
    assert motion_plan.stagger_order(["a", "b", "c"], "reverse") == ["c", "b", "a"]
    assert motion_plan.stagger_order(["a", "b", "c"], "center") == ["b", "a", "c"]
