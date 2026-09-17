"""vendored 弹簧求解器的可信度。

引入外部实现的前提是**它真的对**。这份文件把 assets/vendor/spring.js 拖出来
在 Node 里跑，对着阻尼谐振子的理论值核对——不是核对「我记得的数值」，
而是核对闭式解自己的性质：

  * ζ=1 时不过冲，且单调；
  * ζ<1 时峰值过冲等于 e^(-πζ/√(1-ζ²))（教科书结论，独立于实现）；
  * 曲线只有两个端点固定（0 与 1），与 ω₀ 无关——换 response 只改变快慢，不改变形状；
  * 纯函数：同一入参永远同一结果（没有 Math.random、没有时间源）；
  * 出处与许可证留在文件里，不是「从网上抄来的一段」。

少了这一层，一个符号写错（x₀ = -1 而不是 +1）的解析解看起来也「像弹簧」。
"""

from __future__ import annotations

import json
import math
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".agents" / "skills" / "article2video" / "assets" / "vendor"
SOLVER = VENDOR / "spring.js"
LICENSE = VENDOR / "wobble-LICENSE"

_HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const sandbox = { console: console };
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox, { filename: 'spring.js' });
const solver = sandbox.A2VSpring;

function curve(response, zeta, count) {
  const out = [];
  for (let i = 0; i <= count; i++) {
    out.push(solver.position((i / count) * 2.0, response, zeta));
  }
  return out;
}

const out = {
  atZero: solver.position(0, 0.44, 0.9),
  atNegative: solver.position(-1, 0.44, 0.9),
  critical: curve(0.44, 1, 800),
  lively: curve(0.4, 0.62, 800),
  fastShape: curve(0.2, 0.9, 400),
  slowShape: curve(0.8, 0.9, 400),
  rest: {
    at: solver.restSeconds(0.4, 0.62),
    insideBand: (function () {
      const t = solver.restSeconds(0.4, 0.62);
      return Math.abs(solver.position(t, 0.4, 0.62) - 1);
    })(),
    // Infinity 过不了 JSON.stringify，转成字符串再断言
    zeroDamping: String(solver.restSeconds(0.4, 0))
  },
  source: solver.source,
  license: solver.license,
  deterministic: solver.position(0.123, 0.44, 0.9) === solver.position(0.123, 0.44, 0.9)
};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def solver() -> dict:
    if shutil.which("node") is None:
        pytest.skip("未安装 Node，跳过 vendored 求解器的数学核对")
    harness = ROOT / ".agents" / "skills" / "article2video" / "scripts" / "_solver_harness.js"
    harness.write_text(_HARNESS, encoding="utf-8")
    try:
        result = subprocess.run(
            ["node", str(harness), str(SOLVER)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    finally:
        harness.unlink(missing_ok=True)
    return json.loads(result.stdout.strip().splitlines()[-1])


class TestProvenance:
    def test_declares_its_source_and_license(self, solver):
        # 「从哪儿来的」必须写在文件里，否则没人能判断它能不能用、该不该改
        assert solver["source"] == "wobble@1.5.1"
        assert solver["license"] == "MIT"

    def test_license_text_ships_next_to_it(self):
        assert LICENSE.exists(), "MIT 要求随分发保留许可证全文"
        text = LICENSE.read_text(encoding="utf-8")
        assert "Adam Miskiewicz" in text and "MIT" not in text.splitlines()[0]

    def test_header_records_the_modifications(self):
        header = SOLVER.read_text(encoding="utf-8")
        assert "wobble" in header and "MIT" in header
        assert "改动" in header, "改了上游就必须写明改了什么"


class TestClosedForm:
    def test_starts_at_zero_and_clamps_negative_time(self, solver):
        assert solver["atZero"] == 0
        assert solver["atNegative"] == 0, "负时间要夹到 0，否则会先往回弹一下"

    def test_critical_damping_does_not_overshoot(self, solver):
        critical = solver["critical"]
        assert max(critical) <= 1 + 1e-9, "临界阻尼不该过冲"
        assert critical == sorted(critical), "临界阻尼应当单调"

    def test_overshoot_matches_the_textbook_value(self, solver):
        """峰值过冲 = e^(-πζ/√(1-ζ²))：与实现无关的独立结论。"""
        zeta = 0.62
        expected = math.exp(-math.pi * zeta / math.sqrt(1 - zeta**2))
        measured = max(solver["lively"]) - 1
        assert measured == pytest.approx(expected, rel=0.02), (
            f"实测过冲 {measured:.4f} 与理论 {expected:.4f} 不符——解析解的分支或系数写错了"
        )

    def test_response_scales_time_not_shape(self, solver):
        """response 只决定快慢，不改变曲线形状：position(t; r) == position(4t; 4r)。

        两条曲线的采样网格都是 0..2 秒、400 段，所以快的那条第 i 点
        正好对应慢的那条第 4i 点。
        """
        fast, slow = solver["fastShape"], solver["slowShape"]
        for i in (25, 50, 75, 100):
            assert fast[i] == pytest.approx(slow[4 * i], abs=0.01), (
                "换 response 改变了曲线形状——说明它被当成了形状参数而不是时间尺度"
            )

    def test_is_pure(self, solver):
        assert solver["deterministic"] is True


class TestDependencyIsDeclared:
    """每个加载 timeline.js 的页面都必须先加载求解器。

    运行时故意不做静默回落——缺依赖时 `spring()` 直接抛错，
    所以漏掉的页面在渲染时就会炸（这正是补这个依赖时发生的事：
    `examples/why-effort-fails` 与 `videos/never-fear-interviews` 都漏了）。
    这条把它提前到静态检查，不必等一次渲染失败。
    """

    @staticmethod
    def _pages() -> list[pathlib.Path]:
        skip = ("/.venv/", "/node_modules/", "/outputs/")
        return [
            path
            for path in ROOT.rglob("*.html")
            if not any(part in path.as_posix() for part in skip)
            and "timeline.js" in path.read_text(encoding="utf-8", errors="ignore")
        ]

    def test_every_page_loads_the_solver_first(self):
        pages = self._pages()
        assert pages, "没有找到任何加载 timeline.js 的页面，扫描规则可能失效了"
        for page in pages:
            text = page.read_text(encoding="utf-8")
            name = page.relative_to(ROOT).as_posix()
            # 按 script 标签的真正顺序比较：注释里也会提到 timeline.js，
            # 直接 index() 会命中注释，量到的是文档顺序而不是加载顺序。
            sources = re.findall(r'<script[^>]+src="([^"]+)"', text)
            assert any(src.endswith("vendor/spring.js") for src in sources), (
                f"{name} 加载了 timeline.js 却没有引入 vendor/spring.js"
            )
            solver_at = next(i for i, src in enumerate(sources) if src.endswith("vendor/spring.js"))
            runtime_at = next(i for i, src in enumerate(sources) if src.endswith("timeline.js"))
            assert solver_at < runtime_at, (
                f"{name} 里 vendor/spring.js 在 timeline.js 之后引入——运行时读不到求解器"
            )

class TestRestBound:
    def test_band_is_reached_by_the_predicted_time(self, solver):
        # 包络界 e^(-ζω₀t) ≤ band ⇒ 到点后剩余偏差不超过 0.1%
        assert solver["rest"]["insideBand"] <= 0.001

    def test_zero_damping_never_rests(self, solver):
        assert solver["rest"]["zeroDamping"] == "Infinity"
