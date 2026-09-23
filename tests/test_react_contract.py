"""React 契约页的渲染契约（`__A2V__` version 2）。

分两层：

- **页面层**（需要构建产物与 Chromium）：`seekToFrame(42)` 之后画面上的帧号等于 42、
  连续两次求值结果一致，以及「所有幕都在 DOM 里、只有一幕可见」这条动效量测依赖的结构；
- **判定层**（纯函数，不需要浏览器）：契约版本不符、帧率/尺寸/总帧数与分镜不一致时
  报错**并列出两边的值**。

页面层的用例在契约页未构建时跳过而不是失败：构建产物不入库，
`cd web && pnpm install && pnpm build` 之后才会出现。但跳过必须写清原因——
空转的检查与通过的检查在报告里长得一样，这正是这套机检一直在消灭的失败模式。
"""

from __future__ import annotations

import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STORYBOARD = ROOT / "examples" / "declarative-number" / "storyboard.json"

from a2v import browser, contract_page, render  # noqa: E402
from a2v.errors import A2VError  # noqa: E402


def _expected_span(frame: int) -> tuple[int, int]:
    """第 frame 帧属于第几幕、幕内第几帧。

    刻意在这里重新累加一遍，而不是调 `timeline.ts` 的等价物：
    这是测试的独立实现，能发现「两边一起改错」的情况。
    """
    scenes = json.loads(STORYBOARD.read_text(encoding="utf-8"))["scenes"]
    cursor = 0
    for index, scene in enumerate(scenes):
        length = int(scene["durationInFrames"])
        if frame < cursor + length:
            return index, frame - cursor
        cursor += length
    raise AssertionError(f"第 {frame} 帧超出分镜总长 {cursor}")


@pytest.fixture(scope="module")
def contract_url():
    page = contract_page.contract_page_path()
    if not page.is_file():
        pytest.skip(f"契约页尚未构建：{page}（先执行 cd web && pnpm install && pnpm build）")
    with contract_page.serve_contract_page(STORYBOARD, ROOT) as url:
        yield url


@pytest.fixture(scope="module")
def opened(contract_url, chromium_ready):
    with browser.open_animated_page(contract_url, width=1080, height=1920) as page:
        yield page


def test_contract_is_version_two(opened):
    assert opened.contract.version == browser.CONTRACT_VERSION
    assert opened.contract.fps == 30
    assert (opened.contract.width, opened.contract.height) == (1080, 1920)


def _visible_state(page) -> dict:
    """当前可见那一幕的「帧号 + 画面签名」。

    画面签名取可见幕第一个子元素的计算 `transform` / `opacity`：它们是**由帧号推出来**的
    （入场位移与常驻微动），因此「seek 到了第 42 帧」不只是 Player 自报的数字，
    而是画面真的按第 42 帧画了一遍。

    不再依赖占位文案：这一版 composition 画的是真实图形组件
    （`A2VComposition` → 注册表 → 组件），不再有「第 N 帧」这类调试文本。
    """
    return page.evaluate(
        "() => {"
        "const scenes = [...document.querySelectorAll('[data-a2v-scene]')];"
        "const active = scenes.find((el) => getComputedStyle(el).display !== 'none');"
        "const node = active ? active.querySelector('.a2v-safe > *') : null;"
        "const style = node ? getComputedStyle(node) : null;"
        "return {scene: active ? active.getAttribute('data-scene-id') : null,"
        "frame: window.__A2V__.currentFrame(),"
        "transform: style ? style.transform : '',"
        "opacity: style ? style.opacity : ''};}"
    )


def test_seek_lands_on_the_requested_frame_and_repeats(opened):
    """seek 之后 Player 落在请求的帧上，同一帧求值两次给同一个画面。"""
    index, _local = _expected_span(42)
    scenes = json.loads(STORYBOARD.read_text(encoding="utf-8"))["scenes"]

    opened.seek(42)
    first = _visible_state(opened)
    assert first["frame"] == 42, first
    assert first["scene"] == scenes[index]["id"], first

    # 先去别的帧再回来：随机访问与顺序访问必须给同一个结果
    opened.seek(7)
    assert _visible_state(opened)["frame"] == 7
    opened.seek(42)
    assert _visible_state(opened) == first, "同一帧两次求值的结果不一致"

    # 换一幕：可见的那一幕必须跟着帧号换（画面确实由帧号推导）
    opened.seek(150)
    later = _visible_state(opened)
    assert later["frame"] == 150, later
    assert later["scene"] == scenes[1]["id"], later


def test_every_scene_stays_in_the_dom_with_exactly_one_visible(opened):
    """动效量测按 `[data-a2v-scene]` 的下标定位幕。

    只渲染当前幕会让下标 1 之后全部取到 undefined，扫描直接崩在页面里；
    而探针又是按「第一个非隐藏的幕」判定当前幕的，所以隐藏方式也必须一致。
    """
    scene_count = len(json.loads(STORYBOARD.read_text(encoding="utf-8"))["scenes"])
    for frame in (0, 42, 179):
        opened.seek(frame)
        state = opened.evaluate(
            "() => {"
            "const all = [...document.querySelectorAll('[data-a2v-scene]')];"
            "return {total: all.length,"
            "visible: all.filter((el) => getComputedStyle(el).display !== 'none').length,"
            "ids: all.map((el) => el.getAttribute('data-scene-id'))};}"
        )
        assert state["total"] == scene_count
        assert state["visible"] == 1
        assert state["ids"] == ["count", "closing"]


