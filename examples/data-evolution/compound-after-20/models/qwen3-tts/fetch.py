"""按 models/qwen3-tts/registry.json 恢复并校验 Qwen3-TTS 模型。

模型与对齐模型二进制不入库。默认离线：从 M2V_TTS_CACHE、models/.cache 或
models/files 查找；只有显式 ``--download`` 才联网。参考音色属于作品资产，
只能校验，不能从模型仓库下载。

    python models/qwen3-tts/fetch.py --check --voice clone_tuixiu
    python models/qwen3-tts/fetch.py --restore --voice clone_tuixiu
    python models/qwen3-tts/fetch.py --download --voice clone_tuixiu
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = HERE.parent / "files"
CACHE = HERE.parent / ".cache"
REGISTRY = HERE / "registry.json"


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load() -> dict:
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"models/qwen3-tts/registry.json 无法读取：{exc}")
    if (data.get("schemaVersion") != 1 or data.get("backend") != "qwen3-tts"
            or not isinstance(data.get("files"), list)
            or not isinstance(data.get("voices"), list)
            or not isinstance(data.get("modelDir"), str)
            or not isinstance(data.get("alignerDir"), str)):
        raise SystemExit("models/qwen3-tts/registry.json：schemaVersion=1 且包含 backend、files、voices、modelDir、alignerDir")
    license_path = (HERE / str(data.get("license", ""))).resolve()
    if not license_path.is_relative_to(HERE.resolve()) or not license_path.is_file():
        raise SystemExit(f"模型许可文件不存在或越界：{data.get('license')}")
    for entry in data["files"]:
        for key in ("role", "file", "bytes", "sha256", "provider", "repo", "revision"):
            if key not in entry:
                raise SystemExit(f"模型登记缺少字段 {key}：{entry.get('file')}")
        _check_name(entry["file"])
        _check_hash(entry)
    for voice in data["voices"]:
        _check_name(voice.get("refAudio"))
        for key in ("voice", "refText", "language", "bytes", "sha256", "authorization"):
            if key not in voice:
                raise SystemExit(f"音色档案缺少字段 {key}：{voice.get('voice')}")
        _check_hash({"file": voice["refAudio"], "sha256": voice["sha256"]})
    return data


def _check_name(name) -> None:
    if (not isinstance(name, str) or not name or Path(name).is_absolute()
            or ".." in Path(name).parts or "\\" in name):
        raise SystemExit(f"模型登记路径非法：{name!r}")


def _check_hash(entry: dict) -> None:
    if (not isinstance(entry["sha256"], str) or len(entry["sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in entry["sha256"])):
        raise SystemExit(f"模型登记 sha256 非法：{entry['file']}")


def selected(registry: dict, voice: str | None) -> list[dict]:
    entries = list(registry["files"])
    if voice:
        matches = [v for v in registry["voices"] if v.get("voice") == voice]
        if not matches:
            raise SystemExit(f"登记中没有 Qwen3-TTS 音色：{voice}")
        profile = matches[0]
        entries.append({"role": "voice", "file": profile["refAudio"],
                        "bytes": profile["bytes"], "sha256": profile["sha256"],
                        "provider": "project"})
    return entries


def verify(path: Path, entry: dict) -> str | None:
    if not path.is_file():
        return "缺失"
    if path.stat().st_size != entry["bytes"]:
        return f"字节数不符（期望 {entry['bytes']}，实际 {path.stat().st_size}）"
    actual = digest(path)
    if actual != entry["sha256"]:
        return f"摘要不符（期望 {entry['sha256']}，实际 {actual}）"
    return None


def _safe(relative: str) -> Path:
    path = (FILES / relative).resolve()
    if not path.is_relative_to(FILES.resolve()):
        raise SystemExit(f"模型路径越界：{relative}")
    return path


def _candidates(entry: dict) -> list[Path]:
    places = []
    cache = os.environ.get("M2V_TTS_CACHE")
    if cache:
        places.append(Path(cache) / entry["file"])
    places += [CACHE / entry["file"], FILES / entry["file"]]
    return places


def _urls(entry: dict) -> list[str]:
    provider = entry.get("provider")
    repo, revision, file = entry["repo"], entry["revision"], entry["file"]
    if provider == "modelscope":
        base = os.environ.get("MODELSCOPE_ENDPOINT", "https://modelscope.cn/models").rstrip("/")
        return [f"{base}/{repo}/resolve/{revision}/{file}",
                f"{base}/{repo}/resolve/master/{file}"]
    if provider == "huggingface":
        base = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")
        return [f"{base}/{repo}/resolve/{revision}/{file}",
                f"{base}/{repo}/resolve/main/{file}"]
    return []


def _download(entry: dict) -> Path:
    urls = _urls(entry)
    if not urls:
        raise SystemExit(f"{entry['file']}：没有可用的下载来源")
    staged = CACHE / entry["file"]
    staged.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for url in urls:
        print(f"下载 {entry['file']}：{url}")
        try:
            with urllib.request.urlopen(url, timeout=180) as response, staged.open("wb") as out:
                shutil.copyfileobj(response, out)
        except Exception as exc:  # 尝试下一个镜像或 revision
            last = exc
            staged.unlink(missing_ok=True)
            continue
        problem = verify(staged, entry)
        if problem:
            staged.unlink(missing_ok=True)
            last = RuntimeError(f"下载后{problem}")
            continue
        return staged
    raise SystemExit(f"{entry['file']}：下载失败（{last}）")


def restore(entry: dict, *, download: bool) -> None:
    placed = _safe(entry["file"])
    if placed.is_file():
        problem = verify(placed, entry)
        if problem:
            raise SystemExit(f"{entry['file']}：已存在但{problem}；拒绝覆盖，请自行处理该文件")
        return
    if entry.get("provider") == "project":
        raise SystemExit(
            f"{entry['file']}：参考音色属于作品资产，缺失时不能从模型仓库恢复；"
            "请从作品来源重新导出并核对 sha256")
    source = None
    for candidate in _candidates(entry):
        if candidate.is_file():
            problem = verify(candidate, entry)
            if problem:
                raise SystemExit(f"{entry['file']}：找到 {candidate} 但{problem}；拒绝覆盖")
            source = candidate
            break
    if source is None and download:
        source = _download(entry)
    if source is None:
        raise SystemExit(
            f"{entry['file']}：缺少模型文件。请设置 M2V_TTS_CACHE、放入 {CACHE}，"
            "或确认有网络后使用 --download")
    placed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source, placed)
    print(f"ok  {entry['file']}")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description="恢复并校验 Qwen3-TTS 模型与对齐模型")
    parser.add_argument("--check", action="store_true", help="只校验，不复制或下载")
    parser.add_argument("--restore", action="store_true", help="从本地缓存恢复（默认）")
    parser.add_argument("--download", action="store_true", help="允许联网下载缺失文件")
    parser.add_argument("--voice", help="同时校验所选克隆音色，例如 clone_tuixiu")
    options = parser.parse_args(argv)
    if options.check and (options.restore or options.download):
        raise SystemExit("--check 不能与 --restore/--download 同时使用")
    registry = load()
    entries = selected(registry, options.voice)
    if options.check:
        problems = []
        for entry in entries:
            problem = verify(_safe(entry["file"]), entry)
            if problem:
                problems.append(f"{entry['file']}：{problem}")
        if problems:
            for problem in problems:
                print(f"fail {problem}", file=sys.stderr)
            raise SystemExit("Qwen3-TTS 模型未就绪；运行 python models/qwen3-tts/fetch.py --download" +
                             (f" --voice {options.voice}" if options.voice else ""))
        print(f"ok  Qwen3-TTS 模型已就绪（{len(entries)} 个文件）")
        return 0
    for entry in entries:
        restore(entry, download=options.download)
    return 0


if __name__ == "__main__":
    sys.exit(main())
