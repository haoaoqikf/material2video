"""入场动效的轨迹（按时间量，不是抽静态帧）。

**这个文件补的是一个真实存在过的盲区。** 在此之前所有闸门都只看静态帧：
C 系列抽 24 帧看构图，K 系列看字号、对齐、对比度、越界——都看不见「动作有多快」。
于是这样一个缺陷活了很久：

    第 1 幕标题的 58px 位移，第 1 帧走完 36px，第 3 帧走完 97%，
    之后只剩 0.76px 的过冲；而 timeline.js 的注释写着「约 0.6 秒收敛」。

观众看到的是「带残影的硬切」，不是入场。抽帧永远发现不了它——抽 3 帧可能全部
落在动作结束之后（实测正是如此：第 6、8、10 帧看上去都「已经到位」）。

所以这里真的按帧驱动浏览器，逐帧读入场元素的实际位移，再对轨迹断言：
不弹跳、到位需要足够的帧数、过冲有界、收敛到确切的位置。
"""

from __future__ import annotations

import functools
import http.server
import json
import pathlib
import socketserver
import threading
from dataclasses import dataclass
from urllib.parse import quote

import pytest

from a2v import motion

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / ".agents" / "skills" / "article2video" / "assets"
STORYBOARD = ROOT / "examples" / "keynote-baseline" / "storyboard.json"
WIDTH, HEIGHT, FPS = 1080, 1920, 30

#: 第 1 幕标题的入场：`figures.js` 的 balance 组件在 beat(0.03) 处进场。
#: 采样从第 5 帧起——进场之前的位移恒定，量它没有意义。
SAMPLE_FROM, SAMPLE_TO = 5, 45

#: 轨迹判据。数字来自「观众能不能看出这是一次滑动」：
#:   * 第一帧最多走完 25%——超过它就不是滑动，是弹跳（旧实现是 62%）；
#:   * 走到 90% 至少要 6 帧（0.2 秒）——旧实现 3 帧；
#:   * 过冲不超过 10%（surface 配方的理论过冲是 0.15%）；
#:   * 窗口末尾必须正好落在终点（位移为 0），而不是永远差 0.14px。
MAX_FIRST_FRAME_SHARE = 0.25
MIN_FRAMES_TO_90 = 6
MAX_OVERSHOOT_SHARE = 0.10


def _storyboard() -> dict:
    return json.loads(STORYBOARD.read_text(encoding="utf-8"))


class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D102 - 静音，测试输出只留断言
        pass


def _trajectory() -> list[float]:
    """逐帧读第 1 幕标题的纵向位移（px）。"""
    playwright = pytest.importorskip("playwright.sync_api", reason="未安装 playwright")
    storyboard = _storyboard()
    page_url = ASSETS / "declarative.html"
    rel = "/" + page_url.relative_to(ROOT).as_posix()
    board = "/" + STORYBOARD.relative_to(ROOT).as_posix()

    with socketserver.ThreadingTCPServer(
        ("127.0.0.1", 0), functools.partial(_Handler, directory=str(ROOT))
    ) as httpd:
        httpd.daemon_threads = True
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{port}{rel}?a2v-storyboard={quote(board, safe='')}"
        try:
            with playwright.sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
                page.goto(url)
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-a2v-scene]').length > 0", timeout=20000
                )
                page.wait_for_timeout(600)
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                rows = []
                for frame in range(SAMPLE_FROM, SAMPLE_TO):
                    page.evaluate("(f) => window.__A2V__.seekToFrame(f)", frame)
                    rows.append(
                        page.evaluate(
                            """() => {
                              const scene = document.querySelectorAll('[data-a2v-scene]')[0];
                              const el = scene.querySelector('.title-text');
                              if (!el) return null;
                              const m = new DOMMatrixReadOnly(getComputedStyle(el).transform);
                              return m.m42;
                            }"""
                        )
                    )
                browser.close()
        finally:
            httpd.shutdown()
    assert all(value is not None for value in rows), "第 1 幕找不到 .title-text，采样选择器需要更新"
    assert storyboard["fps"] == FPS
    return [float(value) for value in rows]


@pytest.fixture(scope="module")
def trajectory() -> list[float]:
    return _trajectory()


def _distance(track: list[float]) -> float:
    return track[0]


def _share_done(track: list[float], frame_offset: int) -> float:
    return (_distance(track) - track[frame_offset]) / _distance(track)


