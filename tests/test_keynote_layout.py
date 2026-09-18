"""预设生效时的版面几何。

任务里写的是「安全区网格对齐、居中与下置布局的字号档选择」。这些性质**可以量**，
所以不靠看截图：真的用浏览器打开共享页面，读出每个文本块的位置与字号，
再对着契约断言。截图只能证明「当时看着还行」，量测才能防止以后改坏。

三种布局（`center` / `lower` / 默认左对齐）各测一遍，两种主题各测一遍。
"""

from __future__ import annotations

import functools
import http.server
import json
import pathlib
import re
import socketserver
import threading
from urllib.parse import quote

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / ".agents" / "skills" / "article2video" / "assets" / "declarative.html"

#: 预设的安全区（keynote.css 的 --a2v-safe-top / -bottom / -x）
SAFE_TOP = 240
SAFE_BOTTOM = 320
SAFE_X = 96
WIDTH, HEIGHT = 1080, 1920

#: 字号阶（keynote.css 的 --a2v-size-*）+ 与 K3 统计下限对齐的 44px。
#: 44px 是「组件墨色字号」里的 `--a2v-ink-value`：它刻意与 K3 的 44px 下限同值，
#: 因此不再另立一档，但仍算「阶上」。
def _declared_scale() -> set[float]:
    """从设计语言层读字号阶，不在这里另抄一份。

    这里原先硬写着 `{28, 34, 40, 44, 60, 76, 96, 120, 140}`：**44 并不在阶上**，
    而真实阶里的 220 / 350 又没写进来。抄一份的代价是抄错的那一档恰好
    放过了后来查出的缺陷——组件把 `font-size: 44px` 写死在 `figures.css` 里，
    这一幕的"字号必须在阶上"就没有报错。真源是 `keynote.css` 的
    `--a2v-size-*`；把它读出来，阶变了测试跟着变，抄错就不可能再发生。
    """
    css = (PAGE.parent / "keynote.css").read_text(encoding="utf-8")
    sizes = re.findall(r"--a2v-size-[a-z]+:\s*([\d.]+)px", css)
    assert len(sizes) >= 8, f"只从 keynote.css 读到 {len(sizes)} 档字号，正则或文件结构变了"
    return {float(size) for size in sizes}


SCALE = _declared_scale()

#: 不参与字号阶的装饰字形：引号符号与逐字揭示产生的单字节点。
#: 它们不是「一层信息」，量它们的字号只会把阶外数值混进来。
DECORATIVE = (".quote-mark", ".reveal-char")

#: 允许的取整误差：浏览器会给亚像素位置，字体也有半像素基线
TOLERANCE = 1.5

#: 四种版面各一幕，幕长 90 帧，因此第 i 幕的采样帧取 60 + 90i。
#: 第二项是分镜里声明的 `visual.layout`（`None` 表示不声明）。
SCENES = (
    ("centered", "center"),
    ("lowered", "lower"),
    ("left", "left"),
    ("fallback", None),
)


def _storyboard(theme: str) -> dict:
    return {
        "version": 1,
        "fps": 30,
        "width": WIDTH,
        "height": HEIGHT,
        "title": "版面几何",
        "visual": {"theme": theme, "preset": "keynote"},
        "scenes": [
            {
                "id": "centered",
                "type": "quote",
                "durationInFrames": 90,
                "visual": {"layout": "center"},
                "data": {"text": "居中场景的文字块应该居中", "source": "几何检查"},
            },
            {
                "id": "lowered",
                "type": "conclusion",
                "durationInFrames": 90,
                "visual": {"layout": "lower"},
                "data": {"text": "下置场景的文字块应该靠下", "action": "继续"},
            },
            {
                "id": "left",
                "type": "list",
                "durationInFrames": 90,
                "visual": {"layout": "left"},
                "data": {"items": ["第一项文字", "第二项文字", "第三项文字"]},
            },
            {
                # 不声明 layout：用来钉住「共享页面的兜底是 center」这条契约
                "id": "fallback",
                "type": "quote",
                "durationInFrames": 90,
                "data": {"text": "未声明版面的兜底", "source": "契约检查"},
            },
        ],
    }


