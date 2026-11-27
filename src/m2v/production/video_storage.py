"""作品存储的只读盘点及按清单执行。"""
from __future__ import annotations

import json
import logging
import os
import re
import stat
import subprocess
import time
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from m2v.core.recording_identity import recording_ended
from m2v.core.workspace import bundle_repo_root, content_root
from m2v.production.storage import locked

logger = logging.getLogger(__name__)

OWNER = re.compile(r"code-([1-9][0-9]*)-[a-z0-9_]{8}")
WORKER = re.compile(r"\.worker-([1-9][0-9]*)")
RECORDING_SETTLE_NS = 60 * 60 * 10**9
REVIEW_KEEP_NS = 24 * 60 * 60 * 10**9
REPORT_DIRECTORIES = (
    "outputs", "outputs/code-cache", "outputs/code-cache/.recordings", "outputs/review-pack",
    "outputs/qa", "outputs/samples", "outputs/candidates", "outputs/production", "work", "research",
    ".cache", "node_modules", ".venv", "models", "assets",
)


def _reparse(info) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _local(base: Path, path: Path) -> None:
    if not path.is_relative_to(base):
        raise M2VError(f"文件越界：{path}")
    for part in (path, *path.parents):
        if part == base.parent:
            break
        info = part.lstat()
        if _reparse(info) or stat.S_ISLNK(info.st_mode):
            raise M2VError(f"跳过符号链接或目录联接：{part}")


def _long_path(path: Path) -> str:
    value = str(path)
    if os.name != "nt" or value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    if len(value) >= 3 and value[1:3] == ":\\":
        return "\\\\?\\" + value
    return value


def _entries(directory: Path):
    # 旧示例的 pnpm 依赖和临时包可能超过 Windows MAX_PATH。
    stack = [(_long_path(directory), ())]
    while stack:
        source, relative = stack.pop()
        with os.scandir(source) as scan:
            for item in scan:
                info = item.stat(follow_symlinks=False)
                name = relative + (item.name,)
                if _reparse(info) or stat.S_ISLNK(info.st_mode):
                    yield name, info, "link"
                elif stat.S_ISDIR(info.st_mode):
                    yield name, info, "directory"
                    stack.append((item.path, name))
                elif stat.S_ISREG(info.st_mode):
                    yield name, info, "file"
                else:
                    yield name, info, "other"


def _git_files(root: Path) -> set[str]:
    probe = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-prefix"],
        capture_output=True, check=False,
    )
    if probe.returncode:
        if b"not a git repository" in probe.stderr:
            return set()
        raise M2VError(f"无法确认 Git 跟踪状态：{root}")
    files = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", "."],
        capture_output=True, check=False,
    )
    if files.returncode:
        raise M2VError(f"无法枚举 Git 跟踪文件：{root}")
    names = files.stdout.decode("utf-8").split("\0")
    return {name.casefold() for name in names if name}


def projects(explicit: list[str], content: str | None) -> list[Path]:
    repo = bundle_repo_root()
    candidates = [Path(path).expanduser().absolute() for path in explicit]
    if not explicit:
        workspace = content_root(content)
        roots = {(repo / "videos") if repo else None, (repo / "examples") if repo else None}
        if workspace is not None:
            roots.add(workspace / "videos")
        for parent in roots - {None}:
            if not parent.is_dir():
                continue
            _local(Path(parent.anchor), parent)
            for marker in parent.glob("*/*/project.json"):
                candidates.append(marker.parent)
    roots = set()
    for candidate in candidates:
        _local(Path(candidate.anchor), candidate)
        manifest = candidate / "project.json"
        if not manifest.is_file():
            raise M2VError(f"缺少 project.json：{candidate}")
        _local(candidate, manifest)
        roots.add(candidate.resolve())
    return sorted(roots)


