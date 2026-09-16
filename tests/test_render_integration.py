"""端到端渲染集成测试。

需要 Playwright Chromium，缺失时整组跳过，避免在没有浏览器的环境下失败。
真正的价值是验证「确定性渲染」这条核心契约：同一帧重复渲染必须完全一致。
"""

from __future__ import annotations

import json

import pytest

from a2v import storyboard as sb
from a2v.browser import BrowserError, open_animated_page
from a2v.encoder import EncoderError
from a2v.errors import A2VError
from a2v.render import RenderError, _resolve_page_url, render

from conftest import EXAMPLES_DIR

PAGE = EXAMPLES_DIR / "index.html"


@pytest.fixture
def page_session():
    """打开示例网页并进入渲染模式，退出时释放浏览器。"""
    with _resolve_page_url(PAGE, None) as url:
        with open_animated_page(url, width=1080, height=1920) as page:
            page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
            yield page


class TestPageContract:
    def test_exposes_contract_matching_storyboard(self, chromium_ready, page_session):
        model, report = sb.load(EXAMPLES_DIR / "storyboard.json")
        assert report.ok and model is not None
        contract = page_session.contract
        assert contract.fps == model.fps
        assert contract.duration_in_frames == model.total_frames
        assert (contract.width, contract.height) == (model.width, model.height)

    def test_hides_preview_controls_in_render_mode(self, chromium_ready, page_session):
        # 预览控件必须完全移出画面，否则会出现在成片里
        visible = page_session.evaluate(
            "() => {const el = document.querySelector('[data-a2v-controls]');"
            "if (!el) return false; const r = el.getBoundingClientRect();"
            "return getComputedStyle(el).display !== 'none' && r.width > 0 && r.height > 0;}"
        )
        assert visible is False


class TestDeterminism:
    def test_same_frame_renders_identically(self, chromium_ready, page_session):
        """契约的核心：画面只由帧号决定，重复渲染必须逐字节一致。"""
        page_session.seek(30)
        first = page_session.capture("png")
        # 先跳到别的帧制造状态差异，再回到原帧，排除「缓存上一次画面」的假通过
        page_session.seek(700)
        page_session.seek(30)
        second = page_session.capture("png")
        assert first == second

    def test_same_frame_identical_across_sessions(self, chromium_ready):
        """新建一次浏览器会话渲染同一帧，结果也必须一致。

        字体加载、资源时序都不应影响画面。两个会话必须顺序执行：
        Playwright 同步 API 在同一进程内不允许并发驱动循环。
        """

        def capture_frame(frame: int) -> bytes:
            with _resolve_page_url(PAGE, None) as url:
                with open_animated_page(url, width=1080, height=1920) as session:
                    session.evaluate(
                        "() => document.documentElement.classList.add('a2v-rendering')"
                    )
                    session.seek(frame)
                    return session.capture("png")

        assert capture_frame(45) == capture_frame(45)


class TestMotionPrimitives:
    """新增动效原语必须是纯函数：同一入参永远同一结果，且不越过数值范围。"""

    PROBE = """() => {
      const s = A2V.spring(1, {});
      const r = A2V.range(0.5, 10, 20);
      const b = A2V.breath(30, { periodFrames: 120, amplitude: 4 });
      return {
        springRepeat: [A2V.spring(0.35, {}), A2V.spring(0.35, {})],
        springEnds: [A2V.spring(0, {}), A2V.spring(1, {})],
        springOvershoot: A2V.spring(0.52, {}) > 1,
        springFinite: Number.isFinite(s),
        rangeRepeat: [A2V.range(0.5, 10, 20), A2V.range(0.5, 10, 20)],
        rangeClamped: [A2V.range(-5, 0, 100), A2V.range(5, 0, 100)],
        rangeUnclamped: A2V.range(-5, 0, 100, { clamp: false }),
        breathRepeat: [A2V.breath(30, { periodFrames: 120, amplitude: 4 }), A2V.breath(30, { periodFrames: 120, amplitude: 4 })],
        breathMidPeriod: A2V.breath(60, { periodFrames: 120, amplitude: 4 }),
        breathZeroPeriod: A2V.breath(30, { periodFrames: 0, amplitude: 4 }),
        breathIsNumber: Number.isFinite(b)
      };
    }"""

    def test_primitives_are_pure_and_bounded(self, chromium_ready, page_session):
        probe = page_session.evaluate(self.PROBE)
        assert probe["springRepeat"][0] == probe["springRepeat"][1]
        assert probe["springEnds"] == [0, 1]
        assert probe["springOvershoot"] is True
        assert probe["springFinite"] is True
        assert probe["rangeRepeat"][0] == probe["rangeRepeat"][1] == 15
        assert probe["rangeClamped"] == [0, 100]
        assert probe["rangeUnclamped"] == -500
        assert probe["breathRepeat"][0] == probe["breathRepeat"][1]
        assert probe["breathMidPeriod"] == pytest.approx(0, abs=1e-9)
        assert probe["breathZeroPeriod"] == 0
        assert probe["breathIsNumber"] is True

    def test_reveal_chars_is_frame_driven(self, chromium_ready, page_session):
        """逐字揭示必须只由帧号决定：同一帧的每个字透明度完全一致。"""
        script = """
        () => {
          const el = document.createElement('p');
          el.style.whiteSpace = 'pre-line';
          document.querySelector('[data-a2v-stage]').appendChild(el);
          const opacity = (text, frame) => {
            A2V.revealChars(el, text, 0, { frame: frame, startFrame: 0, staggerFrames: 2 });
            return Array.prototype.map.call(el.children, (c) => c.style.opacity).join(',');
          };
          return {
            first: opacity('努力没有结果\\n而是方向错了。', 6),
            second: opacity('努力没有结果\\n而是方向错了。', 6),
            later: opacity('努力没有结果\\n而是方向错了。', 60),
            count: el.children.length,
            breakClass: el.children[6].className
          };
        }
        """
        result = page_session.evaluate(script)
        assert result["first"] == result["second"]
        assert result["first"] != result["later"]
        assert result["count"] == 14  # 13 个字 + 1 个换行占位
        assert result["breakClass"] == "reveal-char is-break"

    def test_reveal_chars_keeps_frames_deterministic(self, chromium_ready, page_session):
        page_session.seek(44)
        first = page_session.capture("png")
        page_session.seek(1200)
        page_session.seek(44)
        assert first == page_session.capture("png")

    def test_shape_primitives_are_pure(self, chromium_ready, page_session):
        probe = """() => {
          const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
          path.setAttribute('d', 'M 0 0 L 10 0');
          path.getTotalLength = () => 10;
          A2V.drawPath(path, 0.4, { length: 10 });
          const first = [path.getAttribute('stroke-dasharray'), path.getAttribute('stroke-dashoffset'), path.style.opacity];
          A2V.drawPath(path, 0.4, { length: 10 });
          const second = [path.getAttribute('stroke-dasharray'), path.getAttribute('stroke-dashoffset'), path.style.opacity];
          A2V.drawPath(path, 2, { length: 10 });
          const clamped = [path.getAttribute('stroke-dashoffset'), path.style.opacity];
          return { first: first, second: second, clamped: clamped };
        }"""
        probe_result = page_session.evaluate(probe)
        assert probe_result["first"] == probe_result["second"]
        assert probe_result["first"] == ["10", "6", "0.4"]
        assert probe_result["clamped"] == ["0", "1"]