_MEASURE_JS = """() => {
  const scenes = document.querySelectorAll('[data-a2v-scene]');
  let active = null;
  for (const s of scenes) {
    const st = getComputedStyle(s);
    if (st.display !== 'none' && st.visibility !== 'hidden') { active = s; break; }
  }
  if (!active) return null;
  const out = { id: active.getAttribute('data-scene-id'), safe: null, blocks: [] };
  const safe = active.querySelector('.a2v-safe');
  if (!safe) return out;
  const sr = safe.getBoundingClientRect();
  const st = getComputedStyle(safe);
  out.safe = {
    left: sr.left, right: sr.right, top: sr.top, bottom: sr.bottom,
    display: st.display, align: st.alignItems, textAlign: st.textAlign, justify: st.justifyContent
  };

  // 只量「内容文字」：装饰字形跳过，带子节点的容器跳过
  // （否则会量到同一个文字的父盒），逐字揭示产生的单字节点也跳过
  // （它们是同一句话的碎片，量出来只会把阶外字号混进层级统计）。
  const DECOR = ['.quote-mark', '.reveal-char'];
  const nodes = [];
  safe.querySelectorAll('*').forEach((node) => {
    if (DECOR.some((sel) => node.matches(sel))) return;
    if (node.children.length) return;
    const text = (node.textContent || '').trim();
    if (!text) return;
    if (Array.from(text).length < 2) return;
    const cs = getComputedStyle(node);
    const r = node.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    nodes.push({
      role: (node.className && node.className.toString().trim().split(/\\s+/)[0]) || node.tagName.toLowerCase(),
      text: text.slice(0, 12),
      fontSize: parseFloat(cs.fontSize),
      textAlign: cs.textAlign,
      left: r.left, right: r.right, top: r.top, bottom: r.bottom,
      // 文字的**实际**中心：元素盒可能比文字宽（比如带内边距的行盒），
      // 因此居中判断必须用 Range 量到的字形位置，不能用盒子位置
      center: (() => {
        const range = document.createRange();
        range.selectNodeContents(node);
        const rr = range.getBoundingClientRect();
        return rr.width > 0 ? rr.left + rr.width / 2 : r.left + r.width / 2;
      })()
    });
  });
  out.blocks = nodes;
  return out;
}"""


def _measure(theme: str, tmp_path: pathlib.Path, scene_index: int) -> dict:
    """打开共享页面，读出第 scene_index 幕里每个文本块的位置、字号与对齐方式。"""
    playwright = pytest.importorskip("playwright.sync_api")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):  # noqa: D102 - 测试里不需要访问日志
            pass

    # 分镜必须落在静态根目录之内才能被页面 fetch 到；用完即删，
    # 否则会污染仓库（测试失败时也走 finally 删除）。
    storyboard_file = ROOT / f".layout-probe-{theme}.json"
    storyboard_file.write_text(json.dumps(_storyboard(theme), ensure_ascii=False), encoding="utf-8")

    with socketserver.ThreadingTCPServer(
        ("127.0.0.1", 0), functools.partial(Handler, directory=str(ROOT))
    ) as httpd:
        httpd.daemon_threads = True
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            storyboard_url = quote("/" + storyboard_file.relative_to(ROOT).as_posix(), safe="")
            page_url = (
                f"http://127.0.0.1:{port}/{PAGE.relative_to(ROOT).as_posix()}"
                f"?a2v-storyboard={storyboard_url}"
            )
            with playwright.sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
                page.goto(page_url)
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-a2v-scene]').length > 0",
                    timeout=20000,
                )
                page.wait_for_timeout(600)
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                # 采样点取每一幕的后段：入场动画已结束，量到的是稳定的版面
                page.evaluate("(f) => window.__A2V__.seekToFrame(f)", 60 + scene_index * 90)
                page.wait_for_timeout(200)
                facts = page.evaluate(_MEASURE_JS)
                browser.close()
                assert facts, "没有找到可见场景"
                return facts
        finally:
            storyboard_file.unlink(missing_ok=True)
            httpd.shutdown()


@pytest.fixture(scope="module")
def dark_scenes(tmp_path_factory) -> dict[str, dict]:
    tmp = tmp_path_factory.mktemp("layout-dark")
    return {scene_id: _measure("dark", tmp, index) for index, (scene_id, _) in enumerate(SCENES)}


@pytest.fixture(scope="module")
def light_scenes(tmp_path_factory) -> dict[str, dict]:
    tmp = tmp_path_factory.mktemp("layout-light")
    return {scene_id: _measure("light", tmp, index) for index, (scene_id, _) in enumerate(SCENES)}


