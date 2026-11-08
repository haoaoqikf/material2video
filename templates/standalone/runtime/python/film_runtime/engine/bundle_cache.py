"""本地打包缓存：完整构建键、产物完整性检查、锁与原子发布。

为什么要有这一层：一次成片合成里，打包是**与作品无关**的重活——同一份
composition 源码在切换作品、重复导出、并发对照时被反复重打。缓存的目的不是
「少算一点」，而是「不重复做已经确定结果的事」，因此它的正确性前提是：
**键必须覆盖一切会改变产物的输入，且产物本身必须可验证完整**。

三条刻意写死的规则：

1. **键覆盖完整构建输入。** 除源码摘要，还绑定公共静态资产、构建配置和运行版本，
   避免源码没变但构建环境已变时复用旧产物。
2. **先验证再复用。** 命中判定不是「目录存在」，而是逐文件复核摘要与大小；
   上次构建被中断留下的半成品必须判为未命中并重建。
3. **临时目录构建 + 原子发布。** 直接把产物写进缓存目录，会让中断留下一个
   看起来可用、实际残缺的条目；因此先建在临时目录、写完清单后整体改名发布。
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import sys
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import film_runtime.engine.perf as perf
from film_runtime.core.errors import VideoError
from film_runtime.core.fingerprints import file_digest, fingerprint
from film_runtime.core import security

logger = logging.getLogger(__name__)

#: 缓存根（相对作品根）。`.cache/` 已在 `.gitignore` 中，不进版本控制。
CACHE_ROOT = Path(".cache/m2v-bundles")

#: 缓存条目格式版本。键或完整性口径变化时递增：旧条目整体失效而不是被误用。
CACHE_VERSION = 2

#: 清单文件名（缓存条目内）。
MANIFEST_NAME = "manifest.json"

#: 打包产物在缓存条目内的子目录名。
BUNDLE_DIRNAME = "bundle"

#: 打包配置：不写进源码 import 图，却直接决定产物。
BUILD_CONFIG_INPUTS = (
    "remotion.config.ts",
    "tsconfig.json",
    "package.json",
    "pnpm-lock.yaml",
)

#: 公共静态资产目录（相对作品根）。Remotion 打包会整体复制它。
PUBLIC_DIR = "public"

#: 等待同一把键的构建完成；打包按分钟计，给足余量。
KEY_LOCK_TIMEOUT_S = 1800.0

#: 共享前端工作区构建锁的等待时限。
GENERATION_LOCK_TIMEOUT_S = 3600.0

#: 锁文件超过这个时长认为持有者已经死亡（崩溃残留），可以清理。
LOCK_STALE_S = 6 * 3600.0

#: 残留临时目录的清理阈值。
TMP_STALE_S = 24 * 3600.0

_LOCK_POLL_S = 0.2


class BundleCacheError(VideoError):
    """缓存不可用（等待超时、目录被占）或缓存状态损坏。"""


def cache_root(web_dir: str | Path) -> Path:
    return Path(web_dir) / CACHE_ROOT


def entry_dir(web_dir: str | Path, key: str) -> Path:
    return cache_root(web_dir) / key


def bundle_path(entry: Path) -> Path:
    return entry / BUNDLE_DIRNAME


def _relative_key(web_dir: Path, path: Path) -> str:
    """缓存键里的文件标识：相对作品根 的 posix 路径，跨平台稳定。"""
    try:
        return path.resolve().relative_to(web_dir.resolve()).as_posix()
    except ValueError:  # 仓库外的文件（外置内容根的作品模块）：用绝对路径
        return path.resolve().as_posix()


def _digest_files(web_dir: Path, paths: list[Path]) -> dict[str, str]:
    return {_relative_key(web_dir, path): file_digest(path) for path in sorted(paths)}


def _public_files(web_dir: Path) -> list[Path]:
    directory = web_dir / PUBLIC_DIR
    if not directory.is_dir():
        return []
    return [path for path in sorted(directory.rglob("*")) if path.is_file()]


def compute_key(
    *,
    web_dir: str | Path,
    base_files: dict[str, str],
    storyboard_path: str | Path | None = None,
) -> tuple[str, dict]:
    """计算完整构建键，返回 (摘要, 组成说明)。

    `base_files` 是共享源码可达集合的摘要表（与成片溯源同一份口径）；函数再补上
    额外影响构建的输入：`public/` 静态资产、打包配置，
    以及打包器与 Node 的运行版本。
    """
    web = Path(web_dir)
    public = _digest_files(web, _public_files(web))
    config = _digest_files(web, [web / name for name in BUILD_CONFIG_INPUTS if (web / name).is_file()])
    parts = {
        "version": CACHE_VERSION,
        "inputs": dict(sorted(base_files.items())),
        "public": public,
        "config": config,
        "runtime": {
            "node": perf.node_version(),
            # 用稳定材料路径标识本次构建的归属。
            "storyboard": str(Path(storyboard_path).resolve()) if storyboard_path else None,
        },
    }
    key = fingerprint(parts)
    detail = {
        "inputs": len(parts["inputs"]),
        "public": len(public),
        "config": sorted(config),
    }
    return key, detail


def _list_files(root: Path) -> list[Path]:
    return [path for path in sorted(root.rglob("*")) if path.is_file()]


def write_manifest(entry: Path, *, key: str, detail: dict) -> None:
    """在临时条目里写下完成标记与逐文件摘要。

    清单最后写：写它之前进程被中断，条目就没有 `complete` 标记，
    下次复核直接判未命中并重建——而不是把半成品当成可用缓存。
    """
    files: dict[str, dict[str, object]] = {}
    for path in _list_files(entry):
        relative = path.relative_to(entry).as_posix()
        if relative == MANIFEST_NAME:
            continue
        files[relative] = {"sha256": file_digest(path), "size": path.stat().st_size}
    payload = {
        "version": CACHE_VERSION,
        "key": key,
        "complete": True,
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parts": detail,
        "files": files,
    }
    (entry / MANIFEST_NAME).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def verify(entry: Path, key: str) -> tuple[bool, str]:
    """逐文件复核缓存条目；返回 (是否可用, 说明)。

    说明里写**为什么**不可用：只说「未命中」时，人无法区分「输入确实变了」与
    「缓存被错误地写坏了」，而这两种情况的修法完全不同。
    """
    manifest = entry / MANIFEST_NAME
    if not manifest.is_file():
        return False, "没有完成标记"
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, f"完成标记读不出来（{exc}）"
    if not isinstance(payload, dict):
        return False, "完成标记格式不对"
    if payload.get("version") != CACHE_VERSION:
        return False, f"缓存版本是 {payload.get('version')!r}，当前为 {CACHE_VERSION}"
    if payload.get("key") != key:
        return False, "键不匹配"
    if payload.get("complete") is not True:
        return False, "上次构建没有完成"
    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        return False, "产物清单为空"
    if f"{BUNDLE_DIRNAME}/index.html" not in files:
        return False, "缺打包入口 index.html"
    for relative, record in files.items():
        path = entry / relative
        if not path.is_file():
            return False, f"产物缺失 {relative}"
        if not isinstance(record, dict):
            return False, f"产物清单项格式不对 {relative}"
        size = record.get("size")
        if isinstance(size, int) and path.stat().st_size != size:
            return False, f"产物大小不符 {relative}"
        if record.get("sha256") != file_digest(path):
            return False, f"产物摘要不符 {relative}"
    return True, f"命中并复核了 {len(files)} 个产物文件"


def publish(tmp: Path, target: Path, *, key: str) -> None:
    """把临时条目整体发布到缓存位置。

    Windows 下 `os.replace` 不能覆盖非空目录，因此目标存在时先判它是否可用：
    可用就丢弃本次临时产物（并发进程已经发布了同一把键），不可用就清掉再发布。
    持有同一把键的锁时，这条路径只可能发生在「上次崩溃留下残条目」的情形。
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        ok, _reason = verify(target, key)
        if ok:
            shutil.rmtree(tmp, ignore_errors=True)
            return
        shutil.rmtree(target, ignore_errors=True)
    try:
        security.deliver_directory(tmp, target)
    except OSError:
        if not target.is_dir():
            raise
        shutil.rmtree(tmp, ignore_errors=True)


