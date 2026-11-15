"""Qwen3-TTS-12Hz-0.6B-Base 声音克隆后端。

只在作品声明 ``tts.backend = "qwen3-tts"`` 时加载；torch、qwen-tts 与 stable-ts
都是可选依赖。模型、对齐模型与参考音色按作品内
``models/qwen3-tts/registry.json`` 登记的大小与 SHA256 校验。

Qwen3-TTS 本身不返回词级时间戳。合成后先用 stable-ts 对最终音频与旁白原文做
强制对齐，再进入现有字幕断句与停顿整形；不对缺失词语按字符比例估算时间。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import wave
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from film_runtime.core.errors import VideoError

logger = logging.getLogger(__name__)

REPO_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
REVISION = "7ee3cf0b7e7be29c5d8de06cd552b78263f01ece"
ALIGNER_REVISION = "536b0662742c02347bc0e980a01041f333bce120"
SAMPLE_RATE = 24000
SEED_VERSION = 1
VOICE_PATTERN = re.compile(r"^clone_[a-z0-9][a-z0-9-]*$")
_UNSUPPORTED = re.compile(r"[0-9０-９A-Za-z]")
_WORD_CHAR = re.compile(r"[\w一-鿿]")
_PUNCT = re.compile(r"[，。！？；：、,.!?;:]")
_PUNCT_ONLY = re.compile(r"^[，。！？；：、,.!?;:]+$")
_REGISTRY_REL = Path("qwen3-tts") / "registry.json"

#: 同一次准备里复用模型、对齐模型与参考音色提示，避免每段重新加载数 GB 权重。
_LOADED: dict[str, tuple] = {}
_VERIFIED: set[tuple[str, str]] = set()


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "missing"


def versions() -> dict:
    """缓存键使用的后端环境；版本缺失不伪装成已安装。"""
    return {
        "qwen3Tts": _package_version("qwen-tts"),
        "transformers": _package_version("transformers"),
        "torch": _package_version("torch"),
        "stableTs": _package_version("stable-ts"),
        "fasterWhisper": _package_version("faster-whisper"),
        "ctranslate2": _package_version("ctranslate2"),
        "modelRevision": REVISION,
        "alignerRevision": ALIGNER_REVISION,
        "seedVersion": SEED_VERSION,
    }


def _registry_path(models_dir: Path) -> Path:
    return models_dir / _REGISTRY_REL


def _load_registry(models_dir: Path) -> dict:
    path = _registry_path(models_dir)
    if not path.is_file():
        raise VideoError(
            f"缺少 Qwen3-TTS 模型登记：{path}；"
            "请在作品内运行 python models/qwen3-tts/fetch.py --download --voice <音色>")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise VideoError(f"Qwen3-TTS 模型登记无法读取：{path}：{exc}") from exc
    if (data.get("schemaVersion") != 1 or data.get("backend") != "qwen3-tts"
            or not isinstance(data.get("files"), list)
            or not isinstance(data.get("voices"), list)
            or not isinstance(data.get("modelDir"), str)
            or not isinstance(data.get("alignerDir"), str)):
        raise VideoError(f"Qwen3-TTS 模型登记格式不符：{path}")
    license_path = (path.parent / str(data.get("license", ""))).resolve()
    if not license_path.is_relative_to(path.parent.resolve()) or not license_path.is_file():
        raise VideoError(f"Qwen3-TTS 模型许可文件缺失或越界：{data.get('license')!r}")
    for entry in data["files"]:
        _check_entry(entry)
    for voice in data["voices"]:
        _check_voice_entry(voice)
    return data


def _check_entry(entry: dict) -> None:
    if not isinstance(entry, dict):
        raise VideoError("Qwen3-TTS 模型登记条目必须是对象")
    for key in ("role", "file", "bytes", "sha256", "provider", "repo", "revision"):
        if key not in entry:
            raise VideoError(f"Qwen3-TTS 模型登记缺少字段 {key}：{entry.get('file')!r}")
    name = entry["file"]
    if (not isinstance(name, str) or not name or Path(name).is_absolute()
            or ".." in Path(name).parts or "\\" in name):
        raise VideoError(f"Qwen3-TTS 模型登记路径非法：{name!r}")
    if (not isinstance(entry["sha256"], str) or len(entry["sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in entry["sha256"])):
        raise VideoError(f"Qwen3-TTS 模型登记 sha256 非法：{name}")
    if not isinstance(entry["bytes"], int) or entry["bytes"] <= 0:
        raise VideoError(f"Qwen3-TTS 模型登记 bytes 非法：{name}")


def _check_voice_entry(voice: dict) -> None:
    if not isinstance(voice, dict) or not VOICE_PATTERN.fullmatch(str(voice.get("voice", ""))):
        raise VideoError("Qwen3-TTS 音色档案必须使用 clone_<slug> 形式")
    for key in ("refAudio", "refText", "language", "sha256", "bytes", "authorization"):
        if key not in voice:
            raise VideoError(f"Qwen3-TTS 音色档案缺少字段 {key}：{voice.get('voice')!r}")
    name = voice["refAudio"]
    if (not isinstance(name, str) or not name or Path(name).is_absolute()
            or ".." in Path(name).parts or "\\" in name):
        raise VideoError(f"Qwen3-TTS 参考音频路径非法：{name!r}")
    if not isinstance(voice["refText"], str) or not voice["refText"].strip():
        raise VideoError(f"Qwen3-TTS 参考文本为空：{voice.get('voice')!r}")
    auth = voice["authorization"]
    if not isinstance(auth, dict) or not auth.get("userAuthorized") or not str(auth.get("statement", "")).strip():
        raise VideoError(
            f"Qwen3-TTS 音色 {voice.get('voice')!r} 缺少用户明确要求复用参考音色的说明；"
            "参考音色必须留证，不能只凭默认配置启用")


def _voice_entry(registry: dict, voice: str) -> dict:
    for entry in registry["voices"]:
        if entry.get("voice") == voice:
            return entry
    raise VideoError(f"Qwen3-TTS 音色档案中没有 {voice!r}")


def _verify(path: Path, entry: dict) -> None:
    key = (str(path), entry["sha256"])
    if key in _VERIFIED:
        return
    if not path.is_file():
        raise VideoError(
            f"Qwen3-TTS 模型文件缺失：{path}；"
            "请在作品内运行 python models/qwen3-tts/fetch.py --download")
    if path.stat().st_size != entry["bytes"]:
        raise VideoError(f"Qwen3-TTS 模型文件大小不符：{path}（期望 {entry['bytes']}）")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != entry["sha256"]:
        raise VideoError(
            f"Qwen3-TTS 模型文件摘要不符：{path}（期望 {entry['sha256']}，实际 {digest}）；"
            "拒绝使用，请检查或重新恢复")
    _VERIFIED.add(key)


def _safe_path(files_root: Path, relative: str) -> Path:
    path = (files_root / relative).resolve()
    if not path.is_relative_to(files_root.resolve()):
        raise VideoError(f"Qwen3-TTS 模型路径越界：{relative!r}")
    return path


def assets(models_dir: Path, voice: str) -> dict:
    """校验并返回模型、对齐模型与参考音色路径。"""
    if not VOICE_PATTERN.fullmatch(voice):
        raise ValueError(f"Qwen3-TTS 音色必须是形如 clone_tuixiu 的克隆档案名，实际为 {voice!r}")
    registry = _load_registry(models_dir)
    files_root = models_dir / "files"
    profile = _voice_entry(registry, voice)

    for entry in registry["files"]:
        _verify(_safe_path(files_root, entry["file"]), entry)

    ref_audio = _safe_path(files_root, profile["refAudio"])
    ref_entry = {
        "file": profile["refAudio"],
        "bytes": profile["bytes"],
        "sha256": profile["sha256"],
    }
    _verify(ref_audio, ref_entry)

    model_dir = _safe_path(files_root, registry["modelDir"])
    aligner_dir = _safe_path(files_root, registry["alignerDir"])
    if not model_dir.is_dir() or not aligner_dir.is_dir():
        raise VideoError("Qwen3-TTS 模型目录或对齐模型目录不存在")

    return {
        "voice": voice,
        "ref_audio": ref_audio,
        "ref_text": profile["refText"],
        "language": str(profile.get("language") or "Chinese"),
        "model_dir": model_dir,
        "aligner_dir": aligner_dir,
        "profile": profile,
    }


def ensure_assets(models_dir: Path, voice: str) -> None:
    """准备前一次性校验，失败在合成前暴露。"""
    assets(models_dir, voice)


def voice_names(models_dir: Path) -> list[dict]:
    """列出作品内登记的克隆音色；只读文件，不联网。"""
    registry = _load_registry(models_dir)
    return [
        {
            "voice": entry["voice"],
            "gender": entry.get("gender", ""),
            "categories": ["local", "voice-clone"],
            "personalities": [],
            "source": (entry.get("source") or {}).get("platform", ""),
        }
        for entry in registry["voices"]
    ]


def voice_digest(models_dir: Path, voice: str) -> str:
    """参考音色档案摘要；进入语音缓存键与准备记录。"""
    profile = _voice_entry(_load_registry(models_dir), voice)
    payload = {key: profile.get(key) for key in
               ("voice", "refAudio", "refText", "language", "sha256", "bytes")}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def speed_for_rate(rate: str) -> float:
    """edge-tts 的百分比语速映射为不变调变速比例；+20% → 1.2。"""
    match = re.fullmatch(r"([+-])(\d{1,2})%", rate)
    if not match:
        raise ValueError(f"语速必须是 −50% 至 +50% 的有符号百分比，实际为 {rate!r}")
    value = int(match.group(2)) / 100
    return round(1 + value if match.group(1) == "+" else 1 - value, 4)


def _seed(text: str, voice: str, ref_digest: str, speed: float) -> int:
    material = f"{SEED_VERSION}|{voice}|{ref_digest}|{speed:.4f}|{text}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:4], "big")


def _import_backend():
    try:
        import faster_whisper
        import librosa
        import stable_whisper
        import torch
        from qwen_tts import Qwen3TTSModel
    except ImportError as exc:  # pragma: no cover - 依赖缺失路径由环境决定
        raise VideoError(
            "Qwen3-TTS 后端依赖未安装：请在作品内执行 uv sync --extra qwen3-tts "
            f"（或安装 qwen-tts、stable-ts）；原始错误：{exc}"
        ) from exc
    return torch, Qwen3TTSModel, stable_whisper, librosa


def _loaded(paths: dict) -> tuple:
    key = str(paths["model_dir"].resolve())
    if key in _LOADED:
        return _LOADED[key]
    torch, Qwen3TTSModel, stable_whisper, librosa = _import_backend()
    torch.set_num_threads(max(1, min(14, os.cpu_count() or 2)))
    logger.info("加载 Qwen3-TTS 模型：%s", paths["model_dir"])
    model = Qwen3TTSModel.from_pretrained(
        str(paths["model_dir"]), dtype=torch.float32, attn_implementation="eager")
    aligner = stable_whisper.load_faster_whisper(
        str(paths["aligner_dir"]), device="cpu", compute_type="int8")
    value = (torch, model, aligner, librosa, {})
    _LOADED[key] = value
    return value


def _prompt(torch, model, paths: dict, prompts: dict) -> object:
    key = (str(paths["ref_audio"]), paths["ref_text"])
    if key not in prompts:
        prompts[key] = model.create_voice_clone_prompt(
            ref_audio=str(paths["ref_audio"]), ref_text=paths["ref_text"])
    return prompts[key]


def _repair_words(raw: list[dict], duration: float) -> list[dict]:
    """文本保序合并零时长词；不改变任何时间值，不新增估算时间。

    无标点的零时长词并入下一个有时长词的前缀，带标点的并入前一个词的尾；
    末尾零时长词并入前一个词。合并后仍逐词校验单调性与音频边界。
    """
    repaired: list[dict] = []
    pending = ""
    for item in raw:
        token, start, end = item["text"], float(item["start"]), float(item["end"])
        # 对齐器可能把句末标点单独成词；字幕链路会从原文把标点挂回前词。
        # 这里先并入前词并丢弃独立标点，避免下一个真正词语被跳过。
        if _PUNCT_ONLY.fullmatch(token):
            if repaired:
                if not repaired[-1]["text"].endswith(token):
                    repaired[-1]["text"] += token
            else:
                pending += token
            continue
        if end > start:
            if pending:
                token = pending + token
                pending = ""
            repaired.append({"text": token, "start": start, "end": end})
        elif _PUNCT.search(token) and repaired:
            repaired[-1]["text"] += token
        else:
            pending += token
    if pending:
        if not repaired:
            raise ValueError("强制对齐没有返回有时长的词")
        repaired[-1]["text"] += pending

    previous = 0.0
    for word in repaired:
        if word["start"] < previous - 1e-6:
            raise ValueError("强制对齐时间戳倒退")
        if word["end"] > duration + 0.1:
            raise ValueError("强制对齐时间戳超出音频时长")
        previous = word["end"]
    return repaired


def _align(aligner, audio: Path, text: str, duration: float) -> list[dict]:
    result = aligner.align(str(audio), text, language="zh")
    if result is None:
        raise ValueError("强制对齐未返回结果")
    raw = []
    for segment in result.segments:
        for word in getattr(segment, "words", []) or []:
            token = "".join(str(word.word).split())
            if token:
                raw.append({"text": token, "start": float(word.start), "end": float(word.end)})
    if not raw:
        raise ValueError("强制对齐没有返回词边界")
    words = _repair_words(raw, duration)

    cursor = 0
    for word in words:
        position = text.find(word["text"], cursor)
        if position < 0 or _WORD_CHAR.search(text[cursor:position]):
            raise ValueError("强制对齐结果与旁白原文不匹配")
        cursor = position + len(word["text"])
    if _WORD_CHAR.search(text[cursor:]):
        raise ValueError("强制对齐未覆盖完整旁白")
    return words


def _write_pcm16(path: Path, samples, sample_rate: int) -> None:
    import numpy as np
    pcm = (np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0) * 32767).round().astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, sample_rate, 0, "NONE", "not compressed"))
        stream.writeframes(pcm.tobytes())


def synthesize(text: str, voice: str, rate: str, output: Path, *, models_dir: Path) -> list[dict]:
    """合成单段中文旁白，写 24 kHz 单声道 PCM16 WAV 并返回词边界。"""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("旁白为空，无法合成")
    if _UNSUPPORTED.search(text):
        raise ValueError("Qwen3-TTS 后端暂不支持数字或拉丁字母旁白；请改写为中文口语或改用 edge-tts")
    if not re.search(r"[一-鿿]", text):
        raise ValueError("旁白没有可合成的中文内容")
    if re.search(r"\s", text):
        raise ValueError("Qwen3-TTS 当前要求旁白不含空白字符")

    speed = speed_for_rate(rate)
    paths = assets(models_dir, voice)
    torch, model, aligner, librosa, prompts = _loaded(paths)
    prompt = _prompt(torch, model, paths, prompts)
    ref_digest = voice_digest(models_dir, voice)

    torch.manual_seed(_seed(text, voice, ref_digest, speed))
    with torch.no_grad():
        wavs, sample_rate = model.generate_voice_clone(
            text=text, language=paths["language"], voice_clone_prompt=prompt)
    import numpy as np
    audio = np.asarray(wavs[0], dtype=np.float32).reshape(-1)
    if audio.size == 0 or not np.isfinite(audio).all():
        raise ValueError("Qwen3-TTS 没有生成有效音频")
    if abs(speed - 1.0) > 1e-9:
        audio = librosa.effects.time_stretch(audio, rate=speed).astype(np.float32)
    duration = float(audio.size) / int(sample_rate)

    output.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        aligned = Path(temporary) / "speech.wav"
        _write_pcm16(aligned, audio, int(sample_rate))
        words = _align(aligner, aligned, text, duration)

    _write_pcm16(output, audio, int(sample_rate))
    return words
