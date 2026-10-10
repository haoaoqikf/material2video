"""本地打包缓存：完整构建键、完整性复核、锁与原子发布。

对应 openspec 变更 `optimize-final-video-render` 的任务 2.1 与 2.2。
打包本身用替身顶掉（真打包按分钟计、还需要 Node 与浏览器），这里验证的是
**判定口径**：键覆盖了哪些输入、残缺产物会不会被复用、失败会不会留下残件、
以及缓存命中时门禁是否照常执行。
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from a2v import bundle_cache, perf, remotion
from a2v.errors import A2VError


@pytest.fixture
def web(tmp_path, monkeypatch):
    """一个最小 web 工程目录 + 可控的「打包」替身。"""
    directory = tmp_path / "web"
    (directory / "src").mkdir(parents=True)
    (directory / "public").mkdir()
    (directory / ".gen").mkdir()
    (directory / "src" / "index.ts").write_text("// entry\n", encoding="utf-8")
    (directory / "remotion.config.ts").write_text("export default {};\n", encoding="utf-8")
    (directory / "package.json").write_text('{"name": "web"}\n', encoding="utf-8")
    (directory / "public" / "icon.svg").write_text("<svg/>\n", encoding="utf-8")
    (directory / ".gen" / "active-scenes.ts").write_text("export default [];\n", encoding="utf-8")
    storyboard = tmp_path / "storyboard.json"
    storyboard.write_text('{"version": 4, "schemaVersion": 4}\n', encoding="utf-8")

    # 键里要记 Node 版本；测试不该为一次 `node --version` 付进程开销
    monkeypatch.setattr(perf, "node_version", lambda: "v22.0.0")

    state = {"prepare": 0, "scan": 0, "build": 0, "base": {f"web/src/index.ts": "digest-1"}}
    monkeypatch.setattr(
        remotion,
        "prepare_composition_entry",
        lambda **kwargs: state.__setitem__("prepare", state["prepare"] + 1)
        or directory / ".gen" / "active-scenes.ts",
    )

    def scan(files):
        state["scan"] += 1
        return []

    monkeypatch.setattr(remotion, "source_policy", SimpleNamespace(scan=scan))
    monkeypatch.setattr(remotion, "build_inputs", lambda *args, **kwargs: [directory / "src" / "index.ts"])
    monkeypatch.setattr(
        remotion,
        "build_input_fingerprint",
        lambda *args, **kwargs: {"files": dict(state["base"]), "digest": "x"},
    )

    def fake_build(web_dir, out_dir, timeout_s):
        state["build"] += 1
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text("<html></html>\n", encoding="utf-8")
        (out_dir / "bundle.js").write_text("console.log(1)\n", encoding="utf-8")
        return 0.5

    monkeypatch.setattr(remotion, "_bundle_into", fake_build)
    return SimpleNamespace(
        dir=directory, storyboard=storyboard, state=state, tmp=tmp_path, build=fake_build
    )


def _bundle(web, **kwargs):
    options = {
        "web_dir": web.dir,
        "out_dir": web.tmp / "out" / "bundle",
        "storyboard_path": web.storyboard,
        "content_root": web.tmp,
    }
    options.update(kwargs)
    return remotion.bundle(**options)


# ---------------------------------------------------------------- 键的覆盖


def _key(web, base=None):
    key, _detail = bundle_cache.compute_key(
        web_dir=web.dir, base_files=base or {"web/src/index.ts": "digest-1"}, storyboard_path=web.storyboard
    )
    return key


def test_key_covers_generated_manifests_public_assets_and_build_config(web):
    """溯源指纹排除的几类输入必须进缓存键，否则会交付上一份作品的画面。"""
    baseline = _key(web)
    (web.dir / ".gen" / "active-scenes.ts").write_text("export default [1];\n", encoding="utf-8")
    assert _key(web) != baseline, "生成的场景清单变了，键必须变"

    scenes = _key(web)
    (web.dir / ".gen" / "active-tailwind.css").write_text(".a{}", encoding="utf-8")
    assert _key(web) != scenes, "生成的样式清单变了，键必须变"

    styles = _key(web)
    (web.dir / "public" / "icon.svg").write_text("<svg width='1'/>\n", encoding="utf-8")
    assert _key(web) != styles, "public 静态资产变了，键必须变"

    assets = _key(web)
    (web.dir / "package.json").write_text('{"name": "web", "x": 1}\n', encoding="utf-8")
    assert _key(web) != assets, "打包配置变了，键必须变"


def test_key_covers_shared_source_and_dependency_lock(web):
    first = _key(web)
    assert _key(web, {"web/src/index.ts": "digest-2"}) != first, "共享源码变了，键必须变"
    (web.dir / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n", encoding="utf-8")
    assert _key(web) != first, "依赖版本变了，键必须变"


def test_key_is_stable_for_the_same_inputs(web):
    assert _key(web) == _key(web)


# ---------------------------------------------------------------- 复用与重建


def test_second_bundle_hits_the_cache_and_skips_packing(web):
    first = _bundle(web)
    assert first.cache_status == "miss" and web.state["build"] == 1
    assert (first.path / "index.html").is_file()

    second = _bundle(web)
    assert second.cache_status == "hit"
    assert web.state["build"] == 1, "命中缓存时不得重新打包"
    assert second.path == first.path
    assert second.build_seconds == 0.0
    assert "命中" in second.cache_detail


def test_cache_miss_when_a_shared_source_file_changes(web):
    _bundle(web)
    web.state["base"] = {"web/src/index.ts": "digest-2"}
    again = _bundle(web)
    assert again.cache_status == "miss"
    assert web.state["build"] == 2


def test_damaged_cache_is_rebuilt_instead_of_reused(web):
    first = _bundle(web)
    # 产物被截断：大小与摘要都不符，必须判未命中
    (bundle_cache.bundle_path(bundle_cache.entry_dir(web.dir, first.cache_key)) / "bundle.js").write_text(
        "corrupted\n", encoding="utf-8"
    )
    again = _bundle(web)
    assert again.cache_status == "miss"
    assert web.state["build"] == 2
    assert (again.path / "bundle.js").read_text(encoding="utf-8").startswith("console.log")


def test_cache_without_completion_marker_is_rebuilt(web):
    """上次构建被中断：清单没写成，条目必须判未命中。"""
    first = _bundle(web)
    (bundle_cache.entry_dir(web.dir, first.cache_key) / bundle_cache.MANIFEST_NAME).unlink()
    again = _bundle(web)
    assert again.cache_status == "miss"
    assert web.state["build"] == 2


def test_corrupt_manifest_is_not_trusted(web):
    first = _bundle(web)
    manifest = bundle_cache.entry_dir(web.dir, first.cache_key) / bundle_cache.MANIFEST_NAME
    manifest.write_text("{ 不是 JSON", encoding="utf-8")
    again = _bundle(web)
    assert again.cache_status == "miss"


def test_verify_names_the_file_that_is_wrong(web):
    first = _bundle(web)
    entry = bundle_cache.entry_dir(web.dir, first.cache_key)
    ok, reason = bundle_cache.verify(entry, first.cache_key)
    assert ok, reason
    (bundle_cache.bundle_path(entry) / "bundle.js").unlink()
    ok, reason = bundle_cache.verify(entry, first.cache_key)
    assert not ok and "bundle.js" in reason, reason


def test_failed_build_leaves_no_broken_entry_or_temp_dirs(web, monkeypatch):
    def failing(web_dir, out_dir, timeout_s):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text("half", encoding="utf-8")
        raise A2VError("打包失败")

    monkeypatch.setattr(remotion, "_bundle_into", failing)
    with pytest.raises(A2VError):
        _bundle(web)
    root = bundle_cache.cache_root(web.dir)
    leftovers = [path for path in root.glob(".tmp-*")] if root.is_dir() else []
    assert leftovers == [], f"失败后留下了临时目录：{leftovers}"
    assert not [path for path in root.iterdir() if path.is_dir()] if root.is_dir() else True


def test_boundary_checks_and_source_scan_run_even_on_a_cache_hit(web):
    """缓存省掉的是打包，不是门禁：命中时校验与安全扫描照旧执行。"""
    _bundle(web)
    hit = _bundle(web)
    assert hit.cache_status == "hit"
    assert web.state["build"] == 1
    assert web.state["prepare"] == 2
    assert web.state["scan"] == 2


def test_source_violation_stops_before_packing(web, monkeypatch):
    monkeypatch.setattr(
        remotion,
        "source_policy",
        SimpleNamespace(scan=lambda files: [SimpleNamespace(render=lambda web_dir: "用了 Date.now")]),
    )
    with pytest.raises(remotion.RemotionError, match="确定性约束"):
        _bundle(web)
    assert web.state["build"] == 0


def test_disabling_the_cache_always_packs_and_writes_no_entry(web):
    first = _bundle(web, cache=False)
    second = _bundle(web, cache=False)
    assert (first.cache_status, second.cache_status) == ("disabled", "disabled")
    assert web.state["build"] == 2
    assert not bundle_cache.cache_root(web.dir).is_dir() or not [
        path for path in bundle_cache.cache_root(web.dir).iterdir() if path.is_dir()
    ]


# ---------------------------------------------------------------- 锁


def test_concurrent_bundles_are_serialized_by_the_generation_lock(web, monkeypatch):
    """切换作品的两次打包不能交叠：`.gen/` 是全局共享目录，交叠会互相污染。"""
    active = {"now": 0, "peak": 0}
    guard = threading.Lock()
    barrier = threading.Barrier(2)
    bases = [{"web/src/index.ts": "a"}, {"web/src/index.ts": "b"}]

    def slow_build(web_dir, out_dir, timeout_s):
        with guard:
            active["now"] += 1
            active["peak"] = max(active["peak"], active["now"])
        time.sleep(0.1)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text("<html></html>\n", encoding="utf-8")
        with guard:
            active["now"] -= 1
        return 0.1

    monkeypatch.setattr(remotion, "_bundle_into", slow_build)
    errors: list[BaseException] = []

    def run(index: int) -> None:
        monkeypatch.setattr(
            remotion,
            "build_input_fingerprint",
            lambda *args, **kwargs: {"files": dict(bases[index]), "digest": "x"},
        )
        barrier.wait()
        try:
            _bundle(web)
        except BaseException as exc:  # pragma: no cover - 失败时把异常带回主线程
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert not errors, errors
    assert active["peak"] == 1, "两次打包发生了交叠"


def test_waiting_for_a_held_lock_times_out_with_a_clear_error(tmp_path):
    lock = tmp_path / "x.lock"
    lock.write_text("holder", encoding="utf-8")
    with pytest.raises(bundle_cache.BundleCacheError, match="秒仍未获得锁"):
        with bundle_cache._exclusive(lock, what="测试锁", timeout_s=0.3):
            pytest.fail("不该拿到锁")


def test_stale_lock_is_reclaimed(tmp_path):
    lock = tmp_path / "x.lock"
    lock.write_text("dead holder", encoding="utf-8")
    old = time.time() - bundle_cache.LOCK_STALE_S - 10
    import os

    os.utime(lock, (old, old))
    with bundle_cache._exclusive(lock, what="测试锁", timeout_s=1.0):
        assert lock.is_file()
    assert not lock.exists(), "释放后不应留下锁文件"


def test_cache_manifest_records_the_key_and_the_product_files(web):
    outcome = _bundle(web)
    manifest = json.loads(
        (bundle_cache.entry_dir(web.dir, outcome.cache_key) / bundle_cache.MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
    )
    assert manifest["key"] == outcome.cache_key
    assert manifest["complete"] is True
    assert manifest["version"] == bundle_cache.CACHE_VERSION
    assert "bundle/index.html" in manifest["files"]
    assert manifest["files"]["bundle/index.html"]["size"] > 0
    assert "public" in manifest["parts"]