def _cleanup(parent: Path, *, prefix: str, older_than_s: float) -> None:
    """清理上次崩溃留下的临时目录。删不掉不影响本次构建。"""
    if not parent.is_dir():
        return
    cutoff = time.time() - older_than_s
    for path in parent.glob(f"{prefix}*"):
        try:
            if path.stat().st_mtime < cutoff:
                shutil.rmtree(path, ignore_errors=True)
        except OSError:  # pragma: no cover - 并发清理时的正常竞态
            continue


def cleanup_stale(web_dir: str | Path) -> None:
    _cleanup(cache_root(web_dir), prefix=".tmp-", older_than_s=TMP_STALE_S)


@contextlib.contextmanager
def _exclusive(lock_file: Path, *, what: str, timeout_s: float) -> Iterator[None]:
    """按文件独占创建实现跨进程互斥；超时即报错，不静默继续。"""
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    while True:
        try:
            handle = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if _reclaim_stale(lock_file):
                continue
            if time.monotonic() - started > timeout_s:
                raise BundleCacheError(
                    f"等待{what}超过 {timeout_s:.0f} 秒仍未获得锁（{lock_file}）。"
                    f"如确认没有其它构建在运行，可删除该锁文件后重试。"
                )
            time.sleep(_LOCK_POLL_S)
            continue
        try:
            os.write(handle, f"{os.getpid()}\n".encode())
        finally:
            os.close(handle)
        break
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            lock_file.unlink()