class TestSafeArea:
    @pytest.mark.parametrize("scene_id", [scene_id for scene_id, _ in SCENES])
    def test_every_block_stays_inside_the_safe_area(self, dark_scenes, scene_id):
        blocks = dark_scenes[scene_id]["blocks"]
        assert blocks, f"{scene_id} 没有量到任何文本块，探针失效了"
        for block in blocks:
            assert block["left"] >= SAFE_X - TOLERANCE, f"{block['text']!r} 越过左安全线：{block['left']}"
            assert block["right"] <= WIDTH - SAFE_X + TOLERANCE, f"{block['text']!r} 越过右安全线：{block['right']}"
            assert block["top"] >= SAFE_TOP - TOLERANCE, f"{block['text']!r} 顶进状态栏：{block['top']}"
            assert block["bottom"] <= HEIGHT - SAFE_BOTTOM + TOLERANCE, f"{block['text']!r} 压到底部栏：{block['bottom']}"

    @pytest.mark.parametrize("scene_id", [scene_id for scene_id, _ in SCENES])
    def test_light_theme_has_the_same_geometry(self, light_scenes, dark_scenes, scene_id):
        # 换主题只换颜色，不该动版面；动了说明有版式规则漏在主题块里
        light, dark = light_scenes[scene_id], dark_scenes[scene_id]
        assert len(light["blocks"]) == len(dark["blocks"]), f"{scene_id} 两种主题量到的文本块数量不同"
        for one, other in zip(light["blocks"], dark["blocks"]):
            assert abs(one["top"] - other["top"]) <= TOLERANCE, one["text"]
            assert abs(one["left"] - other["left"]) <= TOLERANCE, one["text"]
            assert abs(one["fontSize"] - other["fontSize"]) <= 0.1, one["text"]


class TestTypeScale:
    @pytest.mark.parametrize("scene_id", [scene_id for scene_id, _ in SCENES])
    def test_every_size_sits_on_the_scale(self, dark_scenes, scene_id):
        # 不在阶上的字号会绕过 K3（同帧字号种类），层级就不再可枚举
        for block in dark_scenes[scene_id]["blocks"]:
            size = round(block["fontSize"], 1)
            assert size in SCALE, f"{block['text']!r} 用了阶外字号 {size}"

    @pytest.mark.parametrize("scene_id", [scene_id for scene_id, _ in SCENES])
    def test_at_most_four_sizes_per_frame(self, dark_scenes, scene_id):
        sizes = {round(block["fontSize"], 1) for block in dark_scenes[scene_id]["blocks"]}
        assert len(sizes) <= 4, f"{scene_id} 同帧出现 {len(sizes)} 种字号：{sorted(sizes)}"


class TestLayouts:
    def test_center_layout_centers_its_blocks(self, dark_scenes):
        facts = dark_scenes["centered"]
        assert facts["safe"]["align"] == "center"
        assert facts["safe"]["textAlign"] == "center"
        center = (facts["safe"]["left"] + facts["safe"]["right"]) / 2
        assert abs(center - WIDTH / 2) <= TOLERANCE
        for block in facts["blocks"]:
            assert abs(block["center"] - center) <= 2.0, (
                f"{block['text']!r} 的中心 {block['center']} 偏离画面中心 {center}"
            )

    def test_lower_layout_pushes_content_down(self, dark_scenes):
        # 下置布局：内容底边应明显低于画面中线，否则「下置」名不副实
        facts = dark_scenes["lowered"]
        assert facts["safe"]["justify"] == "flex-end"
        lowest = max(block["bottom"] for block in facts["blocks"])
        assert lowest > HEIGHT / 2

    def test_left_layout_aligns_to_the_left(self, dark_scenes):
        facts = dark_scenes["left"]
        assert facts["safe"]["textAlign"] == "left"
        assert facts["safe"]["align"] == "flex-start"
        # 左对齐场景的正文块应当从同一条左边缘起排（组件自身的图形元素除外）
        lefts = sorted({round(b["left"]) for b in facts["blocks"]})
        assert lefts, "没有量到文本块"
        assert lefts[0] >= SAFE_X - TOLERANCE

    def test_undeclared_layout_falls_back_to_center(self, dark_scenes):
        """没声明 `visual.layout` 时，共享页面的兜底是**居中**。

        这条钉住的是 `declarative.js` 的既有行为（`(scene.visual||{}).layout || 'center'`）。
        预设不推翻它：那需要改共享页面，会波及所有未启用预设的视频。
        """
        facts = dark_scenes["fallback"]
        assert facts["safe"]["textAlign"] == "center"
        assert facts["safe"]["align"] == "center"

    def test_safe_area_is_the_layout_box(self, dark_scenes):
        # `lower` 那类布局靠 justify-content 定位，前提是安全区本身是
        # 撑满全屏的 flex 容器；这条一旦破了，「下置」就会静默失效
        for scene_id, facts in dark_scenes.items():
            assert facts["safe"]["display"] == "flex", scene_id
            assert facts["safe"]["top"] <= SAFE_TOP + TOLERANCE, scene_id
            assert facts["safe"]["bottom"] >= HEIGHT - SAFE_BOTTOM - TOLERANCE, scene_id