class TestEntranceTrajectory:
    def test_entrance_is_not_a_pop(self, trajectory):
        """第一帧不能把位移基本走完。

        旧实现第一帧走完 62%（58px 里的 36px），配合下一帧的 97%，
        看起来就是一次硬切带残影。
        """
        share = _share_done(trajectory, 1)
        assert share <= MAX_FIRST_FRAME_SHARE, (
            f"入场第一帧就走完 {share:.0%} 的位移（上限 {MAX_FIRST_FRAME_SHARE:.0%}），"
            "这不是滑动而是弹跳；检查弹簧的输入是不是又变成了缓动过的进度"
        )

    def test_entrance_takes_enough_frames(self, trajectory):
        """走到 90% 至少要够帧数，否则观众看不到「移动」，只看到「出现」。"""
        offset = next(
            (i for i, value in enumerate(trajectory) if _share_done(trajectory, i) >= 0.9), None
        )
        assert offset is not None, "采样窗口内位移没有走到 90%"
        assert offset >= MIN_FRAMES_TO_90, (
            f"位移在 {offset} 帧内走到 90%（至少需要 {MIN_FRAMES_TO_90} 帧）"
        )

    def test_travel_is_monotone_until_near_the_end(self, trajectory):
        """到位之前不能来回抖：抖一下就是「晃」，不是「弹」。"""
        limit = next(
            i for i, value in enumerate(trajectory) if _share_done(trajectory, i) >= 0.9
        )
        window = trajectory[: limit + 1]
        assert window == sorted(window, reverse=True), (
            "位移在到达 90% 之前出现了回退："
            f"{[round(value, 2) for value in window]}"
        )

    def test_overshoot_stays_subtle(self, trajectory):
        """过冲是刻意的，但要小：surface 配方的理论过冲是 0.15%。"""
        distance = _distance(trajectory)
        overshoot = max(0.0, -min(trajectory)) / distance
        assert overshoot <= MAX_OVERSHOOT_SHARE, f"入场过冲 {overshoot:.1%}，上限 {MAX_OVERSHOOT_SHARE:.0%}"

    def test_settles_exactly_on_target(self, trajectory):
        """收敛必须是确切的 0，不是「永远差 0.14px」。

        弹簧只会无限逼近 1，所以运行时用衰减包络算出收敛时刻并返回 1；
        少了这一步，元素会带着残差停在半路，最细微的位移也永远是「没停稳」。
        """
        assert trajectory[-1] == 0.0, (
            f"窗口末尾仍有 {trajectory[-1]:.4f}px 残余位移——收敛时刻没有生效"
        )


#: 扫描由 `a2v/motion.py` 提供，与 `review.py`（做视频的人真正会跑的验收命令）
#: 共用同一份实现。判据放在只有开发者会跑的地方等于没有；放两份实现则必然漂移。
#: 这里只做参考实现上的**严格**判定，比验收流程多两件事：
#:   * 覆盖度：每一幕都必须真的扫到入场元素，「没扫到」不算通过；
#:   * 反例：把入场加速后重扫，闸门必须报错（证明它量得到，而不是没量到）。

#: 反例：把入场整体加速 8 倍。这就是旧实现的病征——入场在 2–3 帧内走完。
#: 实测：加速后首帧不透明度 0.855、到 0.9 只剩 1 帧（真实分别是 ≤0.095 与 7 帧）。
_FAST_FORWARD_JS = """
() => {
  const motion = window.A2V.motion;
  const enter = motion.enter;
  const enterSvg = motion.enterSvg;
  motion.enter = (state, el, seconds, options) => enter(state, el, seconds * 8, options);
  motion.enterSvg = (state, node, seconds, options) => enterSvg(state, node, seconds * 8, options);
}
"""

#: 有位移的入场至少要量到这么多个：防止「位移读取」悄悄退化之后闸门全过。
MIN_MOVING_TRAVEL_COUNT = 5


def _sweep(patch: str | None = None) -> list[motion.Entrance]:
    """在参考实现上逐幕逐帧扫一遍。`patch` 用来造反例。"""
    playwright = pytest.importorskip("playwright.sync_api", reason="未安装 playwright")
    board = _storyboard()
    rel = "/" + (ASSETS / "declarative.html").relative_to(ROOT).as_posix()
    story = "/" + STORYBOARD.relative_to(ROOT).as_posix()
    with socketserver.ThreadingTCPServer(
        ("127.0.0.1", 0), functools.partial(_Handler, directory=str(ROOT))
    ) as httpd:
        httpd.daemon_threads = True
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            with playwright.sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
                page.goto(f"http://127.0.0.1:{port}{rel}?a2v-storyboard={quote(story, safe='')}")
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-a2v-scene]').length > 0", timeout=20000
                )
                page.wait_for_timeout(600)
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                if patch is not None:
                    page.evaluate(patch)
                found = motion.sweep(page, board["scenes"])
                browser.close()
        finally:
            httpd.shutdown()
    assert not found.truncated, (
        "这些元素的采样被上限截断（不透明度还在上升就停了），轨迹不完整、等于被漏掉："
        f"{found.truncated}"
    )
    return found.records


