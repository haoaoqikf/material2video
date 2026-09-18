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
import re
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


#: 数字幕只看入场与滚动这一段就够：滚动时长约为幕长的 26%，之后是静止保持。
_ROLL_SAMPLE_FRAMES = 72


def _number_display(storyboard_path: pathlib.Path | None = None) -> tuple[object, list[tuple[int, str, float]]]:
    """逐帧读数字幕的数字文本与不透明度。

    `storyboard_path` 默认为发布会基线；传非预设示例可以覆盖"步数够、确实在滚动"
    的那一支——基线示例的数值是 1，走的是"不滚动"分支。
    """
    playwright = pytest.importorskip("playwright.sync_api", reason="未安装 playwright")
    path = storyboard_path or STORYBOARD
    storyboard = json.loads(path.read_text(encoding="utf-8"))
    scenes = storyboard["scenes"]
    target = next(
        s
        for s in scenes
        if (s.get("data") or {}).get("figure", {}).get("kind") == "number"
        or (s.get("data") or {}).get("value") is not None
    )
    start = sum(s["durationInFrames"] for s in scenes[: scenes.index(target)])

    page_url = ASSETS / "declarative.html"
    rel = "/" + page_url.relative_to(ROOT).as_posix()
    board = "/" + path.relative_to(ROOT).as_posix()

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
                for local in range(_ROLL_SAMPLE_FRAMES):
                    page.evaluate("(f) => window.__A2V__.seekToFrame(f)", start + local)
                    rows.append(
                        page.evaluate(
                            """(id) => {
                              const el = document.querySelector(
                                '[data-scene-id="' + id + '"] .fig-number');
                              if (!el) return null;
                              return [el.textContent, parseFloat(getComputedStyle(el).opacity)];
                            }""",
                            target["id"],
                        )
                    )
                browser.close()
        finally:
            httpd.shutdown()
    assert all(row is not None for row in rows), "数字幕找不到 .fig-number，采样选择器需要更新"
    return target, [(i, str(text), float(opacity)) for i, (text, opacity) in enumerate(rows)]


class TestNumberRoll:
    """数字滚动是**动效**：步数不够就不该滚。

    滚动原先是无条件的 `Math.round(raw * progress)`，`value: 1` 于是也"滚"——
    而 1 只有一级，滚动退化成一次瞬跳。这与入场弹簧的闸门是两件事：
    弹簧闸门量的是不透明度爬升，量不到"文本内容跳变"。
    """

    def test_a_legible_numeral_never_shows_a_value_other_than_the_final_one(self):
        target, rows = _number_display()
        want = str(target["data"]["value"])
        legible = [(frame, text) for frame, text, opacity in rows if opacity >= 0.5]
        assert legible, "数字幕没有任何一帧达到可读不透明度，采样范围需要更新"
        wrong = [(frame, text) for frame, text in legible if text != want]
        assert not wrong, (
            f"数字在可读（不透明度 ≥ 0.5）时显示过非最终值 {want!r}："
            f"{wrong[:6]}——滚动步数不足时它不该滚"
        )

    def test_the_numeral_still_rolls_when_it_has_enough_steps(self):
        """反过来：步数够的数值必须仍旧滚动，否则这一条就变成了"禁止数字动效"。

        用非预设示例（`value: 73`）来覆盖滚动分支——它同时也是那条
        "未声明预设的既有作品逐帧不变"契约的载体。
        """
        path = ROOT / "examples" / "declarative-number" / "storyboard.json"
        target, rows = _number_display(path)
        assert abs(float(target["data"]["value"])) >= 10, "这个示例本该是够步数的数值"
        seen = {text for _, text, opacity in rows if opacity >= 0.5}
        assert len(seen) > 1, f"数值足够滚动却只出现过 {seen}，滚动分支没有生效"
        assert str(target["data"]["value"]) in seen, "滚动没有落到最终值上"


#: 焦点交接的采样步长。一次交接跨半个格子（约 27 帧），
#: 合法的一帧变化约 0.077，所以步长 3 的合法上限约 0.23。
_FOCUS_STEP = 3
#: 超过这个幅度就说明焦点是在帧边界上翻牌，而不是淡入淡出。
_FOCUS_MAX_JUMP = 0.4
#: rest / focus 两端的填充（`--fig-surface` / `--a2v-accent-soft-solid`）。
_FOCUS_REST = (23 / 255, 30 / 255, 43 / 255)
_FOCUS_FULL = (22 / 255, 70 / 255, 95 / 255)

_FOCUS_SAMPLE = """(id) => {
  const scene = document.querySelector('[data-scene-id="' + id + '"]');
  if (!scene) return null;
  const out = [];
  scene.querySelectorAll('.loop-node-disc').forEach((d) => {
    out.push([d.getAttribute('data-a2v-state') || 'none', getComputedStyle(d).fill]);
  });
  return out;
}"""


