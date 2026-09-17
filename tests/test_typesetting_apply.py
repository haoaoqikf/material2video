"""取档写回元素时的标记安全性与稳定性。

`applyFit()` 会改字号，也可能为了均衡断行而重排文本。它原先直接写
`el.textContent`，把强调词的 `<span class="key">` 连同强调色一起抹掉——
强调色是「单一焦点」的载体，静默消失等于画面失去焦点。

这一层必须用真实 DOM 测：文本节点、`TreeWalker`、`white-space: pre-line`
的行为都不是替身能模拟的。因此这里打开真实共享页面，往里面注入合成元素，
直接调用引擎的写回函数。
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
STORYBOARD = ROOT / "examples" / "keynote-baseline" / "storyboard.json"

#: 合成元素的可用宽度：小到足以逼出多行，才能真的走重排分支
NARROW_WIDTH = 180

_JS = """
(() => {
  const scene = document.querySelector('[data-a2v-scene]');
  const type = window.A2V.type;

  // 去掉换行符的字符序列：重排只允许移动换行位置，不许动字符集合
  const sig = (text) => Array.from(String(text)).filter((ch) => ch !== '\\n').join('');

  function make(html) {
    const host = document.createElement('p');
    host.className = 'quote-text';
    host.style.cssText =
      'position:absolute;left:-9999px;white-space:pre-line;' +
      'font-family:var(--a2v-font);font-size:60px;width:' + %WIDTH% + 'px;';
    host.innerHTML = html;
    scene.appendChild(host);
    return host;
  }

  function run(html, options) {
    const host = make(html);
    const before = { html: host.innerHTML, sig: sig(host.textContent), keys: host.querySelectorAll('.key').length };
    const fitted = type.applyFit(host, Object.assign({
      text: host.textContent, maxLevel: 4, availableWidth: %WIDTH%, balance: true
    }, options || {}));
    const after = { html: host.innerHTML, sig: sig(host.textContent), keys: host.querySelectorAll('.key').length,
                    keyText: Array.from(host.querySelectorAll('.key')).map((n) => n.textContent).join('|'),
                    fontSize: parseFloat(getComputedStyle(host).fontSize), br: host.querySelectorAll('br').length,
                    reveal: host.querySelectorAll('.reveal-char').length };
    host.remove();
    return { before, after, balanced: fitted.balanced === true, fits: fitted.fits, lines: fitted.lines };
  }

  const out = {};
  // 1. 强调标记必须活下来
  out.emphasis = run('是做决定的<span class="key">力气<span class="key-underline"></span></span>');
  // 2. 硬换行与强调同时存在
  out.emphasisHardBreak = run('第一行有强调<span class="key">重点</span>\\n第二行也不短');
  // 3. <br> 是元素级换行，引擎看不出来，必须放弃重排
  out.brElement = run('第一行<br>第二行也有点长');
  // 4. 逐字揭示的单字节点是动画结构，不能重排
  out.revealChars = run('逐字揭示<span class="reveal-char">甲</span><span class="reveal-char">乙</span>');
  // 5. 退化输入
  out.empty = run('');
  out.whitespace = run('   ');
  out.singleChar = run('短');
  out.pureEmphasis = run('<span class="key">只有强调</span>');

  // 6. 直接打重排契约：构造「均衡后的行与原文断行不同」的情形
  const direct = (() => {
    const host = make('是做决定的<span class="key">力气<span class="key-underline"></span></span>');
    const before = { sig: sig(host.textContent), keys: host.querySelectorAll('.key').length };
    const ok = type.reflow(host, ['是做决定', '的力气']);
    const after = { sig: sig(host.textContent), keys: host.querySelectorAll('.key').length,
                    keyText: Array.from(host.querySelectorAll('.key')).map((n) => n.textContent).join('|'),
                    text: host.textContent };
    // 字符被改动时必须拒绝重排
    const host2 = make('第一行\\n第二行');
    const rejected = type.reflow(host2, ['改了内容']);
    const after2 = { text: host2.textContent };
    // 安全判定
    const safe = type.canReflow(make('<span class="key">甲</span>'));
    const unsafeBr = type.canReflow(make('甲<br>乙'));
    const unsafeReveal = type.canReflow(make('<span class="reveal-char">甲</span>'));
    host.remove(); host2.remove();
    return { ok, before, after, rejected, after2, safe, unsafeBr, unsafeReveal };
  })();
  out.reflowContract = direct;

  // 7. 同一幕重复取档不得产生第二次写入
  const probe = make('要重复取档的一段文字');
  probe.dataset.a2vFit = 'lead';
  const first = type.autofit(scene).length;
  const snapshot = probe.innerHTML + '|' + probe.getAttribute('style');
  const second = type.autofit(scene).length;
  const idempotent = { first, second, unchanged: snapshot === probe.innerHTML + '|' + probe.getAttribute('style') };
  probe.remove();
  out.idempotent = idempotent;
  return out;
})()
""".replace("%WIDTH%", str(NARROW_WIDTH))


@pytest.fixture(scope="module")
def applied() -> dict:
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
            page_url = (
                f"http://127.0.0.1:{port}/{ASSETS.relative_to(ROOT).as_posix()}/declarative.html"
                f"?a2v-storyboard={quote('/' + STORYBOARD.relative_to(ROOT).as_posix(), safe='')}"
            )
            with playwright.sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1080, "height": 1920})
                page.goto(page_url)
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-a2v-scene]').length > 0",
                    timeout=20000,
                )
                page.wait_for_timeout(800)
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                facts = page.evaluate(_JS)
                browser.close()
                return facts
        finally:
            httpd.shutdown()


class TestMarkupIsPreserved:
    def test_emphasis_survives_reflow(self, applied):
        case = applied["reflowContract"]
        assert case["ok"] is True
        assert case["after"]["keys"] == case["before"]["keys"] == 1, "强调元素被重排抹掉了"
        assert case["after"]["keyText"] == "力气"
        assert case["after"]["text"] == "是做决定\n的力气"
        assert case["after"]["sig"] == case["before"]["sig"]

    def test_reflow_refuses_to_change_characters(self, applied):
        case = applied["reflowContract"]
        assert case["rejected"] is False, "断行结果改动了字符，重排必须拒绝"
        assert case["after2"]["text"] == "第一行\n第二行", "拒绝之后文案必须原样不动"

    def test_can_reflow_gate(self, applied):
        case = applied["reflowContract"]
        assert case["safe"] is True
        # <br> 是元素级换行，引擎在文本里看不见它，因此不许重排
        assert case["unsafeBr"] is False
        # 逐字揭示的单字节点是动画结构，重排会让字与节点错位
        assert case["unsafeReveal"] is False

    def test_apply_fit_keeps_markup_end_to_end(self, applied):
        case = applied["emphasis"]
        assert case["after"]["keys"] == case["before"]["keys"] == 1
        assert case["after"]["keyText"] == "力气"
        assert case["after"]["sig"] == case["before"]["sig"]

    def test_every_character_survives(self, applied):
        for name in ("emphasis", "emphasisHardBreak", "revealChars", "pureEmphasis", "singleChar"):
            case = applied[name]
            assert case["after"]["sig"] == case["before"]["sig"], f"{name} 的字符集合变了"

    def test_hard_break_keeps_paragraph_order(self, applied):
        case = applied["emphasisHardBreak"]
        assert case["after"]["keys"] == 1
        # 窄宽度下引擎会把两段各自再断开，但不得丢字、不得把段落次序打乱
        assert "".join(case["lines"]) == case["before"]["sig"]
        assert case["lines"][0].startswith("第一行有")
        assert case["lines"][-1].endswith("也不短")


class TestUnsafeStructuresAreLeftAlone:
    def test_br_disables_reflow(self, applied):
        case = applied["brElement"]
        # <br> 在文本里看不见，引擎无法把它算进断行，因此必须放弃重排
        assert case["balanced"] is False
        assert case["after"]["br"] == 1, "<br> 被吃掉了"
        assert case["after"]["html"] == case["before"]["html"]

    def test_reveal_chars_disable_reflow(self, applied):
        case = applied["revealChars"]
        assert case["balanced"] is False
        assert case["after"]["reveal"] == 2, "逐字揭示的单字节点被重排破坏了"
        assert case["after"]["html"] == case["before"]["html"]


class TestFloorAndFits:
    def test_never_goes_below_the_body_floor(self, applied):
        """溢出的文案不许被缩到正文下限以下。

        旧实现停在 `candidate.size <= minPx`，往下第一个满足它的是 label(34px)——
        比规范写死的 36px 还小，而且 fits 的判断挂在同一个条件上，于是连
        「放不下」都不报，成片里就是一段 34px 的溢出文字。
        """
        for name in ("emphasis", "brElement"):
            size = applied[name]["after"]["fontSize"]
            assert size >= 36, f"{name} 被缩到了 {size}px，低于正文下限"

    def test_long_paragraph_is_re_broken_instead_of_reported_as_overflow(self, applied):
        case = applied["emphasis"]
        # 14 个字在 180px 里放不下，但断成多行就放得下——应当断行并判定放得下
        assert len(case["lines"]) >= 2, case["lines"]
        assert case["fits"] is True, case["lines"]


class TestDegenerateInputs:
    def test_empty_text_does_not_throw(self, applied):
        case = applied["empty"]
        assert case["after"]["sig"] == ""
        assert case["fits"] is True

    def test_whitespace_only_is_left_alone(self, applied):
        case = applied["whitespace"]
        assert case["after"]["html"] == case["before"]["html"]

    def test_single_character(self, applied):
        case = applied["singleChar"]
        assert case["after"]["sig"] == "短"

    def test_emphasis_only(self, applied):
        case = applied["pureEmphasis"]
        assert case["after"]["keys"] == 1
        assert case["after"]["keyText"] == "只有强调"


class TestIdempotence:
    def test_second_pass_writes_nothing(self, applied):
        result = applied["idempotent"]
        assert result is not None, "探针没跑起来"
        assert result["first"] == 1, "第一次取档没有处理任何元素，说明探针没生效"
        assert result["second"] == 0, "第二次取档又处理了一遍：逐帧渲染会每帧重写样式与文本"
        assert result["unchanged"] is True
