"""从服务的字词时间戳构造同步字幕短句。

字幕按**句子**断，而不是按固定字数切；服务未返回的标点依据原文找回，
绝不为缺失词语估算时间。文本与时间戳对不上时直接失败，不猜。
"""
from __future__ import annotations

import math
import re

from film_runtime.core.errors import VideoError

#: 单个字幕 cue 的字数上限：过长会挤掉画面，也会让一行读不完。
_MAX_CUE_CHARS = 28

#: 段末标点：命中即断句。
_SENTENCE_END = re.compile(r"[，。！？；：,.!?;:]")

#: 词边界与原文之间的标点恢复：只跳过非文字字符。
_WORD_CHAR = re.compile(r"[\w\u4e00-\u9fff]")


def _walk_words(text: str, words: list[dict], duration: float):
    """按原文顺序核对时间戳并还原标点，逐词产出词块。"""
    cursor, previous_end = 0, 0.0
    for word in words:
        token = word.get("text", "")
        start, end = word.get("start"), word.get("end")
        if (not isinstance(token, str) or not token.strip()
                or any(isinstance(t, bool) or not isinstance(t, (float, int)) or not math.isfinite(t)
                       for t in (start, end))
                or start < previous_end or end <= start or end > duration + 0.1):
            raise VideoError("配音字词时间戳非法或超出音频时长")
        # 依据原文找回服务未返回的标点，绝不为缺失词语估算时间。
        position = text.find(token, cursor)
        if position < 0 or _WORD_CHAR.search(text[cursor:position]):
            raise VideoError("配音时间戳文本与 narration 不匹配")
        cursor = position + len(token)
        suffix = re.match(r"[^\w\u4e00-\u9fff]*", text[cursor:]).group()
        cursor += len(suffix)
        token += suffix
        if len(token.strip()) > _MAX_CUE_CHARS:
            raise VideoError("单个时间戳词块过长，请缩短口播或更换音色")
        yield {"text": token, "start": start, "end": end}
        previous_end = end
    if _WORD_CHAR.search(text[cursor:]):
        raise VideoError("配音时间戳未覆盖完整口播")


def cues_from_words(text: str, words: list[dict], duration: float) -> list[dict]:
    if not words:
        raise VideoError("配音缺少字词时间戳，无法生成同步字幕")
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


def _cue(words: list[dict]) -> dict:
    return {"start": words[0]["start"], "end": words[-1]["end"],
            "text": "".join(w["text"] for w in words).strip()}