def _reclaim_stale(lock_file: Path) -> bool:
    try:
        age = time.time() - lock_file.stat().st_mtime
    except OSError:  # pragma: no cover - 刚被释放
        return False
    owner = None
    try:
        owner = int(lock_file.read_text(encoding="ascii").strip())
    except (OSError, UnicodeError, ValueError):
        pass
    dead_owner = owner is not None and not _process_is_alive(owner)
    if not dead_owner and age < LOCK_STALE_S:
        return False
    reason = f"持有进程 {owner} 已退出" if dead_owner else f"已存在 {age:.0f} 秒"
    logger.warning("清理过期锁文件 %s（%s）", lock_file, reason)
    with contextlib.suppress(OSError):
        lock_file.unlink()
        return True
    return False


#: Win32 错误码：`OpenProcess` 打不开目标进程时，用来区分「进程不存在」。
_ERROR_INVALID_PARAMETER = 87


def _process_is_alive_after_open_failure(error: int) -> bool:
    """`OpenProcess` 失败后的存活判定：只有「pid 不存在」才算已退出。

    权限不足（`ERROR_ACCESS_DENIED`）或其它错误说明进程可能存在，一律按存活
    处理，交给锁年龄兜底，避免误回收仍然有效的锁。
    """
    return error != _ERROR_INVALID_PARAMETER


def _windows_process_is_alive(pid: int) -> bool:
    """用 Win32 进程句柄的等待语义判断存活。

    这里**不能**用 `os.kill(pid, 0)`：Windows 上 `signal.CTRL_C_EVENT` 就是 `0`，
    该调用会变成 `GenerateConsoleCtrlEvent(CTRL_C_EVENT, pid)`，向控制台进程组
    发送 Ctrl+C，把当前进程和同一控制台的其它进程一起打断。
    """
    import ctypes
    from ctypes import wintypes

    SYNCHRONIZE = 0x00100000
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    WAIT_TIMEOUT = 0x00000102

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(
        SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid
    )
    if not handle:
        return _process_is_alive_after_open_failure(ctypes.get_last_error())
    try:
        # 已结束的进程对象立即进入有信号状态；仍在运行的只会等到超时。
        return kernel32.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT
    finally:
        kernel32.CloseHandle(handle)


def _process_is_alive(pid: int) -> bool:
    """判断锁持有进程是否仍存活，不把权限拒绝当成进程死亡。"""
    if sys.platform == "win32":
        return _windows_process_is_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


@contextlib.contextmanager
def generation_lock(web_dir: str | Path) -> Iterator[None]:
    """串行保护共享前端工作区的打包，避免并发改写工具缓存。"""
    with _exclusive(
        cache_root(web_dir) / ".generation.lock",
        what="前端工作区打包",
        timeout_s=GENERATION_LOCK_TIMEOUT_S,
    ):
        yield


@contextlib.contextmanager
def key_lock(web_dir: str | Path, key: str) -> Iterator[None]:
    """同一把键只允许一个构建，其余进程等待而不是各建一份。"""
    with _exclusive(
        cache_root(web_dir) / f"{key}.lock", what=f"缓存键 {key[:12]} 的构建", timeout_s=KEY_LOCK_TIMEOUT_S
    ):
        yield