def _parse_color(text: str) -> tuple[float, float, float]:
    """解析 `rgb(r, g, b)` 与 `color(srgb r g b)` 两种 Chromium 输出。"""
    numbers = [float(n) for n in re.findall(r"-?\d*\.?\d+", text)]
    if text.startswith("rgb("):
        return (numbers[0] / 255, numbers[1] / 255, numbers[2] / 255)
    return (numbers[0], numbers[1], numbers[2])


def _focus_mix(rgb: tuple[float, float, float]) -> float:
    """把填充色投影到 rest→focus 这条线上，得到 0..1 的焦点量。"""
    axis = [f - r for f, r in zip(_FOCUS_FULL, _FOCUS_REST)]
    delta = [c - r for c, r in zip(rgb, _FOCUS_REST)]
    denom = sum(a * a for a in axis)
    return sum(a * b for a, b in zip(delta, axis)) / denom


def _loop_focus_track() -> list[list[tuple[str, float]]]:
    """逐帧读飞轮幕各节点圆盘的状态与焦点量。"""
    playwright = pytest.importorskip("playwright.sync_api", reason="未安装 playwright")
    storyboard = _storyboard()
    scenes = storyboard["scenes"]
    target = next(s for s in scenes if s["type"] == "diagram")
    start = sum(s["durationInFrames"] for s in scenes[: scenes.index(target)])

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
                track = []
                for local in range(0, target["durationInFrames"], _FOCUS_STEP):
                    page.evaluate("(f) => window.__A2V__.seekToFrame(f)", start + local)
                    rows = page.evaluate(_FOCUS_SAMPLE, target["id"])
                    if rows is None:
                        continue
                    track.append(
                        [(state, _focus_mix(_parse_color(fill))) for state, fill in rows]
                    )
                browser.close()
        finally:
            httpd.shutdown()
    assert track, "飞轮幕采不到节点圆盘，采样选择器需要更新"
    return track


class TestFocusHandover:
    """焦点交接必须是连续的，而且任何一帧仍然只有一个焦点。

    这两条要同时成立，靠的是交接顺序：旧节点以 mix 1→0 淡出，
    **到 mix = 0 的那一帧**才把 `focus` 交给新节点（新节点从 mix 0 淡入）。
    切换瞬间两侧外观都等于 rest，所以视觉上没有缝。
    """

    def test_at_most_one_focus_per_frame(self):
        """规格里的硬约束：强调色只指向一个落点，两个焦点等于没有焦点。"""
        track = _loop_focus_track()
        offenders = [
            (index * _FOCUS_STEP, sum(1 for state, _ in frame if state == "focus"))
            for index, frame in enumerate(track)
            if sum(1 for state, _ in frame if state == "focus") > 1
        ]
        assert not offenders, f"这些帧出现了多个焦点：{offenders[:6]}"

    def test_the_focus_never_jumps_at_a_frame_boundary(self):
        """焦点量逐帧最多变化 _FOCUS_MAX_JUMP——翻牌会一次跳掉整格。"""
        track = _loop_focus_track()
        jumps = []
        for index in range(1, len(track)):
            before = max(mix for _, mix in track[index - 1])
            after = max(mix for _, mix in track[index])
            if abs(after - before) > _FOCUS_MAX_JUMP:
                jumps.append((index * _FOCUS_STEP, round(before, 3), round(after, 3)))
        assert not jumps, (
            f"这些帧之间焦点量发生了跳变（帧, 前, 后）：{jumps[:6]}——"
            "焦点在帧边界上翻牌，而不是淡入淡出"
        )

    def test_a_disc_enters_focus_at_zero_mix(self):
        """拿到 `focus` 的那一帧，它的焦点量必须接近 0。

        否则"从 rest 换成 focus"本身就是一次可见的跳变——
        这正是连续通道存在的理由。
        """
        track = _loop_focus_track()
        offenders = []
        for index in range(1, len(track)):
            for node, (state, mix) in enumerate(track[index]):
                was = track[index - 1][node][0]
                if was == "rest" and state == "focus" and mix > 0.25:
                    offenders.append((index * _FOCUS_STEP, node, round(mix, 3)))
        assert not offenders, (
            f"这些（帧, 节点, 焦点量）在拿到 focus 的瞬间就已经很亮：{offenders[:6]}"
        )


def _loop_node_boxes() -> list[tuple[str, float, float]]:
    """读飞轮幕每个节点圆盘的中心（页面坐标）。"""
    playwright = pytest.importorskip("playwright.sync_api", reason="未安装 playwright")
    storyboard = _storyboard()
    scenes = storyboard["scenes"]
    target = next(s for s in scenes if s["type"] == "diagram")
    start = sum(s["durationInFrames"] for s in scenes[: scenes.index(target)])

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
                # 取幕中段：此时入场已经结束，几何稳定
                page.evaluate(
                    "(f) => window.__A2V__.seekToFrame(f)",
                    start + target["durationInFrames"] // 2,
                )
                rows = page.evaluate(
                    """(id) => {
                      const scene = document.querySelector('[data-scene-id="' + id + '"]');
                      return Array.from(scene.querySelectorAll('.loop-node-disc')).map((d) => {
                        const box = d.getBoundingClientRect();
                        const text = d.parentNode.querySelector('.loop-node-text');
                        return [text ? text.textContent : '?',
                                box.x + box.width / 2, box.y + box.height / 2];
                      });
                    }""",
                    target["id"],
                )
                browser.close()
        finally:
            httpd.shutdown()
    assert rows, "飞轮幕采不到节点圆盘，采样选择器需要更新"
    return [(str(label), float(x), float(y)) for label, x, y in rows]


