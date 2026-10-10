"""字号取档（preset fit）在契约页里的实测行为。

规格（declarative-video-scenes）要求：v3 的 keynote 设计语言预设为必填；共享 composition
对**声明了字号档上限**的文字原语按实测宽度取档，且记录最终档位；同一帧重复取档
不产生节点样式或内容改动。

这里问的是浏览器里的实测结果，不是样式表文本：取档依赖真实的字体度量，
jsdom 量不出来，只能在契约页上验。
"""

from __future__ import annotations

import json
import pathlib

import pytest

from a2v import browser, contract_page
from conftest import v4_storyboard

ROOT = pathlib.Path(__file__).resolve().parents[1]
def _preset_storyboard(tmp_path: pathlib.Path, headline: str = "快速反馈") -> pathlib.Path:
    article = tmp_path / "examples" / "preset-fit"
    article.mkdir(parents=True)
    data = v4_storyboard()
    data["world"]["data"]["headline"] = headline
    target = article / "storyboard.json"
    target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return target


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


def test_preset_fit_is_measured_and_recorded(chromium_ready, tmp_path):
    """预设启用：声明了字号档的文字节点被实测，档位与是否实测记录在节点上。"""
    _skip_if_unbuilt()
    storyboard = _preset_storyboard(tmp_path)
    with contract_page.serve_contract_page(storyboard, tmp_path, repo_root=ROOT) as url:
        with browser.open_animated_page(url, width=1080, height=1920, expected_version=4) as page:
            page.seek(30)
            facts = page.evaluate(_FIT_FACTS)
            ready = page.evaluate("document.querySelector('[data-a2v-world]').dataset.a2vLayoutReady")
            camera_at_30 = page.evaluate("document.querySelector('[data-a2v-camera=global]').dataset.a2vCameraX")
            page.seek(0)
            page.seek(30)
            camera_after_reverse_seek = page.evaluate("document.querySelector('[data-a2v-camera=global]').dataset.a2vCameraX")
    assert ready == "1", "契约 ready/seek 返回前必须完成 tree 布局预检"
    assert camera_after_reverse_seek == camera_at_30, "后段到前段再寻回时镜头几何必须稳定"
    declared = [item for item in facts if item["fitMeasured"] is not None]
    assert declared, "预设启用时没有任何文字节点被实测取档"
    for item in declared:
        assert item["fitMeasured"] == "true"
        assert item["fitRole"], "取档后必须记录最终档位"


def test_repeat_fit_on_the_same_frame_writes_nothing_new(chromium_ready, tmp_path):
    """同一帧重复取档：档位与类名稳定，第二次不产生新的节点改动。"""
    _skip_if_unbuilt()
    storyboard = _preset_storyboard(tmp_path)
    with contract_page.serve_contract_page(storyboard, tmp_path, repo_root=ROOT) as url:
        with browser.open_animated_page(url, width=1080, height=1920, expected_version=4) as page:
            page.seek(30)
            first = page.evaluate(_FIT_FACTS)
            second = page.evaluate(_FIT_FACTS)
            page.seek(31)
            third = page.evaluate(_FIT_FACTS)
    assert first == second, "同一帧重复取档产生了改动"
    assert first == third, "相邻帧的取档结果应当一致（布局不随帧漂移）"


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_preflight_is_ready_and_text_stays_in_safe_area_on_phone_viewport(chromium_ready, tmp_path, theme):
    """深浅主题和手机缩放只改变画布呈现，不应破坏布局就绪或安全区包含。"""
    _skip_if_unbuilt()
    storyboard = json.loads(_preset_storyboard(tmp_path).read_text(encoding="utf-8"))
    storyboard["visual"]["theme"] = theme
    target = tmp_path / f"storyboard-{theme}.json"
    target.write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
    with contract_page.serve_contract_page(target, tmp_path, repo_root=ROOT) as url:
        with browser.open_animated_page(url, width=360, height=640, expected_version=4) as page:
            facts = page.evaluate("""() => {
              const safe = document.querySelector('.a2v-safe').getBoundingClientRect();
              const text = document.querySelector('[data-a2v-node-id="caption"]').getBoundingClientRect();
              return { ready: document.querySelector('[data-a2v-world]').dataset.a2vLayoutReady,
                safe: { left: safe.left, right: safe.right, top: safe.top, bottom: safe.bottom },
                text: { left: text.left, right: text.right, top: text.top, bottom: text.bottom } };
            }""")
    assert facts["ready"] == "1"
    assert facts["text"]["left"] >= facts["safe"]["left"] - 1
    assert facts["text"]["right"] <= facts["safe"]["right"] + 1
    assert facts["text"]["top"] >= facts["safe"]["top"] - 1
    assert facts["text"]["bottom"] <= facts["safe"]["bottom"] + 1


def test_text_that_exceeds_line_limit_is_reported_as_not_fitting(chromium_ready, tmp_path):
    """最低字号仍超过四行的中文文案留下 K7 可识别的失败标记。"""
    _skip_if_unbuilt()
    storyboard = _preset_storyboard(tmp_path, "反馈周期" * 180)
    with contract_page.serve_contract_page(storyboard, tmp_path, repo_root=ROOT) as url:
        with browser.open_animated_page(url, width=1080, height=1920, expected_version=4) as page:
            facts = page.evaluate("""() => {
              const text = document.querySelector('[data-a2v-node-id="caption"]');
              return { fits: text.dataset.a2vFitFits, role: text.dataset.a2vFitRole,
                lines: (() => { const r = document.createRange(); r.selectNodeContents(text.querySelector('span')); return r.getClientRects().length; })() };
            }""")
    assert facts["role"] == "caption"
    assert facts["lines"] > 4
    assert facts["fits"] == "false"


def test_stage_text_change_remeasures_after_reverse_seek(chromium_ready, tmp_path):
    """阶段数据切换文案时重新取档；后段到前段再返回不沿用旧测量。"""
    _skip_if_unbuilt()
    storyboard = json.loads(_preset_storyboard(tmp_path).read_text(encoding="utf-8"))
    storyboard["stages"][1]["data"]["headline"] = "阶段切换后的长文案" * 40
    target = tmp_path / "storyboard-dynamic.json"
    target.write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
    with contract_page.serve_contract_page(target, tmp_path, repo_root=ROOT) as url:
        with browser.open_animated_page(url, width=1080, height=1920, expected_version=4) as page:
            page.seek(0)
            initial = page.evaluate("""() => {
              const el = document.querySelector('[data-a2v-node-id="caption"]');
              return { text: el.textContent, role: el.dataset.a2vFitRole, fits: el.dataset.a2vFitFits };
            }""")
            page.seek(400)
            changed = page.evaluate("""() => {
              const el = document.querySelector('[data-a2v-node-id="caption"]');
              return { text: el.textContent, role: el.dataset.a2vFitRole, fits: el.dataset.a2vFitFits };
            }""")
            page.seek(0)
            page.seek(400)
            repeated = page.evaluate("""() => {
              const el = document.querySelector('[data-a2v-node-id="caption"]');
              return { text: el.textContent, role: el.dataset.a2vFitRole, fits: el.dataset.a2vFitFits };
            }""")
    assert initial["text"] == "快速反馈"
    assert changed["text"] == "阶段切换后的长文案" * 40
    assert changed["role"] == "caption" and changed["fits"] == "false"
    assert repeated == changed