def _stale_recording(path: Path, now: int) -> str | None:
    owner = OWNER.fullmatch(path.name)
    if not owner:
        return "录制目录命名未知"
    info = path.stat()
    if now - info.st_mtime_ns < RECORDING_SETTLE_NS:
        return "录制目录仍在保留期"
    if not recording_ended(int(owner[1]), path / ".owner", legacy_before_ns=getattr(info, "st_birthtime_ns", info.st_ctime_ns)):
        return "录制进程身份未确认退出"
    for piece in path.iterdir():
        if not piece.name.startswith(".worker-"):
            continue
        worker = WORKER.fullmatch(piece.name)
        attr = piece.lstat()
        if not worker or _reparse(attr) or not stat.S_ISREG(attr.st_mode):
            return "录制子进程记录未知"
        if not recording_ended(int(worker[1]), piece, legacy_before_ns=attr.st_mtime_ns):
            return "录制子进程身份未确认退出"
    return None



def _recording_references(root: Path) -> set[str]:
    base = root / "outputs"
    text_suffixes = {".md", ".json", ".jsonl"}
    sources = [path for directory in (root, base) for path in directory.iterdir()
               if path.suffix.lower() in text_suffixes]
    production = base / "production"
    if production.is_dir():
        _local(root, production)
        sources.extend(production.joinpath(*parts) for parts, _, kind in _entries(production)
                       if kind == "file" and Path(parts[-1]).suffix.lower() in text_suffixes)
    references = set()
    pattern = re.compile(rb"\.recordings[/\\]+(code-[1-9][0-9]*-[a-z0-9_]{8})")
    for path in sources:
        if path.is_file():
            _local(root, path)
            with path.open("rb") as file:
                for line in file:
                    references.update(match[1].decode("ascii") for match in pattern.finditer(line))
    return references


def _recording_entry(root: Path, path: Path, tracked: set[str], now: int, references: set[str]) -> dict:
    relative = path.relative_to(root).as_posix()
    _local(root, path)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        return {"path": relative, "skip": "录制条目不是普通目录"}
    rows, size = [], 0
    if (path / ".owner").exists() or (path / ".owner").is_symlink():
        _local(root, path / ".owner")
    skip = "录制目录仍有制作记录引用" if path.name in references else _stale_recording(path, now)
    for names, entry, kind in _entries(path):
        name = "/".join(names)
        if kind in {"link", "other"} or f"{relative}/{name}".casefold() in tracked:
            skip = "含链接、特殊文件或 Git 跟踪文件"
        if kind == "file":
            size += entry.st_size
        rows.append([name, kind, entry.st_size, entry.st_mtime_ns, entry.st_ctime_ns])
    if skip:
        return {"path": relative, "bytes": size, "skip": skip}
    return {
        "path": relative, "bytes": size, "reason": "中断采集的临时逐帧目录",
        "identity": fingerprint([info.st_ctime_ns, info.st_mtime_ns, sorted(rows)]),
    }


def inventory(root: Path) -> dict:
    sizes = dict.fromkeys(REPORT_DIRECTORIES, 0)
    total = 0
    skipped = 0
    for names, info, kind in _entries(root):
        if kind != "file":
            skipped += kind in {"link", "other"}
            continue
        total += info.st_size
        for depth in range(1, min(3, len(names) - 1) + 1):
            bucket = "/".join(names[:depth])
            if bucket in sizes:
                sizes[bucket] += info.st_size
    return {"bytes": total, "directories": {name: size for name, size in sizes.items() if size},
            "linksOrSpecialFiles": skipped}


def cleanup_plan(root: Path) -> dict:
    base = root / "outputs/code-cache/.recordings"
    entries = []
    if base.exists() or base.is_symlink():
        _local(root, base)
        tracked = _git_files(root)
        references = _recording_references(root)
        now = time.time_ns()
        for path in sorted(base.iterdir()):
            try:
                entries.append(_recording_entry(root, path, tracked, now, references))
            except (OSError, M2VError) as exc:
                entries.append({"path": path.relative_to(root).as_posix(), "skip": str(exc)})
    eligible = [entry for entry in entries if "identity" in entry]
    return {"project": str(root), "candidates": eligible,
            "skipped": [entry for entry in entries if "skip" in entry],
            "candidateBytes": sum(entry["bytes"] for entry in eligible),
            "planSha256": fingerprint({"project": str(root), "entries": eligible})}