@pytest.fixture(scope="module")
def entrances() -> list[motion.Entrance]:
    found = _sweep()
    assert found, "整支片子没有扫到任何入场元素，扫描规则或页面结构可能变了"
    return found


@pytest.fixture(scope="module")
def fast_forward_entrances() -> list[motion.Entrance]:
    return _sweep(patch=_FAST_FORWARD_JS)


def _label(entry: motion.Entrance) -> str:
    return f"{entry.scene}/{entry.key}"


class TestEveryEntrance:
    """把「一个标题」的机检扩到每一幕每一个入场元素。"""

    def test_sweep_covers_the_whole_film(self, entrances):
        """扫描本身要可信：覆盖每一幕，否则「全部通过」可能只是没扫到。"""
        per_scene: dict[str, int] = {}
        for entry in entrances:
            per_scene[entry.scene] = per_scene.get(entry.scene, 0) + 1
        missing = [
            scene["id"] for scene in _storyboard()["scenes"] if per_scene.get(scene["id"], 0) == 0
        ]
        assert not missing, f"这些幕没有扫到任何入场元素：{missing}（逐幕统计：{per_scene}）"
        moving = [entry for entry in entrances if entry.moving]
        assert len(moving) >= MIN_MOVING_TRAVEL_COUNT, (
            f"只有 {len(moving)} 个元素量到位移（至少应有 {MIN_MOVING_TRAVEL_COUNT} 个），"
            "位移读取可能退化了"
        )

    def test_no_moving_entrance_pops(self, entrances):
        """有位移的入场，第一帧不能把不透明度基本拉满。

        旧实现第一帧就到 0.438，同时位移走完大半——观众看到的就是一次硬切。
        """
        bad = [e for e in entrances if e.moving and e.first_opacity > motion.MAX_FIRST_FRAME_OPACITY]
        assert not bad, (
            f"这些有位移的入场第一帧不透明度就超过 {motion.MAX_FIRST_FRAME_OPACITY:.0%}："
            + ", ".join(f"{_label(e)} {e.first_opacity:.2f}" for e in bad)
        )

    def test_moving_entrances_take_enough_frames(self, entrances):
        """有位移的入场要够慢：观众得看见「移动」，而不是「换了个位置」。

        速度判据只适用于有位移的入场：另外 81 个是纯淡入（逐字揭示的单字符 2 帧、
        小标注与箭头 2–5 帧），那是刻意的做法，一刀切会把它们误判成弹跳。
        """
        bad = [
            e for e in entrances if e.moving and e.frames_to_90 < motion.MIN_OPACITY_FRAMES_TO_90
        ]
        assert not bad, (
            f"这些有位移的入场在不足 {motion.MIN_OPACITY_FRAMES_TO_90} 帧内就到 90%："
            + ", ".join(f"{_label(e)} {e.frames_to_90} 帧" for e in bad)
        )

    def test_no_entrance_flickers(self, entrances):
        """入场期间不透明度只能上升：中途回退就是一闪。"""
        bad = [e for e in entrances if e.reverses]
        assert not bad, "这些入场在落地之前不透明度回退了：" + ", ".join(_label(e) for e in bad)

    def test_every_entrance_lands_inside_its_scene(self, entrances):
        """入场必须在幕内走完：内容不能还在动就被切到下一幕。

        入场变慢之后这条才有意义（旧的 3 帧弹跳天然不会超时）。
        """
        bad = [e for e in entrances if e.margin < motion.MIN_LANDING_MARGIN]
        assert not bad, (
            f"这些入场落地时距幕尾不足 {motion.MIN_LANDING_MARGIN} 帧："
            + ", ".join(f"{_label(e)} 落地于 {e.landed}/{e.duration}" for e in bad)
        )


class TestTheGateItself:
    """新乐器必须先证明它抓得住那个缺陷，否则它只是装饰。"""

    def test_gate_catches_a_spring_that_is_too_fast(self, fast_forward_entrances):
        popped = [
            e
            for e in fast_forward_entrances
            if e.moving
            and (
                e.first_opacity > motion.MAX_FIRST_FRAME_OPACITY
                or e.frames_to_90 < motion.MIN_OPACITY_FRAMES_TO_90
            )
        ]
        assert popped, (
            "把入场加速 8 倍（等价于旧的 2–3 帧弹跳）之后闸门仍然全过——"
            "说明它量不到真正的问题"
        )

    def test_gate_accepts_the_real_spring(self, entrances):
        """反过来说：真实配方必须过，否则闸门只是禁止一切动效。"""
        popped = [
            e for e in entrances if e.moving and e.first_opacity > motion.MAX_FIRST_FRAME_OPACITY
        ]
        assert not popped