class TestLoopGeometry:
    """环的停位数必须等于节点数。

    `loopPoint` 同时给「小球走的环」和「节点摆在哪」用。它原先把每格 120°
    写死（= 一圈 3 个停位），而分镜给的是 4 个节点，于是 index 3 落到
    360° = index 0——两个圆盘画在同一处，屏幕上只看得到三个圆盘，
    「打开选项」这一步被完全遮住（实测两者中心都是 ≈(540, 760)）。
    """

    def test_every_node_gets_its_own_place_on_the_ring(self):
        boxes = _loop_node_boxes()
        assert len(boxes) >= 3, f"节点太少，测不出重合：{boxes}"
        offenders = []
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                gap = ((boxes[i][1] - boxes[j][1]) ** 2 + (boxes[i][2] - boxes[j][2]) ** 2) ** 0.5
                # 圆盘直径约 215px；中心距小于半个直径就一定叠在一起
                if gap < 110:
                    offenders.append((boxes[i][0], boxes[j][0], round(gap, 1)))
        assert not offenders, (
            f"这些节点画在了同一个位置（节点, 节点, 中心距 px）：{offenders}——"
            "环的停位数没有跟着节点数走"
        )


@functools.lru_cache(maxsize=1)
def _versus_board() -> dict:
    """读比较幕的板面、安全区宽度与选项文字字号。三次断言共用一次浏览器。"""
    playwright = pytest.importorskip("playwright.sync_api", reason="未安装 playwright")
    storyboard = _storyboard()
    scenes = storyboard["scenes"]
    target = next(s for s in scenes if s["type"] == "comparison")
    start = sum(s["durationInFrames"] for s in scenes[: scenes.index(target)])

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
                # 取幕中段：入场已经结束，量到的是稳定版面
                page.evaluate(
                    "(f) => window.__A2V__.seekToFrame(f)",
                    start + target["durationInFrames"] // 2,
                )
                facts = page.evaluate(
                    """(id) => {
                      const scene = document.querySelector('[data-scene-id="' + id + '"]');
                      const safe = scene.querySelector('.a2v-safe') || scene;
                      const rect = (e) => { const r = e.getBoundingClientRect();
                        return {w: r.width, x: r.x}; };
                      const texts = Array.from(scene.querySelectorAll('.vs-text'));
                      return {
                        safe: rect(safe),
                        board: rect(scene.querySelector('.vs-board')),
                        sides: Array.from(scene.querySelectorAll('.vs-side')).map(rect),
                        fonts: texts.map((t) =>
                          parseFloat(getComputedStyle(t).fontSize)),
                        fit: texts.map((t) => t.getAttribute('data-a2v-fit'))
                      };
                    }""",
                    target["id"],
                )
                browser.close()
        finally:
            httpd.shutdown()
    assert facts and facts["fonts"], "比较幕采不到两栏文字，采样选择器需要更新"
    return facts


class TestVersusGeometry:
    """比较幕的两栏是这一幕的**载荷**，不该缩成正文大小。

    未启用预设时板面按内容收缩、文字固定在 46px 兜底值，于是实测板面只有
    596px（安全区 888px 的 67%）、文字 44px，而幕标题 76px——
    **要看的东西比问题还小**，层级是倒的（K3 量到的字号层级只有 [44, 76]）。
    """

    def test_the_two_columns_use_the_available_width(self):
        facts = _versus_board()
        share = facts["board"]["w"] / facts["safe"]["w"]
        assert share >= 0.9, (
            f"板面只占安全区宽度的 {share:.0%}（{facts['board']['w']:.0f}/"
            f"{facts['safe']['w']:.0f}）——两栏按内容收缩，载荷被挤小了"
        )

    def test_the_two_columns_are_the_same_width(self):
        widths = [side["w"] for side in _versus_board()["sides"]]
        spread = max(widths) - min(widths)
        assert spread <= 2, f"两栏宽度不一致（{widths}）——并排比较应当等宽，差 {spread:.0f}px"

    def test_the_payload_text_is_not_at_the_fallback_size(self):
        """选项文字必须落在排版阶上，而不是那个 46px 的兜底值。"""
        facts = _versus_board()
        assert all(fit for fit in facts["fit"]), (
            f"两栏文字没有声明排版档位（data-a2v-fit）：{facts['fit']}——"
            "于是它只能吃 --a2v-ink-value 的兜底值，永远不参与自适应"
        )
        smallest = min(facts["fonts"])
        assert smallest >= 60, (
            f"选项文字只有 {smallest:.0f}px，仍在正文那一档——"
            "这一幕的载荷应当落在 lead（60px）及以上"
        )