def apply_cleanup(root: Path, plan_sha256: str) -> dict:
    import shutil

    with locked(root):
        plan = cleanup_plan(root)
        if plan["planSha256"] != plan_sha256:
            raise M2VError("存储清单已变化，请重新生成预览")
        removed = []
        skipped = list(plan["skipped"])
        tracked = _git_files(root)
        references = _recording_references(root) if plan["candidates"] else set()
        for entry in plan["candidates"]:
            target = root / entry["path"]
            try:
                current = _recording_entry(root, target, tracked, time.time_ns(), references)
                if entry != current:
                    raise M2VError("目录身份或进程状态已变化")
                _local(root, target)
                shutil.rmtree(_long_path(target))
                removed.append(entry)
            except (OSError, M2VError) as exc:
                skipped.append({"path": entry["path"], "skip": str(exc)})
    return {"project": str(root), "removed": removed, "skipped": skipped,
            "removedBytes": sum(entry["bytes"] for entry in removed)}


def reclaim_recordings(root: Path) -> None:
    """管理入口也维护既有独立运行时留下的录制临时目录。"""
    recordings = root / "outputs/code-cache/.recordings"
    if not recordings.is_dir() or not any(recordings.iterdir()):
        return
    try:
        plan = cleanup_plan(root)
        if plan["candidates"]:
            result = apply_cleanup(root, plan["planSha256"])
            logger.info("已回收录制临时文件 %d 字节", result["removedBytes"])
    except (M2VError, OSError, ValueError) as exc:
        logger.warning("暂缓清理录制临时文件：%s", exc)


def _review_links(root: Path) -> dict[str, set[str]]:
    """保留制作说明中直接指向单个文件的链接。报告里的逻辑路径由证据校验解析。"""
    notes = list(root.glob("*.md"))
    for folder in (root / "design", root / "outputs/production"):
        if folder.is_dir() and not folder.is_symlink() and not _reparse(folder.lstat()):
            notes.extend(path for path in folder.rglob("*.md") if "review-tasks" not in path.parts)
    notes.append(root / "outputs/visual-notes.md")
    result: dict[str, set[str]] = {}
    for note in notes:
        if not note.is_file():
            continue
        _local(root, note)
        for match in re.finditer(
            r"review-pack/([a-f0-9]{32})/([^\s<>\"')]+)", note.read_text(encoding="utf-8-sig")
        ):
            result.setdefault(match[1], set()).add(match[2])
    return result


def _imported_review_manifests(root: Path) -> dict[str, str]:
    """近期仍待独立评审的包保留在原位。已导入的报告须匹配封存账本。"""
    from . import ledger
    from .storage import local, read

    base = root / "outputs"
    if not (base / "production/workflow.json").is_file():
        return {}
    try:
        _local(root, base / "production/workflow.json")
        with ledger.query():
            events, errors = ledger.history(root)
            if errors:
                return {}
            result = {}
            for event in events:
                if event["type"] != "review":
                    continue
                data = event["data"]
                if not ledger.evidence_valid(root, data["receipts"]):
                    continue
                report = read(local(base, data["reportPath"]))
                result[report["packPath"]] = report["packSha256"]
            return result
    except (M2VError, OSError, ValueError, TypeError, KeyError):
        return {}


