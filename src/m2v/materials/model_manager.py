"""Explicit model restoration and offline integrity checks.

The checked-in registry is the only model identity authority. Runtime backends never
use a hub id, mutable revision or an unverified cached installation as a fallback.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
from typing import Callable

from m2v.materials.errors import MaterialError

_LOG = logging.getLogger(__name__)
_REGISTRY = Path(__file__).with_name("model_registry.json")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_path(root: Path, relative: str) -> Path:
    part = PurePosixPath(relative)
    if (not relative or "\\" in relative or ":" in relative or part.is_absolute()
            or any(p in {".", ".."} for p in relative.split("/"))):
        raise MaterialError("invalid-request", "模型登记包含非法相对路径", stage="models")
    target = root.joinpath(*part.parts)
    # resolve() alone would hide a junction already present in an ancestor.
    for location in (target, *target.parents):
        if location.exists() or location.is_symlink():
            info = location.lstat()
            if location.is_symlink() or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise MaterialError("security-blocked", "模型路径不得经过符号链接或目录联接", stage="models")
    return target


def _load_registry(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if set(raw) != {"schemaVersion", "models", "software"} or type(raw["schemaVersion"]) is not int or raw["schemaVersion"] != 1:
            raise ValueError("schema")
        if not isinstance(raw["models"], dict) or not raw["models"]:
            raise ValueError("models")
        for name, model in raw["models"].items():
            if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
                raise ValueError("name")
            if not _REVISION.fullmatch(model["revision"]) or not model["license"] or not model["files"]:
                raise ValueError("identity")
            seen = set()
            for item in model["files"]:
                _safe_path(Path.cwd(), item["path"])
                if item["path"] in seen or not _SHA256.fullmatch(item["sha256"]):
                    raise ValueError("file identity")
                if type(item["bytes"]) is not int or item["bytes"] <= 0:
                    raise ValueError("size")
                seen.add(item["path"])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise MaterialError("invalid-request", "模型 registry 无效，必须含固定 revision、文件大小及 SHA256", stage="models") from exc
    return raw


class ModelManager:
    """Manage one explicitly selected model root, without implicit global state.

    ``prepare`` is the sole network operation. ``verify``, ``path``, ``identity``,
    ``list`` and ``doctor`` do not import inference packages or access the network.
    A downloader can be injected for deterministic offline restoration tests; its
    contract is ``downloader(model_spec, file_spec, destination) -> None``.
    """

    def __init__(self, root: Path, *, registry_path: Path | None = None):
        self.root = Path(root).absolute()
        self.registry = _load_registry(Path(registry_path) if registry_path else _REGISTRY)
        self.registry_digest = hashlib.sha256(json.dumps(self.registry, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _spec(self, name: str) -> dict:
        try:
            return self.registry["models"][name]
        except KeyError as exc:
            raise MaterialError("invalid-request", f"未知模型 {name}；可用项：{', '.join(self.registry['models'])}", stage="models") from exc

    def identity(self, name: str) -> dict:
        spec = self._spec(name)
        # Return a fresh JSON value: callers cannot mutate the manager authority.
        return json.loads(json.dumps({"name": name, "repoId": spec["repoId"], "revision": spec["revision"],
            "license": spec["license"], "preprocessing": spec["preprocessing"],
            "files": [{"path": x["path"], "sha256": x["sha256"]} for x in spec["files"]]}))

    def list(self) -> list[dict]:
        results = []
        for name, spec in self.registry["models"].items():
            missing, invalid = [], []
            for item in spec["files"]:
                path = _safe_path(self.root, f"{name}/{item['path']}")
                if not path.is_file():
                    missing.append(item["path"])
                elif path.stat().st_size != item["bytes"]:
                    invalid.append(item["path"])
            results.append({"name": name, "repoId": spec["repoId"], "revision": spec["revision"],
                "license": spec["license"], "bytes": sum(x["bytes"] for x in spec["files"]),
                "present": not missing, "sizeValid": not invalid, "hashVerified": False,
                "missing": missing, "invalidSize": invalid, "extra": spec["extra"]})
        return results

    def verify(self, name: str) -> dict:
        spec = self._spec(name)
        _LOG.info("Verify material model %s revision=%s", name, spec["revision"])
        for item in spec["files"]:
            path = _safe_path(self.root, f"{name}/{item['path']}")
            if not path.is_file():
                raise MaterialError("model-missing", f"模型 {name} 缺少 {item['path']}；请显式运行 models prepare", stage="models")
            if path.stat().st_size != item["bytes"] or _hash(path) != item["sha256"]:
                raise MaterialError("hash-mismatch", f"模型 {name} 文件摘要不符：{item['path']}；请显式 prepare --repair", stage="models")
        return {"name": name, "verified": True, "identity": self.identity(name)}

    def path(self, name: str) -> Path:
        self.verify(name)
        return _safe_path(self.root, name)

    def prepare(self, name: str, *, repair: bool = False,
                downloader: Callable[[dict, dict, Path], None] | None = None) -> dict:
        """Download fixed public model files and publish only verified bytes.

        Existing valid files are reused. Unexpected bytes are never silently
        accepted or overwritten unless this explicit call requests ``repair``.
        Downloads go to a private staging directory; no signed URL is serialized.
        """
        spec = self._spec(name)
        directory = _safe_path(self.root, name)
        directory.mkdir(parents=True, exist_ok=True)
        download = downloader or self._download
        required = sum(x["bytes"] for x in spec["files"])
        if shutil.disk_usage(self.root).free < required + 256 * 1024 * 1024:
            raise MaterialError("resource-limit", f"准备 {name} 的可用磁盘空间不足", stage="models")
        restored = []
        for item in spec["files"]:
            target = _safe_path(self.root, f"{name}/{item['path']}")
            if target.is_file():
                if target.stat().st_size == item["bytes"] and _hash(target) == item["sha256"]:
                    continue
                if not repair:
                    raise MaterialError("hash-mismatch", f"模型 {name} 已有文件不符；显式 repair 才能替换", stage="models")
            target.parent.mkdir(parents=True, exist_ok=True)
            _LOG.info("Restore material model %s file=%s bytes=%s", name, item["path"], item["bytes"])
            # The destination is inside the explicit root; private temporary
            # names are not part of the persistent model identity.
            with tempfile.TemporaryDirectory(prefix=".prepare-", dir=self.root) as tmp:
                staged = Path(tmp) / "artifact"
                try:
                    download(spec, item, staged)
                    if not staged.is_file() or staged.stat().st_size != item["bytes"] or _hash(staged) != item["sha256"]:
                        raise MaterialError("hash-mismatch", f"下载模型 {name} 文件校验失败：{item['path']}", stage="models")
                    # Recheck the path after network work, not just before it.
                    target = _safe_path(self.root, f"{name}/{item['path']}")
                    os.replace(staged, target)
                except MaterialError:
                    raise
                except Exception as exc:
                    _LOG.warning("Model restoration failed name=%s type=%s", name, type(exc).__name__)
                    # Hub errors often embed signed redirect URLs or tokens.
                    raise MaterialError("network-unavailable", f"模型 {name} 恢复失败（{type(exc).__name__}），可重试", stage="models", retryable=True) from None
            restored.append(item["path"])
        result = self.verify(name)
        result["restored"] = restored
        return result

    def _download(self, spec: dict, item: dict, destination: Path) -> None:
        try:
            from huggingface_hub import hf_hub_download
        except ImportError as exc:
            raise MaterialError("dependency-missing", "请安装对应素材模型 extra（含 huggingface-hub）", stage="models") from exc
        # An explicit public-model restore must not pick up a personal HF token.
        cached = hf_hub_download(repo_id=item.get("repoId", spec["repoId"]),
            revision=item.get("revision", spec["revision"]), filename=item.get("filename", item["path"]),
            cache_dir=str(self.root / ".hub-cache"), token=False,
            local_files_only=False, etag_timeout=30)
        shutil.copyfile(cached, destination)

    def doctor(self) -> dict:
        dependencies = {}
        for package in self.registry["software"]:
            try:
                version = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                version = None
            expected = self.registry["software"][package]["version"]
            dependencies[package] = {"installed": version, "expected": expected, "matches": version == expected}
        return {"models": self.list(), "dependencies": dependencies,
            "networkTested": False, "runtimeInferenceTested": False,
            "note": "文件存在/依赖已安装不等于模型摘要或真实推理通过；verify 才检查完整摘要"}
