"""媒体清单校验与分镜派生；源分镜始终不被覆盖。"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit, urlunsplit, parse_qsl

from . import storyboard as sb
from .audio import wav_duration
from .errors import A2VError


def fingerprint(source: dict) -> str:
    return hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Media:
    path: Path
    data: dict
    storyboard: sb.Storyboard
    audio: Path


def load_media(path: str | Path, source_path: str | Path | None = None) -> Media:
    path = Path(path).resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        source = data["source"]
        if type(data["version"]) is not int or data["version"] != 1 or data["sourceFingerprint"] != fingerprint(source):
            raise ValueError("版本或分镜指纹非法")
        if source_path and fingerprint(json.loads(Path(source_path).read_text(encoding="utf-8"))) != data["sourceFingerprint"]:
            raise ValueError("分镜已修改，请重新 prepare")
        report = sb.validate(source)
        if not report.ok:
            raise ValueError("清单中的源分镜无效")
        effective = copy.deepcopy(source)
        if len(data["scenes"]) != len(source["scenes"]):
            raise ValueError("场景数量不匹配")
        for item, scene in zip(effective["scenes"], data["scenes"]):
            frames = scene["durationInFrames"]
            if (scene["id"] != item["id"] or type(frames) is not int
                    or frames < item["durationInFrames"]):
                raise ValueError("场景 ID 或时长非法")
            item["durationInFrames"] = frames
        model = sb._build(effective, report)
        previous_end = 0
        if not isinstance(data["cues"], list):
            raise ValueError("字幕必须是列表")
        for cue in data["cues"]:
            start, end = cue["start"], cue["end"]
            if (any(type(t) not in (int, float) or not math.isfinite(t) for t in (start, end))
                    or start < previous_end or end <= start or end > model.total_frames / model.fps
                    or not isinstance(cue["text"], str) or not cue["text"].strip() or len(cue["text"]) > 28):
                raise ValueError("字幕时间段非法")
            previous_end = end
        audio = (path.parent / data["audio"]).resolve()
        if not audio.is_relative_to(path.parent):
            raise ValueError("音轨必须位于清单目录内")
        if abs(wav_duration(audio) - model.total_frames / model.fps) > 1 / 24000:
            raise ValueError("音轨时长与时间轴不一致")
        return Media(path, data, model, audio)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise A2VError(f"媒体清单无效 {path}: {exc}") from exc


def media_url(page_url: str, server_url: str, media: Media) -> str:
    parts = urlsplit(page_url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "a2v-media"]
    query.append(("a2v-media", server_url + "/" + quote(media.path.name)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
