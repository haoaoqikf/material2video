from a2v import diversity

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
