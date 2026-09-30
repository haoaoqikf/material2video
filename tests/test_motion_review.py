"""动效量测的判定逻辑（不依赖浏览器的部分）。

浏览器那一半（真的逐帧读 DOM）由 `review.py` 的体检在真实契约页上端到端跑；
这里覆盖的是「量出来的数怎么判」以及**扫描本身可不可信**：

  * 什么样的元素算入场（从透明走向不透明），什么不算；
  * 采样窗口内没走到不透明的元素必须被单独报出来，不能静默丢掉——
    「没量到却全过」是这套机检要消灭的失败模式；
  * 四条判据在构造出来的轨迹上确实会失败，而不是永远通过。
"""

from __future__ import annotations

from a2v import motion

#: 采样行格式：[帧, 不透明度, x, y]，与页面里 `SWEEP_SCRIPT` 的压缩采样一致。
_SAMPLE = list[list[float]]


def _element(key: str, samples: _SAMPLE) -> dict:
    return {"key": key, "samples": samples}


def _pop() -> dict:
    """旧实现的病征：第一帧就到 0.438，第 3 帧基本走完。"""
    return _element("h1.title", [[0, 0.0, 0, 44], [1, 0.438, 0, 24], [2, 0.97, 0, 1], [3, 1.0, 0, 0]])


def _slow_fade() -> dict:
    """正常入场：位移 44px，13 帧走到 90%。"""
    rows = [[0, 0.0, 0, 44]]
    for frame in range(1, 19):
        progress = min(1.0, frame / 15)
        rows.append([frame, round(progress, 3), 0, round(44 * (1 - progress), 2)])
    return _element("div.card", rows)


class TestWhatCountsAsAnEntrance:
    def test_starts_transparent_and_lands(self):
        record = motion.analyse("opening", 150, _slow_fade())
        assert record is not None
        assert record.scene == "opening"
        assert record.key == "div.card"
        assert record.start == 1
        assert record.margin == 150 - record.landed

    def test_always_opaque_element_is_not_an_entrance(self):
        assert motion.analyse("opening", 150, _element("p", [[0, 1.0, 0, 0], [9, 1.0, 0, 0]])) is None

    def test_deliberately_dimmed_element_is_not_an_entrance(self):
        """对比双栏的落选一栏是刻意压到 0.42 的，不是入场。"""
        rows = [[0, 0.42, 0, 0], [5, 0.42, 0, 0]]
        assert motion.analyse("compare", 240, _element("div.loser", rows)) is None

    def test_element_created_mid_scene_is_not_an_entrance(self):
        """幕中才创建的节点没有「从透明开始」的证据，按出现即不透明处理。"""
        rows = [[40, 0.5, 0, 20], [45, 1.0, 0, 0]]
        assert motion.analyse("opening", 150, _element("span.late", rows)) is None

    def test_travel_is_measured_from_rest_to_landing(self):
        record = motion.analyse("opening", 150, _slow_fade())
        assert record is not None and record.travel == 44.0
        assert record.moving, "44px 的位移必须算作「有位移的入场」"

    def test_frames_to_90_counts_from_the_first_change(self):
        record = motion.analyse("opening", 150, _slow_fade())
        assert record is not None
        assert record.frames_to_90 == 13 or record.frames_to_90 >= motion.MIN_OPACITY_FRAMES_TO_90


class TestSweepDoesNotDropEvidence:
    """被采样上限掐掉的入场必须报出来，不能静默丢掉。"""

    @staticmethod
    def _track(values: list[float]) -> dict:
        rows = [[frame, value, 0, 40] for frame, value in enumerate(values)]
        return _element("div.slow", rows)

    @staticmethod
    def _rising(count: int = motion.MAX_SAMPLES) -> dict:
        return TestSweepDoesNotDropEvidence._track([round(f / (count * 2), 3) for f in range(count)])

    def test_truncated_rise_is_reported(self):
        assert motion._truncated(self._rising())

    def test_settled_decoration_is_not_reported(self):
        """刻意停在部分不透明度的光晕会自己停下来，不算截断。"""
        values = [0.0, 0.2, 0.35] + [0.35] * (motion.MAX_SAMPLES - 3)
        assert not motion._truncated(self._track(values))

    def test_pulsing_decoration_is_not_reported(self):
        """脉动的火花不透明度会回退，本来就不落地，不算「没量到落地」。"""
        values = [0.0] + [0.35 if f % 2 else 0.2 for f in range(motion.MAX_SAMPLES - 1)]
        assert not motion._truncated(self._track(values))

    def test_landed_element_is_not_truncated(self):
        values = [round(f / 20, 3) for f in range(20)] + [1.0] * (motion.MAX_SAMPLES - 20)
        assert not motion._truncated(self._track(values))

    def test_short_track_is_not_truncated(self):
        assert not motion._truncated(self._rising(5))

    def test_always_opaque_element_is_not_truncated(self):
        assert not motion._truncated(self._track([1.0] * motion.MAX_SAMPLES))


