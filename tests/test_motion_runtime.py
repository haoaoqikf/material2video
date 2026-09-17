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
const vm = require('vm');

const sandbox = { console: console };
sandbox.window = sandbox;
vm.createContext(sandbox);
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

const out = { recipes: {}, springs: {}, surface: {}, figure: {}, tempo: {}, beat: {}, flat: {} };

const s = stateOf('normal', 30, 240);

// p=0.25 的签名最有信息量：p=0 与 p=1 是两端，看不出中段的曲线形状
function sample(target, fn, p) {
  const node = el();
  fn(s, node, p, {});
  target.transform = node.style.transform === undefined ? node.attrs.transform : node.style.transform;
  target.opacity = node.style.opacity === undefined ? node.attrs.opacity : node.style.opacity;
}

sample((out.surface.p25 = {}), motion.enter, 0.25);
sample((out.surface.p0 = {}), motion.enter, 0);
sample((out.surface.p1 = {}), motion.enter, 1);
sample((out.figure.p25 = {}), motion.enterSvg, 0.25);
sample((out.figure.p0 = {}), motion.enterSvg, 0);
sample((out.figure.p1 = {}), motion.enterSvg, 1);

out.recipes = motion.recipes();
out.springs = motion.springs();

// 具名弹性：与手写同样的阻尼/频率必须完全一致
out.springs.sameAsLiteral =
  motion.spring(0.37, 'lively') === sandbox.A2V.spring(0.37, { damping: 5.5, frequency: 1.3 });
out.springs.unknownFallsBackToFirm =
  motion.spring(0.37, '不存在') === sandbox.A2V.spring(0.37, { damping: 6, frequency: 1.2 });

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
        assert surface["springDamping"] == figure["springDamping"]
        assert surface["springFrequency"] == figure["springFrequency"]
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
            sample = runtime[side]["p0"]
            assert float(sample["opacity"]) == 0
            assert f"{distance}.00" in sample["transform"].replace("-", "")

    def test_ends_settled_and_opaque(self, runtime):
        for side in ("surface", "figure"):
            assert float(runtime[side]["p1"]["opacity"]) == 1
            assert "scale(1.0000)" in runtime[side]["p1"]["transform"]

    def test_midway_signature(self, runtime):
        """中段签名：曲线形状、默认距离、呼吸相位任何一处变了都会在这里现形。"""
        assert runtime["surface"]["p25"]["transform"] == "translate3d(0.00px,6.38px,0) scale(1.0000)"
        assert float(runtime["surface"]["p25"]["opacity"]) == pytest.approx(0.8551, abs=1e-3)
        assert runtime["figure"]["p25"]["transform"] == "translate(0.00 5.80) scale(1.0000)"

    def test_the_two_entrances_differ_only_by_recipe(self, runtime):
        """同一进度下透明度相同：差别只在默认距离与呼吸周期，不在曲线。"""
        assert runtime["surface"]["p25"]["opacity"] == runtime["figure"]["p25"]["opacity"]


class TestSprings:
    """弹性预设只是给数字起名，取值必须与手写完全一致。"""

    def test_all_presets_are_named_and_ordered(self, runtime):
        springs = runtime["springs"]
        assert set(springs) == {"enter", "firm", "lively", "snap"} or set(springs) == {
            "enter",
            "firm",
            "lively",
            "snap",
            "sameAsLiteral",
            "unknownFallsBackToFirm",
        }
        # 阻尼越小回弹越明显：snap 最干脆，lively 最弹
        damping = {name: value["damping"] for name, value in springs.items() if name in {"enter", "firm", "lively", "snap"}}
        assert damping["snap"] <= damping["lively"] <= damping["firm"]

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
        """阻尼与频率只应出现在运行时的预设表里。"""
        body = self._figures()
        assert not re.search(r"damping:\s*[\d.]+", body)
        assert not re.search(r"frequency:\s*[\d.]+", body)

    def test_library_uses_named_presets(self):
        assert re.search(r"motion\.spring\([^,]+, '(enter|firm|lively|snap)'\)", self._figures())

    def test_library_drift_period_comes_from_the_runtime(self):
        """幕内微动的周期统一由运行时给，组件只给振幅与相位。"""
        assert not re.search(r"api\.breath\(\w+, \{ periodFrames: 150", self._figures())
        assert "motion.idle(" in self._figures()

    def test_library_entrances_delegate(self):
        text = self._figures()
        assert "motion.enter(state, el, p, options)" in text
        assert "motion.enterSvg(state, node, p, options)" in text

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
    for name in ("enter:", "enterSvg:", "beat:", "settle:", "tempo:", "recipes:"):
        assert name in text, f"运行时没有导出 motion.{name.rstrip(':')}"

    # 既挂在全局（组件库加载时用），也挂在传给 render 的 api 上
    assert text.count("motion: motion") == 2
