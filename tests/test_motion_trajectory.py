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


#: 扫描：每一幕、每一个入场元素都要满足「平滑进入」与「在幕内落地」。
#:
#: 只测一个标题拦不住「某个组件把起始帧或距离算错了」，也拦不住入场变慢之后
#: 新出现的风险——某个元素的入场在幕内来不及落地（旧的 3 帧弹跳天然掩盖了它）。
#:
#: 判据量在**不透明度**上，不是位移上。两个原因：
#:   * 位移里混着常驻呼吸（settleAt 之后渐入的 2–3px 微动），拿它判「单调」
#:     会把呼吸的摆动读成入场回退——第一版就是这么误报 `title-sub-line` 的；
#:   * 不透明度由同一个弹簧值驱动且被夹在 0..1，是干净、单调的入场信号。
#: 位移曲线本身由 `TestEntranceTrajectory` 精确钉住（那里是一个元素、一段窗口），
#: 这里的职责是**覆盖到每一个入场元素**。

#: 「有位移的入场」的判据。实测 90 个入场元素里只有 9 个真的有位移，
#: 另外 81 个是纯淡入（逐字揭示的单字符 2 帧、小组件 2–5 帧）——那是刻意的设计，
#: 不是缺陷。所以**速度判据只适用于有位移的元素**：观众看到「弹」是因为它同时
#: 跳完了位移；一个原地淡入的小标签快一点并不叫弹。
#:
#: 这两个数字都由实测反推，并留出余量：有位移元素的实测值是
#: 到 0.9 最少 7 帧、首帧不透明度最大 0.095；旧实现的首帧是 0.438（被判失败）。
MOVING_TRAVEL_PX = 1.0
MIN_MOVING_TRAVEL_COUNT = 5
MAX_FIRST_FRAME_OPACITY = 0.25
MIN_OPACITY_FRAMES_TO_90 = 6

#: 入场落地后距幕尾至少留多少帧：内容不能还在动就被切到下一幕。
#: 实测最小 25 帧（`opening` 一幕的最后一个分组），取 12 帧（0.4 秒）作为下限。
MIN_LANDING_MARGIN = 12

#: 每个元素最多记录多少次变化。入场最长约 50 帧（缓动淡入），60 够用；
#: 上限是为了不让「整幕都在呼吸」的元素把数据撑爆。
MAX_SAMPLES = 60

_SWEEP_JS = """
(args) => {
  const scene = document.querySelectorAll('[data-a2v-scene]')[args.index];
  const duration = args.duration;
  const read = (el) => {
    const cs = getComputedStyle(el);
    const op = Math.round(parseFloat(cs.opacity) * 1000) / 1000;
    const raw = (el.style && el.style.transform) || el.getAttribute('transform') || '';
    let x = 0, y = 0;
    if (raw && raw !== 'none') {
      try {
        const m = new DOMMatrixReadOnly(raw);
        x = Math.round(m.m41 * 100) / 100;
        y = Math.round(m.m42 * 100) / 100;
      } catch (e) { /* 解析不了的变换当作没有位移 */ }
    }
    return [op, x, y];
  };
  // SVG 的 className 是 SVGAnimatedString 对象，String() 之后所有 SVG 元素会塌成
  // 同一个 key——第一版探针就是这么量出「两幕零入场元素」的假结论的。
  const key = (el) => {
    const cls = (el.getAttribute('class') || '').split(' ')[0];
    return el.tagName.toLowerCase() + (cls ? '.' + cls : '');
  };
  // 用元素引用本身做身份：这一幕的 DOM 是逐帧渲染出来的，
  // 在进入这一幕之前 querySelectorAll 拿到的是空列表（第一版扫描只覆盖第 0 幕，
  // 就是因为元素集合在 seek 之前就取好了）。按元素身份收集还顺带处理了
  // 「组件在幕中才创建节点」的情况。
  const tracks = new Map();
  const order = [];
  for (let f = 0; f < duration; f++) {
    window.__A2V__.seekToFrame(args.start + f);
    for (const el of scene.querySelectorAll('*')) {
      let track = tracks.get(el);
      if (track === undefined) {
        track = { key: key(el), samples: [] };
        tracks.set(el, track);
        order.push(track);
      }
      const cur = read(el);
      const last = track.samples[track.samples.length - 1];
      if (!last || last[1] !== cur[0] || last[2] !== cur[1] || last[3] !== cur[2]) {
        if (track.samples.length < args.maxSamples) track.samples.push([f].concat(cur));
      }
    }
  }
  return { index: args.index, duration: duration, elements: order };
}
"""


