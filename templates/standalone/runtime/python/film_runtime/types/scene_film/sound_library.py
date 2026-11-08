"""音效双来源落盘、留证和离线复核；不向画面服务器暴露音频目录。"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import wave

from film_runtime.core import security
from film_runtime.core.errors import VideoError
from film_runtime.core.project import _write_json, load_project
from film_runtime.core.validate import obj
from film_runtime.engine import audio
from film_runtime.core.media_policy import UNKNOWN_LICENSES
from film_runtime.engine.http_transport import HttpTransport, MAX_DOWNLOAD_BYTES
from film_runtime.engine.sound import asset_digest
from .media_assets import _http
from . import sound_synthesis

logger = logging.getLogger(__name__)
RECORD = "assets/sound-sources.json"
DIRECTORY = "assets/sound"
ID = re.compile(r"[A-Za-z0-9_-]{1,80}")


def probe(path: Path) -> dict:
    """完整读取标准化 PCM，拒绝伪时长与截断 WAV。"""
    try:
        with wave.open(str(path), "rb") as stream:
            frames, channels, rate = stream.getnframes(), stream.getnchannels(), stream.getframerate()
            if stream.getsampwidth() != 2 or rate != audio.SAMPLE_RATE or channels not in (1, 2):
                raise VideoError("音效必须是 PCM16 / 24000Hz / 单或双声道 WAV")
            if not 0 < frames <= 600 * rate:
                raise VideoError("音效时长须大于 0 且不超过 600 秒")
            size = 0
            while block := stream.readframes(rate):
                size += len(block)
            if size != frames * channels * 2:
                raise VideoError("音效 WAV 数据截断")
        return {"sampleRate": rate, "channels": channels, "frames": frames, "durationSeconds": frames/rate}
    except (wave.Error, EOFError, OSError) as exc:
        raise VideoError(f"音效无法解码：{path.name}") from exc


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or value.strip().lower() in UNKNOWN_LICENSES:
        raise VideoError(f"音效 {field} 必须明确，不能未知")
    return value.strip()


def decode(source: Path, target: Path) -> dict:
    # 多解码一秒以明确拒绝过长素材，而不是默默截成合法时长。
    audio.ffmpeg(["-xerror", "-i", str(source), "-map", "0:a:0", "-t", "601", "-vn",
                  "-ar", str(audio.SAMPLE_RATE), "-ac", "2", "-c:a", "pcm_s16le", str(target)])
    return probe(target)


def _provenance(entry: dict) -> None:
    _text(entry.get("author"), "author")
    _text(entry.get("license"), "license")
    if entry.get("source") == "synthesized":
        generated = obj(entry.get("synthesis"), "音效 synthesis", {"generator", "version", "parameters"})
        if (generated.get("generator") != "film_runtime.sound-synthesis" or generated.get("version") != sound_synthesis.VERSION
                or sound_synthesis.recipe(generated.get("parameters")) != generated.get("parameters")):
            raise VideoError("音效生成配方或版本无效，请重新合成")
    elif entry.get("source") == "third-party":
        if not isinstance(entry.get("sourceUrl"), str) or not _http(entry["sourceUrl"]):
            raise VideoError("第三方音效必须提供 sourceUrl 来源页")
        if not isinstance(entry.get("originalSha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", entry["originalSha256"]):
            raise VideoError("第三方音效缺少原始文件摘要")
    else:
        raise VideoError("音效 source 必须为 synthesized/third-party")


def load_record(root: Path) -> dict:
    path = root / RECORD
    if not path.resolve().is_relative_to(root.resolve()):
        raise VideoError("音效来源记录不可越出作品目录")
    if not path.exists():
        return {"schemaVersion": 1, "assets": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        obj(data, RECORD, {"schemaVersion", "assets"})
        if type(data.get("schemaVersion")) is not int or data["schemaVersion"] != 1 or not isinstance(data.get("assets"), list):
            raise VideoError("音效来源记录结构无效")
        if len(data["assets"]) > 300:
            raise VideoError("音效库最多 300 项")
        return data
    except (ValueError, OSError) as exc:
        raise VideoError("音效来源记录无法读取") from exc


def resolve(root: Path) -> tuple[dict, dict]:
    assets, inputs = {}, {}
    record = load_record(root)
    if (root / RECORD).exists():
        inputs["file:" + RECORD] = asset_digest(root / RECORD)
    else:
        inputs["absent-file:" + RECORD] = "absent"
    for entry in record["assets"]:
        if not isinstance(entry, dict):
            raise VideoError("音效记录项必须是对象")
        identity, sha = entry.get("id"), entry.get("sha256")
        if not isinstance(identity, str) or not ID.fullmatch(identity) or identity in assets:
            raise VideoError("音效 ID 无效或重复")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise VideoError(f"音效 {identity} 摘要无效")
        expected = f"{DIRECTORY}/{sha}.wav"
        path = (root / expected).resolve()
        if (entry.get("path") != expected or not path.is_relative_to(root.resolve())
                or not path.is_relative_to((root / DIRECTORY).resolve())):
            raise VideoError(f"音效 {identity} 路径无效")
        _provenance(entry)
        if not path.is_file() or asset_digest(path) != sha:
            raise VideoError(f"音效 {identity} 文件缺失或摘要变化")
        info = probe(path)
        if any(entry.get(key) != value for key, value in info.items()):
            raise VideoError(f"音效 {identity} 实测参数变化")
        assets[identity] = {**entry, "file": path}
        inputs["file:" + expected] = sha
    return assets, inputs


def import_assets(root: Path, manifest: dict, *, base: Path, transport=None) -> dict:
    manifest = obj(manifest, "sound manifest", {"schemaVersion", "assets"})
    entries = manifest.get("assets")
    if type(manifest.get("schemaVersion")) is not int or manifest["schemaVersion"] != 1:
        raise VideoError("音效清单 schemaVersion 必须为 1")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 300:
        raise VideoError("音效 assets 必须有 1～300 项")
    prior = load_record(root)
    # 先验证旧记录，防止无关的坏素材被新批次掩盖。
    resolve(root)
    target_dir = root / DIRECTORY
    if not target_dir.resolve().is_relative_to(root.resolve()):
        raise VideoError("音效目录不可越出作品目录")
    target_dir.mkdir(parents=True, exist_ok=True)
    transport = transport or HttpTransport()
    adopted, staged, ids = [], [], set()
    with tempfile.TemporaryDirectory(prefix="import-", dir=target_dir) as temporary:
        for entry in entries:
            obj(entry, "sound asset", {"id", "synthesis", "localPath", "mediaUrl", "sourceUrl", "author", "license"})
            identity = entry.get("id")
            if not isinstance(identity, str) or not ID.fullmatch(identity) or identity in ids:
                raise VideoError("音效 ID 无效或重复")
            ids.add(identity)
            sources = [key for key in ("synthesis", "localPath", "mediaUrl") if key in entry]
            if len(sources) != 1:
                raise VideoError("音效 synthesis/localPath/mediaUrl 必须三选一")
            logger.info("准备音效 %s，来源 %s", identity, sources[0])
            file = Path(temporary) / f"{identity}.wav"
            if "synthesis" in entry:
                value = entry["synthesis"]
                if isinstance(value, dict) and set(value) == {"generator", "version", "parameters"}:
                    if value["generator"] != "film_runtime.sound-synthesis" or value["version"] != sound_synthesis.VERSION:
                        raise VideoError("音效生成配方或版本无效，请重新合成")
                    value = value["parameters"]
                generated = sound_synthesis.synthesize(value, file)
                info = probe(file)
                provenance = {"source": "synthesized", "synthesis": generated,
                              "author": "material2video", "license": "CC0-1.0"}
            else:
                provenance = {"source": "third-party", "sourceUrl": entry.get("sourceUrl"),
                              "author": entry.get("author"), "license": entry.get("license")}
                # 在任何联网操作前检查许可和来源。
                _provenance({**provenance, "originalSha256": "0"*64})
                original = Path(temporary) / f"{identity}.input"
                if "localPath" in entry:
                    local = entry["localPath"]
                    if not isinstance(local, str) or not local:
                        raise VideoError("音效 localPath 必须为非空路径")
                    source = (base / local).resolve()
                    if (not source.is_relative_to(root.resolve()) or not source.is_file()
                            or not 0 < source.stat().st_size <= MAX_DOWNLOAD_BYTES):
                        raise VideoError("本地音效缺失、为空或超过 256MiB")
                    shutil.copyfile(source, original)
                else:
                    remote = entry["mediaUrl"]
                    if not isinstance(remote, str) or not _http(remote):
                        raise VideoError("音效 mediaUrl 必须是 HTTP(S) 直链")
                    transport.download(remote, original, {}, 30)
                    provenance["mediaUrl"] = remote
                if not 0 < original.stat().st_size <= MAX_DOWNLOAD_BYTES:
                    raise VideoError("音效文件为空或超过 256MiB")
                provenance["originalSha256"] = asset_digest(original)
                info = decode(original, file)
            sha = asset_digest(file)
            relative = f"{DIRECTORY}/{sha}.wav"
            adopted.append({"id": identity, "path": relative, "sha256": sha, **info, **provenance})
            staged.append((file, root / relative))
        record = {"schemaVersion": 1, "assets": [e for e in prior["assets"] if e["id"] not in ids] + adopted}
        if len(record["assets"]) > 300:
            raise VideoError("音效库最多 300 项")
        # 只创建内容寻址新文件，不覆盖已有文件；发布失败时回滚本批新增文件。
        created = []
        try:
            for file, destination in staged:
                if destination.exists():
                    if asset_digest(destination) != destination.stem:
                        raise VideoError("音效内容寻址目标已损坏，请先修复")
                else:
                    created.append(destination)
                    security.deliver(file, destination)
            _write_json(root / RECORD, record)
        except Exception:
            for path in created:
                path.unlink(missing_ok=True)
            raise
    logger.info("音效库发布完成：%d 项", len(adopted))
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="m2v author sounds")
    parser.add_argument("command", choices=("catalog", "import", "audit"))
    parser.add_argument("--project")
    parser.add_argument("--manifest")
    parser.add_argument("--base")
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            result = {"generatorVersion": sound_synthesis.VERSION, "effects": sound_synthesis.catalog()}
        else:
            if not args.project:
                parser.error("需要 --project")
            root, project = load_project(args.project)

            if args.command == "import":
                if not args.manifest:
                    parser.error("import 需要 --manifest")
                manifest = Path(args.manifest).resolve()
                result = import_assets(root, json.loads(manifest.read_text(encoding="utf-8-sig")),
                                       base=Path(args.base).resolve() if args.base else manifest.parent)
            else:
                assets, inputs = resolve(root)
                result = {"valid": True, "count": len(assets), "inputs": inputs}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (VideoError, OSError, ValueError, TypeError, subprocess.TimeoutExpired) as exc:
        logger.warning("音效操作失败：%s", type(exc).__name__)
        print(f"m2v author sounds: {exc}", file=sys.stderr)
        return 2