def review_plan(root: Path, *, imported_only: bool = False) -> dict:
    from m2v.core.delivery import digest

    from . import review_blobs
    from .storage import read

    base = root / "outputs/review-pack"
    if not base.exists():
        candidates, skipped = [], []
    else:
        _local(root, base)
        tracked = _git_files(root)
        named_links = _review_links(root)
        imported = _imported_review_manifests(root)
        candidates, skipped = [], []
        cutoff = time.time_ns() - REVIEW_KEEP_NS
        for pack in sorted(base.iterdir()):
            if not review_blobs.IDENTIFIER.fullmatch(pack.name):
                continue
            try:
                manifest = pack / "manifest.json"
                _local(root, manifest)
                manifest_sha = digest(manifest)
                is_imported = imported.get(manifest.relative_to(base.parent).as_posix()) == manifest_sha
                if not is_imported and (imported_only or manifest.stat().st_mtime_ns >= cutoff):
                    raise M2VError("保留尚未导入的观察目录")
                pack_manifest = read(manifest)
                if pack_manifest.get("reviewId") != pack.name:
                    raise M2VError("评审包身份与清单不一致")
                files = review_blobs.manifest_files(pack_manifest["files"])
                archived = review_blobs.index(pack, files)
                keep = named_links.get(pack.name, set())
                present = {"/".join(parts): info for parts, info, kind in _entries(pack) if kind == "file"}
                eligible = []
                for name, sha in files.items():
                    if name not in present:
                        if name not in archived:
                            review_blobs.file_for(pack, name, archived)
                        continue
                    if Path(name).suffix.lower() not in review_blobs.MEDIA:
                        continue
                    local_name = f"outputs/review-pack/{pack.name}/{name}"
                    if name in keep or local_name.casefold() in tracked:
                        keep.add(name)
                        continue
                    info = present[name]
                    eligible.append([name, sha, info.st_size, info.st_mtime_ns, info.st_ctime_ns])
                if eligible:
                    candidates.append({"id": pack.name, "files": len(eligible),
                                       "sourceBytes": sum(row[2] for row in eligible),
                                       "keep": sorted(keep), "manifestSha256": manifest_sha,
                                       "identity": fingerprint(eligible)})
            except (M2VError, OSError, ValueError, TypeError, KeyError) as exc:
                skipped.append({"id": pack.name, "skip": str(exc)})
    return {"project": str(root), "candidates": candidates, "skipped": skipped,
            "planSha256": fingerprint({"project": str(root), "compact": candidates})}


def apply_review_plan(root: Path, plan_sha256: str) -> dict:
    from . import dependencies, review_blobs

    with locked(root), dependencies.snapshot(fresh=True):
        plan = review_plan(root)
        if plan["planSha256"] != plan_sha256:
            raise M2VError("评审封存清单已变化，请重新生成预览")
        completed, skipped = [], list(plan["skipped"])
        for entry in plan["candidates"]:
            try:
                pack = root / "outputs/review-pack" / entry["id"]
                result = review_blobs.compact(pack, keep=set(entry["keep"]), planned=entry)
                completed.append({"id": entry["id"], **result})
            except (M2VError, OSError, ValueError, TypeError, KeyError) as exc:
                skipped.append({"id": entry["id"], "skip": str(exc)})
    saved = sum(row["logicalRemovedBytes"] - row["objectBytesAdded"] for row in completed)
    return {"project": str(root), "compacted": completed, "skipped": skipped, "savedBytes": saved}


def compact_older_reviews(root: Path) -> None:
    """新送审时分批补封存已导入报告的媒体，调用方持有制作写锁。"""
    from . import dependencies, review_blobs

    try:
        with dependencies.snapshot(fresh=True):
            plan = review_plan(root, imported_only=True)
            for entry in plan["candidates"][:2]:
                pack = root / "outputs/review-pack" / entry["id"]
                try:
                    review_blobs.compact(pack, keep=set(entry["keep"]), planned=entry)
                except (M2VError, OSError, ValueError, TypeError, KeyError) as exc:
                    logger.warning("暂缓封存评审包 %s：%s", entry["id"], exc)
    except (M2VError, OSError, ValueError) as exc:
        logger.warning("暂缓评审媒体轮转：%s", exc)


def add_parser(sub) -> None:
    parser = sub.add_parser("storage", help="盘点和清理作品存储")
    parser.add_argument("action", choices=("inventory", "plan", "clean", "compact-plan", "compact"))
    parser.add_argument("--project", action="append", default=[], help="作品目录，可重复；默认盘点仓库作品和示例")
    parser.add_argument("--content-root", help="同时纳入该内容根下的 videos")
    parser.add_argument("--plan-sha256", help="clean 或 compact 确认单个作品的当前清单摘要")


def dispatch(args) -> int:
    roots = projects(args.project, args.content_root)
    if args.action in {"clean", "compact"}:
        if len(roots) != 1 or len(args.project) != 1 or not args.plan_sha256:
            raise M2VError(f"storage {args.action} 需要一个显式 --project 和已核对的 --plan-sha256")
        apply = apply_cleanup if args.action == "clean" else apply_review_plan
        result = [apply(roots[0], args.plan_sha256)]
    elif args.action == "plan":
        result = [cleanup_plan(root) for root in roots]
    elif args.action == "compact-plan":
        result = [review_plan(root) for root in roots]
    else:
        result = [{"project": str(root), **inventory(root)} for root in roots]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
