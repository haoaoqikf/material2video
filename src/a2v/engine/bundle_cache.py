"""本地打包缓存：完整构建键、产物完整性检查、锁与原子发布。

为什么要有这一层：一次成片合成里，打包是**与作品无关**的重活——同一份
composition 源码在切换作品、重复导出、并发对照时被反复重打。缓存的目的不是
「少算一点」，而是「不重复做已经确定结果的事」，因此它的正确性前提是：
**键必须覆盖一切会改变产物的输入，且产物本身必须可验证完整**。

三条刻意写死的规则：

1. **键不等于成片溯源指纹。** 溯源指纹有意排除全局生成索引（`.gen/`）：它是
   按当前作品派生的临时文件，记进去会让其它作品的产物被判「落后」。缓存恰好
   相反——生成的场景清单、Tailwind 内容、`public/` 静态资产、打包配置和依赖
   版本都会改变 bundle，漏一项就会交付上一份作品的画面，而这种错误**没有症状**。
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
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import a2v.engine.perf as perf
from a2v.core.errors import A2VError
from a2v.core.fingerprints import file_digest, fingerprint

logger = logging.getLogger(__name__)

#: 缓存根（相对 `web/`）。`.cache/` 已在 `.gitignore` 中，不进版本控制。
CACHE_ROOT = Path(".cache/a2v-bundles")

#: 缓存条目格式版本。键或完整性口径变化时递增：旧条目整体失效而不是被误用。
CACHE_VERSION = 1

#: 清单文件名（缓存条目内）。
MANIFEST_NAME = "manifest.json"

#: 打包产物在缓存条目内的子目录名。
BUNDLE_DIRNAME = "bundle"

#: 生成物：由当前作品派生、会进入 bundle，但不在溯源指纹里。
GENERATED_INPUTS = (
    ".gen/scene-manifest.json",
    ".gen/active-scenes.ts",
    ".gen/active-tailwind.css",
)

#: 打包配置：不写进源码 import 图，却直接决定产物。
BUILD_CONFIG_INPUTS = (
    "remotion.config.ts",
    "tsconfig.json",
    "package.json",
    "pnpm-lock.yaml",
)

#: 公共静态资产目录（相对 `web/`）。Remotion 打包会整体复制它。
PUBLIC_DIR = "public"

#: 等待同一把键的构建完成；打包按分钟计，给足余量。
KEY_LOCK_TIMEOUT_S = 1800.0

#: 等待全局 `.gen` 生成到构建结束；串行保护会把不同作品的打包排成一队。
GENERATION_LOCK_TIMEOUT_S = 3600.0

#: 锁文件超过这个时长认为持有者已经死亡（崩溃残留），可以清理。
LOCK_STALE_S = 6 * 3600.0

#: 残留临时目录的清理阈值。
TMP_STALE_S = 24 * 3600.0

_LOCK_POLL_S = 0.2


class BundleCacheError(A2VError):
    """缓存不可用（等待超时、目录被占）或缓存状态损坏。"""


def cache_root(web_dir: str | Path) -> Path:
    return Path(web_dir) / CACHE_ROOT


def entry_dir(web_dir: str | Path, key: str) -> Path:
    return cache_root(web_dir) / key


def bundle_path(entry: Path) -> Path:
    return entry / BUNDLE_DIRNAME


def _relative_key(web_dir: Path, path: Path) -> str:
    """缓存键里的文件标识：相对 `web/` 的 posix 路径，跨平台稳定。"""
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
    溯源**有意排除**的那几类输入：生成清单、`public/` 静态资产、打包配置，
    以及打包器与 Node 的运行版本。
    """
    web = Path(web_dir)
    generated = _digest_files(web, [web / name for name in GENERATED_INPUTS if (web / name).is_file()])
    public = _digest_files(web, _public_files(web))
    config = _digest_files(web, [web / name for name in BUILD_CONFIG_INPUTS if (web / name).is_file()])
    parts = {
        "version": CACHE_VERSION,
        "inputs": dict(sorted(base_files.items())),
        "generated": generated,
        "public": public,
        "config": config,
        "runtime": {
            "node": perf.node_version(),
            # 分镜路径进入键：代码场景清单按当前作品生成，切换作品必须换键。
            # （清单内容本身也在 `generated` 里，这条只是把「哪支作品」也写进键。）
            "storyboard": str(Path(storyboard_path).resolve()) if storyboard_path else None,
        },
    }
    key = fingerprint(parts)
    detail = {
        "inputs": len(parts["inputs"]),
        "generated": sorted(generated),
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
        os.replace(tmp, target)
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
    if age < LOCK_STALE_S:
        return False
    logger.warning("清理过期锁文件 %s（已存在 %.0f 秒）", lock_file, age)
    with contextlib.suppress(OSError):
        lock_file.unlink()
        return True
    return False


@contextlib.contextmanager
def generation_lock(web_dir: str | Path) -> Iterator[None]:
    """串行保护「生成 `.gen` 清单 → 打包完成」这一段。

    `.gen/` 是全局共享的临时目录：A 作品生成清单、B 作品紧接着覆盖它，A 打出来
    的就是 B 的画面（反之亦然），而缓存会把这份污染固化下来。因此从生成之前
    一直锁到打包结束。
    """
    with _exclusive(
        cache_root(web_dir) / ".generation.lock",
        what="全局代码场景清单与打包",
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
