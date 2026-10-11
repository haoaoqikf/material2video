"""从服务的字词时间戳构造短句与分段节拍；字幕和 SRT 共用秒级时间轴。"""
from __future__ import annotations

import math
import re

from a2v.core.errors import A2VError

#: 单个字幕 cue / 词块的字数上限：过长会挤掉画面，也会让一行读不完。
_MAX_CUE_CHARS = 28

#: 段末标点：命中即断句。字幕按句子断，而不是按固定字数切。
_SENTENCE_END = re.compile(r"[，。！？；：,.!?;:]")

#: 词边界与原文之间的标点恢复：只跳过非文字字符，绝不为缺失词语估算时间。
_WORD_CHAR = re.compile(r"[\w\u4e00-\u9fff]")


def _walk_words(text: str, words: list[dict], duration: float):
    """按原文顺序核对并还原标点，逐词产出词块。

    每个词块带 ``charStart`` / ``coreEnd``：前者是词本身在**完整口播文本**里的
    起点，后者是词本身（不含恢复出来的标点）的终点。分段口播按这两个位置把
    词块归到各段，因此重复短语不会被映射到前一处，段末标点也不会把词算到
    下一段去。
    """
    cursor, previous_end = 0, 0.0
    for word in words:
        token = word.get("text", "")
        start, end = word.get("start"), word.get("end")
        if (not isinstance(token, str) or not token.strip()
                or any(isinstance(t, bool) or not isinstance(t, (float, int)) or not math.isfinite(t)
                       for t in (start, end))
                or start < previous_end or end <= start or end > duration + 0.1):
            raise A2VError("配音字词时间戳非法或超出音频时长")
        # 依据原文找回服务未返回的标点，绝不为缺失词语估算时间。
        position = text.find(token, cursor)
        if position < 0 or _WORD_CHAR.search(text[cursor:position]):
            raise A2VError("配音时间戳文本与 narration 不匹配")
        cursor = position + len(token)
        core_end = cursor
        suffix = re.match(r"[^\w\u4e00-\u9fff]*", text[cursor:]).group()
        cursor += len(suffix)
        token += suffix
        if len(token.strip()) > _MAX_CUE_CHARS:
            raise A2VError("单个时间戳词块过长，请缩短口播或更换音色")
        yield {"text": token, "start": start, "end": end,
               "charStart": position, "coreEnd": core_end, "charEnd": cursor}
        previous_end = end
    if _WORD_CHAR.search(text[cursor:]):
        raise A2VError("配音时间戳未覆盖完整口播")


def cues_from_words(text: str, words: list[dict], duration: float) -> list[dict]:
    if not words:
        raise A2VError("配音缺少字词时间戳，无法生成同步字幕")
    cues, group = [], []
    for item in _walk_words(text, words, duration):
        token = item["text"]
        if group and sum(len(w["text"]) for w in group) + len(token) > _MAX_CUE_CHARS:
            cues.append(_cue(group))
            group = []
        group.append({"text": token, "start": item["start"], "end": item["end"]})
        if _SENTENCE_END.search(token):
            cues.append(_cue(group))
            group = []
    if group:
        cues.append(_cue(group))
    return cues


def segment_windows(text: str, segments: list[str], words: list[dict], duration: float) -> list[tuple[float, float]]:
    """把每段口播解析为 ``(start, end)`` 秒区间。

    完整口播就是各段按顺序拼接，因此每段在文本里有确定的字符区间；词块按
    WordBoundary 顺序消费，落在哪一段就归哪一段。段末恢复出来的标点允许落到
    下一段开头（它本来就没有独立时间），但**词本身**跨过段边界即失败——
    那说明分段切在词中间。任何一段拿不到词块、或文本覆盖不完整同样失败，
    绝不猜测。
    """
    if not segments:
        return []
    bounds: list[tuple[int, int]] = []
    cursor = 0
    for segment in segments:
        bounds.append((cursor, cursor + len(segment)))
        cursor += len(segment)
    if cursor != len(text):
        raise A2VError("分段口播与完整口播文本不一致，无法按词边界解析")
    windows: list[list[float | None]] = [[None, None] for _ in segments]
    index = 0
    for item in _walk_words(text, words, duration):
        while index < len(bounds) - 1 and item["charStart"] >= bounds[index][1]:
            index += 1
        start_char, end_char = bounds[index]
        if item["charStart"] < start_char or item["coreEnd"] > end_char:
            raise A2VError("口播段边界切在词中间，无法按词边界解析节拍")
        window = windows[index]
        if window[0] is None:
            window[0] = item["start"]
        window[1] = item["end"]
    for position, window in enumerate(windows):
        if window[0] is None:
            raise A2VError(f"第 {position + 1} 段口播没有对应的词边界时间戳")
    return [(float(window[0]), float(window[1])) for window in windows]


def _cue(words: list[dict]) -> dict:
    return {"start": words[0]["start"], "end": words[-1]["end"],
            "text": "".join(w["text"] for w in words).strip()}


def srt(cues: list[dict], limit: float | None = None) -> str:
    def timestamp(seconds: float) -> str:
        ms = round(seconds * 1000)
        hours, ms = divmod(ms, 3600000)
        minutes, ms = divmod(ms, 60000)
        seconds, ms = divmod(ms, 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"

    rows = []
    for cue in cues:
        end = min(cue["end"], limit) if limit is not None else cue["end"]
        if cue["start"] >= end:
            continue
        rows.append(f'{len(rows) + 1}\n{timestamp(cue["start"])} --> {timestamp(end)}\n{cue["text"]}\n')
    return "\n".join(rows)