class TestPlaybackControl:
    def test_play_after_end_restarts_and_keeps_playing(self, chromium_ready, page_session):
        """播放结束后再点播放必须从头继续。

        早期实现只重置了帧号却忘了重置累计时间，下一次 tick 会立刻按旧时间
        算回末帧并暂停，表现为「点了没反应」。
        """
        page_session.evaluate(
            "() => {const c = A2V.controller; c.pause(); return c.seek(c.timeline.totalFrames - 1);}"
        )
        page_session.evaluate("() => A2V.controller.play()")
        page_session.evaluate("() => new Promise((resolve) => setTimeout(resolve, 400))")

        state = page_session.evaluate(
            "() => ({playing: A2V.controller.isPlaying(),"
            " frame: A2V.controller.currentFrame()})"
        )
        assert state["playing"] is True
        assert state["frame"] < 30


class TestContractFailures:
    def test_page_without_contract_raises_a2v_error(self, chromium_ready, tmp_path):
        """网页没实现契约时必须抛出可被 CLI 捕获的 A2VError，而不是裸栈。"""
        page = tmp_path / "broken.html"
        page.write_text("<!doctype html><html><body>没有契约</body></html>", encoding="utf-8")
        with pytest.raises(A2VError, match="等待 window.__A2V__ 定义超时"):
            render(page_path=page, output=tmp_path / "out.mp4", timeout_ms=1500)

    def test_error_types_share_one_base(self):
        # CLI 只捕获 A2VError 一次，任一子类脱离基类都会让用户看到 Python 栈
        assert issubclass(BrowserError, A2VError)
        assert issubclass(EncoderError, A2VError)
        assert issubclass(RenderError, A2VError)


class TestRenderPipeline:
    def test_render_short_clip_produces_playable_video(self, chromium_ready, tmp_path):
        output = tmp_path / "clip.mp4"
        result = render(
            page_path=PAGE,
            output=output,
            storyboard=sb.load(EXAMPLES_DIR / "storyboard.json")[0],
            limit_frames=6,
        )
        assert output.exists()
        assert result.frames == 6
        assert (result.width, result.height) == (1080, 1920)
        assert result.fps == 30
        assert result.size_bytes > 0

    def test_rejects_storyboard_with_mismatched_length(self, chromium_ready, tmp_path):
        data = json.loads((EXAMPLES_DIR / "storyboard.json").read_text(encoding="utf-8"))
        data["scenes"][0]["durationInFrames"] += 30
        path = tmp_path / "storyboard.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        model, report = sb.load(path)
        assert report.ok and model is not None

        with pytest.raises(RenderError, match="总帧数不一致"):
            render(
                page_path=PAGE,
                output=tmp_path / "should_not_exist.mp4",
                storyboard=model,
                limit_frames=3,
            )

    def test_rejects_missing_page(self, chromium_ready, tmp_path):
        with pytest.raises(RenderError, match="不存在"):
            render(page_path=tmp_path / "absent.html", output=tmp_path / "out.mp4")
