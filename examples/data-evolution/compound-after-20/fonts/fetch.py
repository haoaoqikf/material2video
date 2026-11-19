"""按 fonts/registry.json 恢复并校验字体。

字体二进制不入库。默认完全离线：从 M2V_FONT_CACHE、fonts/.cache、fonts/files
或目标位置查找；只有显式 `--download` 且登记了下载地址时才联网。

    python fonts/fetch.py --check
    python fonts/fetch.py
    python fonts/fetch.py --download
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
ROOT = HERE.parent
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> list[dict]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != 1 or not isinstance(data.get("fonts"), list):
        raise SystemExit("fonts/registry.json：schemaVersion 必须为 1，且必须包含 fonts 列表")
    seen: set[str] = set()
    for entry in data["fonts"]:
        for key in ("id", "file", "source", "version", "bytes", "sha256", "license", "targets"):
            if key not in entry:
                raise SystemExit(f"字体登记缺少字段 {key}：{entry.get('id') or entry}")
        if entry["id"] in seen:
            raise SystemExit(f"字体 id 重复：{entry['id']}")
        seen.add(entry["id"])
        if len(entry["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in entry["sha256"]):
            raise SystemExit(f"{entry['id']}：sha256 必须是 64 位小写十六进制")
        name = entry["file"]
        if (not isinstance(name, str) or not name or Path(name).name != name
                or "/" in name or "\\" in name or ".." in Path(name).parts):
            raise SystemExit(f"{entry['id']}：file 必须是字体目录内的纯文件名")
        license = (HERE / entry["license"]).resolve()
        if not license.is_relative_to(HERE.resolve()) or not license.is_file():
            raise SystemExit(f"{entry['id']}：许可文件不存在或越界 {entry['license']}")
    return data["fonts"]


def target_paths(entry: dict) -> list[Path]:
    paths = []
    for value in entry["targets"]:
        target = (ROOT / value).resolve()
        if not target.is_relative_to(ROOT):
            raise SystemExit(f"{entry['id']}：恢复目标越界 {value}")
        paths.append(target)
    return paths


def candidates(entry: dict) -> list[Path]:
    places = []
    cache = os.environ.get("M2V_FONT_CACHE")
    if cache:
        places.append(Path(cache) / entry["file"])
    places += [CACHE / entry["file"], FILES / entry["file"], *target_paths(entry)]
    return places


def verify(path: Path, entry: dict) -> str | None:
    if not path.is_file():
        return "缺失"
    if path.stat().st_size != entry["bytes"]:
        return f"字节数不符（期望 {entry['bytes']}，实际 {path.stat().st_size}）"
    actual = digest(path)
    if actual != entry["sha256"]:
        return f"摘要不符（期望 {entry['sha256']}，实际 {actual}）"
    return None


def source_for(entry: dict, *, download: bool) -> Path | None:
    for path in candidates(entry):
        if path.is_file():
            problem = verify(path, entry)
            if problem:
                raise SystemExit(f"{entry['id']}：找到 {path} 但{problem}；拒绝覆盖，请自行处理该文件")
            return path
    if download:
        url = entry.get("download")
        if not url:
            raise SystemExit(
                f"{entry['id']}：未登记下载地址。请把 {entry['file']} 放入 "
                f"M2V_FONT_CACHE 或 {CACHE} 后重试")
        CACHE.mkdir(parents=True, exist_ok=True)
        staged = CACHE / entry["file"]
        print(f"下载 {entry['id']}：{url}")
        with urllib.request.urlopen(url, timeout=60) as response, staged.open("wb") as out:
            shutil.copyfileobj(response, out)
        problem = verify(staged, entry)
        if problem:
            staged.unlink(missing_ok=True)
            raise SystemExit(f"{entry['id']}：下载后{problem}；已删除该缓存")
        return staged
    return None


def _safe_files_directory() -> None:
    resolved_root = ROOT.resolve()
    if FILES.is_symlink() or not FILES.resolve().is_relative_to(resolved_root):
        raise SystemExit(f"字体目录经链接指向作品外：{FILES}")


def _safe_font_file(path: Path) -> None:
    if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise SystemExit(f"字体文件经链接指向作品外：{path}")


def restore(entry: dict, *, download: bool) -> None:
    source = source_for(entry, download=download)
    if source is None:
        raise SystemExit(
            f"{entry['id']}：缺少 {entry['file']}。请把它放入 M2V_FONT_CACHE 或 {CACHE}，"
            "或确认有网络后使用 --download（仅登记了下载地址的字体）")
    FILES.mkdir(parents=True, exist_ok=True)
    _safe_files_directory()
    placed = FILES / entry["file"]
    _safe_font_file(placed)
    if not placed.is_file():
        shutil.copyfile(source, placed)
    for target in target_paths(entry):
        _safe_font_file(target)
        if target.is_file():
            problem = verify(target, entry)
            if problem:
                raise SystemExit(f"{entry['id']}：目标 {target} 已存在且{problem}；拒绝覆盖")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(placed, target)
    print(f"ok  {entry['id']}: {entry['file']} -> {', '.join(entry['targets']) or 'fonts/files'}")


def check(entries: list[dict]) -> list[str]:
    problems = []
    for entry in entries:
        placed = FILES / entry["file"]
        _safe_font_file(placed)
        problem = verify(placed, entry)
        if problem:
            problems.append(f"{entry['id']} fonts/files/{entry['file']}: {problem}")
        for target in target_paths(entry):
            problem = verify(target, entry)
            if problem:
                problems.append(f"{entry['id']} {target.relative_to(ROOT)}: {problem}")
    return problems


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验，不写文件")
    parser.add_argument("--download", action="store_true", help="缓存缺失时允许联网下载")
    options = parser.parse_args(argv)
    entries = load()
    if options.check:
        problems = check(entries)
        for problem in problems:
            print("缺失 " + problem)
        print("字体就绪" if not problems else f"缺少 {len(problems)} 项；运行 uv run python fonts/fetch.py")
        return 0 if not problems else 1
    for entry in entries:
        restore(entry, download=options.download)
    problems = check(entries)
    if problems:
        for problem in problems:
            print("失败 " + problem)
        return 1
    print(f"字体恢复完成：{len(entries)} 项")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
