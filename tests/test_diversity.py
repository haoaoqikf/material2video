from a2v import diversity
import copy

def scene(scene_id: str, text: str="不同正文") -> dict:
    return {"id":scene_id,"data":{"text":text},"visualIntent":{"relation":"focus","focus":"text","composition":"center","density":"sparse"},"sceneTree":{"id":"root","type":"stack","children":[{"id":"copy","type":"text","contentRef":"data.text"}]},"motions":[{"target":"copy","recipe":"fade"}]}

def test_fingerprint_excludes_copy_and_ids():
    assert diversity.fingerprint(scene("a","甲")) == diversity.fingerprint(scene("b","乙"))

def test_reports_adjacent_identical_and_skipped_cross_work():
    result=diversity.inspect({"scenes":[scene("a"),scene("b")]})
    assert result["findings"][0]["rule"] == "adjacent-identical"
    assert result["crossWork"]["status"] == "skipped"

def test_explicit_reference_is_checked():
    result=diversity.inspect({"scenes":[scene("a")]}, [{"scenes":[scene("r")]}])
    assert result["crossWork"]["status"] == "checked"
    assert result["crossWork"]["matches"]


def _v4_world(renderer="tree"):
    value = {
        "version": 4,
        "world": {
            "id": "world",
            "renderer": {"kind": renderer, **({"module": "demo/world"} if renderer == "code" else {})},
            "objects": [{"id": "counter", "role": "primary", "description": "文章正文不得进入指纹"}],
            "data": {"objects": {"counter": {"value": 0}}},
            "sceneTree": {"id": "counter", "type": "number", "value": 0},
            "stateTracks": [
                {"id": "increase", "target": "counter", "property": "value", "binding": {"beatId": "b2"},
                 "to": 2, "interpolation": "linear"}
            ],
            "motions": [],
            "camera": {"shot": "medium", "composition": "center", "depth": "flat"},
        },
        "stages": [
            {"id": "one", "data": {"copy": "第一句"}, "visualIntent": {"mode": "metaphor"},
             "beats": [{"id": "b1", "action": "establish", "targets": ["counter"]}]},
            {"id": "two", "data": {"copy": "第二句"}, "visualIntent": {"mode": "metaphor"},
             "beats": [{"id": "b2", "action": "accumulate", "targets": ["counter"]}]},
        ],
    }
    return value


def test_v4_same_layout_with_state_progression_passes():
    result = diversity.inspect(_v4_world())
    assert result["status"] == "pass"
    assert result["findings"] == []
    assert result["progression"]["stages"][1]["evidence"]


def test_v4_text_only_changes_fail_to_prove_progression():
    value = _v4_world()
    value["world"]["stateTracks"] = [
        {"id": "copy", "target": "counter", "property": "contentRef", "binding": {"beatId": "b2"},
         "to": "data.copy", "interpolation": "step-end"}
    ]
    value["stages"][1]["beats"][0]["action"] = "highlight"
    result = diversity.inspect(value)
    assert result["status"] == "fail"
    assert result["findings"][0]["scenes"] == ["one", "two"]


def test_v4_fingerprint_excludes_article_copy_and_descriptive_text():
    first = _v4_world()
    second = copy.deepcopy(first)
    second["title"] = "另一篇文章标题"
    second["world"]["objects"][0]["description"] = "完全不同的正文内容"
    second["stages"][0]["data"]["copy"] = "替换后的口播"
    assert diversity.fingerprint(first) == diversity.fingerprint(second)


def test_v4_missing_references_are_skipped_and_code_is_pending():
    result = diversity.inspect(_v4_world("code"))
    assert result["crossWork"]["status"] == "skipped"
    assert result["status"] == "pending"
    assert "探针" in result["progression"]["reason"]
