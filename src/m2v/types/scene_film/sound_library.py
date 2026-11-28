"""复核创作命令读到的作品本地音效记录。"""
from __future__ import annotations

import json
from pathlib import Path
import re
import wave

from m2v.core.errors import M2VError
from m2v.core.media_policy import UNKNOWN_LICENSES
from m2v.core.validate import obj
from m2v.engine.audio import SAMPLE_RATE
from m2v.engine.sound import asset_digest
from .media_assets import _http
from . import sound_synthesis

RECORD = "assets/sound-sources.json"
DIRECTORY = "assets/sound"
ID = re.compile(r"[A-Za-z0-9_-]{1,80}")


def probe(path: Path) -> dict:
    """完整读取标准化 PCM，拒绝伪时长与截断 WAV。"""
    try:
        with wave.open(str(path), "rb") as stream:
            frames, channels, rate = stream.getnframes(), stream.getnchannels(), stream.getframerate()
            if stream.getsampwidth() != 2 or rate != SAMPLE_RATE or channels not in (1, 2):
                raise M2VError("音效必须是 PCM16 / 24000Hz / 单或双声道 WAV")
            if not 0 < frames <= 600 * rate:
                raise M2VError("音效时长须大于 0 且不超过 600 秒")
            size = 0
            while block := stream.readframes(rate):
                size += len(block)
            if size != frames * channels * 2:
                raise M2VError("音效 WAV 数据截断")
        return {"sampleRate": rate, "channels": channels, "frames": frames, "durationSeconds": frames/rate}
    except (wave.Error, EOFError, OSError) as exc:
        raise M2VError(f"音效无法解码：{path.name}") from exc


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or value.strip().lower() in UNKNOWN_LICENSES:
        raise M2VError(f"音效 {field} 必须明确，不能未知")
    return value.strip()


def _provenance(entry: dict) -> None:
    _text(entry.get("author"), "author")
    _text(entry.get("license"), "license")
    if entry.get("source") == "synthesized":
        generated = obj(entry.get("synthesis"), "音效 synthesis", {"generator", "version", "parameters"})
        if (generated.get("generator") != "film_runtime.sound-synthesis" or generated.get("version") != sound_synthesis.VERSION
                or sound_synthesis.recipe(generated.get("parameters")) != generated.get("parameters")):
            raise M2VError("音效生成配方或版本无效，请用作品本地 setup 重新合成")
    elif entry.get("source") == "third-party":
        if not isinstance(entry.get("sourceUrl"), str) or not _http(entry["sourceUrl"]):
            raise M2VError("第三方音效必须提供 sourceUrl 来源页")
        if not isinstance(entry.get("originalSha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", entry["originalSha256"]):
            raise M2VError("第三方音效缺少原始文件摘要")
    else:
        raise M2VError("音效 source 必须为 synthesized/third-party")


def load_record(root: Path) -> dict:
    path = root / RECORD
    if not path.resolve().is_relative_to(root.resolve()):
        raise M2VError("音效来源记录不可越出作品目录")
    if not path.exists():
        return {"schemaVersion": 1, "assets": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        obj(data, RECORD, {"schemaVersion", "assets"})
        if type(data.get("schemaVersion")) is not int or data["schemaVersion"] != 1 or not isinstance(data.get("assets"), list):
            raise M2VError("音效来源记录结构无效")
        if len(data["assets"]) > 300:
            raise M2VError("音效库最多 300 项")
        return data
    except (ValueError, OSError) as exc:
        raise M2VError("音效来源记录无法读取") from exc


def resolve(root: Path) -> tuple[dict, dict]:
    assets, inputs = {}, {}
    record = load_record(root)
    if (root / RECORD).exists():
        inputs["file:" + RECORD] = asset_digest(root / RECORD)
    else:
        inputs["absent-file:" + RECORD] = "absent"
    for entry in record["assets"]:
        if not isinstance(entry, dict):
            raise M2VError("音效记录项必须是对象")
        identity, sha = entry.get("id"), entry.get("sha256")
        if not isinstance(identity, str) or not ID.fullmatch(identity) or identity in assets:
            raise M2VError("音效 ID 无效或重复")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise M2VError(f"音效 {identity} 摘要无效")
        expected = f"{DIRECTORY}/{sha}.wav"
        path = (root / expected).resolve()
        if (entry.get("path") != expected or not path.is_relative_to(root.resolve())
                or not path.is_relative_to((root / DIRECTORY).resolve())):
            raise M2VError(f"音效 {identity} 路径无效")
        _provenance(entry)
        if not path.is_file() or asset_digest(path) != sha:
            raise M2VError(f"音效 {identity} 文件缺失或摘要变化")
        info = probe(path)
        if any(entry.get(key) != value for key, value in info.items()):
            raise M2VError(f"音效 {identity} 实测参数变化")
        assets[identity] = {**entry, "file": path}
        inputs["file:" + expected] = sha
    return assets, inputs