def test_scene_index_does_not_render_scene_numbers(opened):
    """发布会预设保留作者角标，但不再渲染「01 / 10」幕序号。"""
    opened.seek(0)
    state = opened.evaluate(
        "() => ({"
        "indexCount: document.querySelectorAll('.a2v-scene-number').length,"
        "indexText: [...document.querySelectorAll('.a2v-scene-index')].map((el) => el.textContent)"
        "})"
    )
    assert state["indexCount"] == 0, state
    assert all("/" not in text for text in state["indexText"]), state


def test_scene_zero_has_no_entrance_but_frame_zero_is_readable(opened):
    """第 0 帧必须能读到内容：契约页的 `ready()` 承诺首帧已经画出来了。"""
    opened.seek(0)
    text = opened.evaluate("() => document.querySelector('.a2v-safe').textContent")
    assert text.strip(), "首帧是空的：ready() 没有等到画面可用"


def test_fonts_are_registered_and_loaded(opened):
    """两套随仓库分发的字体必须真的加载完成。

    「字体静默回退成系统字体」在成片里几乎看不出来（浏览器不报错、不警告，
    字宽字重却全变了），因此这条断言是必须的：它问的是注册表里那两个
    字族有没有到 `loaded`，而不是画面看起来对不对。
    """
    state = opened.evaluate(
        "() => ({"
        "loaded: [...document.fonts].filter((f) => f.status === 'loaded')"
        ".map((f) => f.family),"
        "inter: document.fonts.check('16px \"A2V Inter\"'),"
        "sans: document.fonts.check('16px \"A2V Sans\"')})"
    )
    # 字族名从 CSSOM 读回来时带引号（`"A2V Inter"`），比较前先归一化
    loaded = {name.strip('"') for name in state["loaded"]}
    assert "A2V Inter" in loaded, state
    assert "A2V Sans" in loaded, state
    assert state["inter"] and state["sans"], state


def _contract(fps: int = 30, frames: int = 180, width: int = 1080, height: int = 1920):
    return browser.PageContract(
        fps=fps, duration_in_frames=frames, width=width, height=height
    )


def _storyboard_like(fps: int = 30, frames: int = 180, width: int = 1080, height: int = 1920):
    import types

    return types.SimpleNamespace(
        fps=fps, total_frames=frames, width=width, height=height
    )


def test_rejects_a_page_that_does_not_declare_a_version():
    """旧页面（version 1）必须被明确拒绝，而不是等它在首帧截图上出问题。"""
    raw = {
        "ready": "function",
        "seek": "function",
        "version": None,
        "fps": 30,
        "durationInFrames": 180,
        "width": 1080,
        "height": 1920,
    }
    with pytest.raises(browser.BrowserError) as excinfo:
        browser._validate_contract(raw, "http://example.invalid/page.html")
    message = str(excinfo.value)
    assert "version" in message
    assert str(browser.CONTRACT_VERSION) in message


def test_rejects_a_page_with_the_wrong_version():
    raw = {
        "ready": "function",
        "seek": "function",
        "version": 1,
        "fps": 30,
        "durationInFrames": 180,
        "width": 1080,
        "height": 1920,
    }
    with pytest.raises(browser.BrowserError) as excinfo:
        browser._validate_contract(raw, "http://example.invalid/page.html", browser.CONTRACT_VERSION)
    message = str(excinfo.value)
    assert "1" in message and "2" in message


def test_legacy_version_is_accepted_where_it_is_not_required():
    """迁移期旧页面仍要能渲：不传 expected_version 时不因版本拦人。"""
    raw = {
        "ready": "function",
        "seek": "function",
        "version": contract_page.LEGACY_CONTRACT_VERSION,
        "fps": 30,
        "durationInFrames": 180,
        "width": 1080,
        "height": 1920,
    }
    browser._validate_contract(raw, "http://example.invalid/page.html")


def test_fps_mismatch_lists_both_values():
    with pytest.raises(render.RenderError) as excinfo:
        render._resolve_fps(_contract(fps=25), _storyboard_like(fps=30), None)
    message = str(excinfo.value)
    assert "25" in message and "30" in message


def test_dimension_mismatch_lists_both_values():
    with pytest.raises(render.RenderError) as excinfo:
        render._resolve_dimensions(
            _contract(width=720, height=1280), _storyboard_like(width=1080, height=1920)
        )
    message = str(excinfo.value)
    assert "720" in message and "1280" in message
    assert "1080" in message and "1920" in message


def test_frame_count_mismatch_lists_both_values():
    with pytest.raises(render.RenderError) as excinfo:
        render._resolve_total_frames(_contract(frames=150), _storyboard_like(frames=180))
    message = str(excinfo.value)
    assert "150" in message and "180" in message


def test_contract_page_missing_reports_how_to_build(tmp_path):
    """契约页不存在时要报出**构建命令**，而不是一句找不到文件。"""
    with pytest.raises(A2VError) as excinfo:
        contract_page.require_contract_page(tmp_path)
    message = str(excinfo.value)
    assert "pnpm" in message and "build" in message
