"""动效配方层（timeline.js 的 A2V.motion）。

这一层的存在理由是「手感参数只有一处」：入场用哪条曲线、弹性多大、
什么时候收敛、常驻微动多快。散落在组件里就没人能整体调，
新写的组件也会慢慢长成另一种手感。

因此这里用真跑一遍运行时来钉住数值，而不是只做文本匹配：
改配方是可以的（那正是它存在的意义），但改动必须是有意的、能被看见的。
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[1] / ".agents/skills/article2video/assets"
FIGURES = ASSETS / "figures.js"
TIMELINE = ASSETS / "timeline.js"

_HARNESS = r"""
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const sandbox = { console: console };
sandbox.window = sandbox;
vm.createContext(sandbox);
// 弹簧求解器是 timeline.js 的依赖，必须先加载——缺了它运行时取曲线时会直接抛错
vm.runInContext(
  fs.readFileSync(path.join(path.dirname(process.argv[2]), 'vendor', 'spring.js'), 'utf8'),
  sandbox,
  { filename: 'vendor/spring.js' }
);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox, { filename: 'timeline.js' });

const A2V = sandbox.A2V;
const motion = A2V.motion;

// 极简元素替身：只记录被写入的属性
function el() {
  return { style: {}, attrs: {}, setAttribute(k, v) { this.attrs[k] = v; } };
}

function stateOf(motionName, localFrame, duration) {
  return {
    frame: localFrame,
    localFrame: localFrame,
    sceneDurationFrames: duration,
    scene: { id: 's', type: 'diagram', data: { figure: { kind: 'loop', motion: motionName } } }
  };
}

const out = { recipes: {}, springs: {}, surface: {}, figure: {}, tempo: {}, beat: {}, flat: {}, since: {} };

const s = stateOf('normal', 30, 240);

// 入场签名取三个时刻：起点、中段、已收敛。
// 中段最有信息量：两端看不出曲线的形状。
function sample(target, fn, p) {
  const node = el();
  fn(s, node, p, {});
  target.transform = node.style.transform === undefined ? node.attrs.transform : node.style.transform;
  target.opacity = node.style.opacity === undefined ? node.attrs.opacity : node.style.opacity;
}

sample((out.surface.at0 = {}), motion.enter, 0);
sample((out.surface.mid = {}), motion.enter, 0.15);
sample((out.surface.settled = {}), motion.enter, 2);
sample((out.figure.at0 = {}), motion.enterSvg, 0);
sample((out.figure.mid = {}), motion.enterSvg, 0.15);
sample((out.figure.settled = {}), motion.enterSvg, 2);

out.recipes = motion.recipes();
out.springs = motion.springs();

// 具名弹性：与手写同样的物理参数必须完全一致
out.springs.sameAsLiteral =
  motion.spring(0.37, 'lively') === sandbox.A2V.spring(0.37, { response: 0.4, dampingFraction: 0.62 });
out.springs.unknownFallsBackToFirm =
  motion.spring(0.37, '不存在') === sandbox.A2V.spring(0.37, { response: 0.44, dampingFraction: 0.9 });

// 秒数换算是弹簧的时间基准：帧号按 fps 换成秒，起点之前夹到 0
out.since.atStart = A2V.since(30, 30);
out.since.oneFrameAt30 = A2V.since(31, 30);
out.since.beforeStart = A2V.since(20, 30);
out.since.oneSecondAt30 = A2V.since(60, 30);

['calm', 'normal', 'impact', 'unknown'].forEach(function (name) {
  out.tempo[name] = motion.tempo(name);
  out.beat[name] = motion.beat(stateOf(name, 0, 240), 0.5);
});

// 声明写在 data 里；同时接受直接传 data 的形状
out.flat.beatFromData = motion.beat(
  { localFrame: 0, sceneDurationFrames: 240, scene: { figure: { motion: 'impact' } } },
  0.5
);
// 没有声明时按正常速度，不抛错
out.flat.beatWithoutFigure = motion.beat({ localFrame: 0, sceneDurationFrames: 240, scene: {} }, 0.5);

