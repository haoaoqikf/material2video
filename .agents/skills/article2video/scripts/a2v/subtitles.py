"""从服务的字词时间戳构造短句；字幕和 SRT 共用秒级时间轴。"""
from __future__ import annotations

import math
import re

from .errors import A2VError


def cues_from_words(text: str, words: list[dict], duration: float) -> list[dict]:
    if not words:
        raise A2VError("配音缺少字词时间戳，无法生成同步字幕")
    cues, group = [], []
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
        if position < 0 or re.search(r"[\w\u4e00-\u9fff]", text[cursor:position]):
            raise A2VError("配音时间戳文本与 narration 不匹配")
        cursor = position + len(token)
        suffix = re.match(r"[^\w\u4e00-\u9fff]*", text[cursor:]).group()
        cursor += len(suffix)
        token += suffix
        if len(token.strip()) > 28:
            raise A2VError("单个时间戳词块过长，请缩短口播或更换音色")
        if group and sum(len(w["text"]) for w in group) + len(token) > 28:
            cues.append(_cue(group))
            group = []
        group.append({"text": token, "start": start, "end": end})
        if re.search(r"[，。！？；：,.!?;:]", suffix):
            cues.append(_cue(group))
            group = []
        previous_end = end
    if re.search(r"[\w\u4e00-\u9fff]", text[cursor:]):
        raise A2VError("配音时间戳未覆盖完整口播")
    if group:
        cues.append(_cue(group))
    return cues


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
