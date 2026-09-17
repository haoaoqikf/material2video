"""视觉组件库的静态契约。

组件库是「AI 只选组件、不画组件」这条链路的地基，因此这里锁定最容易
静默出错的几处：注册表与页面声明的 kind 是否对得上、组件取的每个
data-el 是否真的存在于自己的 markup、以及库里有没有引入时间/随机源。
这些都是纯静态检查，不需要浏览器，可以在每次提交时跑。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1] / ".agents/skills/article2video"
FIGURES_JS = SKILL / "assets/figures.js"
FIGURES_CSS = SKILL / "assets/figures.css"
PAGE = SKILL.parents[2] / "videos/never-fear-interviews/index.html"

# 每注册一个组件：define('kind', [...labels], MARKUP_X, updateX)
_DEFINE = re.compile(r"define\('([a-z0-9-]+)',\s*(\[[^\]]*\]),\s*([A-Z_]+),\s*(\w+)\);")


def _source() -> str:
    return FIGURES_JS.read_text(encoding="utf-8")


def _figures() -> list[tuple[str, list[str], str, str, str]]:
    """返回 (kind, labels, markup, markup_source, body)。

    文件结构固定为「函数体 → markup 常量 → define 调用」，因此每个组件的
    函数体落在上一个 define 结束与自己的 markup 常量之间。
    """
    text = _source()
    matches = list(_DEFINE.finditer(text))
    found = []
    for index, match in enumerate(matches):
        kind, labels, markup_name, _update = match.groups()
        start = matches[index - 1].end() if index > 0 else 0
        marker = f"var {markup_name} = "
        end = text.index(marker, start)
        markup_match = re.search(rf"var {markup_name} = `(.*?)`;", text, re.DOTALL)
        assert markup_match, markup_name
        found.append((kind, json.loads(labels), markup_match.group(1), markup_name, text[start:end]))
    return found


def test_library_registers_the_expected_kinds():
    kinds = [kind for kind, *_ in _figures()]
    assert kinds == ["balance", "gap", "iceberg", "loop", "stairs", "exchange"]


def test_exposes_the_public_api():
    text = _source()
    assert "A2V.figures = {" in text
    for name in ("register", "known", "mount", "renderScene", "describe"):
        assert re.search(rf"\b{name}: {name}\b", text), name


@pytest.mark.parametrize("kind", [kind for kind, *_ in _figures()])
def test_every_picked_element_exists_in_its_markup(kind):
    """组件按 data-el 取元素，取错名字不会报错，只会让画面对不上。

    这类错误在逐帧渲染里表现为「某个元素始终不动」，很难从成片上定位，
    所以在这里静态对照 markup 与函数体。
    """
    for name, _labels, markup, markup_source, body in _figures():
        if name != kind:
            continue
        available = set(re.findall(r'data-el="([^"]+)"', markup))
        assert available, f"{markup_source} 没有任何 data-el"
        # markup 常量本身与 define 行不属于函数体，排除后再找 pick
        for picked in sorted(set(re.findall(r"pick\('([^']+)'\)", body))):
            assert picked in available, f"{kind} 取了 markup 里不存在的 data-el: {picked}"


@pytest.mark.parametrize("kind", [kind for kind, *_ in _figures()])
def test_component_body_has_no_time_or_random_source(kind):
    for name, _labels, _markup, _source, body in _figures():
        if name != kind:
            continue
        for pattern in (r"\bDate\.now\s*\(", r"\bperformance\.now\s*\(", r"\bMath\.random\s*\("):
            assert not re.search(pattern, body), f"{kind} 使用了 {pattern}"


def test_stylesheet_has_no_clock_driven_motion():
    text = FIGURES_CSS.read_text(encoding="utf-8")
    for pattern in (r"@keyframes\b", r"(?<![\w-])animation(?:-[\w-]+)?\s*:", r"(?<![\w-])transition(?:-[\w-]+)?\s*:"):
        assert not re.search(pattern, text), pattern


def test_page_defaults_point_at_registered_kinds():
    """页面给出的「类型 → 默认组件」必须都能挂载，否则渲染时才抛错。"""
    page = PAGE.read_text(encoding="utf-8")
    match = re.search(r"var DEFAULT_FIGURES = \{(.*?)\};", page, re.DOTALL)
    assert match, "页面不再声明 DEFAULT_FIGURES"
    mapping = dict(re.findall(r"(\w+):\s*'([\w-]+)'", match.group(1)))
    assert mapping, "DEFAULT_FIGURES 为空"
    registered = {kind for kind, *_ in _figures()}
    for scene_type, kind in mapping.items():
        assert kind in registered, f"场景类型 {scene_type} 指向未注册的组件 {kind}"


def test_page_mounts_a_figure_slot_in_every_scene():
    page = PAGE.read_text(encoding="utf-8")
    scenes = page.count("<section data-a2v-scene")
    slots = page.count("data-a2v-figure")
    assert scenes > 0
    assert slots == scenes, f"{scenes} 个场景只有 {slots} 个挂载点"


def test_storyboard_annotation_keys_are_declared_by_the_component():
    """分镜写的标注键必须落在组件的 labels 声明里。

    拼错键名不会报错，只会让某个标签空着，因此在这里对照一次。
    """
    declared = {kind: labels for kind, labels, *_ in _figures()}
    page = PAGE.read_text(encoding="utf-8")
    mapping = dict(re.findall(r"(\w+):\s*'([\w-]+)'", re.search(r"var DEFAULT_FIGURES = \{(.*?)\};", page, re.DOTALL).group(1)))
    storyboard = json.loads((PAGE.parent / "storyboard.json").read_text(encoding="utf-8"))
    for scene in storyboard["scenes"]:
        annotations = (scene["data"].get("figure") or {}).get("labels")
        if annotations is None:
            annotations = scene["data"].get("annotations")
        if not annotations:
            continue
        kind = (scene["data"].get("figure") or {}).get("kind") or mapping[scene["type"]]
        unknown = set(annotations) - set(declared[kind])
        assert not unknown, f"场景 {scene['id']} 给 {kind} 传了未声明的标注键: {sorted(unknown)}"
