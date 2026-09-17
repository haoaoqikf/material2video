"""排版引擎的纯函数行为。

`typography.js` 有三类函数：依赖实测宽度的（`fit` / `measureAdvance` / `autofit`）、
依赖 DOM 的（`optical` / `applyFit`）、以及完全不依赖浏览器的纯函数
（`balance` / `levelAtLeast` / `scale` / `estimatedLines` 的估算分支）。

纯函数这层最容易悄悄改坏：断行结果变了不会报错，只会让成片里的换行位置
看起来「有点怪」。这里用 Node 直接跑真实脚本（不是抄一份逻辑），
把边界固定下来。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / ".agents" / "skills" / "article2video" / "assets"
TYPOGRAPHY = ASSETS / "typography.js"
TIMELINE = ASSETS / "timeline.js"
SCRIPTS = ROOT / ".agents" / "skills" / "article2video" / "scripts"

_HARNESS = r"""
const fs = require('fs');
const vm = require('vm');

// 最小 DOM 替身：只够纯函数用；需要真实测量的分支不走这里。
function makeNode(width, font) {
  const node = {
    textContent: '',
    style: {},
    dataset: {},
    attrs: {},
    children: [],
    parentElement: null,
    setAttribute(k, v) { this.attrs[k] = v; if (k.startsWith('data-')) this.dataset[k.slice(5).replace(/-([a-z])/g, (m, c) => c.toUpperCase())] = v; },
    getAttribute(k) { return this.attrs[k] === undefined ? null : this.attrs[k]; },
    hasAttribute(k) { return this.attrs[k] !== undefined; },
    appendChild(child) { this.children.push(child); child.parentElement = this; return child; },
    removeChild(child) { this.children = this.children.filter(c => c !== child); return child; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    closest() { return null; },
    getBoundingClientRect() { return { width: width, height: 0, top: 0, left: 0, right: width, bottom: 0 }; },
    get clientWidth() { return width; },
    get offsetWidth() { return width; },
    get ownerDocument() { return doc; }
  };
  Object.defineProperty(node, 'firstChild', { get() { return this.children[0] || null; } });
  return node;
}

const doc = {
  documentElement: { style: { setProperty() {} }, dataset: {}, classList: { add() {}, remove() {} } },
  fonts: { ready: Promise.resolve(), check() { return true; }, load() { return Promise.resolve(); } },
  createElement(tag) { return makeNode(0); },
  createRange() {
    return { selectNodeContents() {}, getBoundingClientRect() { return { width: 0 }; } };
  },
  getComputedStyle() { return { fontFamily: 'sans-serif', fontSize: '16px', letterSpacing: 'normal', getPropertyValue() { return ''; } }; },
  querySelector() { return null; },
  querySelectorAll() { return []; }
};

const sandbox = {
  console,
  document: doc,
  getComputedStyle: doc.getComputedStyle,
  requestAnimationFrame() {},
  setTimeout,
  clearTimeout,
  Promise,
  Math,
  Array,
  Object,
  String,
  Number,
  JSON,
  Range: function Range() {}
};
sandbox.window = sandbox;
vm.createContext(sandbox);
// 真实加载顺序：typography.js 挂在 timeline.js 建立的 A2V 命名空间上
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox, { filename: 'timeline.js' });
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox, { filename: 'typography.js' });

const type = sandbox.A2V.type;
const out = { scale: type.scale(), balance: {}, levels: {}, estimate: {} };
// 均衡断行：中文语义断点
out.balance.cjk = type.balance('多一个选项并不是多一份自由', 8);
out.balance.cjkLong = type.balance('我们以为选择越多越自由，其实每多一个选项就多一次犹豫', 10);
// 硬换行必须被尊重
out.balance.hardBreak = type.balance('第一行\n第二行更长一些', 4);
// 中英混排按空格断
out.balance.mixed = type.balance('越多的选项 means 越慢的决定', 9);
// 行首禁则：逗号/句号不能被甩到行首
out.balance.noLeadingPunctuation = type.balance('事实是，选择越多，决定越慢，人越累。', 8);
// 极端输入
out.balance.empty = type.balance('', 8);
out.balance.shortText = type.balance('短', 8);
out.balance.tinyLimit = type.balance('一二三四五六七八九十', 1);
out.balance.nullText = type.balance(null, 6);

