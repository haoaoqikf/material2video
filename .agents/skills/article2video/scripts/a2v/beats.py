"""语义节拍（beats）：受控动作词汇、口播段绑定与共享求值模型。

**为什么需要这一层。** 字幕、配音和入场动效各自有稳定实现，却没有共享
「正在解释哪一步推理」的时间语义：画面只能按整幕进度编排，评审也无法
判断动画到底解释了论点还是只做了入场。这里把口播段、语义动作和帧区间
收进同一份模型，供校验器、媒体准备、评审与 React 运行时共用。

**三段式。** 本模块只做三件事：

1. 声明受控动作词汇（:data:`ACTIONS`）与「是否改变状态或关系」的分类
   （:data:`CHANGE_ACTIONS`），供校验、评审与文档共用同一口径；
2. 把「口播段 → 帧区间」的解析收敛为 :func:`resolve_silent`（无声估算）
   与 :func:`merge_runs`（有声按真实词边界），两条路径产出同一个
   :class:`BeatTimeline`；
3. 提供逐帧纯函数 :meth:`BeatTimeline.state_at`，同一帧号永远得到同一份
   ``{current, progress, completed, estimated}``。

**不做什么。** 这里不读 JSON 文件、不碰网络、不认识节点属性；结构校验
（唯一性、引用完整性）在 ``a2v.storyboard`` 里，因为它们要产出带路径的
校验报告。

**与 TypeScript 的等价实现。** ``web/src/runtime/beats.ts`` 复刻同一套
解析与求值规则；两边由 ``tests/test_beats.py`` 与
``web/src/runtime/beats.test.ts`` 用同一组样例固定行为。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from . import catalog
from .errors import A2VError

#: 受控语义动作全集。动作描述「画面用什么变化解释这一步推理」，
#: 与入场配方（reveal/fade/rise/count/draw）正交：配方管出现方式，
#: 动作管状态与关系的变化。词汇表与逐原语支持清单的唯一真源是
#: `web/src/registry/registry.json`，这里只做转发，避免第二份名单。
ACTIONS: tuple[str, ...] = catalog.SEMANTIC_ACTIONS

#: 动作的中文人读说明：错误信息、报告与文档共用同一份措辞。
ACTION_LABELS: dict[str, str] = catalog.ACTION_LABELS

#: 中性动作：只让对象出现或更醒目，**不**改变对象状态与关系。
#: A3 闸门据此区分「一堆元素入场」和「真的解释了论点」——
#: 一幕全是 establish/highlight 时，观众看到的是依次出现的卡片，
#: 不是一次推理。
NEUTRAL_ACTIONS: frozenset[str] = catalog.NEUTRAL_ACTIONS

#: 改变对象状态或关系的动作。与 :data:`NEUTRAL_ACTIONS` 互补。
CHANGE_ACTIONS: frozenset[str] = catalog.CHANGE_ACTIONS

#: 新生成的非文字幕至少要有几个 beat。
MIN_BEATS_PER_SCENE = 2

#: 最后一个解释性 beat 完成后，场景结尾至少要留出的稳定阅读帧数。
#: 有声路径由真实词边界决定这个余量（作者把声明时长留足即可）；
#: 无声估算路径按同一个下限把口播预算与阅读余量分开，使估算时间轴
#: 与「结尾能读完结论」这条契约一致。
STABLE_READING_FRAMES = 12


@dataclass(frozen=True)
class ResolvedBeat:
    """一条已解析到帧区间的语义节拍。

    ``start_frame`` 含、``end_frame`` 不含，与字幕 cue 和场景区间同一约定。
    """

    id: str
    action: str
    targets: tuple[str, ...]
    meaning: str
    start_frame: int
    end_frame: int

    @property
    def frames(self) -> int:
        return self.end_frame - self.start_frame

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "targets": list(self.targets),
            "meaning": self.meaning,
            "startFrame": self.start_frame,
            "endFrame": self.end_frame,
        }

    @classmethod
    def from_json(cls, data: Any) -> "ResolvedBeat":
        """从媒体清单/有效分镜里的 JSON 形式还原；字段非法时抛 ``A2VError``。"""
        if not isinstance(data, dict):
            raise A2VError("resolvedBeats 的每一项必须是对象")
        targets = data.get("targets")
        if not isinstance(targets, list) or not targets or not all(isinstance(t, str) for t in targets):
            raise A2VError("resolvedBeats 的 targets 必须是非空字符串数组")
        start, end = data.get("startFrame"), data.get("endFrame")
        if any(isinstance(t, bool) or not isinstance(t, int) for t in (start, end)):
            raise A2VError("resolvedBeats 的帧区间必须是整数")
        return cls(
            id=str(data.get("id")),
            action=str(data.get("action")),
            targets=tuple(targets),
            meaning=str(data.get("meaning")),
            start_frame=start,
            end_frame=end,
        )


@dataclass(frozen=True)
class BeatTimeline:
    """一幕的 beat 时间轴。

    ``estimated`` 为 True 表示这是无声估算（按声明时长等比例解析），
    False 表示来自真实 TTS 词边界。运行时把该标记原样交给场景树与
    代码场景，画面可以据此区分「这是估算时间轴」。
    """

    beats: tuple[ResolvedBeat, ...] = ()
    estimated: bool = True

    @property
    def empty(self) -> bool:
        return not self.beats

    def beat(self, beat_id: str) -> ResolvedBeat | None:
        return next((item for item in self.beats if item.id == beat_id), None)

    def state_at(self, frame: int) -> dict[str, Any]:
        """逐帧纯函数：返回 ``{current, progress, completed, estimated}``。

        - ``current``：包含该帧的 beat id；区间外（幕首或结尾阅读段）为 None；
        - ``progress``：当前 beat 的局部进度，区间外为 0；
        - ``completed``：``endFrame <= frame`` 的 beat id，按时间顺序；
        - ``estimated``：整幕时间轴是否为无声估算。

        同一帧号永远得到同一份结果：没有缓存、没有时钟、没有随机。
        """
        current = next(
            (item for item in self.beats if item.start_frame <= frame < item.end_frame),
            None,
        )
        progress = 0.0
        if current is not None and current.frames > 0:
            progress = min(1.0, max(0.0, (frame - current.start_frame) / current.frames))
        return {
            "current": current.id if current is not None else None,
            "progress": progress,
            "completed": [item.id for item in self.beats if item.end_frame <= frame],
            "estimated": self.estimated,
        }

    def to_json(self) -> list[dict[str, Any]]:
        return [item.to_json() for item in self.beats]

    @classmethod
    def from_json(cls, data: Any, *, estimated: bool = False) -> "BeatTimeline":
        if data is None:
            return cls((), estimated)
        if not isinstance(data, list):
            raise A2VError("resolvedBeats 必须是数组")
        return cls(tuple(ResolvedBeat.from_json(item) for item in data), estimated)


def proportional_spans(duration: int, texts: Sequence[str]) -> list[tuple[int, int]]:
    """把 ``duration`` 帧按文本长度等比例切给每段口播。

    用**最大余数法**分配：先给每段保底 1 帧，再把剩下的帧按文本长度的
    小数部分从大到小补齐，因此

    * 总和恰好等于 ``duration``（不靠取整误差累积凑数）；
    * 每段至少 1 帧，长句拿到更多帧——真实配音时长与字数强相关，
      等比例是无声预览能做到的最好近似；
    * 相同输入永远得到同一结果（同分时按下标先后），随机寻帧稳定。

    ``duration < len(texts)`` 时无法给每段保底 1 帧，抛 ``A2VError``：
    这一幕装不下自己的口播，应当报错而不是把某段压成 0 帧。
    """
    count = len(texts)
    if count == 0:
        return []
    if duration < count:
        raise A2VError(f"场景只有 {duration} 帧，装不下 {count} 段口播")
    weights = [max(len(text.strip()), 1) for text in texts]
    total = sum(weights)
    budget = duration - count
    exact = [budget * weight / total for weight in weights]
    extra = [int(math.floor(value)) for value in exact]
    remainder = budget - sum(extra)
    order = sorted(range(count), key=lambda index: (-(exact[index] - extra[index]), index))
    for index in order[:remainder]:
        extra[index] += 1
    counts = [value + 1 for value in extra]
    spans: list[tuple[int, int]] = []
    cursor = 0
    for value in counts:
        spans.append((cursor, cursor + value))
        cursor += value
    return spans


def merge_runs(
    segments: Sequence[dict[str, Any]],
    spans: Sequence[tuple[int, int]],
    beats_by_id: dict[str, dict[str, Any]],
) -> tuple[ResolvedBeat, ...]:
    """把「逐段帧区间」合并成「逐 beat 帧区间」。

    同一个 beat 可以被连续多段口播引用（一句话分两句说），此时取这几段的
    并集；引用不连续（同一 beat 中间夹了别的 beat）会让区间倒退或重叠，
    直接抛 ``A2VError``——这是作者写错了，不该猜。
    """
    if len(segments) != len(spans):
        raise A2VError("口播段与帧区间数量不一致")
    merged: list[ResolvedBeat] = []
    order: dict[str, int] = {}
    for segment, (start, end) in zip(segments, spans):
        beat_id = str(segment.get("beatId"))
        if end <= start:
            raise A2VError(f"口播段 {segment.get('id')!r} 的帧区间为空")
        if beat_id in order:
            index = order[beat_id]
            previous = merged[index]
            if index != len(merged) - 1:
                raise A2VError(f"beat {beat_id} 的口播段不连续，时间轴会倒退或重叠")
            if start < previous.end_frame:
                raise A2VError(f"beat {beat_id} 的帧区间重叠")
            merged[index] = ResolvedBeat(
                id=previous.id,
                action=previous.action,
                targets=previous.targets,
                meaning=previous.meaning,
                start_frame=previous.start_frame,
                end_frame=end,
            )
            continue
        beat = beats_by_id.get(beat_id)
        if beat is None:
            raise A2VError(f"口播段引用了不存在的 beat {beat_id!r}")
        order[beat_id] = len(merged)
        merged.append(
            ResolvedBeat(
                id=beat_id,
                action=str(beat.get("action")),
                targets=tuple(beat.get("targets") or ()),
                meaning=str(beat.get("meaning")),
                start_frame=start,
                end_frame=end,
            )
        )
    return tuple(merged)


def segment_texts(scene: dict[str, Any]) -> list[str]:
    """一幕的分段口播文本（按声明顺序）；没有分段口播时返回空表。"""
    segments = scene.get("narrationSegments")
    if not isinstance(segments, list):
        return []
    return [str(item.get("text", "")) for item in segments if isinstance(item, dict)]


def scene_narration(scene: dict[str, Any]) -> str:
    """一幕完整口播仅由分段文本按顺序拼接。"""
    return "".join(segment_texts(scene))


def beats_by_id(scene: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """一幕的 beat 索引（按 id）。非对象项直接跳过，交给校验器报错。"""
    beats = scene.get("beats")
    if not isinstance(beats, list):
        return {}
    return {
        str(item.get("id")): item
        for item in beats
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def resolve_silent(scene: dict[str, Any]) -> BeatTimeline:
    """无声预览的等比例时间轴；没有分段口播时返回空时间轴。

    口播预算取 ``durationInFrames - STABLE_READING_FRAMES``（至少 1 帧），
    余下的帧留给最后一个 beat 完成后的稳定阅读；场景本身太短时预算退化
    为整幕时长，A5 闸门会如实报出余量不足。
    """
    segments = scene.get("narrationSegments")
    if not isinstance(segments, list) or not segments:
        return BeatTimeline((), True)
    duration = scene.get("durationInFrames")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
        raise A2VError("无声 beat 解析需要正整数 durationInFrames")
    texts = segment_texts(scene)
    budget = duration - STABLE_READING_FRAMES
    if budget < len(texts):
        budget = duration
    spans = proportional_spans(budget, texts)
    return BeatTimeline(merge_runs(segments, spans, beats_by_id(scene)), True)


def resolve_from_windows(
    scene: dict[str, Any],
    windows: Sequence[tuple[float, float]],
    fps: int,
    duration_frames: int,
) -> BeatTimeline:
    """有声路径：按真实词边界（秒）解析场景内的 beat 帧区间。

    以场景 fps **向外取整**（起点向下、终点向上），再把起点钳到上一段的终点，
    使相邻区间首尾相接、不因取整而重叠。任何一段不足 1 帧或超出场景都失败：
    画面按一份自相矛盾的时间轴渲染，比直接报错难查得多。
    """
    segments = scene.get("narrationSegments")
    if not isinstance(segments, list) or not segments:
        return BeatTimeline()
    if len(windows) != len(segments):
        raise A2VError("口播段与词边界区间数量不一致")
    spans: list[tuple[int, int]] = []
    cursor = 0
    for index, (start_seconds, end_seconds) in enumerate(windows):
        start = max(int(math.floor(start_seconds * fps)), cursor)
        end = int(math.ceil(end_seconds * fps))
        if end <= start:
            raise A2VError(f"第 {index + 1} 段口播不足 1 帧，无法形成节拍区间")
        if end > duration_frames:
            raise A2VError(f"第 {index + 1} 段口播超出场景（{end} > {duration_frames}）")
        spans.append((start, end))
        cursor = end
    return BeatTimeline(merge_runs(segments, spans, beats_by_id(scene)), False)


def validate_timeline(beats: Iterable[ResolvedBeat], duration: int, *, path: str = "resolvedBeats") -> list[str]:
    """校验一份已解析时间轴的顺序、重叠与越界，返回人读问题列表。

    媒体清单与有效分镜都走这里：倒退、重叠、越界必须在读取阶段失败，
    而不是让画面按一份自相矛盾的时间轴渲染。
    """
    issues: list[str] = []
    previous_end = 0
    seen: set[str] = set()
    for index, beat in enumerate(beats):
        where = f"{path}[{index}]"
        if not beat.id or beat.id in seen:
            issues.append(f"{where}: beat id 缺失或重复（{beat.id!r}）")
        seen.add(beat.id)
        if beat.action not in ACTIONS:
            issues.append(f"{where}: 未知语义动作 {beat.action!r}")
        if not beat.meaning.strip():
            issues.append(f"{where}: meaning 不能为空")
        if not beat.targets:
            issues.append(f"{where}: 至少要有一个目标节点")
        if beat.end_frame <= beat.start_frame:
            issues.append(f"{where}: 帧区间为空（{beat.start_frame}–{beat.end_frame}）")
        if beat.start_frame < previous_end:
            issues.append(f"{where}: 帧区间相对上一条倒退或重叠（起点 {beat.start_frame} < {previous_end}）")
        if beat.end_frame > duration:
            issues.append(f"{where}: 帧区间超出场景（{beat.end_frame} > {duration}）")
        previous_end = max(previous_end, beat.end_frame)
    return issues
