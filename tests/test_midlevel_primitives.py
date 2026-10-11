"""中层原语（flow / cycle / timeline / gauge / pictogram）的声明与校验口径。

覆盖 openspec 变更 add-narration-synced-visual-beats 的任务 3.2 与 3.3 中
「注册表登记 + 受控属性 + 容量 + 方向关系 + 图标白名单」的静态部分；
逐帧渲染行为由 web 侧 `primitives/SceneTree.test.tsx` 验证。
"""

from __future__ import annotations

import pytest

import a2v.core.catalog as catalog
import a2v.types.article.storyboard as storyboard
MIDLEVEL = {"flow", "cycle", "timeline", "gauge", "pictogram"}

def v3() -> dict:
    return {
        "version": 3, "schemaVersion": 3, "directingVersion": 1,
        "directingBrief": {"thesis": "阶段推进", "audienceShift": "理解关系", "emotionalArc": ["观察", "确认"], "visualMotif": "流程", "stylePack": "editorial", "avoid": []},
        "visual": {"theme": "dark", "preset": "keynote"}, "fps": 30, "width": 1080, "height": 1920,
        "visualDirection": {"motif": "流程", "compositionBias": "mixed", "density": "balanced", "rhythm": "steady", "avoid": []},
        "scenes": [{
            "id": "example", "type": "process", "durationInFrames": 90, "data": {"text": "阶段"},
            "renderer": {"kind": "tree"},
            "visualIntent": {"relation": "sequence", "focus": "shape", "composition": "center", "density": "balanced", "tone": "neutral", "mode": "process", "claim": "阶段逐步变化", "showWithoutText": "不同阶段在路径上依次推进", "primaryObject": "阶段路径", "motionMeaning": "阶段随节拍逐步出现"},
            "camera": {"shot": "medium", "composition": "center", "depth": "flat", "focus": "root", "segments": [{"phase": "establish", "kind": "hold"}]},
            "sceneTree": {"id": "root", "type": "stack", "children": [{"id": "copy", "type": "text", "contentRef": "data.text", "role": "body"}]},
            "motions": [],
        }],
    }


def staged(count: int, node_type: str = "text") -> dict:
    """把 base 分镜的场景树换成 `node_type` 容器 + `count` 个阶段。"""
    data = v3()
    data["scenes"][0]["sceneTree"] = {
        "id": "root",
        "type": node_type,
        "children": [
            {"id": f"stage-{index}", "type": "text", "contentRef": "data.text", "role": "label"}
            for index in range(count)
        ],
    }
    data["scenes"][0]["motions"] = []
    return data


def quantity(node_type: str, value: object, **extra: object) -> dict:
    """量级类原语：data.ratio 是内容引用指向的数值。"""
    data = v3()
    data["scenes"][0]["data"] = {"text": "占比", "ratio": value}
    data["scenes"][0]["sceneTree"] = {
        "id": "root",
        "type": node_type,
        "contentRef": "data.ratio",
        **extra,
    }
    data["scenes"][0]["motions"] = []
    return data


def test_registry_declares_midlevel_primitives():
    registry = catalog.PRIMITIVE_CATALOG
    assert MIDLEVEL <= set(registry)
    for node_type in ("flow", "cycle", "timeline"):
        entry = registry[node_type]
        assert entry.category == "layout"
        assert entry.children == (2, 6), f"{node_type} 的阶段容量应是 2–6"
        assert "direction" in entry.props and "state" in entry.props
        assert {"establish", "connect", "loop"} <= set(entry.actions)
    for node_type in ("gauge", "pictogram"):
        entry = registry[node_type]
        assert entry.category == "content"
        assert entry.children == (0, 0)
        assert "contentRef" in entry.props
        assert {"accumulate", "deplete", "compare"} <= set(entry.actions)
    assert "icon" in registry["pictogram"].props


def test_icon_whitelist_is_the_registry_list():
    assert catalog.ICON_NAMES
    assert set(catalog.ICON_NAMES) == set(
        __import__("sync_catalog").load_registry()["icons"]
    )
    # 示例中使用的四个名称必须继续有效
    assert {"arrow", "check", "cross", "spark"} <= set(catalog.ICON_NAMES)


@pytest.mark.parametrize("node_type", ["flow", "cycle", "timeline"])
@pytest.mark.parametrize("count,ok", [(2, True), (6, True), (1, False), (7, False)])
def test_stage_capacity(node_type, count, ok):
    assert storyboard.validate(staged(count, node_type)).ok is ok


@pytest.mark.parametrize(
    "node_type,direction,ok",
    [
        ("flow", "ltr", True),
        ("flow", "btt", True),
        ("flow", "cw", False),
        ("timeline", "ttb", True),
        ("timeline", "ccw", False),
        ("cycle", "cw", True),
        ("cycle", "ccw", True),
        ("cycle", "ltr", False),
    ],
)
def test_direction_is_controlled_per_primitive(node_type, direction, ok):
    data = staged(3, node_type)
    data["scenes"][0]["sceneTree"]["direction"] = direction
    report = storyboard.validate(data)
    assert report.ok is ok
    if not ok:
        assert any("direction" in issue.path for issue in report.errors)


def test_icon_names_are_whitelisted():
    for name in ("arrow", "users", "database"):
        data = staged(3, "flow")
        data["scenes"][0]["sceneTree"]["children"][0] = {"id": "glyph", "type": "icon", "icon": name}
        assert storyboard.validate(data).ok, name
    data = staged(3, "flow")
    data["scenes"][0]["sceneTree"]["children"][0] = {"id": "glyph", "type": "icon", "icon": "rocket"}
    report = storyboard.validate(data)
    assert not report.ok
    assert any(issue.path.endswith(".icon") for issue in report.errors)


def test_pictogram_takes_a_whitelisted_icon():
    assert storyboard.validate(quantity("pictogram", 42, icon="users")).ok
    report = storyboard.validate(quantity("pictogram", 42, icon="rocket"))
    assert not report.ok and any(issue.path.endswith(".icon") for issue in report.errors)


@pytest.mark.parametrize("node_type", ["gauge", "pictogram"])
@pytest.mark.parametrize("value,ok", [(0, True), (42, True), (100, True), (120, False), (-1, False), ("42", False)])
def test_quantity_content_range(node_type, value, ok):
    report = storyboard.validate(quantity(node_type, value))
    assert report.ok is ok
    if not ok:
        assert any(issue.path.endswith(".contentRef") for issue in report.errors)


def test_quantity_requires_content_reference():
    data = quantity("gauge", 42)
    del data["scenes"][0]["sceneTree"]["contentRef"]
    # 缺内容引用时不会静默画一个空盘：校验器必须报出来
    assert not storyboard.validate(data).ok


def test_midlevel_props_are_consumed_by_the_renderer():
    source = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "web/src/primitives/SceneTree.tsx"
    ).read_text(encoding="utf-8")
    for node_type in MIDLEVEL:
        assert f"a2v-primitive-{node_type}" in source or f"'{node_type}'" in source
        for prop in catalog.PRIMITIVE_CATALOG[node_type].props:
            assert prop in source, f"{node_type}.{prop} 未被渲染器消费"
