"""参考音轨提取：把用户明确指定复用的参考作品音频落到作品目录并留证。

参考素材默认只用于分析；这是唯一受控的音频复用入口。命令不直接让渲染链路读取
``refs/``，而是先提取为作品目录内的独立 WAV，再写出来源、摘要与授权原文。提取格式
为 PCM 16-bit / 48 kHz / 保留源声道，便于用标准库精确计算采样数与 60 fps 帧数。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import wave
from datetime import datetime
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError
from m2v.core.project import load_project
from m2v.core.video_config import project_fps
from m2v.reference.douyin import verify_directory

FPS = 60
SAMPLE_RATE = 48000
MAX_FRAMES = 36000
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_RESERVED = {"CON", "PRN", "AUX", "NUL",
             *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
_LICENSE = "未取得书面许可；用户明确指定复用，不构成许可"
_THIRD_PARTY = "参考音频可能包含第三方音乐或声音，权利状态未知"


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def validate_name(value: str) -> str:
    """名称只用于文件名；拒绝路径、保留名与已经带目标后缀的输入。"""
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise M2VError("音轨名称只能包含字母、数字与 ._-，且必须以字母或数字开头")
    if value.endswith("."):
        raise M2VError("音轨名称不能以点结尾")
    if value.upper().split(".")[0] in _RESERVED:
        raise M2VError(f"音轨名称不能使用 Windows 保留名：{value}")
    lowered = value.lower()
    if lowered.endswith(".wav") or lowered.endswith(".provenance.json"):
        raise M2VError("音轨名称不要包含扩展名；命令会自动写入 .wav 与 .provenance.json")
    return value


def _read_metadata(directory: Path) -> dict:
    path = directory / "metadata.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M2VError(f"无法读取参考元数据 {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("kind") != "video":
        raise M2VError("参考作品不是视频；只有视频作品可以提取音轨")
    return data


def _video_record(records: list[dict]) -> dict:
    for record in records:
        if record.get("path") == "video.mp4":
            return record
    raise M2VError("参考作品没有登记的 video.mp4")


def _ffmpeg(args: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess:
    try:
        return subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", *args],
                              capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise M2VError("音轨提取超时（300 秒）") from exc


def _ffmpeg_version() -> str:
    try:
        result = subprocess.run([get_ffmpeg_exe(), "-version"], capture_output=True, timeout=30)
        line = result.stdout.decode("utf-8", "replace").splitlines()
        return line[0].strip() if line else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def _extract(video: Path, target: Path) -> None:
    result = _ffmpeg(["-i", str(video), "-map", "0:a:0", "-vn",
                      "-c:a", "pcm_s16le", "-ar", str(SAMPLE_RATE),
                      "-f", "wav", str(target)])
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        if "matches no streams" in detail or "does not contain any stream" in detail:
            raise M2VError("参考视频没有可用的音频流，无法复用音轨")
        raise M2VError("音轨提取失败：" + (detail[-1200:] or "ffmpeg 未返回错误信息"))


def frames_at_60fps(samples: int, sample_rate: int = SAMPLE_RATE) -> int:
    """按 60 fps 向上取整；不截断尾部，最多多出 1 帧静音。"""
    return (samples * FPS + sample_rate - 1) // sample_rate


def _audio_info(path: Path) -> dict:
    try:
        with wave.open(str(path), "rb") as stream:
            channels, width, rate = stream.getnchannels(), stream.getsampwidth(), stream.getframerate()
            samples = stream.getnframes()
    except (wave.Error, OSError, EOFError) as exc:
        raise M2VError(f"提取结果不是可读的 PCM WAV：{exc}") from exc
    if width != 2 or rate != SAMPLE_RATE or channels < 1 or samples <= 0:
        raise M2VError(f"提取结果参数异常：{rate} Hz / {channels} 声道 / {width * 8} bit / {samples} 采样")
    frames = frames_at_60fps(samples, rate)
    if frames > MAX_FRAMES:
        raise M2VError(f"参考音轨对应 {frames} 帧，超过 {MAX_FRAMES} 帧（600 秒）上限")
    return {
        "samples": samples,
        "sampleRate": rate,
        "channels": channels,
        "bitsPerSample": width * 8,
        "codec": "pcm_s16le",
        "durationSeconds": round(samples / rate, 6),
        "framesAt60fps": frames,
        "frameRounding": "ceil",
        "bytes": path.stat().st_size,
        "sha256": _digest(path),
    }


def _soundtrack(source_ref: str) -> dict:
    return {"music": {"sourceRef": source_ref, "gainDb": 0, "loop": False,
                      "fadeInMs": 0, "fadeOutMs": 0}}


def _provenance(metadata: dict, video: dict, audio: dict, *, reference: Path,
                target_ref: str, project: dict, statement: str) -> dict:
    author = (metadata.get("author") or {}).get("nickname") or "未知"
    return {
        "schemaVersion": 1,
        "generatedBy": "m2v ref audio",
        "reference": {
            "directory": reference.as_posix(),
            "awemeId": metadata.get("awemeId"),
            "kind": metadata.get("kind"),
            "author": author,
            "authorUid": (metadata.get("author") or {}).get("uid"),
            "desc": metadata.get("desc", ""),
            "sourceUrl": metadata.get("sourceUrl"),
            "finalUrl": metadata.get("finalUrl"),
            "capturedAt": metadata.get("capturedAt"),
            "videoPath": video.get("path"),
            "videoSha256": video.get("sha256"),
            "videoBytes": video.get("bytes"),
            "declaredDurationMs": metadata.get("durationMs"),
        },
        "audio": {"path": target_ref, **audio},
        "extraction": {"tool": "ffmpeg", "ffmpegVersion": _ffmpeg_version(),
                       "audioStreamIndex": 0, "extractedAt": _now()},
        "authorization": {
            "userAuthorized": True,
            "statement": statement,
            "scope": "仅用于本作品",
            "licenseStatus": _LICENSE,
            "thirdPartyRisk": _THIRD_PARTY,
            "attribution": f"抖音 @{author}",
        },
        "usage": {"projectId": project.get("id"), "soundtrack": _soundtrack(target_ref)},
    }


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _existing(info: dict, *, provenance: Path, video: dict, target: Path) -> dict | None:
    if not provenance.is_file():
        return None
    try:
        saved = json.loads(provenance.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    reference = saved.get("reference") or {}
    audio = saved.get("audio") or {}
    if (reference.get("videoSha256") == video.get("sha256")
            and audio.get("sha256") == info["sha256"]
            and audio.get("bytes") == info["bytes"]
            and target.is_file()):
        return saved
    return None


def extract_audio(reference_dir: str | Path, project_dir: str | Path, *, statement: str,
                  name: str | None = None, force: bool = False) -> dict:
    """提取参考作品音轨；返回 CLI 可直接打印的结果。"""
    if not isinstance(statement, str) or not statement.strip():
        raise M2VError("复用参考音轨必须提供用户授权说明（--user-authorized）")
    reference = Path(reference_dir).expanduser().resolve()
    records = verify_directory(reference, quiet=True)
    metadata = _read_metadata(reference)
    video = _video_record(records)
    video_path = reference / video["path"]
    if not video_path.is_file():
        raise M2VError(f"参考视频缺失：{video['path']}")

    root, project = load_project(project_dir)
    if project.get("type") != "general":
        raise M2VError("ref audio 只适用于 general 作品")
    aweme_id = str(metadata.get("awemeId") or "")
    if not aweme_id:
        raise M2VError("参考元数据缺少作品 ID")
    name = validate_name(name or f"ref-{aweme_id}")

    audio_dir = root / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    target = audio_dir / f"{name}.wav"
    provenance = audio_dir / f"{name}.provenance.json"
    target_ref = target.relative_to(root).as_posix()
    provenance_ref = provenance.relative_to(root).as_posix()

    if target.exists() and not force:
        try:
            info = _audio_info(target)
        except M2VError:
            info = None
        saved = _existing(info, provenance=provenance, video=video, target=target) if info else None
        if saved is None:
            raise M2VError("目标音轨已存在且与当前来源或摘要不一致；确认替换请加 --force")
        return _result(reference, root, project, name, target_ref, provenance_ref,
                       metadata, video, info, statement, reused=True, saved_audio=saved.get("audio"))

    handle, temporary = tempfile.mkstemp(prefix=f".{name}-", suffix=".wav", dir=audio_dir)
    os.close(handle)
    partial = Path(temporary)
    try:
        _extract(video_path, partial)
        info = _audio_info(partial)
        payload = _provenance(metadata, video, info, reference=reference, target_ref=target_ref,
                              project=project, statement=statement.strip())
        side = partial.with_suffix(".json")
        _write_json(side, payload)
        os.replace(partial, target)
        os.replace(side, provenance)
    finally:
        partial.unlink(missing_ok=True)
        partial.with_suffix(".json").unlink(missing_ok=True)

    # 摘要基于最终文件复核一次，避免写到一半的差异被当作成功。
    info = _audio_info(target)
    saved = json.loads(provenance.read_text(encoding="utf-8"))
    if saved["audio"]["sha256"] != info["sha256"]:
        raise M2VError("音轨写入后摘要不一致，请重试")
    return _result(reference, root, project, name, target_ref, provenance_ref,
                   metadata, video, info, statement, reused=False)


def _result(reference: Path, root: Path, project: dict, name: str, target_ref: str,
            provenance_ref: str, metadata: dict, video: dict, info: dict,
            statement: str, *, reused: bool, saved_audio: dict | None = None) -> dict:
    source_audio = saved_audio or info
    fps = project_fps(root, project, allow_missing_storyboard=True)
    total_frames = (info["samples"] * fps + info["sampleRate"] - 1) // info["sampleRate"]
    declared = metadata.get("durationMs")
    warning = None
    if isinstance(declared, (int, float)) and declared > 0:
        diff = abs(declared / 1000 - info["durationSeconds"])
        if diff > 1:
            warning = f"参考声明时长 {declared / 1000:.2f} 秒与实测 {info['durationSeconds']:.2f} 秒相差 {diff:.2f} 秒"
    return {
        "directory": str(reference),
        "project": str(root),
        "projectId": project.get("id"),
        "name": name,
        "reused": reused,
        "audio": target_ref,
        "provenance": provenance_ref,
        "source": {
            "awemeId": metadata.get("awemeId"),
            "author": (metadata.get("author") or {}).get("nickname") or "未知",
            "sourceUrl": metadata.get("sourceUrl"),
            "finalUrl": metadata.get("finalUrl"),
            "videoSha256": video.get("sha256"),
            "videoBytes": video.get("bytes"),
        },
        "audioInfo": source_audio,
        "timeline": {
            "fps": fps,
            "totalFrames": total_frames,
            "rounding": "ceil",
            "tailSilenceMaxMs": round(1000 / fps, 1),
            "formula": "全部 cut 时 sum(durationFrames) = totalFrames；使用 fade/crossfade 时另加 transitionFrames 之和",
        },
        "soundtrack": _soundtrack(target_ref),
        "authorization": {
            "statement": statement.strip(),
            "licenseStatus": _LICENSE,
            "attribution": f"抖音 @{(metadata.get('author') or {}).get('nickname') or '未知'}",
        },
        "warning": warning,
    }
