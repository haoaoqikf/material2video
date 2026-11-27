"""按 models/qwen3-tts/registry.json 恢复并校验 Qwen3-TTS 模型。

模型与对齐模型二进制不入库。同一磁盘从本机摘要缓存硬链接恢复，
跨磁盘自动复制。仍可从 M2V_TTS_CACHE、models/.cache 或 models/files 查找；只有显式 ``--download`` 才联网。参考音色属于作品资产，
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
import tempfile
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


def _shared(entry: dict) -> Path:
    override = os.environ.get("M2V_QWEN3_MODEL_STORE")
    if override:
        base = Path(override).expanduser()
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"]) / "material2video" / "qwen3-tts"
    else:
        cache_root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
        base = cache_root / "material2video" / "qwen3-tts"
    sha = entry["sha256"]
    return base / "objects" / sha[:2] / sha


def _stage(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".weight-", dir=directory)
    os.close(fd)
    return Path(name)


def _download(entry: dict, target: Path) -> None:
    urls = _urls(entry)
    if not urls:
        raise SystemExit(f"{entry['file']}：没有可用的下载来源")
    last = None
    for url in urls:
        print(f"下载 {entry['file']}：{url}")
        try:
            with urllib.request.urlopen(url, timeout=180) as response, target.open("wb") as out:
                shutil.copyfileobj(response, out)
        except OSError as exc:
            last = exc
            continue
        problem = verify(target, entry)
        if not problem:
            return
        last = RuntimeError(f"下载后{problem}")
    raise SystemExit(f"{entry['file']}：下载失败（{last}）")


def _require(path: Path, entry: dict) -> None:
    problem = verify(path, entry)
    if problem:
        raise SystemExit(f"{entry['file']}：{path} {problem}；拒绝覆盖")


def _publish(source: Path, target: Path, entry: dict, *, portable: bool = False) -> bool:
    """先校验暂存内容，再原子替换目标。同盘优先硬链接，跨盘保留普通副本。"""
    pending = _stage(target.parent)
    linked = False
    try:
        if not portable:
            pending.unlink()
            try:
                os.link(source, pending)
                linked = True
            except OSError:
                pass
        if not linked:
            shutil.copyfile(source, pending)
        _require(pending, entry)
        os.replace(pending, target)
    finally:
        pending.unlink(missing_ok=True)
    return linked


def restore(entry: dict, *, download: bool, portable: bool = False) -> None:
    placed = _safe(entry["file"])
    if entry.get("provider") == "project":
        _require(placed, entry)
        return
    if placed.is_file():
        _require(placed, entry)
        if portable:
            if placed.stat().st_nlink > 1:
                _publish(placed, placed, entry, portable=True)
            return
    shared = _shared(entry)
    if shared.is_file():
        _require(shared, entry)
    else:
        source = next((p for p in _candidates(entry) if p.is_file()), None)
        if source is not None:
            if source != placed:
                _require(source, entry)
            _publish(source, shared, entry)
        elif download:
            staged = _stage(shared.parent)
            try:
                _download(entry, staged)
                os.replace(staged, shared)
            finally:
                staged.unlink(missing_ok=True)
        else:
            raise SystemExit(f"{entry['file']}：缺少模型文件；设置 M2V_TTS_CACHE 或使用 --download")

    if placed.is_file() and os.path.samefile(shared, placed):
        return
    # 不用跨盘复制覆盖一份现有且已核验的本地权重。
    if placed.is_file() and placed.stat().st_dev != shared.stat().st_dev:
        return
    linked = _publish(shared, placed, entry, portable=portable)
    print(f"ok  {entry['file']}（{'共享' if linked else '独立副本'}）")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description="恢复并校验 Qwen3-TTS 模型与对齐模型")
    parser.add_argument("--check", action="store_true", help="只校验，不复制或下载")
    parser.add_argument("--restore", action="store_true", help="从本地缓存恢复（默认）")
    parser.add_argument("--download", action="store_true", help="允许联网下载缺失文件")
    parser.add_argument("--portable", action="store_true", help="恢复可独立编辑的模型副本")
    parser.add_argument("--project-root", type=Path, help="用当前恢复脚本处理指定的存量作品")
    parser.add_argument("--voice", help="同时校验所选克隆音色，例如 clone_tuixiu")
    options = parser.parse_args(argv)
    if options.check and (options.restore or options.download or options.portable):
        raise SystemExit("--check 不能与 --restore/--download 同时使用")
    if options.project_root is not None:
        global HERE, FILES, CACHE, REGISTRY
        HERE = options.project_root.resolve() / "models/qwen3-tts"
        FILES, CACHE, REGISTRY = HERE.parent / "files", HERE.parent / ".cache", HERE / "registry.json"
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
        restore(entry, download=options.download, portable=options.portable)
    return 0


if __name__ == "__main__":
    sys.exit(main())
