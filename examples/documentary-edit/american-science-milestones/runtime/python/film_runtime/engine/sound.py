"""声音参数契约和本地素材解析；不在校验期间联网。"""
from __future__ import annotations

import math
import hashlib
import re
from pathlib import Path
from film_runtime.core.errors import VideoError

RATE = re.compile(r"^[+-]\d+%$")

def asset_digest(path: Path) -> str:
    """声音素材可能很长，摘要同样按块读取，不将文件整体装入内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024): digest.update(block)
    return digest.hexdigest()

def valid_rate(value: object) -> bool:
    return isinstance(value, str) and bool(RATE.fullmatch(value)) and -50 <= int(value[:-1]) <= 50

def local_ref(value: object) -> bool:
    return (isinstance(value, str) and bool(value.strip()) and "\\" not in value
            and ":" not in value and not value.startswith("/")
            and all(part not in {"", ".", ".."} for part in value.split("/")))

def validate_sound(source: dict, report, *, effects: bool = True) -> None:
    """校验声音参数与本地素材引用。

    `effects` 为假时只接受音床 `soundtrack.music`，用于没有 beat 轴、
    因而无法定位音效起点的场景结构（如通用多场景编排）。
    """
    def fields(value, allowed, where):
        if not isinstance(value, dict):
            report.error(where, "必须是对象"); return False
        for key in set(value) - allowed:
            report.error(f"{where}.{key}", "未知声音字段")
        return True
    def number(value, lo, hi):
        return type(value) in (int, float) and math.isfinite(value) and lo <= value <= hi
    for i, scene in enumerate(source.get("scenes", [])):
        if not isinstance(scene, dict): continue
        segments = scene.get("narrationSegments")
        if not isinstance(segments, list): continue
        for j, segment in enumerate(segments):
            if not isinstance(segment, dict) or "speech" not in segment: continue
            speech = segment["speech"]; where = f"scenes[{i}].narrationSegments[{j}].speech"
            if not fields(speech, {"rate", "pauseBeforeMs", "pauseAfterMs"}, where): continue
            if "rate" in speech and not valid_rate(speech["rate"]): report.error(where + ".rate", "语速必须是 −50% 至 +50% 的有符号百分比")
            for key in ("pauseBeforeMs", "pauseAfterMs"):
                if key in speech and (type(speech[key]) is not int or not 0 <= speech[key] <= 2000): report.error(where + "." + key, "停顿必须为 0–2000ms 整数")
    if "soundtrack" not in source: return
    track = source["soundtrack"]
    if not fields(track, {"music", "effects"}, "soundtrack"): return
    def asset(item, where, allowed):
        if not fields(item, allowed, where): return False
        if not local_ref(item.get("sourceRef")): report.error(where + ".sourceRef", "必须是分镜目录内本地相对路径")
        if "gainDb" in item and not number(item["gainDb"], -60, 0): report.error(where + ".gainDb", "增益必须为 −60 至 0 dB")
        return True
    if "music" in track:
        music = track["music"]
        if asset(music, "soundtrack.music", {"sourceRef", "gainDb", "loop", "fadeInMs", "fadeOutMs"}):
            if "loop" in music and type(music["loop"]) is not bool: report.error("soundtrack.music.loop", "必须是布尔值")
            for key in ("fadeInMs", "fadeOutMs"):
                if key in music and (type(music[key]) is not int or not 0 <= music[key] <= 60000): report.error("soundtrack.music." + key, "淡入淡出必须为 0–60000ms 整数")
    effect_items = track.get("effects", [])
    if not effect_items:
        return
    if not effects:
        report.error("soundtrack.effects", "该场景结构没有 beat 轴，只支持 soundtrack.music")
        return
    if not isinstance(effect_items, list) or len(effect_items) > 128:
        report.error("soundtrack.effects", "音效必须为最多 128 项的数组"); return
    scenes = {s.get("id"): s for s in source.get("scenes", []) if isinstance(s, dict) and isinstance(s.get("id"), str)}
    for i, item in enumerate(effect_items):
        where = f"soundtrack.effects[{i}]"
        if not asset(item, where, {"sourceRef", "sceneId", "beatId", "offsetMs", "gainDb"}): continue
        scene = scenes.get(item.get("sceneId")) if isinstance(item.get("sceneId"), str) else None
        if not scene: report.error(where + ".sceneId", "未知场景")
        elif not isinstance(scene.get("beats"), list) or not any(isinstance(b, dict) and b.get("id") == item.get("beatId") for b in scene["beats"]): report.error(where + ".beatId", "未知节拍")
        if "offsetMs" in item and (type(item["offsetMs"]) is not int or not -60000 <= item["offsetMs"] <= 60000): report.error(where + ".offsetMs", "偏移必须为 ±60000ms 内整数")

def sound_assets(source: dict, source_path: Path) -> dict[str, Path]:
    track = source.get("soundtrack") or {}
    items = ([track["music"]] if "music" in track else []) + track.get("effects", [])
    result = {}
    root = source_path.resolve().parent
    for item in items:
        ref = item["sourceRef"]
        if not local_ref(ref): raise VideoError(f"声音素材路径非法：{ref}")
        path = (root / ref).resolve()
        if not path.is_relative_to(root) or not path.is_file(): raise VideoError(f"声音素材缺失或越界：{ref}")
        result[ref] = path
    return result

def configuration(source: dict) -> dict:
    units = source.get("stages", source.get("scenes", []))
    return {"soundtrack": source.get("soundtrack"),
            "speech": [[s.get("speech") for s in unit.get("narrationSegments", [])] for unit in units]}
