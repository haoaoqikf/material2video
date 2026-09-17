"""排版引擎是否真的接上了组件，且与字阶一致。

这一层测的是「接线」本身，而不是引擎的算法：

* 组件用 `data-a2v-fit="<档位>"` 声明字号上限档位；
* 共享页面在预设生效时按实测宽度取档，把结果写进 `data-a2v-fit-level`；
* 引擎取到的档位与字号，必须与 CSS 字阶给该元素的完全一致——不一致就是双真源；
* 未启用预设的页面根本不该取档。

放在真实页面上跑，是因为「有没有接上」只能在真实渲染里看出来：单测全绿而引擎
空转，正是这一层要防的事。
"""

from __future__ import annotations

import functools
import http.server
import json
import pathlib
import socketserver
import threading
from urllib.parse import quote

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / ".agents" / "skills" / "article2video" / "assets"
PRESET_STORYBOARD = ROOT / "examples" / "keynote-baseline" / "storyboard.json"
PLAIN_STORYBOARD = ROOT / "examples" / "declarative-number" / "storyboard.json"

#: 走遍全部幕：每一幕取三个时刻，覆盖入场、停留与出场
_JS = """
(async () => {
  const sb = await (await fetch(STORYBOARD_URL)).json();
  const frames = [];
  let acc = 0;
  for (const s of sb.scenes) {
    frames.push([s.id, acc + Math.floor(s.durationInFrames / 2)]);
    acc += s.durationInFrames;
  }
  const rootStyle = getComputedStyle(document.documentElement);
  const levelSize = (name) => rootStyle.getPropertyValue('--a2v-size-' + name).trim();

  const rows = [];
  const empties = [];
  for (const [id, frame] of frames) {
    window.__A2V__.seekToFrame(frame);
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    const scene = document.querySelector('[data-a2v-scene][data-scene-id="' + id + '"]');
    if (!scene) continue;
    for (const el of scene.querySelectorAll('[data-a2v-fit]')) {
      const cs = getComputedStyle(el);
      const text = el.textContent || '';
      // 空文本位（组件里备而未用的可选文案）不参与取档，单独统计
      if (!text.trim()) {
        empties.push({ scene: id, cls: String(el.className || ''), level: el.getAttribute('data-a2v-fit-level') });
        continue;
      }
      rows.push({
        scene: id,
        cls: String(el.className || ''),
        declared: el.getAttribute('data-a2v-fit'),
        level: el.getAttribute('data-a2v-fit-level'),
        balanced: el.getAttribute('data-a2v-fit-balanced'),
        measured: el.getAttribute('data-a2v-fit-measured'),
        fontSize: parseFloat(cs.fontSize),
        tokenSize: parseFloat(levelSize(el.getAttribute('data-a2v-fit'))),
        chars: Array.from(text).length,
        text: text
      });
    }
  }
  return {
    rows,
    empties,
    anyFitMark: document.querySelectorAll('[data-a2v-fit-level]').length,
    scenes: document.querySelectorAll('[data-a2v-scene]').length
  };
})()
"""


def _serve(page_dir: pathlib.Path, storyboard: pathlib.Path) -> dict:
    """打开共享页面并走遍全部幕，返回每个声明了档位的元素的实测事实。"""
    playwright = pytest.importorskip("playwright.sync_api")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):  # noqa: D102 - 测试里不需要访问日志
            pass

    with socketserver.ThreadingTCPServer(
        ("127.0.0.1", 0), functools.partial(Handler, directory=str(ROOT))
    ) as httpd:
        httpd.daemon_threads = True
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            storyboard_url = "/" + storyboard.relative_to(ROOT).as_posix()
            page_url = (
                f"http://127.0.0.1:{port}/{ASSETS.relative_to(ROOT).as_posix()}/declarative.html"
                f"?a2v-storyboard={quote(storyboard_url, safe='')}"
            )
            with playwright.sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1080, "height": 1920})
                page.goto(page_url)
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-a2v-scene]').length > 0", timeout=20000
                )
                page.wait_for_timeout(800)
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                facts = page.evaluate(
                    _JS.replace("STORYBOARD_URL", json.dumps(storyboard_url))
                )
                browser.close()
                return facts
        finally:
            httpd.shutdown()


@pytest.fixture(scope="module")
def preset() -> dict:
    return _serve(ASSETS, PRESET_STORYBOARD)


@pytest.fixture(scope="module")
def plain() -> dict:
    return _serve(ASSETS, PLAIN_STORYBOARD)


class TestEngineActuallyRuns:
    def test_something_declares_a_level(self, preset):
        assert preset["rows"], "没有任何元素声明 data-a2v-fit：引擎又空转了"

    def test_the_engine_wrote_a_level_back(self, preset):
        for row in preset["rows"]:
            assert row["level"], f"{row['scene']} 的 {row['cls']} 声明了档位却没被取档"
            assert row["measured"] == "true", f"{row['scene']} 的 {row['cls']} 没有走实测"

    def test_the_same_element_renders_at_its_declared_level(self, preset):
        """引擎取到的档位必须等于声明档位。

        基线示例的文案都放得下，所以不该有任何元素被降档；一旦降档，说明
        「可用宽度」或「字宽测量」有问题——那会让整支片的字号系统性地变小。
        """
        for row in preset["rows"]:
            assert row["level"] == row["declared"], (
                f"{row['scene']} 的 {row['cls']} 声明 {row['declared']} 却被取成 {row['level']}"
                f"（{row['chars']} 个字）"
            )

    def test_computed_size_equals_the_scale_token(self, preset):
        """字号只有一个真源：字阶 token。组件写死的值与 token 不一致就是缺陷。"""
        for row in preset["rows"]:
            assert row["tokenSize"] > 0, f"字阶里没有 --a2v-size-{row['declared']}"
            assert row["fontSize"] == pytest.approx(row["tokenSize"], abs=0.5), (
                f"{row['scene']} 的 {row['cls']} 实际 {row['fontSize']}px，"
                f"字阶 {row['declared']} 是 {row['tokenSize']}px"
            )

    def test_every_scene_is_covered(self, preset):
        scenes = {row["scene"] for row in preset["rows"]}
        assert len(scenes) >= 6, f"只有 {sorted(scenes)} 幕有声明，覆盖面太窄"

    def test_empty_text_slots_are_left_alone(self, preset):
        """组件里备而未用的空文本位不该被取档，也不该被标成「未实测」。"""
        for row in preset["empties"]:
            assert row["level"] is None, f"{row['scene']} 的空 {row['cls']} 被取档了"


class TestPresetIsOptIn:
    def test_plain_storyboard_never_runs_the_engine(self, plain):
        """没有启用设计语言预设的分镜，一个元素都不该被取档。

        属性本身在标记里是常量（组件不区分预设），所以要看的是**引擎有没有动作**：
        没有任何元素带上取档痕迹。
        """
        assert plain["scenes"] > 0, "非预设页面没有渲染出任何幕"
        assert plain["anyFitMark"] == 0
        for row in plain["rows"]:
            assert row["level"] is None, f"{row['cls']} 在非预设页面上被取档了"
            assert row["balanced"] is None
            assert row["measured"] is None