@dataclass
class Entrance:
    """一个入场元素的实测轨迹（不透明度视角）。"""

    scene: str
    key: str
    start: int
    landed: int
    duration: int
    travel: float
    first_opacity: float
    frames_to_half: int
    frames_to_90: int
    reverses: bool

    @property
    def margin(self) -> int:
        return self.duration - self.landed


def _scene_offsets(board: dict) -> list[tuple[int, int]]:
    """每一幕的（起始全局帧, 帧数）。seekToFrame 收的是全局帧。"""
    offsets, acc = [], 0
    for scene in board["scenes"]:
        duration = int(scene.get("durationInFrames") or 0)
        offsets.append((acc, duration))
        acc += duration
    return offsets


def _analyse(scene_id: str, duration: int, element: dict) -> Entrance | None:
    """把一个元素的压缩采样整理成入场记录；不是入场元素时返回 None。"""
    samples = element["samples"]
    if len(samples) < 2:
        return None
    frames = [row[0] for row in samples]
    ops = [row[1] for row in samples]
    # 入场 = 从透明走向不透明。刻意压暗的元素（落选一栏 0.42）与整幕静止的元素都不是。
    # 幕中才创建的节点没有「第 0 帧」样本，会被当成「出现时已经可见」，不算入场。
    if ops[0] > 0.05:
        return None
    first = next((i for i in range(1, len(samples)) if ops[i] != ops[0]), None)
    if first is None:
        return None
    landed = next((i for i in range(first, len(samples)) if ops[i] >= 0.99), None)
    if landed is None:
        return None
    window = [(frames[i], ops[i]) for i in range(first, landed + 1)]
    half = next((f for f, op in window if op >= 0.5), frames[landed])
    ninety = next((f for f, op in window if op >= 0.9), frames[landed])
    rises = [op for _, op in window]
    travel = (element["samples"][0][3] - samples[landed][3]) if len(samples[landed]) > 3 else 0.0
    return Entrance(
        scene=scene_id,
        key=element["key"],
        start=frames[first],
        landed=frames[landed],
        duration=duration,
        travel=round(abs(travel), 2),
        first_opacity=window[0][1],
        frames_to_half=half - frames[first],
        frames_to_90=ninety - frames[first],
        reverses=rises != sorted(rises),
    )


def _sweep(patch: str | None = None) -> list[Entrance]:
    """逐幕逐帧扫一遍，返回所有入场元素的轨迹。

    `patch` 是页面加载后注入的 JS：用来造反例（把弹簧整体加速，看闸门会不会报），
    正常扫描传 None。
    """
    playwright = pytest.importorskip("playwright.sync_api", reason="未安装 playwright")
    board = _storyboard()
    offsets = _scene_offsets(board)
    rel = "/" + (ASSETS / "declarative.html").relative_to(ROOT).as_posix()
    story = "/" + STORYBOARD.relative_to(ROOT).as_posix()
    found: list[Entrance] = []

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
                for index, scene in enumerate(board["scenes"]):
                    start, duration = offsets[index]
                    data = page.evaluate(
                        _SWEEP_JS,
                        {
                            "index": index,
                            "start": start,
                            "duration": duration,
                            "maxSamples": MAX_SAMPLES,
                        },
                    )
                    for element in data["elements"]:
                        record = _analyse(scene["id"], duration, element)
                        if record is not None:
                            found.append(record)
                browser.close()
        finally:
            httpd.shutdown()
    return found


@pytest.fixture(scope="module")
def entrances() -> list[Entrance]:
    found = _sweep()
    assert found, "整支片子没有扫到任何入场元素，扫描规则或页面结构可能变了"
    return found


def _offenders(entrances: list[Entrance], predicate) -> list[Entrance]:
    return [entry for entry in entrances if predicate(entry)]


#: 反例：把弹簧整体加速 8 倍。这就是旧实现的病征——入场在 2–3 帧内走完，
#: 观众看到的是一次带残影的硬切。闸门必须报出来，否则它只是个装饰。
_FAST_FORWARD_JS = """
() => {
  const motion = window.A2V.motion;
  const enter = motion.enter;
  const enterSvg = motion.enterSvg;
  motion.enter = (state, el, seconds, options) => enter(state, el, seconds * 8, options);
  motion.enterSvg = (state, node, seconds, options) => enterSvg(state, node, seconds * 8, options);
}
"""


