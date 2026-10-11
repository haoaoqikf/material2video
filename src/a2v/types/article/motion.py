"""入场动效的量测：逐帧扫一遍，量每一个入场元素的轨迹。

**为什么放在这里而不是测试里。** 这套判据最初只活在一个跑 pytest 才会执行的
测试模块里（`tests/test_motion_trajectory.py`，已删除）——而 `review.py`
（做视频的人真正会跑的验收命令）里一行动效判据都没有。判据放在只有一半人
会跑的地方，等于没有。现在两边共用这一份实现：`inspect.py` 的体检把它跑在
真实契约页上，`tests/test_motion_review.py` 覆盖「量出来的数怎么判」。

**量什么。** 逐幕逐帧把页面走一遍，收集每一个「从不透明走向不透明」的元素，
记录它的不透明度与位移序列。判据量在**不透明度**上：位移里可能混着刻意的
常驻微动，拿它判单调会把微动的摆动读成入场回退。

**速度判据只适用于有位移的入场。** 参考实现的 90 个入场元素里只有 9 个真的有位移，
另外 81 个是纯淡入（逐字揭示的单字符 2 帧、小标注与箭头 2–5 帧）——
那是刻意的做法。观众感到「弹」是因为位移在一帧里跳完，所以速度判据跟着位移走。

**闸门默认只提示、不拦人**（与 K 系列同性质）：这里报出的问题不改错误数与退出码。
「入场快了一点」不是「画面坏了」，最终判断归人；参考实现上的严格判定由
`tests/test_motion_review.py` 用构造出来的轨迹做正反例承担。
"""

from __future__ import annotations

import dataclasses
from typing import Any, Iterable

#: 入场落地后距幕尾至少留多少帧：内容不能还在动就被切到下一幕。
#: 参考实现实测最小 25 帧，取 12 帧（0.4 秒）作为下限。
MIN_LANDING_MARGIN = 12

#: 位移超过这个值才算「有位移的入场」，速度判据才适用于它。
MOVING_TRAVEL_PX = 1.0

#: 有位移的入场：首帧不透明度上限。参考实现实测最大 0.095，
#: 换成旧的「缓动进度喂给弹簧」写法时实测 0.438。
MAX_FIRST_FRAME_OPACITY = 0.25

#: 有位移的入场：不透明度走到 0.9 至少需要多少帧。参考实现实测最少 7 帧。
MIN_OPACITY_FRAMES_TO_90 = 6

#: 每个元素最多记录多少次变化。入场最长约 50 帧（缓动淡入），60 够用；
#: 上限是为了不让「整幕都在呼吸」的元素把数据撑爆。
MAX_SAMPLES = 60

