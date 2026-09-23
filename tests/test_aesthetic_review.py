from a2v import aesthetic_review


def test_directing_review_requires_camera_and_motif():
    storyboard = {
        "directingVersion": 1,
        "visualDirection": {"motif": "路径", "compositionBias": "mixed", "density": "balanced", "rhythm": "steady", "avoid": []},
        "scenes": [{"id": "a", "visualIntent": {}}, {"id": "b", "visualIntent": {}}],
    }
    result = aesthetic_review.analyze(storyboard)
    rules = {item["rule"] for item in result["findings"]}
    assert {"camera-declaration", "motif-coverage"} <= rules
    assert result["publishable"] is False


def test_directing_review_reports_adjacent_reuse():
    camera = {"shot": "medium", "composition": "center", "depth": "flat", "focus": "x", "movement": "static"}
    storyboard = {
        "directingVersion": 1,
        "visualDirection": {"motif": "路径", "compositionBias": "mixed", "density": "balanced", "rhythm": "steady", "avoid": []},
        "scenes": [
            {"id": "a", "camera": camera, "visualIntent": {"relation": "focus", "mode": "process", "primaryObject": "路径"}},
            {"id": "b", "camera": camera, "visualIntent": {"relation": "focus", "mode": "process", "primaryObject": "路径"}},
        ],
    }
    result = aesthetic_review.analyze(storyboard)
    assert any(item["rule"] == "adjacent-shot-reuse" for item in result["findings"])
