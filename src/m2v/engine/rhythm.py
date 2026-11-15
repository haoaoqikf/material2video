"""Deterministic pause shaping for synthesized narration.

合成一次、按文本标点给停顿分类、再把每类停顿调到目标长度——这样节奏可以
主动控制，而不必依赖"标点会恰好产生多长停顿"这件事。音频与词边界同源重映射，
字幕和时间轴因此自动跟随，不需要第二处补丁。

只用标准库：这是渲染链路的内置能力，不为了一个停顿整形去引入数值依赖。
"""
from __future__ import annotations

import array
import json
import wave
from dataclasses import dataclass
from pathlib import Path

from m2v.core.errors import M2VError

#: 停顿类别 → 触发它的标点。
PAUSE_PUNCTUATION = {
    "comma": "，,、；;：:",
    "period": "。.？！?!…",
}
#: 单个停顿允许的目标区间；上界防止把停顿拉成静音空档。
BOUNDS = {"comma": (0.03, 0.45), "period": (0.03, 0.90), "paragraph": (0.03, 1.40)}
HEAD_PAD_RANGE = (0.0, 0.80)
#: 低于该时长的静音不当作可塑形的停顿。
SILENCE_THRESHOLD = 0.05
#: 静音判定：低于整段峰值这么多 dB 视为静音。
NOISE_MARGIN_DB = 40.0
#: 音量按 10ms 窗口判定。
WINDOW_SECONDS = 0.01


@dataclass(frozen=True)
class Pause:
    """音频里一处可塑形的停顿，以及它应达到的目标时长。"""

    start: float
    end: float
    kind: str
    target: float | None

    @property
    def duration(self) -> float:
        return self.end - self.start


def configure(declared: dict) -> dict:
    """校验并归一化韵律声明；未提到的类别不参与塑形。

    这里只管停顿与引子；语速属于音色那一层（`tts.rate` 与场景级 `speech.rate`），
    避免同一个"语速"有两处入口。
    """
    if not isinstance(declared, dict):
        raise M2VError("speech 必须是对象")
    unknown = set(declared) - {"headPad", "pause", "rate"}
    if unknown:
        raise M2VError(f"speech 存在未知字段：{'、'.join(sorted(unknown))}")
    result: dict = {}
    if "headPad" in declared:
        result["headPad"] = _seconds(declared["headPad"], "speech.headPad", *HEAD_PAD_RANGE)
    if "pause" in declared:
        pause = declared["pause"]
        if not isinstance(pause, dict) or not pause:
            raise M2VError("speech.pause 必须是非空对象，键取 comma、period、paragraph")
        unknown = set(pause) - set(BOUNDS)
        if unknown:
            raise M2VError(f"speech.pause 存在未知类别：{'、'.join(sorted(unknown))}")
        result["pause"] = {
            kind: _seconds(value, f"speech.pause.{kind}", *BOUNDS[kind])
            for kind, value in pause.items()
        }
    if not result:
        raise M2VError("speech 至少需要声明 headPad 或 pause 之一")
    return result


