"""按 models/registry.json 恢复并校验 Kokoro 模型。

模型二进制不入库。默认离线：从 M2V_TTS_CACHE、models/.cache 或 models/files
查找；只有显式 ``--download`` 才联网。``--voice`` 只恢复所选中文音色，
省略时只处理模型与 config。

    python models/fetch.py --check --voice zf_027
    python models/fetch.py --restore --voice zf_027
    python models/fetch.py --download --voice zf_027
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
REGISTRY = HERE / "registry.json"
FILES = HERE / "files"
CACHE = HERE / ".cache"


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def digest(path: Path) -> str:
    # 模型权重 313 MB，不能整文件读入内存。
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load() -> dict:
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"models/registry.json 无法读取：{exc}")
    if (data.get("schemaVersion") != 1 or not isinstance(data.get("files"), list)
            or not isinstance(data.get("repo"), str) or not isinstance(data.get("revision"), str)):
        raise SystemExit("models/registry.json：schemaVersion 必须为 1，并包含 repo、revision 与 files")
    license_path = (HERE / str(data.get("license", ""))).resolve()
    if not license_path.is_relative_to(HERE.resolve()) or not license_path.is_file():
        raise SystemExit(f"模型许可文件不存在或越界：{data.get('license')}")
    roles = {"model", "config", "voice"}
    for entry in data["files"]:
        if entry.get("role") not in roles:
            raise SystemExit(f"模型登记 role 非法：{entry.get('role')!r}")
        for key in ("file", "bytes", "sha256"):
            if key not in entry:
                raise SystemExit(f"模型登记缺少字段 {key}：{entry.get('file')}")
        if entry["role"] == "voice" and not isinstance(entry.get("voice"), str):
            raise SystemExit(f"音色登记缺少 voice：{entry.get('file')}")
        name = entry["file"]
        if (not isinstance(name, str) or not name or Path(name).is_absolute()
                or ".." in Path(name).parts or "\\" in name):
            raise SystemExit(f"模型登记路径非法：{name!r}")
        if (not isinstance(entry["sha256"], str) or len(entry["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in entry["sha256"])):
            raise SystemExit(f"模型登记 sha256 非法：{name}")
    return data


def selected(registry: dict, voice: str | None) -> list[dict]:
    entries = [e for e in registry["files"] if e["role"] in {"model", "config"}]
    if voice:
        matches = [e for e in registry["files"] if e["role"] == "voice" and e["voice"] == voice]
        if not matches:
            raise SystemExit(f"登记中没有 Kokoro 音色：{voice}")
        entries += matches
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


def _safe(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(FILES.resolve()) and resolved != FILES.resolve():
        raise SystemExit(f"模型路径越界：{path}")
    return resolved


def _candidates(entry: dict) -> list[Path]:
    places = []
    cache = os.environ.get("M2V_TTS_CACHE")
    if cache:
        places.append(Path(cache) / entry["file"])
    places += [CACHE / entry["file"], FILES / entry["file"]]
    return places


def _download(entry: dict, registry: dict) -> Path:
    endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")
    url = f"{endpoint}/{registry['repo']}/resolve/{registry['revision']}/{entry['file']}"
    staged = CACHE / entry["file"]
    staged.parent.mkdir(parents=True, exist_ok=True)
    print(f"下载 {entry['file']}：{url}")
    with urllib.request.urlopen(url, timeout=120) as response, staged.open("wb") as out:
        shutil.copyfileobj(response, out)
    problem = verify(staged, entry)
    if problem:
        staged.unlink(missing_ok=True)
        raise SystemExit(f"{entry['file']}：下载后{problem}；已删除该缓存")
    return staged


def restore(entry: dict, registry: dict, *, download: bool) -> None:
    placed = _safe(FILES / entry["file"])
    if placed.is_file():
        problem = verify(placed, entry)
        if problem:
            raise SystemExit(f"{entry['file']}：已存在但{problem}；拒绝覆盖，请自行处理该文件")
        return
    source = None
    for candidate in _candidates(entry):
        if candidate.is_file():
            problem = verify(candidate, entry)
            if problem:
                raise SystemExit(f"{entry['file']}：找到 {candidate} 但{problem}；拒绝覆盖")
            source = candidate
            break
    if source is None and download:
        source = _download(entry, registry)
    if source is None:
        raise SystemExit(
            f"{entry['file']}：缺少模型文件。请设置 M2V_TTS_CACHE、放入 {CACHE}，"
            "或确认有网络后使用 --download")
    placed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, placed)
    print(f"ok  {entry['file']}")


def check(entries: list[dict]) -> list[str]:
    problems = []
    for entry in entries:
        problem = verify(FILES / entry["file"], entry)
        if problem:
            problems.append(f"{entry['file']}：{problem}")
    return problems


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description="恢复并校验 Kokoro 模型")
    parser.add_argument("--check", action="store_true", help="只校验，不复制或下载")
    parser.add_argument("--restore", action="store_true", help="从本地缓存恢复（默认）")
    parser.add_argument("--download", action="store_true", help="允许联网下载缺失文件")
    parser.add_argument("--voice", help="只处理所选中文音色，例如 zf_027")
    options = parser.parse_args(argv)
    if options.check and (options.restore or options.download):
        raise SystemExit("--check 不能与 --restore/--download 同时使用")
    # --restore --download 同时出现是允许的：download 只表示允许联网补齐。
    registry = load()
    entries = selected(registry, options.voice)
    if options.check:
        problems = check(entries)
        if problems:
            for problem in problems:
                print(f"fail {problem}", file=sys.stderr)
            raise SystemExit("Kokoro 模型未就绪；运行 python models/fetch.py --download" +
                             (f" --voice {options.voice}" if options.voice else ""))
        print(f"ok  Kokoro 模型已就绪（{len(entries)} 个文件）")
        return 0
    for entry in entries:
        restore(entry, registry, download=options.download)
    return 0


if __name__ == "__main__":
    sys.exit(main())
