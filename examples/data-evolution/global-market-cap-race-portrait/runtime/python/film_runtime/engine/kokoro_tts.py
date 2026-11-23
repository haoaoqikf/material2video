"""Kokoro v1.1-zh 本地配音后端。

只在作品声明 ``tts.backend = "kokoro"`` 时加载；torch 等依赖是可选的。
模型权重按作品内 ``models/registry.json`` 登记的大小与 SHA256 校验，
时间戳来自模型时长预测与中文前端 token，不估算。
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import wave
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from film_runtime.core.errors import VideoError

logger = logging.getLogger(__name__)

REPO_ID = "hexgrad/Kokoro-82M-v1.1-zh"
REVISION = "01e7505bd6a7a2ac4975463114c3a7650a9f7218"
SAMPLE_RATE = 24000
SEED_VERSION = 1
VOICE_PATTERN = re.compile(r"^z[fm]_\d{3}$")
_UNSUPPORTED = re.compile(r"[0-9０-９A-Za-z]")

#: 同一次准备里复用模型与音色，避免每段重新加载 313 MB 权重。
_LOADED: dict[str, object] = {}
_VERIFIED: set[tuple[str, str]] = set()


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "missing"


def versions() -> dict:
    """缓存键使用的后端环境；版本缺失不伪装成已安装。"""
    return {"kokoro": _package_version("kokoro"), "misaki": _package_version("misaki"),
            "torch": _package_version("torch"), "modelRevision": REVISION,
            "seedVersion": SEED_VERSION}


def _import_backend():
    try:
        import torch
        from kokoro import KModel
        from kokoro.pipeline import KPipeline
        from misaki.zh import ZHG2P
    except ImportError as exc:  # pragma: no cover - 依赖缺失路径由环境决定
        raise VideoError(
            "Kokoro 后端依赖未安装：请在作品内执行 uv sync --extra kokoro "
            f"（或安装 kokoro、misaki[zh]）；原始错误：{exc}"
        ) from exc
    return torch, KModel, KPipeline, ZHG2P


def _load_registry(models_dir: Path) -> dict:
    path = models_dir / "registry.json"
    if not path.is_file():
        raise VideoError(f"缺少 Kokoro 模型登记：{path}；请在作品内运行 models/fetch.py --download")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise VideoError(f"Kokoro 模型登记无法读取：{path}：{exc}") from exc
    if (data.get("schemaVersion") != 1 or data.get("repo") != REPO_ID
            or data.get("revision") != REVISION or not isinstance(data.get("files"), list)):
        raise VideoError(f"Kokoro 模型登记与后端不一致：{path}")
    return data


def _entry(registry: dict, *, role: str, voice: str | None = None) -> dict:
    for entry in registry["files"]:
        if entry.get("role") == role and (voice is None or entry.get("voice") == voice):
            return entry
    raise VideoError(f"Kokoro 模型登记缺少 {role}" + (f"：{voice}" if voice else ""))


def _verify(path: Path, entry: dict) -> None:
    key = (str(path), entry["sha256"])
    if key in _VERIFIED:
        return
    if not path.is_file():
        raise VideoError(
            f"Kokoro 模型文件缺失：{path}；请在作品内运行 python models/fetch.py --download")
    if path.stat().st_size != entry["bytes"]:
        raise VideoError(f"Kokoro 模型文件大小不符：{path}（期望 {entry['bytes']}）")
    # 313 MB 权重不能整文件读入内存；校验只流式读取一次。
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != entry["sha256"]:
        raise VideoError(
            f"Kokoro 模型文件摘要不符：{path}（期望 {entry['sha256']}，实际 {digest}）；"
            "拒绝使用，请检查或重新恢复")
    _VERIFIED.add(key)


def assets(models_dir: Path, voice: str) -> dict:
    """校验并返回模型、config 与所选音色路径。"""
    if not VOICE_PATTERN.fullmatch(voice):
        raise ValueError(f"Kokoro 音色必须是形如 zf_027 的中文音色名，实际为 {voice!r}")
    registry = _load_registry(models_dir)
    result = {}
    for role, name in (("model", None), ("config", None), ("voice", voice)):
        entry = _entry(registry, role=role, voice=name)
        file = entry.get("file")
        if not isinstance(file, str) or Path(file).is_absolute() or ".." in Path(file).parts:
            raise VideoError(f"Kokoro 模型登记路径非法：{file!r}")
        path = models_dir / "files" / file
        files_root = (models_dir / "files").resolve()
        if not path.resolve().is_relative_to(files_root):
            raise VideoError(f"Kokoro 模型文件经链接指向模型目录外：{path}")
        _verify(path, entry)
        result[role] = path
    return result


def ensure_assets(models_dir: Path, voice: str) -> None:
    """准备前一次性校验，失败在合成前暴露。"""
    assets(models_dir, voice)


def voice_names() -> list[dict]:
    """列出中文音色；只读文件，不联网。"""
    path = Path(__file__).with_name("kokoro_voices.json")
    if not path.is_file():
        raise VideoError(f"Kokoro 音色清单缺失：{path}；请恢复开发包数据")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise VideoError(f"Kokoro 音色清单无法读取：{path}：{exc}") from exc
    voices = data.get("voices")
    if not isinstance(voices, list) or not voices:
        raise VideoError(f"Kokoro 音色清单为空或格式不符：{path}")
    return voices


def speed_for_rate(rate: str) -> float:
    """edge-tts 的百分比语速映射为 Kokoro speed；+20% → 1.2。"""
    match = re.fullmatch(r"([+-])(\d{1,2})%", rate)
    if not match:
        raise ValueError(f"语速必须是 −50% 至 +50% 的有符号百分比，实际为 {rate!r}")
    value = int(match.group(2)) / 100
    speed = 1 + value if match.group(1) == "+" else 1 - value
    return round(speed, 4)


def _seed(text: str, voice: str, speed: float) -> int:
    material = f"{SEED_VERSION}|{voice}|{speed:.4f}|{text}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:4], "big")


def _english_unsupported(word: str) -> str:
    raise ValueError(f"Kokoro 后端暂不支持英文旁白：{word!r}；请改写为中文或改用 edge-tts")


def _loaded(models_dir: Path, voice: str):
    torch, KModel, _KPipeline, ZHG2P = _import_backend()
    key = f"{models_dir.resolve()}|{voice}"
    if key in _LOADED:
        return _LOADED[key]
    logger.info("加载 Kokoro 模型：%s（音色 %s）", models_dir, voice)
    paths = assets(models_dir, voice)
    config = json.loads(paths["config"].read_text(encoding="utf-8"))
    model = KModel(repo_id=REPO_ID, config=config, model=str(paths["model"])).to("cpu").eval()
    pack = torch.load(paths["voice"], map_location="cpu", weights_only=True)
    g2p = ZHG2P(version="1.1", en_callable=_english_unsupported)
    _LOADED[key] = (torch, model, pack, g2p, _KPipeline)
    return _LOADED[key]


def synthesize(text: str, voice: str, rate: str, output: Path, *, models_dir: Path) -> list[dict]:
    """合成单段中文旁白，写 24 kHz 单声道 PCM16 WAV 并返回词边界。"""
    if _UNSUPPORTED.search(text):
        raise ValueError("Kokoro 后端暂不支持数字或英文旁白；请改写为中文口语或改用 edge-tts")
    speed = speed_for_rate(rate)
    torch, model, pack, g2p, pipeline = _loaded(models_dir, voice)

    import cn2an
    from misaki.zh import ZHG2P

    normalized = ZHG2P.map_punctuation(cn2an.transform(text, "an2cn"))
    phonemes, tokens = g2p.frontend(normalized)
    if not phonemes:
        raise ValueError("旁白没有可合成的中文内容")
    if len(phonemes) > 510:
        raise ValueError("单段旁白过长，请拆分为更短的口播段")

    torch.manual_seed(_seed(text, voice, speed))
    with torch.no_grad():
        result = model(phonemes, pack[len(phonemes) - 1], speed, return_output=True)
    audio = result.audio.detach().cpu().float().reshape(-1)
    duration = float(audio.numel()) / SAMPLE_RATE

    pipeline.join_timestamps(tokens, result.pred_dur)
    words = []
    for token in tokens:
        if getattr(token, "tag", None) == "x":
            continue
        start, end = getattr(token, "start_ts", None), getattr(token, "end_ts", None)
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            raise ValueError("Kokoro 未返回完整词时间戳，无法生成同步字幕")
        words.append({"text": token.text, "start": float(start), "end": float(end)})

    if not words:
        raise ValueError("Kokoro 没有生成可用的词时间戳")
    joined = "".join(str(token.text) for token in tokens).replace(" ", "")
    if joined != normalized.replace(" ", ""):
        raise ValueError("Kokoro 分词结果与旁白不一致，拒绝生成可能错位的字幕")
    previous = 0.0
    for word in words:
        if word["start"] < previous - 1e-6 or word["end"] <= word["start"]:
            raise ValueError("Kokoro 词时间戳倒退或区间非法")
        if word["end"] > duration + 0.05:
            raise ValueError("Kokoro 词时间戳超出音频时长")
        previous = word["end"]

    pcm = (audio.clamp(-1.0, 1.0) * 32767).round().to(torch.int16)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as stream:
        stream.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
        stream.writeframes(pcm.numpy().tobytes())
    return words