console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def runtime() -> dict:
    """在 Node 里真跑一遍运行时，取回配方与两个入口的实际输出。"""
    if shutil.which("node") is None:
        pytest.skip("未安装 Node，跳过运行时行为测试（文本层面的约束仍由其他用例覆盖）")
    harness = ASSETS.parent / "scripts" / "_motion_harness.js"
    harness.write_text(_HARNESS, encoding="utf-8")
    try:
        result = subprocess.run(
            ["node", str(harness), str(TIMELINE)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    finally:
        harness.unlink(missing_ok=True)
    return json.loads(result.stdout.strip().splitlines()[-1])


class TestRecipes:
    def test_two_recipes_with_the_same_curve(self, runtime):
        """两档配方只差「移动多远、呼吸多快」，弹性必须一致，否则同屏两种手感。"""
        surface, figure = runtime["recipes"]["surface"], runtime["recipes"]["figure"]
        assert surface["springResponse"] == figure["springResponse"]
        assert surface["springDampingFraction"] == figure["springDampingFraction"]
        assert surface["settleAt"] == figure["settleAt"]
        assert surface["settleFrames"] == figure["settleFrames"]

    def test_surface_moves_more_and_breathes_faster(self, runtime):
        surface, figure = runtime["recipes"]["surface"], runtime["recipes"]["figure"]
        assert surface["distance"] > figure["distance"]
        assert surface["periodFrames"] < figure["periodFrames"]

    def test_amplitude_stays_subtle(self, runtime):
        for name, entry in runtime["recipes"].items():
            assert 0 < entry["amplitude"] <= 6, f"{name} 的常驻振幅过大，会让人以为是手抖"

    def test_recipes_are_a_copy(self, runtime):
        """取回的是快照，改它不该影响运行时。"""
        assert runtime["recipes"]["surface"]["distance"] == 44


class TestEntrances:
    """两个入口各自用对配方——SVG 一侧曾经落到 surface 配方上，呼吸周期错成 130。"""

    def test_starts_fully_shifted_and_transparent(self, runtime):
        for side, distance in (("surface", 44), ("figure", 40)):
            sample = runtime[side]["at0"]
            assert float(sample["opacity"]) == 0
            assert f"{distance}.00" in sample["transform"].replace("-", "")

    def test_settles_opaque_and_in_place(self, runtime):
        for side in ("surface", "figure"):
            assert float(runtime[side]["settled"]["opacity"]) == 1
            assert "scale(1.0000)" in runtime[side]["settled"]["transform"]

    def test_midway_signature(self, runtime):
        """中段签名：曲线形状、默认距离、呼吸相位任何一处变了都会在这里现形。

        0.15 秒（30fps 的第 4.5 帧）上进度是 0.672：一半多一点的位移已经走完。
        改回「喂缓动过的进度」会让这个数跳到 0.85 以上——那正是弹跳的来源。
        """
        assert runtime["surface"]["mid"]["transform"] == "translate3d(0.00px,14.43px,0) scale(1.0000)"
        assert float(runtime["surface"]["mid"]["opacity"]) == pytest.approx(0.6720, abs=1e-3)
        assert runtime["figure"]["mid"]["transform"] == "translate(0.00 13.12) scale(1.0000)"

    def test_the_two_entrances_differ_only_by_recipe(self, runtime):
        """同一时刻透明度相同：差别只在默认距离与呼吸周期，不在曲线。"""
        assert runtime["surface"]["mid"]["opacity"] == runtime["figure"]["mid"]["opacity"]


class TestSince:
    """秒数是弹簧的时间基准，换算错了整条曲线的时间尺度就错了。"""

    def test_converts_frames_to_seconds(self, runtime):
        assert runtime["since"]["atStart"] == 0
        assert runtime["since"]["oneSecondAt30"] == pytest.approx(1.0)
        assert runtime["since"]["oneFrameAt30"] == pytest.approx(1 / 30)

    def test_clamps_before_the_start(self, runtime):
        # 起点之前必须是 0，否则弹簧会拿到负数时间（负半周期会先往回弹一下）
        assert runtime["since"]["beforeStart"] == 0


class TestSprings:
    """弹性预设只是给数字起名，取值必须与手写完全一致。"""

    NAMED = ("enter", "firm", "lively", "snap")

    def test_all_presets_are_named_and_physically_ordered(self, runtime):
        springs = runtime["springs"]
        assert set(springs) == set(self.NAMED) | {"sameAsLiteral", "unknownFallsBackToFirm"}
        named = {name: springs[name] for name in self.NAMED}
        # 阻尼比只决定过冲：越小越弹。lively 最弹，enter 临界（一点不过冲）
        assert named["enter"]["dampingFraction"] >= 1
        assert named["lively"]["dampingFraction"] < named["firm"]["dampingFraction"] <= 1
        # response 是自然周期，只决定快慢
        assert named["snap"]["response"] == min(v["response"] for v in named.values())

    def test_preset_equals_hand_written_numbers(self, runtime):
        assert runtime["springs"]["sameAsLiteral"] is True

    def test_unknown_preset_falls_back(self, runtime):
        assert runtime["springs"]["unknownFallsBackToFirm"] is True


class TestTempo:
    def test_named_speeds(self, runtime):
        assert runtime["tempo"] == {"calm": 0.82, "normal": 1, "impact": 1.24, "unknown": 1}

    def test_impact_reaches_a_beat_earlier(self, runtime):
        assert runtime["beat"]["impact"] < runtime["beat"]["normal"] < runtime["beat"]["calm"]

    def test_beat_scales_with_scene_length(self, runtime):
        assert runtime["beat"]["normal"] == 120

    def test_reads_declaration_from_scene_data(self, runtime):
        assert runtime["flat"]["beatFromData"] == pytest.approx(120 / 1.24)

    def test_missing_declaration_falls_back_to_normal(self, runtime):
        assert runtime["flat"]["beatWithoutFigure"] == 120


class TestLibraryDelegates:
    """组件库不再自己持有手感参数。"""

    @staticmethod
    def _figures() -> str:
        return FIGURES.read_text(encoding="utf-8")

    def test_library_has_no_tempo_table(self):
        text = self._figures()
        assert "TEMPO_SPEED" not in text
        assert "currentTempo" not in text

    def test_library_has_no_spring_numbers(self):
        """物理参数只应出现在运行时的预设表里。"""
        body = self._figures()
        assert not re.search(r"\bresponse:\s*[\d.]+", body)
        assert not re.search(r"dampingFraction:\s*[\d.]+", body)
        assert "frequency:" not in body

    def test_library_uses_named_presets(self):
        assert re.search(r"motion\.spring\([^,]+, '(enter|firm|lively|snap)'\)", self._figures())

    def test_library_feeds_the_spring_seconds_not_progress(self):
        """组件喂给弹簧的必须是秒数（api.since），不是缓动过的进度。

        曾经喂的是 `api.progress(f, beat(...), 26, EASE_OUT)`：两条曲线串起来，
        弹簧的自然周期失去意义，实测 3 帧走完 58px。这条断言把它钉住。
        """
        body = self._figures()
        assert "api.since(" in body
        assert not re.search(r"motion\.spring\(\s*api\.progress\(", body)
        assert not re.search(r"enterAlive\([^;]*api\.progress\(", body)
        assert not re.search(r"enterFig\([^;]*api\.progress\(", body)

    def test_library_drift_period_comes_from_the_runtime(self):
        """幕内微动的周期统一由运行时给，组件只给振幅与相位。"""
        assert not re.search(r"api\.breath\(\w+, \{ periodFrames: 150", self._figures())
        assert "motion.idle(" in self._figures()

    def test_library_entrances_delegate(self):
        text = self._figures()
        assert "motion.enter(state, el, seconds, options)" in text
        assert "motion.enterSvg(state, node, seconds, options)" in text

    def test_library_beat_delegates(self):
        assert "return motion.beat(state, fraction);" in self._figures()

    def test_only_one_entry_implementation(self):
        """HTML 与 SVG 的参数解析只写一次，否则必然走偏。"""
        runtime_text = TIMELINE.read_text(encoding="utf-8")
        assert runtime_text.count("function enterRecipe(") == 1
        assert runtime_text.count("function enterAlive(") == 1
        assert runtime_text.count("function enterSvg(") == 1


def test_motion_api_is_exposed_on_the_runtime():
    text = TIMELINE.read_text(encoding="utf-8")
    for name in ("enter:", "enterSvg:", "beat:", "settle:", "tempo:", "recipes:", "since:"):
        assert name in text, f"运行时没有导出 motion.{name.rstrip(':')}"

    # 既挂在全局（组件库加载时用），也挂在传给 render 的 api 上
    assert text.count("motion: motion") == 2
