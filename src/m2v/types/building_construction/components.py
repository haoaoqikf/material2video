"""建筑构件 ID 的确定性生成与选择器展开。

Python 校验器与前端渲染器使用同一套规则：场地、开挖、基础、柱、梁、板、
楼梯与梯井、墙体、屋顶、门窗与庭院。这里只生成身份与类别，最终几何由
前端按 `house` 参数计算。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

SIDES = ("front", "back", "left", "right")


@dataclass(frozen=True)
class Component:
    id: str
    kind: str
    floor: int


def _add(components: list[Component], identity: str, kind: str, floor: int = 0) -> None:
    if any(item.id == identity for item in components):
        raise ValueError(f"构件 ID 重复：{identity}")
    components.append(Component(identity, kind, floor))


def build_components(house: dict[str, Any]) -> list[Component]:
    """按 v2 `house` 参数生成全部构件；顺序固定。"""
    components: list[Component] = []
    floors = int(house["floors"])
    bays = int(house["bayCount"])
    _add(components, "site", "site")
    _add(components, "excavation", "excavation")
    _add(components, "foundation-slab", "foundation")
    for side in SIDES:
        _add(components, f"foundation-ring-{side}", "foundation")
    for floor in range(1, floors + 1):
        _add(components, f"slab-{floor}", "slab", floor)
        for bay in range(bays + 1):
            for side in ("front", "back"):
                _add(components, f"column-{floor}-{bay}-{side}", "column", floor)
        for side in ("front", "back"):
            for bay in range(bays):
                _add(components, f"beam-{floor}-{side}-{bay}", "beam", floor)
        for side in ("left", "right"):
            _add(components, f"beam-{floor}-{side}", "beam", floor)
        for side in SIDES:
            _add(components, f"wall-{floor}-{side}-0", "wall", floor)
        if floor < floors:
            _add(components, f"stairwell-{floor}", "stair", floor)
            for step in range(10):
                _add(components, f"stair-{floor}-{step}", "stair", floor)
    _add(components, f"stairwell-{floors}", "stair", floors)
    roof = house["roof"]
    if roof["type"] == "gable":
        for panel in ("left", "right"):
            _add(components, f"roof-{panel}", "roof", floors)
        _add(components, "roof-ridge", "roof", floors)
        _add(components, "roof-gable-front", "roof", floors)
        _add(components, "roof-gable-back", "roof", floors)
    else:
        _add(components, "roof-slab", "roof", floors)
        for side in SIDES:
            _add(components, f"parapet-{side}", "roof", floors)
    for opening in house["openings"]:
        _add(components, f"opening-{opening['id']}", "opening", int(opening["floor"]))
        _add(components, f"finish-{opening['id']}", "finish", int(opening["floor"]))
    _add(components, "yard-path", "yard")
    _add(components, "yard-steps", "yard")
    _add(components, "yard-hedge", "yard")
    return components


def expand_selector(components: Iterable[Component], selector: str) -> list[str]:
    """展开只支持末尾 `*` 的简单 glob；未知字符或中间 `*` 视为错误。"""
    if "*" in selector[:-1] or selector.count("*") > 1:
        raise ValueError(f"选择器只支持末尾一个 *：{selector}")
    if selector.endswith("*"):
        prefix = selector[:-1]
        return [item.id for item in components if item.id.startswith(prefix)]
    return [item.id for item in components if item.id == selector]