#: 在页面里逐帧扫一幕，返回每个元素的变化序列（压缩过：只在数值变了才记一条）。
#:
#: 三个坑写在代码里，因为都真实发生过：
#:   * 元素集合必须在**进入这一幕之后**收集——在 seek 之前 querySelectorAll
#:     拿到的是空列表（这一幕还没渲染），扫描会只覆盖第 0 幕却报「全部通过」；
#:   * 身份必须用元素引用本身，不能用 className——SVG 的 className 是
#:     SVGAnimatedString 对象，String() 之后所有 SVG 元素塌成同一个 key；
#:   * `seekToFrame` 必须 **await**。version 3 的契约页（React/Remotion）里它是
#:     异步的：它等 Player 的 `seeked` 事件、再等两帧绘制。不 await 就立刻读
#:     `getComputedStyle`，读到的是**上一帧**的画面，整幕量出来「一个入场元素都没有」，
#:     而 M1 只会给一句提醒（实测：旧路径 90 个入场元素，新路径 0 个）。
#:     旧页面的隐式返回值不再作为兼容路径接受。
SWEEP_SCRIPT = """
async (args) => {
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
  const key = (el) => {
    const cls = (el.getAttribute('class') || '').split(' ')[0];
    return el.tagName.toLowerCase() + (cls ? '.' + cls : '');
  };
  const tracks = new Map();
  const order = [];
  for (let f = 0; f < duration; f++) {
    await window.__A2V__.seekToFrame(args.start + f);
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


@dataclasses.dataclass
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
        """落地后距幕尾还剩多少帧。"""
        return self.duration - self.landed

    @property
    def moving(self) -> bool:
        return self.travel >= MOVING_TRAVEL_PX

    def to_json(self) -> dict[str, Any]:
        return {
            "scene": self.scene,
            "key": self.key,
            "start": self.start,
            "landed": self.landed,
            "duration": self.duration,
            "margin": self.margin,
            "travel": self.travel,
            "moving": self.moving,
            "firstOpacity": self.first_opacity,
            "framesToHalf": self.frames_to_half,
            "framesTo90": self.frames_to_90,
            "reverses": self.reverses,
        }


@dataclasses.dataclass
class Gate:
    """一条动效结论。形状与 `keynote.Gate` 保持一致，方便一起打印与落盘。"""

    id: str
    title: str
    status: str
    detail: str = ""
    value: Any = None
    threshold: Any = None
    scene: str = ""

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def scene_offsets(scenes: Iterable[dict[str, Any]]) -> list[tuple[int, int]]:
    """每一幕的（起始全局帧, 帧数）。seekToFrame 收的是全局帧。"""
    offsets: list[tuple[int, int]] = []
    acc = 0
    for scene in scenes:
        duration = int(scene.get("durationInFrames") or 0)
        offsets.append((acc, duration))
        acc += duration
    return offsets


def analyse(scene_id: str, duration: int, element: dict[str, Any]) -> Entrance | None:
    """把一个元素的压缩采样整理成入场记录；不是入场元素时返回 None。"""
    samples = element.get("samples") or []
    if len(samples) < 2:
        return None
    frames = [row[0] for row in samples]
    ops = [row[1] for row in samples]
    # 入场 = 从透明走向不透明。刻意压暗的元素（落选一栏 0.42）与整幕静止的元素都不是。
    # 幕中才创建的节点没有第 0 帧样本，会被当成「出现时已经可见」，不算入场。
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
    travel = samples[0][3] - samples[landed][3] if len(samples[landed]) > 3 else 0.0
    return Entrance(
        scene=scene_id,
        key=str(element.get("key") or "?"),
        start=frames[first],
        landed=frames[landed],
        duration=duration,
        travel=round(abs(travel), 2),
        first_opacity=window[0][1],
        frames_to_half=half - frames[first],
        frames_to_90=ninety - frames[first],
        reverses=rises != sorted(rises),
    )


def _truncated(element: dict[str, Any]) -> bool:
    """采样被上限截断，而且截断时不透明度还在上升——量到的轨迹不完整。

    判据是「单调上升到上限、却还没接近不透明」，三个条件缺一不可：

      * **单调上升**：脉动的装饰（火花、呼吸的光晕）不透明度会自己回退，
        它们不是「没量到落地」，是本来就不落地；
      * **到上限时仍 < 0.95**：已经落地的元素不会进来；
      * **最后一帧还在上升**：刻意停在部分不透明度的装饰（光晕、注脚、引号）
        会自己停下来，最后一帧不再变化。

    这类元素要么不进扫描，要么必须被单独报出来——**不能静默丢掉**：
    丢掉之后闸门全过，而人以为自己量过了，这正是这套机检要消灭的失败模式。
    """
    samples = element.get("samples") or []
    if len(samples) < MAX_SAMPLES or len(samples) < 2:
        return False
    ops = [row[1] for row in samples]
    return ops[0] <= 0.05 and ops[-1] < 0.95 and ops[-1] > ops[-2] and ops == sorted(ops)


@dataclasses.dataclass
class Sweep:
    """一次扫描的结果。

    `truncated` 单独留一个字段：被采样上限掐掉的入场**不能静默丢掉**。
    丢掉之后闸门会全过，而人以为自己量过了——这正是这套机检要消灭的失败模式。
    """

    records: list[Entrance] = dataclasses.field(default_factory=list)
    truncated: list[str] = dataclasses.field(default_factory=list)


def sweep(page: Any, scenes: list[dict[str, Any]]) -> Sweep:
    """在已打开的页面上逐幕逐帧扫一遍，返回所有入场元素。"""
    offsets = scene_offsets(scenes)
    result = Sweep()
    for index, scene in enumerate(scenes):
        start, duration = offsets[index]
        if duration <= 0:
            continue
        data = page.evaluate(
            SWEEP_SCRIPT,
            {"index": index, "start": start, "duration": duration, "maxSamples": MAX_SAMPLES},
        )
        scene_id = str(scene.get("id") or index)
        for element in (data or {}).get("elements") or []:
            record = analyse(scene_id, duration, element)
            if record is not None:
                result.records.append(record)
            elif _truncated(element):
                result.truncated.append(f"{scene_id}/{element.get('key') or '?'}")
    return result


def _offenders(records: list[Entrance], predicate: Any) -> list[Entrance]:
    return [record for record in records if predicate(record)]


def _brief(records: list[Entrance], render: Any, limit: int = 4) -> str:
    shown = ", ".join(render(record) for record in records[:limit])
    if len(records) > limit:
        shown += f"，另有 {len(records) - limit} 处（见 report.json）"
    return shown


class MotionResult:
    """一次扫描的全部结论：给终端看的摘要，也给 report.json 存档。"""

    #: 闸门编号。C 系列回答「是不是废片」，K 系列回答「够不够发布会级」，
    #: M 系列回答「动作对不对」——三者分开报，不揉成一个分。
    def __init__(self, enabled: bool, reason: str = "") -> None:
        self.enabled = enabled
        self.reason = reason
        self.records: list[Entrance] = []
        self.gates: list[Gate] = []

    def render(self, swept: Sweep) -> None:
        """把扫描结果转成一条条结论。"""
        records = swept.records
        self.records = records
        if not records:
            self.gates.append(
                Gate(
                    id="M1",
                    title="入场覆盖",
                    status="warn",
                    detail="整支片子没有扫到任何入场元素：要么内容完全不进场，要么量测没生效",
                )
            )
            return

        moving = [record for record in records if record.moving]
        self.gates.append(
            Gate(
                id="M0",
                title="扫描覆盖",
                status="warn" if swept.truncated else "pass",
                value=f"{len(records)} 个入场元素（其中 {len(moving)} 个有位移）",
                threshold="—",
                detail="逐幕：" + "，".join(
                    f"{scene} {count}" for scene, count in sorted(self._per_scene().items())
                )
                + (
                    "；另有 "
                    f"{len(swept.truncated)} 个元素的采样被上限截断（不透明度还在上升就停了），"
                    "轨迹不完整、未计入：" + "、".join(swept.truncated[:4])
                    if swept.truncated
                    else ""
                ),
            )
        )

        pops = _offenders(
            moving, lambda record: record.first_opacity > MAX_FIRST_FRAME_OPACITY
        )
        self.gates.append(
            Gate(
                id="M1",
                title="入场不弹跳",
                status="fail" if pops else "pass",
                value=f"{max((r.first_opacity for r in moving), default=0):.3f}",
                threshold=f"≤ {MAX_FIRST_FRAME_OPACITY:.2f}",
                detail=""
                if not pops
                else "第一帧就把不透明度拉起来，观众看到的是硬切："
                + _brief(pops, lambda r: f"{r.scene}/{r.key} {r.first_opacity:.2f}"),
            )
        )

        rushed = _offenders(
            moving, lambda record: record.frames_to_90 < MIN_OPACITY_FRAMES_TO_90
        )
        self.gates.append(
            Gate(
                id="M2",
                title="入场够慢",
                status="fail" if rushed else "pass",
                value=f"{min((r.frames_to_90 for r in moving), default=0)} 帧到 90%",
                threshold=f"≥ {MIN_OPACITY_FRAMES_TO_90} 帧",
                detail=""
                if not rushed
                else "位移在太少帧内走完，看不到移动的过程："
                + _brief(rushed, lambda r: f"{r.scene}/{r.key} {r.frames_to_90} 帧"),
            )
        )

        late = _offenders(records, lambda record: record.margin < MIN_LANDING_MARGIN)
        self.gates.append(
            Gate(
                id="M3",
                title="入场在幕内落地",
                status="fail" if late else "pass",
                value=f"最小余量 {min(r.margin for r in records)} 帧",
                threshold=f"≥ {MIN_LANDING_MARGIN} 帧",
                detail=""
                if not late
                else "入场还没走完就要切幕："
                + _brief(late, lambda r: f"{r.scene}/{r.key} 落地于 {r.landed}/{r.duration}"),
            )
        )

        flickers = _offenders(records, lambda record: record.reverses)
        self.gates.append(
            Gate(
                id="M4",
                title="入场不闪烁",
                status="fail" if flickers else "pass",
                value=f"{len(flickers)} 处回退",
                threshold="0 处",
                detail=""
                if not flickers
                else "入场期间不透明度回退（一闪）："
                + _brief(flickers, lambda r: f"{r.scene}/{r.key}"),
            )
        )

    def _per_scene(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self.records:
            counts[record.scene] = counts.get(record.scene, 0) + 1
        return counts

    def summary(self) -> dict[str, int]:
        counts = {"pass": 0, "warn": 0, "fail": 0, "skipped": 0}
        for gate in self.gates:
            counts[gate.status] = counts.get(gate.status, 0) + 1
        return counts

    def to_json(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "reason": self.reason,
            "summary": self.summary(),
            "gates": [gate.to_json() for gate in self.gates],
            "entrances": [record.to_json() for record in self.records],
        }


def audit(page: Any, scenes: list[dict[str, Any]]) -> MotionResult:
    """对已打开的页面跑一次动效量测。取不到幕时如实报告「跳过」。"""
    if not scenes:
        return MotionResult(False, "分镜里没有场景，无法定位入场元素")
    if not any(int(scene.get("durationInFrames") or 0) > 0 for scene in scenes):
        return MotionResult(False, "分镜里的场景没有声明帧数，无法逐帧扫描")
    result = MotionResult(True)
    result.render(sweep(page, scenes))
    return result