def _seconds(value: object, field: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise M2VError(f"{field} 必须是数值秒数")
    if not low <= value <= high:
        raise M2VError(f"{field} 必须在 {low} 至 {high} 秒之间")
    return float(value)


def fingerprint_of(config: dict) -> str:
    return json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_samples(wav: Path) -> tuple[int, array.array]:
    """读成 16 位单声道整数样本；只支持合成链路自己产出的 PCM。"""
    with wave.open(str(wav), "rb") as stream:
        if stream.getsampwidth() != 2 or stream.getnchannels() != 1:
            raise M2VError("韵律整形只支持 16 位单声道 PCM 旁白")
        rate = stream.getframerate()
        samples = array.array("h", stream.readframes(stream.getnframes()))
    return rate, samples


def write_samples(path: Path, rate: int, samples: array.array) -> None:
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        stream.writeframes(samples.tobytes())


def detect(samples: array.array, rate: int) -> list[tuple[int, int]]:
    """找出低于阈值且足够长的静音区段，返回样本下标区间。

    逐窗口取绝对值的最大值：这一步在 C 层完成，整段旁白只有毫秒级开销。
    """
    window = max(1, int(rate * WINDOW_SECONDS))
    count = len(samples) // window
    if not count:
        return []
    levels = [max(abs(value) for value in samples[index * window:(index + 1) * window])
              for index in range(count)]
    peak = max(levels)
    if peak <= 0:
        return [(0, count * window)]
    # 与峰值差 40dB：24kHz 16 位下约为 ±328，远高于底噪、远低于语音。
    floor = peak / (10 ** (NOISE_MARGIN_DB / 20.0))
    spans: list[tuple[int, int]] = []
    begin: int | None = None
    for index, level in enumerate(levels):
        quiet = level < floor
        if quiet and begin is None:
            begin = index
        elif not quiet and begin is not None:
            spans.append((begin * window, index * window))
            begin = None
    if begin is not None:
        spans.append((begin * window, count * window))
    minimum = int(rate * SILENCE_THRESHOLD)
    return [(start, end) for start, end in spans if end - start >= minimum]


def kinds(text: str, words: list[dict]) -> list[str | None]:
    """为每个词边界处标出停顿类别。

    词边界事件只给词、不给标点（实测 edge-tts 的 `WordBoundary` 就是这样），
    所以不能从词的文本里找标点；改为按顺序把每个词对齐回原文下标，
    再取相邻两词之间出现的标点。对齐失败时跳过该词，容忍漏词与半词。
    """
    spans = _positions(text, words)
    result: list[str | None] = []
    for index in range(len(words) - 1):
        after = spans[index]
        following = spans[index + 1]
        kind = None
        if after is not None and following is not None:
            cursor = after[1]
            while cursor < following[0]:
                character = text[cursor]
                if character in PAUSE_PUNCTUATION["comma"]:
                    kind = "comma"
                elif character in PAUSE_PUNCTUATION["period"]:
                    kind = "period"
                cursor += 1
        result.append(kind)
    result.append(None)
    return result


def _positions(text: str, words: list[dict]) -> list[tuple[int, int] | None]:
    """把每个词对齐回原文，返回 `(起始, 结束)` 下标；对不上的词得到 None。"""
    spans: list[tuple[int, int] | None] = []
    cursor = 0
    for word in words:
        surface = str(word.get("text") or "")
        if not surface:
            spans.append(None)
            continue
        found = None
        scan = cursor
        while scan < len(text):
            character = text[scan]
            if character.isspace() or character in _ALL_PUNCTUATION:
                scan += 1
                continue
            if text.startswith(surface, scan):
                found = (scan, scan + len(surface))
                break
            # 半词或核对不齐时容忍一个字符，避免整条对齐从此错位。
            scan += 1
        if found is None:
            spans.append(None)
        else:
            spans.append(found)
            cursor = found[1]
    return spans


_ALL_PUNCTUATION = "".join(PAUSE_PUNCTUATION.values())


def plan(text: str, words: list[dict], rate: int, samples: array.array, config: dict) -> list[Pause]:
    """把检测到的停顿按相邻词边界归类，并给出目标时长。

    只在能同时确认「这是停顿」与「这是标点」时塑形；两者对不上的停顿原样保留，
    宁可不改也不猜一个位置。
    """
    if not config.get("pause"):
        return []
    labels = kinds(text, words)
    pauses: list[Pause] = []
    for start, end in detect(samples, rate):
        before = _word_before(words, start / rate)
        if before is None:
            continue
        kind = labels[before]
        if kind is None:
            continue
        if kind == "period" and before == len(words) - 1:
            kind = "paragraph"
        target = config.get("pause", {}).get(kind)
        if target is None:
            continue
        pauses.append(Pause(start=start / rate, end=end / rate, kind=kind, target=target))
    return pauses


def _word_before(words: list[dict], moment: float) -> int | None:
    """返回开始时间不晚于该时刻的最后一个词的下标。"""
    found = None
    for index, word in enumerate(words):
        if float(word.get("start", 0.0)) <= moment + 1e-6:
            found = index
        else:
            break
    return found


def reshape(samples: array.array, rate: int, pauses: list[Pause],
            config: dict) -> tuple[array.array, list[tuple[float, float]]]:
    """按目标时长重建音频，返回新样本与「原时刻 → 位移」对照表。"""
    shifts: list[tuple[float, float]] = []
    pieces: list[array.array] = []
    cursor = 0
    head = config.get("headPad")
    if head is not None:
        lead = _lead_silence(samples, rate)
        if lead > head:
            cut = int(round((lead - head) * rate))
            cursor = cut
            shifts.append((0.0, -cut / rate))
    for pause in pauses:
        start = int(round(pause.start * rate))
        end = int(round(pause.end * rate))
        if start < cursor or pause.target is None:
            continue
        pieces.append(samples[cursor:start])
        delta = int(round((pause.target - pause.duration) * rate))
        if delta >= 0:
            # 拉长：在停顿中间插入等长静音，两端原有的近静音仍是过渡。
            pieces.append(array.array("h", bytes(2 * delta)))
        else:
            # 缩短：只保留停顿两端，避免削到相邻语音。
            keep = max(0, (end - start) + delta)
            lead, trail = keep // 2, keep - keep // 2
            pieces.append(samples[start:start + lead])
            pieces.append(samples[end - trail:end])
        shifts.append((pause.start, delta / rate))
        cursor = end
    pieces.append(samples[cursor:])
    shaped = array.array("h")
    for piece in pieces:
        shaped.extend(piece)
    return shaped, shifts


def _lead_silence(samples: array.array, rate: int) -> float:
    spans = detect(samples, rate)
    if spans and spans[0][0] == 0:
        return spans[0][1] / rate
    return 0.0


def remap(moment: float, shifts: list[tuple[float, float]], limit: float | None = None) -> float:
    """把原时间轴上的时刻映射到整形后的时间轴。

    缩短停顿会把后面的音频前移，末词的结束时刻可能因此落到音频长度之外；
    字幕校验要求时间戳落在音频内，所以给一个上界。
    """
    moved = moment
    for position, delta in shifts:
        if position <= moment:
            moved += delta
    moved = max(0.0, moved)
    return min(moved, limit) if limit is not None else moved


def remap_all(moments: list[float], shifts: list[tuple[float, float]],
              limit: float) -> list[float]:
    """整批重映射并保持严格递增：字幕校验要求时间戳落在音频内且不倒退。"""
    moved: list[float] = []
    previous = 0.0
    step = 0.001
    for index, moment in enumerate(moments):
        value = remap(moment, shifts)
        # 每个时刻至少要给后面留出空间，同时不越过音频长度。
        ceiling = max(limit - step * (len(moments) - index), previous + step)
        value = min(max(value, previous + step), ceiling)
        moved.append(round(value, 6))
        previous = moved[-1]
    return moved
