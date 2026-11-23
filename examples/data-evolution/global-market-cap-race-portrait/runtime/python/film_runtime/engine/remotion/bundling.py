"""本地composition构建与完整缓存；CLI读取本工程配置，缓存命中仍执行源码与输入检查。"""

from __future__ import annotations

import logging
import os
import shutil
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import film_runtime.core.source_policy as source_policy
import film_runtime.engine.bundle_cache as bundle_cache

from .inputs import ENTRY_POINT, build_input_fingerprint, build_inputs
from .process import _BUNDLE_TIMEOUT_S, RemotionError, _run, program

#: 日志名保持拆包前的 `film_runtime.engine.remotion`：订阅方与输出格式都不需要改。
logger = logging.getLogger(__package__)


@dataclass(frozen=True)
class BundleOutcome:
    """一次打包的结果，包含产物位置与缓存判定。

    返回值里带上缓存状态是刻意的：性能报告要标明命中与否，日志也要——否则
    「这次快是因为缓存命中」与「这次本来就快」在输出里长得一样。
    """

    #: 可直接交给元数据读取与渲染的 bundle 目录
    path: Path
    #: `hit` / `miss` / `disabled`
    cache_status: str
    cache_key: str | None
    cache_detail: str
    #: 键计算与完整性复核耗时
    cache_seconds: float
    #: 实际打包耗时（命中时为 0）
    build_seconds: float
    #: 本次用于算键的构建输入指纹；调用方可复用它写成片溯源，
    #: 不必再对同一批文件哈希一遍（禁用缓存时为 None）
    input_fingerprint: dict | None = None


@contextmanager
def bundle(
    *,
    web_dir: Path,
    out_dir: Path,
    storyboard_path: str | Path,
    content_root: str | Path | None = None,
    workspace_root: str | Path | None = None,
    timeout_s: float = _BUNDLE_TIMEOUT_S,
    cache: bool = True,
    cache_identity: str | Path | None = None,
) -> Iterator[BundleOutcome]:
    """在调用方读取静态构建期间登记使用状态，防止并发淘汰。

    走 CLI 而不是 `@remotion/bundler` 的 `bundle()`：CLI 会读 `remotion.config.ts`，
    因此 `@/` 本地别名与样式 只在一处配置。程序化打包不会读那个配置，
    两条路径各配一遍迟早会漂移，而漂移的表现是「Studio 里对、渲染出来错」。

    启用缓存（默认）时，产物落进被忽略的 `.cache/m2v-bundles/<键>/`：
    键覆盖源码可达集合、`public/` 静态资产、打包配置与运行版本，
    命中前逐文件复核完整性。`cache=False`（CLI 的 `--no-bundle-cache`）时每次都
    打到调用方给的临时目录，用于诊断与基准对照。

    无论命中与否，**源码确定性扫描都会执行**：
    缓存省掉的是打包，不是门禁。
    """
    web = Path(web_dir)
    marker = None
    try:
        # 共享构建锁只覆盖打包和缓存登记，后续渲染可以并发。
        with bundle_cache.generation_lock(web):
            violations = source_policy.scan(build_inputs())
            if violations:
                detail = "\n".join(item.render(web) for item in violations)
                raise RemotionError(f"composition 源码违反确定性约束：\n{detail}")
            if cache:
                outcome = _cached_bundle(web, out_dir, storyboard_path=cache_identity or storyboard_path,
                                         workspace_root=workspace_root, timeout_s=timeout_s)
                if outcome.path != out_dir:
                    assert outcome.cache_key is not None
                    marker = bundle_cache.retain(web, outcome.cache_key)
            else:
                seconds = _bundle_into(web, out_dir, timeout_s)
                logger.info("打包 composition 用了 %.1f 秒（本次禁用缓存）", seconds)
                outcome = BundleOutcome(out_dir, "disabled", None, "本次禁用缓存", 0.0, seconds)
        yield outcome
    finally:
        if marker is not None:
            bundle_cache.release(marker)


def _cached_bundle(web: Path, out_dir: Path, *, storyboard_path: str | Path,
                   workspace_root: str | Path | None, timeout_s: float) -> BundleOutcome:
    started = time.monotonic()
    # 同一份构建输入指纹也用于成片溯源。
    fingerprint = build_input_fingerprint(workspace_root=workspace_root)
    key, detail = bundle_cache.compute_key(web_dir=web, base_files=fingerprint["files"],
                                           storyboard_path=storyboard_path)
    entry = bundle_cache.entry_dir(web, key)
    path = bundle_cache.bundle_path(entry)
    local = bundle_cache.local_cache(web)
    active = bundle_cache.active_keys(web) if local else set()
    if local:
        bundle_cache.cleanup_stale(web)
        ok, reason = bundle_cache.verify(entry, key)
        if ok:
            bundle_cache.prune(web, key=key, active=active)
            logger.info("打包缓存命中（%s）：%s", key[:12], reason)
            return BundleOutcome(path, "hit", key, reason, time.monotonic() - started, 0.0, fingerprint)
    else:
        reason = "构建缓存目录不可用"

    if not local or key in active or not bundle_cache.prune(web, key=key, active=active):
        # 另一个渲染仍在读此键，或缓存没有可回收的位置。
        reason = f"{reason}。本次使用临时构建"
        path = out_dir
        seconds = _bundle_into(web, path, timeout_s)
    else:
        with bundle_cache.key_lock(web, key):
            temporary = entry.parent / f".tmp-{key[:12]}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
            temporary.mkdir()
            try:
                seconds = _bundle_into(web, bundle_cache.bundle_path(temporary), timeout_s)
                bundle_cache.write_manifest(temporary, key=key, detail=detail)
                bundle_cache.publish(temporary, entry, key=key)
            except BaseException:
                shutil.rmtree(temporary, ignore_errors=True)
                raise
        logger.info("打包完成并写入缓存（%s，%.1f 秒）", key[:12], seconds)
    return BundleOutcome(path, "miss", key, reason, max(time.monotonic() - started - seconds, 0.0),
                         seconds, fingerprint)


def _bundle_into(web: Path, out_dir: Path, timeout_s: float) -> float:
    """真正调用 `remotion bundle`，返回耗时。产物目录必须是新的。"""
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    _run(
        [program("npx"), "remotion", "bundle", ENTRY_POINT, "--out-dir", str(out_dir)],
        cwd=web,
        timeout_s=timeout_s,
        what="打包 composition",
    )
    if not out_dir.is_dir():
        raise RemotionError(f"打包 composition 后没有产物目录：{out_dir}")
    return time.monotonic() - started