// 取档：下限 36px 应落到 body(40)，上限与越界
out.levels.atLeast36 = type.levelAtLeast(36).name;
out.levels.atLeast40 = type.levelAtLeast(40).name;
out.levels.atLeast1000 = type.levelAtLeast(1000).name;
out.levels.minBodyPx = type.minBodyPx;

console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def engine() -> dict:
    if shutil.which("node") is None:
        pytest.skip("未安装 Node，跳过排版引擎的纯函数测试")
    harness = SCRIPTS / "_typography_harness.js"
    harness.write_text(_HARNESS, encoding="utf-8")
    try:
        result = subprocess.run(
            ["node", str(harness), str(TIMELINE), str(TYPOGRAPHY)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    finally:
        harness.unlink(missing_ok=True)
    return json.loads(result.stdout.strip().splitlines()[-1])


class TestScale:
    def test_scale_is_descending(self, engine):
        # 契约：SCALE 从大到小排列，fit() 与 levelAtLeast() 都依赖这个顺序
        sizes = [entry["size"] for entry in engine["scale"]]
        assert sizes == sorted(sizes, reverse=True)
        assert sizes[0] == 140 and sizes[-1] == 28
        assert len(sizes) == 8

    def test_every_level_carries_leading_and_tracking(self, engine):
        for entry in engine["scale"]:
            assert entry["leading"] > 0, entry
            assert "tracking" in entry

    def test_min_body_floor_lands_on_a_scale_level(self, engine):
        # 正文下限 36px 不是档位，向上取档必须落在 body(40) 上，
        # 否则「不低于 36px」会在取档时落到阶外
        assert engine["levels"]["minBodyPx"] == 36
        assert engine["levels"]["atLeast36"] == "body"


class TestLevelAtLeast:
    def test_rounds_up_to_the_scale(self, engine):
        # 36 不是档位，应向上落到 body(40)
        assert engine["levels"]["atLeast36"] == "body"
        assert engine["levels"]["atLeast40"] == "body"

    def test_request_beyond_top_returns_top(self, engine):
        # 越界时给最大档，不能返回 undefined（返回 undefined 会让字号变成 NaN）
        assert engine["levels"]["atLeast1000"] == "hero"


class TestBalance:
    def test_respects_the_line_limit(self, engine):
        for name, lines in engine["balance"].items():
            if not isinstance(lines, list):
                continue
            limit = {
                "cjk": 8,
                "cjkLong": 10,
                "hardBreak": 4,
                "mixed": 9,
                "noLeadingPunctuation": 8,
                "empty": 8,
                "shortText": 8,
                "tinyLimit": 2,
                "nullText": 6,
            }[name]
            for line in lines:
                assert len(line) <= limit, f"{name} 的行 {line!r} 超过 {limit} 字"

    def test_no_line_starts_with_punctuation(self, engine):
        # 中文避头尾：逗号、句号不能被甩到下一行行首
        for line in engine["balance"]["noLeadingPunctuation"]:
            if line:
                assert line[0] not in "，。、；：！？）】》", f"行首出现标点：{line!r}"

    def test_hard_break_wins(self, engine):
        assert engine["balance"]["hardBreak"][0] == "第一行"

    def test_no_orphan_last_line(self, engine):
        # 末行只剩一个字是最典型的「排坏了」，均衡断行必须避免
        for name in ("cjk", "cjkLong"):
            lines = engine["balance"][name]
            if len(lines) > 1:
                assert len(lines[-1]) >= 2, f"{name} 末行成了孤字：{lines}"

    def test_keeps_every_character(self, engine):
        # 断行不许丢字：这是最安静的一类错，只有读成片才发现
        text = "我们以为选择越多越自由，其实每多一个选项就多一次犹豫"
        assert "".join(engine["balance"]["cjkLong"]) == text

    def test_degenerate_inputs_do_not_throw(self, engine):
        assert engine["balance"]["empty"] == [""]
        assert engine["balance"]["shortText"] == ["短"]
        assert engine["balance"]["nullText"] == [""]
        # 上限小于 2 时按 2 处理，不能返回空行把文本吃掉
        assert "".join(engine["balance"]["tinyLimit"]) == "一二三四五六七八九十"
