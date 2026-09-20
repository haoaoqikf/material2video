"""字号取档（preset fit）在契约页里的实测行为。

规格（declarative-video-scenes）要求：设计语言预设启用时，共享 composition
对**声明了字号档上限**的文字原语按实测宽度取档；档位与是否实测要记录在节点上；
未启用预设时不取档；同一帧重复取档不产生节点样式或内容改动。

这里问的是浏览器里的实测结果，不是样式表文本：取档依赖真实的字体度量，
jsdom 量不出来，只能在契约页上验。
"""

from __future__ import annotations

import pathlib

import pytest

from a2v import browser, contract_page

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAIN = ROOT / "examples" / "declarative-number" / "storyboard.json"
PRESET = ROOT / "examples" / "keynote-baseline" / "storyboard.json"


def _skip_if_unbuilt() -> None:
    page = contract_page.contract_page_path()
    if not page.is_file():
        pytest.skip(f"契约页尚未构建：{page}（先执行 cd web && pnpm install && pnpm build）")


_FIT_FACTS = """
() => {
  const nodes = Array.from(document.querySelectorAll('[data-a2v-primitive="text"]'));
  return nodes.map((el) => ({
    id: el.getAttribute('data-a2v-node-id'),
    fitRole: el.getAttribute('data-a2v-fit-role'),
    fitMeasured: el.getAttribute('data-a2v-fit-measured'),
    className: el.querySelector('span') ? el.querySelector('span').className : '',
  }));
}
"""


def test_preset_fit_is_measured_and_recorded(chromium_ready):
    """预设启用：声明了字号档的文字节点被实测，档位与是否实测记录在节点上。"""
    _skip_if_unbuilt()
    with contract_page.serve_contract_page(PRESET, ROOT) as url:
        with browser.open_animated_page(url, width=1080, height=1920) as page:
            page.seek(30)
            facts = page.evaluate(_FIT_FACTS)
    declared = [item for item in facts if item["fitMeasured"] is not None]
    assert declared, "预设启用时没有任何文字节点被实测取档"
    for item in declared:
        assert item["fitMeasured"] == "true"
        assert item["fitRole"], "取档后必须记录最终档位"


def test_no_preset_means_no_fit(chromium_ready):
    """未启用预设：不执行取档，节点上不出现取档记录。"""
    _skip_if_unbuilt()
    with contract_page.serve_contract_page(PLAIN, ROOT) as url:
        with browser.open_animated_page(url, width=1080, height=1920) as page:
            page.seek(10)
            facts = page.evaluate(_FIT_FACTS)
    assert facts, "示例应有文字原语"
    offenders = [item["id"] for item in facts if item["fitMeasured"] is not None]
    assert not offenders, f"未启用预设却出现了取档记录：{offenders}"


def test_repeat_fit_on_the_same_frame_writes_nothing_new(chromium_ready):
    """同一帧重复取档：档位与类名稳定，第二次不产生新的节点改动。"""
    _skip_if_unbuilt()
    with contract_page.serve_contract_page(PRESET, ROOT) as url:
        with browser.open_animated_page(url, width=1080, height=1920) as page:
            page.seek(30)
            first = page.evaluate(_FIT_FACTS)
            second = page.evaluate(_FIT_FACTS)
            page.seek(31)
            third = page.evaluate(_FIT_FACTS)
    assert first == second, "同一帧重复取档产生了改动"
    assert first == third, "相邻帧的取档结果应当一致（布局不随帧漂移）"
