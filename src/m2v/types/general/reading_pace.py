"""字幕阅读速度的量算与报告。

按 Netflix《Chinese Simplified Timed Text Style Guide》的成人上限（≤9 字/秒）逐条量算，
**只报告不阻断**：字幕时长由实际 TTS 语速决定，超限只是提示制作人，
不拦下准备、预演或导出。

本模块不进 `implementation_digest`：它只产出报告，不影响准备产物与预演契约，
改报告口径不该让已验收的预演失效。
"""
from __future__ import annotations

from pathlib import Path

from m2v.core.project import _write_json

#: 成人节目上限，单位「字/秒」。字数按 `count_characters` 计，排除标点与空白。
LIMIT_PER_SECOND = 9.0

#: 取值出处，写进报告以便日后复核来源。
SOURCE = "Netflix Chinese Simplified Timed Text Style Guide：成人节目 ≤9 字/秒"

REPORT = "outputs/reading-pace.json"

from m2v.core.video_config import GENERAL_DEFAULT_FPS


def entries(cues: list[dict], fps: int = GENERAL_DEFAULT_FPS) -> list[dict]:
    """逐条字幕的字数、秒数与字/秒。无字或零长的 cue 跳过，不参与判定。"""
    from m2v.types.general.article_text import count_characters

    measured = []
    for cue in cues:
        seconds = (cue["endFrame"] - cue["startFrame"]) / fps
        characters = count_characters(cue["text"])
        if seconds <= 0 or characters == 0:
            continue
        measured.append({
            "startFrame": cue["startFrame"],
            "endFrame": cue["endFrame"],
            "characters": characters,
            "seconds": round(seconds, 3),
            "charactersPerSecond": round(characters / seconds, 2),
        })
    return measured


def report(prepared: dict) -> dict:
    """阅读速度报告。超限条目单独列一份，便于提示与复盘。"""
    measured = entries(prepared["subtitles"], prepared["fps"])
    over = [cue for cue in measured if cue["charactersPerSecond"] > LIMIT_PER_SECOND]
    return {
        "schemaVersion": 1,
        "preparedFingerprint": prepared["preparedFingerprint"],
        "limitPerSecond": LIMIT_PER_SECOND,
        "source": SOURCE,
        "status": "over-limit" if over else "pass",
        "cues": measured,
        "overLimit": over,
    }


def write(root: Path, prepared: dict) -> dict:
    """写报告，返回它本身。绑定当前准备指纹，但不参与准备产物与预演契约。"""
    payload = report(prepared)
    _write_json(root / REPORT, payload)
    return payload
