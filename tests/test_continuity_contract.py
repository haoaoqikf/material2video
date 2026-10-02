"""跨幕连续性在真实 composition 中同时保留源节点与目标节点。"""

from __future__ import annotations

import pathlib

import pytest

from a2v import browser, contract_page


ROOT = pathlib.Path(__file__).resolve().parents[1]
STORYBOARD = ROOT / "examples" / "buffer-smoothing" / "storyboard.json"

# These source/target transition assertions exercise the retired v3 renderer.
pytestmark = pytest.mark.skip(reason="v3 scene transition contract retired; v4 continuity uses world identity/state tracks")


@pytest.fixture(scope="module")
def continuity_page(chromium_ready):
    page_file = contract_page.contract_page_path()
    if not page_file.is_file():
        pytest.skip(f"契约页尚未构建：{page_file}")
    with contract_page.serve_contract_page(STORYBOARD, ROOT) as url:
        with browser.open_animated_page(url, width=1080, height=1920) as page:
            yield page


def _state(page) -> dict:
    return page.evaluate(
        "() => { const scenes = [...document.querySelectorAll('[data-a2v-scene]')];"
        "return { visible: scenes.filter((el) => getComputedStyle(el).display !== 'none').map((el) => el.dataset.sceneId),"
        "source: document.querySelector('[data-a2v-node-id][data-a2v-continuity-phase=\"source\"]')?.getAttribute('data-a2v-node-id'),"
        "target: document.querySelector('[data-a2v-node-id][data-a2v-continuity-phase=\"target\"]')?.getAttribute('data-a2v-node-id') }; }"
    )


def test_transform_keeps_source_and_target_during_window(continuity_page):
    continuity_page.seek(210)
    state = _state(continuity_page)
    assert state["visible"] == ["claim", "stages"]
    assert state["source"] == "claim-text"
    assert state["target"] == "stages-title"

    continuity_page.seek(240)
    assert _state(continuity_page)["visible"] == ["stages"]


def test_decompose_exposes_one_source_and_all_targets(continuity_page):
    # claim 210 + stages 255 + loop 300 = milestones 的首帧
    continuity_page.seek(765)
    state = continuity_page.evaluate(
        "() => ({ source: [...document.querySelectorAll('[data-a2v-node-id][data-a2v-continuity-phase=\"source\"]')].map((el) => el.getAttribute('data-a2v-node-id'))," 
        "targets: [...document.querySelectorAll('[data-a2v-node-id][data-a2v-continuity-phase=\"target\"]')].map((el) => el.getAttribute('data-a2v-node-id')) })"
    )
    assert state["source"] == ["loop-ring"]
    assert state["targets"] == ["tl-a", "tl-b", "tl-c", "tl-d"]