#: 真分镜：八幕，每幕都用了不同的组件。上面那套合成样张只有四种版面、
#: 没有 `title` / `exchange` 这类组件，所以**量不到组件自己写死的字号**——
#: 两个真实缺陷（`figures.css` 里写死 44px、结论句自算出 88px）都是从这里漏掉的。
BASELINE = ROOT / "examples" / "keynote-baseline" / "storyboard.json"

_ALL_SIZES_JS = """(id) => {
  const scene = document.querySelector('[data-scene-id="' + id + '"]');
  const out = [];
  scene.querySelectorAll('*').forEach((e) => {
    if (!e.textContent || !e.textContent.trim()) return;
    // 只取叶子节点：容器会把子元素的字号一起带进来
    if (Array.from(e.childNodes).some((n) => n.nodeType === 1)) return;
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    if (parseFloat(cs.opacity) === 0) return;
    const cls = (e.className && e.className.baseVal !== undefined)
      ? e.className.baseVal : (e.className || e.tagName);
    out.push({size: parseFloat(cs.fontSize), cls: String(cls).split(' ')[0],
              text: e.textContent.trim().slice(0, 12)});
  });
  return out;
}"""


def _baseline_sizes() -> list[dict]:
    """打开真分镜，读出每一幕每个文字节点的字号。"""
    playwright = pytest.importorskip("playwright.sync_api", reason="未安装 playwright")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):  # noqa: D102 - 测试里不需要访问日志
            pass

    with socketserver.ThreadingTCPServer(
        ("127.0.0.1", 0), functools.partial(Handler, directory=str(ROOT))
    ) as httpd:
        httpd.daemon_threads = True
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        page_url = f"http://127.0.0.1:{port}/{PAGE.relative_to(ROOT).as_posix()}"
        board_url = quote("/" + BASELINE.relative_to(ROOT).as_posix(), safe="")
        try:
            with playwright.sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
                page.goto(f"{page_url}?a2v-storyboard={board_url}")
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-a2v-scene]').length > 0",
                    timeout=20000,
                )
                page.wait_for_timeout(600)
                page.evaluate("() => document.documentElement.classList.add('a2v-rendering')")
                storyboard = json.loads(BASELINE.read_text(encoding="utf-8"))
                cursor = 0
                found: list[dict] = []
                for scene in storyboard["scenes"]:
                    # 采样点取每一幕的六成处：入场结束，量到稳定版面
                    page.evaluate(
                        "(f) => window.__A2V__.seekToFrame(f)",
                        cursor + int(scene["durationInFrames"] * 0.6),
                    )
                    cursor += scene["durationInFrames"]
                    for row in page.evaluate(_ALL_SIZES_JS, scene["id"]):
                        row["scene"] = scene["id"]
                        found.append(row)
                browser.close()
        finally:
            httpd.shutdown()
    assert found, "真分镜里一个文字节点都没读到，采样选择器需要更新"
    return found


class TestBaselineTypeScale:
    """真分镜的每一个字号都必须在阶上。

    这条在合成样张那边是量不到的（那边没有组件），所以之前两个阶外字号
    ——`figures.css` 写死的 44px、结论句自算出来的 88px——都从检查里漏了过去。
    """

    @pytest.fixture(scope="class")
    def baseline_sizes(self) -> list[dict]:
        return _baseline_sizes()

    def test_every_rendered_size_is_a_declared_rung(self, baseline_sizes):
        offenders = [
            (row["scene"], row["cls"], row["text"], row["size"])
            for row in baseline_sizes
            if not any(abs(row["size"] - rung) <= TOLERANCE for rung in SCALE)
        ]
        assert not offenders, (
            f"真分镜里出现阶外字号（幕, 类, 文字, px）：{offenders}——"
            f"字号阶是 {sorted(SCALE, reverse=True)}，组件不许自己另立一档"
        )

    def test_the_ladder_has_no_duplicate_neighbours(self, baseline_sizes):
        """相邻两档至少要差 10%：差 4px 的两个字号看不出区别，只会像失手。"""
        used = sorted({round(row["size"]) for row in baseline_sizes}, reverse=True)
        for big, small in zip(used, used[1:]):
            assert big - small >= big * 0.1, (
                f"{big}px 与 {small}px 相差不到 10%——同一支片子里两个"
                "看不出区别的字号不是一个层级，是失手"
            )