@pytest.fixture(scope="module")
def fast_forward_entrances() -> list[Entrance]:
    return _sweep(patch=_FAST_FORWARD_JS)


class TestTheGateItself:
    """新乐器必须先证明它抓得住那个缺陷，否则它只是装饰。"""

    def test_gate_catches_a_spring_that_is_too_fast(self, fast_forward_entrances):
        popped = _offenders(
            fast_forward_entrances,
            lambda e: e.travel >= MOVING_TRAVEL_PX
            and (
                e.first_opacity > MAX_FIRST_FRAME_OPACITY
                or e.frames_to_90 < MIN_OPACITY_FRAMES_TO_90
            ),
        )
        assert popped, (
            "把入场加速 8 倍（等价于旧的 2–3 帧弹跳）之后闸门仍然全过——"
            "说明它量不到真正的问题"
        )

    def test_gate_accepts_the_real_spring(self, entrances):
        """反过来说：真实配方必须过，否则闸门只是禁止一切动效。"""
        popped = _offenders(
            entrances,
            lambda e: e.travel >= MOVING_TRAVEL_PX and e.first_opacity > MAX_FIRST_FRAME_OPACITY,
        )
        assert not popped


def _label(entry: Entrance) -> str:
    return f"{entry.scene}/{entry.key}"


class TestEveryEntrance:
    """把「一个标题」的机检扩到每一幕每一个入场元素。"""

    def test_sweep_covers_the_whole_film(self, entrances):
        """扫描本身要可信：覆盖每一幕，否则「全部通过」可能只是没扫到。"""
        per_scene: dict[str, int] = {}
        for entry in entrances:
            per_scene[entry.scene] = per_scene.get(entry.scene, 0) + 1
        missing = [
            scene["id"]
            for scene in _storyboard()["scenes"]
            if per_scene.get(scene["id"], 0) == 0
        ]
        assert not missing, f"这些幕没有扫到任何入场元素：{missing}（逐幕统计：{per_scene}）"
        moving = [entry for entry in entrances if entry.travel >= MOVING_TRAVEL_PX]
        assert len(moving) >= MIN_MOVING_TRAVEL_COUNT, (
            f"只有 {len(moving)} 个元素量到位移（至少应有 {MIN_MOVING_TRAVEL_COUNT} 个），"
            "位移读取可能退化了"
        )

    def test_no_moving_entrance_pops(self, entrances):
        """有位移的入场，第一帧不能把不透明度基本拉满。

        旧实现第一帧就跳到 0.438，同时位移走完 44%——观众看到的就是一次硬切。
        """
        bad = _offenders(
            entrances,
            lambda e: e.travel >= MOVING_TRAVEL_PX and e.first_opacity > MAX_FIRST_FRAME_OPACITY,
        )
        assert not bad, (
            f"这些有位移的入场第一帧不透明度就超过 {MAX_FIRST_FRAME_OPACITY:.0%}："
            + ", ".join(f"{_label(e)} {e.first_opacity:.2f}" for e in bad)
        )

    def test_moving_entrances_take_enough_frames(self, entrances):
        """有位移的入场要够慢：观众得看见「移动」，而不是「换了个位置」。"""
        bad = _offenders(
            entrances,
            lambda e: e.travel >= MOVING_TRAVEL_PX and e.frames_to_90 < MIN_OPACITY_FRAMES_TO_90,
        )
        assert not bad, (
            f"这些有位移的入场在不足 {MIN_OPACITY_FRAMES_TO_90} 帧内就到 90%："
            + ", ".join(f"{_label(e)} {e.frames_to_90} 帧" for e in bad)
        )

    def test_no_entrance_flickers(self, entrances):
        """入场期间不透明度只能上升：中途回退就是一闪。"""
        bad = _offenders(entrances, lambda e: e.reverses)
        assert not bad, "这些入场在落地之前不透明度回退了：" + ", ".join(_label(e) for e in bad)

    def test_every_entrance_lands_inside_its_scene(self, entrances):
        """入场必须在幕内走完：内容不能还在动就被切到下一幕。

        入场变慢之后这条才有意义（旧的 3 帧弹跳天然不会超时）。
        """
        bad = _offenders(entrances, lambda e: e.margin < MIN_LANDING_MARGIN)
        assert not bad, (
            f"这些入场落地时距幕尾不足 {MIN_LANDING_MARGIN} 帧："
            + ", ".join(f"{_label(e)} 落地于 {e.landed}/{e.duration}" for e in bad)
        )