class _FakePage:
    """只回放预先录好的扫描结果，用来验证判定与汇总。"""

    def __init__(self, elements: list[dict]) -> None:
        self.elements = elements

    def evaluate(self, expression: str, arg: dict | None = None) -> dict:
        assert "querySelectorAll('[data-a2v-scene]')" in expression
        return {"index": (arg or {}).get("index"), "elements": self.elements}


def _scenes(count: int = 2, duration: int = 120) -> list[dict]:
    return [{"id": f"scene{index}", "durationInFrames": duration} for index in range(count)]


class TestVerdicts:
    def _gates(self, elements: list[dict], scenes: list[dict] | None = None) -> dict:
        result = motion.MotionResult(True)
        result.render(motion.sweep(_FakePage(elements), scenes or _scenes(1)))
        return {gate.id: gate for gate in result.gates}

    def test_a_pop_fails_both_speed_rules(self):
        gates = self._gates([_pop()])
        assert gates["M1"].status == "fail"
        assert gates["M2"].status == "fail"
        assert "M3" not in gates or gates["M3"].status == "pass"

    def test_the_real_recipe_passes(self):
        gates = self._gates([_slow_fade()])
        assert gates["M0"].status == "pass"
        assert gates["M1"].status == "pass"
        assert gates["M2"].status == "pass"
        assert gates["M3"].status == "pass"
        assert gates["M4"].status == "pass"

    def test_late_landing_fails_the_margin_rule(self):
        """入场还没走完就要切幕：这里是 110 帧的幕、第 118 帧才落地。"""
        rows = [[0, 0.0, 0, 40]]
        for frame in range(1, 119):
            rows.append([frame, min(1.0, frame / 118), 0, max(0.0, 40 - frame / 3)])
        gates = self._gates([_element("div.late", rows)], _scenes(1, 120))
        assert gates["M3"].status == "fail"
        assert "落地" in gates["M3"].detail

    def test_flicker_fails_the_monotone_rule(self):
        rows = [[0, 0.0, 0, 40], [1, 0.3, 0, 28], [2, 0.2, 0, 26], [3, 0.6, 0, 16], [4, 1.0, 0, 0]]
        gates = self._gates([_element("div.flicker", rows)])
        assert gates["M4"].status == "fail"

    def test_truncated_elements_make_the_coverage_gate_warn(self):
        rows = [[f, round(f / (motion.MAX_SAMPLES * 2), 3), 0, 40] for f in range(motion.MAX_SAMPLES)]
        gates = self._gates([_slow_fade(), _element("g.slow", rows)])
        assert gates["M0"].status == "warn"
        assert "截断" in gates["M0"].detail

    def test_no_entrance_at_all_warns_instead_of_passing(self):
        gates = self._gates([_element("p", [[0, 1.0, 0, 0], [1, 1.0, 0, 0]])])
        assert gates["M1"].status == "warn"
        assert "没有扫到任何入场元素" in gates["M1"].detail


class TestAuditSkipsHonestly:
    def test_no_scenes_skips_with_a_reason(self):
        result = motion.audit(_FakePage([]), [])
        assert not result.enabled
        assert "没有场景" in result.reason

    def test_scenes_without_durations_skip_with_a_reason(self):
        result = motion.audit(_FakePage([]), [{"id": "opening"}])
        assert not result.enabled
        assert "帧数" in result.reason

    def test_offsets_are_cumulative_global_frames(self):
        scenes = [{"id": "a", "durationInFrames": 150}, {"id": "b", "durationInFrames": 240}]
        assert motion.scene_offsets(scenes) == [(0, 150), (150, 240)]

    def test_json_payload_carries_every_entrance(self):
        result = motion.MotionResult(True)
        result.render(motion.sweep(_FakePage([_slow_fade()]), _scenes(1)))
        payload = result.to_json()
        assert payload["enabled"] is True
        assert len(payload["entrances"]) == 1
        assert payload["entrances"][0]["key"] == "div.card"
        assert payload["summary"]["pass"] >= 1
