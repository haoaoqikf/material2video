"""Node 侧的逐帧渲染与编码：Python 与 Remotion 之间唯一的边界。

职责划分是刻意的：Python 保留分镜校验、路径归属推导、配音与字幕准备、体检编排、
溯源与交付文件权限修复；Node 只负责**画面执行**——把 React composition 逐帧
渲染并编码成无声 MP4。因此这里只有「起进程、解析它报出来的行、把失败翻译成
能定位的错误」三件事，没有任何判定逻辑。

两边靠 stdout 上**带前缀的行**通信：

- `__A2V_SESSION__{...}`：会话信息（浏览器开了几个、选中了哪个 composition）；
- `__A2V_COMPOSITION__{...}`：composition 的真实元数据，渲染前就报出来，
  供渲染入口与分镜交叉校验；
- `__A2V_READY__`：元数据已报出，正在等 Python 的确认；
- `__A2V_DONE__{...}`：渲染完成；
- `__A2V_PROGRESS__<百分比>`：渲染进度。

反向只有两种行：`__A2V_CONFIRM__{...}` 表示校验通过、可以开始渲染，
`__A2V_ABORT__{...}` 表示校验没过、立即退出。**先握手再渲染**是刻意的：
composition 的时长由 props 推导，与分镜累计时长是两份可能不一致的数据，
让不一致的画面先渲完再发现，代价是整段渲染时间。

为什么不用退出码或日志文本猜原因：`remotion` 的日志面向人看，措辞会随版本变化；
把判定挂在日志上，升级一次就会静默失效。
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import queue
import re
import shutil
import signal
import subprocess
import threading
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import a2v.core.assets as assets
import a2v.engine.bundle_cache as bundle_cache
import a2v.engine.perf as perf
import a2v.core.code_gate as code_gate
import a2v.core.code_scenes as code_scenes
import a2v.engine.contract_page as contract_page
import a2v.engine.scene_manifest as scene_manifest
import a2v.core.source_policy as source_policy
from a2v.engine.browser import PageContract
from a2v.core.errors import A2VError
from a2v.core.fingerprints import file_digest, fingerprint

logger = logging.getLogger(__name__)

#: Remotion 的入口与 composition 标识。两者都写死在 Python 侧：
#: 它们是渲染契约的一部分，改名会让 `--engine remotion` 找不到画面，
#: 而找不到时的报错必须指向这里而不是让人去猜。
ENTRY_POINT = "src/index.ts"
COMPOSITION_ID = "A2V"

#: 渲染脚本相对 `web/` 的位置
RENDER_SCRIPT = "scripts/remotion-render.mjs"

METADATA_PREFIX = "__A2V_COMPOSITION__"
PROGRESS_PREFIX = "__A2V_PROGRESS__"
SESSION_PREFIX = "__A2V_SESSION__"
READY_PREFIX = "__A2V_READY__"
DONE_PREFIX = "__A2V_DONE__"
CONFIRM_PREFIX = "__A2V_CONFIRM__"
ABORT_PREFIX = "__A2V_ABORT__"

#: 依赖安装与打包都按分钟计，逐帧渲染按十分钟计
_BUNDLE_TIMEOUT_S = 600
_METADATA_TIMEOUT_S = 300

#: 默认渲染并发。提高它是显式选择：历史注释记录了 Windows 下多并发页签
#: 抬高峰值内存、长片被系统关闭并报 `Target closed` 的风险。
DEFAULT_CONCURRENCY = 1

#: 拒绝确认后等 Node 优雅退出的时长；超时才连同进程树强杀。
_ABORT_GRACE_S = 30.0

#: 收到「渲染完成」后等 Node 自己退出的时长；超时只收进程树，不判失败。
_EXIT_GRACE_S = 60.0


class RemotionError(A2VError):
    """Remotion 渲染失败：依赖缺失、打包失败或渲染失败。"""


def check_concurrency(value: int) -> int:
    """并发必须是正整数；非法取值在打包之前就报错。"""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RemotionError(f"渲染并发必须是正整数，收到 {value!r}")
    return value


#: 兼容内部旧写法
_check_concurrency = check_concurrency


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


#: 后台读行线程遇到 EOF 时投递的哨兵
_EOF = object()


class _LineReader:
    """带超时的逐行读取。

    直接 `for line in process.stdout` 会在**静默进程**上永久阻塞：超时判定写在
    循环体里，而循环体根本不执行。因此读动作放进后台线程，调用方按截止时间
    取行，超时就能真正生效。
    """

    def __init__(self, stream) -> None:
        self._stream = stream
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._pump, name="a2v-line-reader", daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        try:
            for line in self._stream:
                self._queue.put(line.rstrip("\n"))
        except (ValueError, OSError):  # 进程被杀、管道关闭
            pass
        finally:
            self._queue.put(_EOF)

    def read(self, timeout_s: float):
        """取一行；超时返回 None，EOF 返回 :data:`_EOF`。"""
        try:
            item = self._queue.get(timeout=max(timeout_s, 0))
        except queue.Empty:
            return None
        return item

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self._stream.close()


def _spawn(
    command: list[str], cwd: Path, *, stdin: int | None
) -> subprocess.Popen[str]:
    """起一个子进程；POSIX 下单独成组，便于连同子进程一起收掉。"""
    creationflags = 0
    if os.name == "nt":  # pragma: no cover - 平台分支
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        return subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )
    except OSError as exc:  # 可执行文件不存在、权限不足等
        raise RemotionError(f"无法启动渲染进程：{exc}（命令：{' '.join(command)}）") from exc


def _terminate_tree(process: subprocess.Popen[str]) -> None:
    """连同子进程一起收掉。

    只 kill Node 是不够的：Chromium 是它的子进程，父进程一死就成孤儿，
    继续占着内存和端口。渲染超时、校验失败与用户中断都必须走这里。
    """
    if process.poll() is not None:
        return
    if os.name == "nt":  # pragma: no cover - 平台分支
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                timeout=60,
            )
    else:  # pragma: no cover - 平台分支
        with contextlib.suppress(OSError, ProcessLookupError):
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:  # pragma: no cover - 极端顽固的进程
        with contextlib.suppress(OSError):
            process.kill()


def _tail_text(tail: list[str]) -> str:
    return "\n".join(tail[-100:]) or "（没有输出）"


@dataclass(frozen=True)
class CompositionMetadata:
    """composition 从分镜 props 推导出来的画面参数。"""

    fps: int
    width: int
    height: int
    duration_in_frames: int

    @property
    def contract(self) -> PageContract:
        """当成页面契约用。

        这样 `_resolve_fps` / `_resolve_dimensions` / `_resolve_total_frames`
        三条判定对两条渲染路径完全一致——「画面声明的时长」与「分镜累计的时长」
        必须相等这件事不该因为换了渲染器就换一套写法。
        """
        return PageContract(
            fps=self.fps,
            duration_in_frames=self.duration_in_frames,
            width=self.width,
            height=self.height,
        )


def web_dir() -> Path:
    """前端工程目录（`web/`）。"""
    return contract_page.web_dir()


def program(name: str) -> str:
    """外部程序的**完整路径**。

    不能直接用 `"npx"`：Windows 上 `CreateProcess` 只会自动补 `.exe`，
    而 `npx` 是 `npx.cmd`，于是 `Popen(["npx", …])` 报「系统找不到指定的文件」——
    看起来像没装 Node，实际是调用方式不对。
    """
    found = shutil.which(name)
    if found is None:
        raise RemotionError(
            f"找不到 {name}：Remotion 渲染需要 Node 20 以上版本，"
            f"请安装后重新执行（当前 PATH 里没有 {name}）。"
        )
    return found


def require_environment(web_dir: Path | None = None) -> Path:
    """确认渲染所需的前端依赖与外部程序都在，缺什么就说什么。

    契约页路径下依赖缺失会表现为浏览器里的空白画面或超时，很难反推到
    「没装依赖」；因此这里在起进程之前先查，并把修复命令写在错误里。
    """
    directory = web_dir if web_dir is not None else contract_page.web_dir()
    if not (directory / "package.json").is_file():
        raise RemotionError(
            f"找不到前端工程：{directory / 'package.json'}。请确认仓库完整。"
        )
    if not (directory / "node_modules").is_dir():
        raise RemotionError(
            f"前端依赖未安装：{directory / 'node_modules'} 不存在。"
            f"请先执行 `cd {directory} && pnpm install`。"
        )
    for name in ("npx", "node"):
        program(name)
    return directory


def progress_handler(total_frames: int) -> Callable[[str], None]:
    """把 `__A2V_PROGRESS__` 行翻译成人看的进度日志，每 10% 报一次。"""

    state = {"last": -10}

    def report(line: str) -> None:
        if not line.startswith(PROGRESS_PREFIX):
            return
        percent = _safe_int(line[len(PROGRESS_PREFIX) :])
        if percent is None or percent < state["last"] + 10:
            return
        state["last"] = percent
        logger.info(
            "渲染进度 %d%%（约 %d/%d 帧）", percent, total_frames * percent // 100, total_frames
        )

    return report


def _run(
    command: list[str],
    *,
    cwd: Path,
    timeout_s: float,
    what: str,
    on_line: Callable[[str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    """跑一个子进程，把超时与失败翻译成带命令的错误。

    `on_line` 收到每一行输出（stdout 与 stderr 都在内），用于把进度回显给用户；
    失败时的报错里附上输出的最后若干行——Remotion 的失败原因几乎总在最后几行里，
    只报一句「渲染失败」会让人必须重跑一次才能看到原因。

    超时按**截止时间**判定而不是「读到行之后才看表」：打包与渲染都可能长时间
    不输出，静默进程必须照样超时。
    """
    process = _spawn(command, cwd, stdin=subprocess.DEVNULL)
    reader = _LineReader(process.stdout)
    tail: list[str] = []
    deadline = time.monotonic() + timeout_s
    returncode: int | None = None
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _terminate_tree(process)
                raise RemotionError(f"{what}超时（超过 {timeout_s:.0f} 秒）")
            line = reader.read(min(remaining, 1.0))
            if line is None:
                continue
            if line is _EOF:
                break
            tail.append(line)
            if len(tail) > 200:
                del tail[0]
            if on_line is not None:
                on_line(line)
        returncode = process.wait()
    finally:
        if process.poll() is None:  # 中途异常（含用户中断）时必须收掉整棵树
            _terminate_tree(process)
        # 后台线程可能持有 stdout 的读锁；先终止进程释放读操作，再关闭管道。
        reader.close()
    if returncode != 0:
        raise RemotionError(f"{what}失败（退出码 {returncode}）：\n{_tail_text(tail)}")
    return subprocess.CompletedProcess(command, returncode, "", "")


def prepare_composition_entry(
    *,
    web_dir: Path,
    storyboard_path: str | Path,
    content_root: str | Path | None = None,
) -> Path:
    """按当前作品重建代码场景静态清单，并检查其归属与安全边界。

    清单在每次 preview / review / render 前整体覆盖：只包含当前作品分镜
    引用的模块，切换作品不会残留上一个作品的引用。分镜声明了代码场景时，
    模块在这里解析归属并确认存在——缺失会在打包/起浏览器之前失败；
    依赖白名单与源码安全闸门也在这里执行，违规即终止，预览与导出都不会开始。

    composition 本身不再由构建期入口选择：契约页与 Remotion 根都按分镜声明的
    契约版本在运行时选择实现，因此「先构建了哪个版本」不再决定这次预览或导出
    能不能渲染当前作品。返回的是本次生成的代码场景清单路径。
    """
    try:
        Path(storyboard_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise RemotionError(f"分镜读取失败，无法重建代码场景清单：{exc}") from exc
    manifest = scene_manifest.generate(
        web_dir=web_dir, storyboard_path=storyboard_path, content_root=content_root
    )
    _check_code_scene_boundaries(
        web_dir=web_dir, storyboard_path=Path(storyboard_path), content_root=content_root
    )
    return manifest


def _check_code_scene_boundaries(
    *, web_dir: Path, storyboard_path: Path, content_root: str | Path | None
) -> None:
    """对当前作品的代码场景执行依赖白名单与安全闸门。

    只有分镜声明了代码场景时才解析归属；违规一次性全部列出，
    让 AI 一次修完而不是改一个撞一个。
    """
    try:
        data = json.loads(storyboard_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RemotionError(f"分镜读取失败，无法检查代码场景边界：{exc}") from exc
    if not any(True for _ in code_scenes.iter_code_scenes(data)):
        return
    violations = code_gate.check_storyboard(
        article_dir=Path(storyboard_path).resolve().parent, storyboard_data=data
    )
    if violations:
        detail = "\n".join(v.render(web_dir) for v in violations)
        raise RemotionError(f"代码场景违反依赖白名单或安全边界：\n{detail}")


def bundle(
    *,
    web_dir: Path,
    out_dir: Path,
    storyboard_path: str | Path,
    content_root: str | Path | None = None,
    workspace_root: str | Path | None = None,
    timeout_s: float = _BUNDLE_TIMEOUT_S,
    cache: bool = True,
) -> BundleOutcome:
    """把 composition 打包成静态产物，交给后续的取元数据与渲染复用。

    走 CLI 而不是 `@remotion/bundler` 的 `bundle()`：CLI 会读 `remotion.config.ts`，
    因此 `@/` 别名与 Tailwind 只在一处配置。程序化打包不会读那个配置，
    两条路径各配一遍迟早会漂移，而漂移的表现是「Studio 里对、渲染出来错」。

    启用缓存（默认）时，产物落进被忽略的 `web/.cache/a2v-bundles/<键>/`：
    键覆盖源码可达集合、生成的场景清单、`public/` 静态资产、打包配置与运行版本，
    命中前逐文件复核完整性。`cache=False`（CLI 的 `--no-bundle-cache`）时每次都
    打到调用方给的临时目录，用于诊断与基准对照。

    无论命中与否，**分镜校验、代码场景边界检查与源码确定性扫描都会执行**：
    缓存省掉的是打包，不是门禁。
    """
    web = Path(web_dir)
    # `.gen/` 是全局共享目录：生成到打包之间必须串行，否则并发的另一支作品
    # 会把清单覆盖掉，而缓存会把这份污染固化下来。
    with bundle_cache.generation_lock(web):
        prepare_composition_entry(
            web_dir=web, storyboard_path=storyboard_path, content_root=content_root
        )
        violations = source_policy.scan(build_inputs())
        if violations:
            detail = "\n".join(item.render(web) for item in violations)
            raise RemotionError(f"composition 源码违反确定性约束：\n{detail}")

        if not cache:
            build_seconds = _bundle_into(web, out_dir, timeout_s)
            logger.info("打包 composition 用了 %.1f 秒（本次禁用缓存）", build_seconds)
            return BundleOutcome(
                path=out_dir,
                cache_status="disabled",
                cache_key=None,
                cache_detail="本次禁用缓存",
                cache_seconds=0.0,
                build_seconds=build_seconds,
            )

        prepare_started = time.monotonic()
        # 这份指纹同时用于缓存键与成片溯源：同一批文件只哈希一次。
        # 算两遍不只是浪费——冷路径会因此平白多出几百毫秒。
        # 参数必须与写溯源时**逐字相同**，否则溯源里的键与复核时算出来的对不上，
        # 每次渲染后都会被判成「旧资产」。
        fingerprint = build_input_fingerprint(
            storyboard_path=storyboard_path,
            content_root=content_root or workspace_root,
            workspace_root=workspace_root,
        )
        base = fingerprint["files"]
        key, detail = bundle_cache.compute_key(
            web_dir=web, base_files=base, storyboard_path=storyboard_path
        )
        entry = bundle_cache.entry_dir(web, key)
        ok, reason = bundle_cache.verify(entry, key)
        if ok:
            cache_seconds = time.monotonic() - prepare_started
            logger.info("打包缓存命中（%s）：%s", key[:12], reason)
            return BundleOutcome(
                path=bundle_cache.bundle_path(entry),
                cache_status="hit",
                cache_key=key,
                cache_detail=reason,
                cache_seconds=cache_seconds,
                build_seconds=0.0,
                input_fingerprint=fingerprint,
            )

        with bundle_cache.key_lock(web, key):
            # 等锁期间可能有别的进程把同一把键建好了，复查一次再动手
            ok, reason = bundle_cache.verify(entry, key)
            if ok:
                cache_seconds = time.monotonic() - prepare_started
                logger.info("打包缓存命中（%s）：%s", key[:12], reason)
                return BundleOutcome(
                    path=bundle_cache.bundle_path(entry),
                    cache_status="hit",
                    cache_key=key,
                    cache_detail=reason,
                    cache_seconds=cache_seconds,
                    build_seconds=0.0,
                    input_fingerprint=fingerprint,
                )
            bundle_cache.cleanup_stale(web)
            temporary = bundle_cache.cache_root(web) / f".tmp-{key[:12]}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
            temporary.mkdir(parents=True, exist_ok=True)
            try:
                build_seconds = _bundle_into(web, bundle_cache.bundle_path(temporary), timeout_s)
                bundle_cache.write_manifest(temporary, key=key, detail=detail)
                bundle_cache.publish(temporary, entry, key=key)
            except BaseException:
                shutil.rmtree(temporary, ignore_errors=True)
                raise
        cache_seconds = time.monotonic() - prepare_started - build_seconds
        logger.info("打包完成并写入缓存（%s，%.1f 秒）", key[:12], build_seconds)
        return BundleOutcome(
            path=bundle_cache.bundle_path(entry),
            cache_status="miss",
            cache_key=key,
            cache_detail=reason,
            cache_seconds=max(cache_seconds, 0.0),
            build_seconds=build_seconds,
            input_fingerprint=fingerprint,
        )


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


def metadata(
    *,
    web_dir: Path,
    bundle_dir: Path,
    props: Path,
    composition_id: str = COMPOSITION_ID,
    timeout_s: float = _METADATA_TIMEOUT_S,
) -> CompositionMetadata:
    """读出 composition 由分镜 props 推导出的画面参数。"""
    lines: list[str] = []
    _run(
        [
            program("node"),
            RENDER_SCRIPT,
            "--bundle",
            str(bundle_dir),
            "--props",
            str(props),
            "--composition-id",
            composition_id,
            "--metadata-only",
        ],
        cwd=web_dir,
        timeout_s=timeout_s,
        what="读取 composition 元数据",
        on_line=lines.append,
    )
    payload = _metadata_from(lines)
    if payload is None:
        raise RemotionError(
            f"渲染脚本没有报出 composition 元数据（应有一行以 {METADATA_PREFIX} 开头）。"
            f"输出：\n" + "\n".join(lines[-10:])
        )
    if payload.get("id") != composition_id:
        raise RemotionError(
            f"渲染脚本选中的 composition 是 {payload.get('id')!r}，期望 {composition_id!r}"
        )
    return CompositionMetadata(
        fps=int(payload["fps"]),
        width=int(payload["width"]),
        height=int(payload["height"]),
        duration_in_frames=int(payload["durationInFrames"]),
    )


def render_frames(
    *,
    web_dir: Path,
    bundle_dir: Path,
    props: Path,
    out: Path,
    total_frames: int,
    crf: int,
    preset: str,
    timeout_s: float,
    frame_start: int = 0,
    scale: float = 1,
    composition_id: str = COMPOSITION_ID,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> None:
    """把 composition 渲染并编码成无声 MP4。

    音频不在这里合成：配音与字幕的合成、成片验收与交付权限都留在 Python 侧，
    与旧路径共用同一段代码，因此两条路径的成片参数不会各走一套。

    这条路径每次单独起 Node（元数据由调用方另行读取），保留给金融专题导出等
    需要分别控制两步的调用方；文章正式渲染走 :func:`render_session`。
    """
    concurrency = check_concurrency(concurrency)
    command = [
        program("node"),
        RENDER_SCRIPT,
        "--bundle",
        str(bundle_dir),
        "--props",
        str(props),
        "--composition-id",
        composition_id,
        "--out",
        str(out),
        "--crf",
        str(crf),
        "--preset",
        preset,
        # 显式给出帧区间：composition 自己也有时长，但**渲染的帧数**是验收项，
        # 让它由 Python 算出来并在命令行上写死，比隐含在画面里可核对
        "--frames",
        f"{frame_start}-{frame_start + total_frames - 1}",
        "--scale",
        str(scale),
        "--concurrency",
        str(concurrency),
    ]
    _run(
        command,
        cwd=web_dir,
        timeout_s=timeout_s,
        what=f"渲染 {total_frames} 帧",
        on_line=progress_handler(total_frames),
    )
    if not out.is_file() or out.stat().st_size == 0:
        raise RemotionError(f"渲染完成后没有产出文件：{out}")


def render_session(
    *,
    web_dir: Path,
    bundle_dir: Path,
    props: Path,
    composition_id: str = COMPOSITION_ID,
    on_metadata: Callable[[CompositionMetadata], dict | None],
    timeout_s: float,
    metadata_timeout_s: float = _METADATA_TIMEOUT_S,
    on_line: Callable[[str], None] | None = None,
) -> dict:
    """在**同一个 Node 会话**里先取元数据、校验通过后再渲染。

    两次进程调用（一次取元数据、一次渲染）各自冷启动浏览器并各选一次
    composition。这里把两件事压进一个会话：Node 只开一个浏览器，选择
    composition 之后把真实元数据报回来，然后**停在原地等确认**。

    `on_metadata` 是判定入口：它拿到元数据后做交叉校验，返回要下发的渲染参数；
    校验不通过时它应当抛错——那时本函数向 Node 发 `ABORT` 并收掉整棵进程树，
    异常原样抛出。因此「帧数/尺寸/帧率不匹配」的代价是一次选择而不是一次渲染。

    返回会话信息（浏览器开启次数、完成回报），供性能报告留证。
    """
    command = [
        program("node"),
        RENDER_SCRIPT,
        "--bundle",
        str(bundle_dir),
        "--props",
        str(props),
        "--composition-id",
        composition_id,
        "--session",
    ]
    process = _spawn(command, web_dir, stdin=subprocess.PIPE)
    memory_sampler = perf.ProcessTreeMemorySampler(process.pid) if getattr(process, "pid", None) else None
    if memory_sampler is not None:
        memory_sampler.start()
    reader = _LineReader(process.stdout)
    tail: list[str] = []
    session: dict = {}
    metadata: CompositionMetadata | None = None
    returncode: int | None = None
    done = False
    handshake_started = time.monotonic()
    # 进度日志要等确认之后才知道总帧数，因此处理器是可换的
    sink: dict[str, Callable[[str], None] | None] = {"handler": on_line}

    def consume(line: str) -> None:
        tail.append(line)
        if len(tail) > 200:
            del tail[0]
        handler = sink["handler"]
        if handler is not None:
            handler(line)

    def abort(reason: str) -> None:
        """把「不渲染」明确告诉 Node，再收掉进程树。

        先给 Node 一小段时间**优雅退出**：它会走 `finally` 关掉浏览器再退出，
        比直接杀进程树干净（否则 Chromium 会被强杀，留下孤儿进程占着内存）。
        超时仍未退出才强杀整棵树。
        """
        stdin = process.stdin
        if stdin is not None and not stdin.closed:
            try:
                stdin.write(f"{ABORT_PREFIX}{json.dumps({'reason': reason}, ensure_ascii=False)}\n")
                stdin.flush()
            except (OSError, ValueError):  # pragma: no cover - 进程已经退出
                pass
            with contextlib.suppress(OSError, ValueError):
                stdin.close()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=_ABORT_GRACE_S)
        _terminate_tree(process)

    try:
        deadline = time.monotonic() + metadata_timeout_s
        while metadata is None or not session.get("ready"):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                abort("等待 composition 元数据超时")
                raise RemotionError(
                    f"等待 composition 元数据超时（超过 {metadata_timeout_s:.0f} 秒）："
                    f"渲染脚本没有报出元数据或没有进入等待确认状态。\n{_tail_text(tail)}"
                )
            line = reader.read(min(remaining, 1.0))
            if line is None:
                continue
            if line is _EOF:
                returncode = process.wait()
                raise RemotionError(
                    f"渲染脚本在开始渲染前就退出了（退出码 {returncode}）：\n{_tail_text(tail)}"
                )
            consume(line)
            if line.startswith(METADATA_PREFIX):
                payload = _metadata_from([line])
                if payload is None:  # pragma: no cover - 前缀已匹配
                    continue
                metadata = CompositionMetadata(
                    fps=int(payload["fps"]),
                    width=int(payload["width"]),
                    height=int(payload["height"]),
                    duration_in_frames=int(payload["durationInFrames"]),
                )
                if payload.get("id") != composition_id:
                    abort("composition 标识不匹配")
                    raise RemotionError(
                        f"渲染脚本选中的 composition 是 {payload.get('id')!r}，期望 {composition_id!r}"
                    )
            elif line.startswith(SESSION_PREFIX):
                session.update(json.loads(line[len(SESSION_PREFIX) :]))
            elif line.startswith(READY_PREFIX):
                session["ready"] = True
        if metadata is None:  # pragma: no cover - 循环条件已保证
            abort("没有元数据")
            raise RemotionError("渲染脚本没有报出 composition 元数据")

        try:
            params = on_metadata(metadata)
        except BaseException:
            abort("Python 侧未通过元数据校验")
            raise
        if params is None:
            abort("Python 侧未通过元数据校验")
            raise RemotionError("元数据校验未通过，已取消渲染")
        assert process.stdin is not None
        process.stdin.write(f"{CONFIRM_PREFIX}{json.dumps(params, ensure_ascii=False)}\n")
        process.stdin.flush()
        # 握手结束：从起进程到确认下发，就是报告里的「元数据」阶段
        session["readySeconds"] = time.monotonic() - handshake_started
        if sink["handler"] is None:
            total = params.get("progressTotal")
            if isinstance(total, int) and total > 0:
                sink["handler"] = progress_handler(total)

        deadline = time.monotonic() + timeout_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                abort("渲染超时")
                raise RemotionError(f"渲染超时（超过 {timeout_s:.0f} 秒）")
            line = reader.read(min(remaining, 1.0))
            if line is None:
                continue
            if line is _EOF:
                break
            consume(line)
            if line.startswith(DONE_PREFIX):
                session.update(json.loads(line[len(DONE_PREFIX) :]))
                done = True
                break
        if done:
            # 已经收到「渲染完成」：Node 之后卡在退出上也**不能**算成一次超时，
            # 给它一段时间自己收尾，超时就只收进程树（成片随后照常验收）。
            try:
                returncode = process.wait(timeout=_EXIT_GRACE_S)
            except subprocess.TimeoutExpired:
                logger.warning("渲染脚本在回报完成后仍未退出，收回进程树")
                _terminate_tree(process)
                returncode = process.wait()
        else:
            returncode = process.wait()
    except KeyboardInterrupt:
        abort("用户中断")
        raise
    finally:
        # 协议解析或进度回调也可能抛错，不能让 close 等待仍存活的静默进程。
        if process.poll() is None:
            _terminate_tree(process)
        reader.close()
        if process.stdin is not None and not process.stdin.closed:
            with contextlib.suppress(OSError, ValueError):
                process.stdin.close()
        session["peakMemoryBytes"] = memory_sampler.stop() if memory_sampler is not None else None
        session["memorySamples"] = memory_sampler.samples if memory_sampler is not None else 0

    # `done` 时退出码可能是收进程树留下的，不代表渲染失败；成片随后照常验收
    if returncode != 0 and not done:
        raise RemotionError(f"渲染 {metadata.duration_in_frames} 帧失败（退出码 {returncode}）：\n{_tail_text(tail)}")
    expected = session.get("frames")
    if isinstance(expected, int) and expected < 1:
        raise RemotionError(f"渲染脚本回报了异常的帧数：{expected}")
    return session


def _metadata_from(lines: list[str]) -> dict | None:
    """从输出里取元数据行。

    取**最后**一条：打包器与 Remotion 自己的日志都可能出现在前面，
    而元数据是脚本在渲染前打印的，重放时最后一条才是本次的。
    """
    found: dict | None = None
    for line in lines:
        if not line.startswith(METADATA_PREFIX):
            continue
        try:
            found = json.loads(line[len(METADATA_PREFIX) :])
        except json.JSONDecodeError as exc:
            raise RemotionError(f"composition 元数据不是合法 JSON：{line!r}（{exc}）") from exc
    return found


def _safe_int(text: str) -> int | None:
    try:
        return int(text.strip())
    except ValueError:
        return None


#: 指纹的起点。三个文件都不是被 import 进来的，必须显式给出：
#: composition 入口、渲染脚本（编码参数由它决定）、打包配置（别名与 Tailwind 在这里）。
_ENTRY_ROOTS = (
    "src/index.ts",
    "scripts/remotion-render.mjs",
    "remotion.config.ts",
)

#: 依赖清单：裸模块的内容不在仓库里，但**版本**由这两份文件锁定
_PACKAGE_FILES = ("package.json", "pnpm-lock.yaml")

#: 引用写法。只认「会真的把另一个文件拉进构建」的那几种。
_IMPORT_PATTERNS = (
    re.compile(r"""\bfrom\s*['"]([^'"]+)['"]"""),  # import x from 'y' / export … from 'y'
    re.compile(r"""\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)"""),  # 动态 import('y')
    re.compile(r"""^[ \t]*import\s+['"]([^'"]+)['"]""", re.MULTILINE),  # 纯副作用 import 'y'
    re.compile(r"""@import\s+(?:url\()?['"]([^'"]+)['"]"""),  # CSS @import
    re.compile(r"""url\(\s*['"]?([^'")]+?)['"]?\s*\)"""),  # CSS url(...)
)

#: 解析引用时依次尝试的后缀（含目录入口）
_RESOLVE_SUFFIXES = ("", ".ts", ".tsx", ".css", ".json", ".mjs", "/index.ts", "/index.tsx")


#: 作品文件的指纹键前缀：读自场景清单的 workspaceRoot，让外部内容根的
#: 作品文件也有**可复核**的键（而不是退化成只剩文件名）。
WORK_MOUNT_PREFIX = "__a2v_workspace__"

_MANIFEST_PATH = Path(".gen/scene-manifest.json")


def _manifest_data(repo_root: Path | None = None) -> dict | None:
    """读当前作品的场景清单；没有或损坏时返回 None。"""
    manifest_path = contract_page.web_dir(repo_root) / _MANIFEST_PATH
    if not manifest_path.is_file():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def fingerprint_mounts(repo_root: Path | None = None, workspace_root: str | Path | None = None) -> dict[str, Path]:
    """指纹键使用的挂载表：与契约页服务器同一套别名。

    构建输入全在 `web/` 下，而工作区根可能是仓库之外的内容根——那时
    `asset_key` 会退化成只记文件名，复核时拼不回去、每一份成片都被判成
    「资产不见了」。挂上 `web/` 的别名之后，键与工作区根在哪无关；
    作品文件再挂 `__a2v_workspace__`（根读自场景清单），记录与复核
    两侧走同一份清单，键永远能拼回真实文件。
    """
    mounts = {**assets.default_mounts(), **contract_page.web_mounts(repo_root)}
    data = _manifest_data(repo_root)
    workspace = str(workspace_root) if workspace_root is not None else (data.get("workspaceRoot") if data else None)
    if workspace:
        mounts[WORK_MOUNT_PREFIX] = Path(str(workspace))
    return mounts


def _imports_of(path: Path) -> list[str]:
    """文件里引用的其它文件（原样，不解析）。"""
    if path.suffix.lower() not in (".ts", ".tsx", ".mjs", ".css"):
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    found: list[str] = []
    for pattern in _IMPORT_PATTERNS:
        found.extend(match.group(1) for match in pattern.finditer(text))
    return found


def _resolve_import(specifier: str, importer: Path, web: Path) -> Path | None:
    """引用 → 仓库里的文件；裸模块与取不到的引用返回 None。"""
    if Path(specifier).is_absolute():
        base = Path(specifier)
    elif specifier.startswith(("@/", "~/")):
        base = web / "src" / specifier[2:]
    elif specifier.startswith("."):
        base = importer.parent / specifier
    else:
        # 裸模块（react、remotion、dagre…）：内容在 node_modules 里，
        # 由 package.json 与锁文件锁定版本，不逐个指纹
        return None
    for suffix in _RESOLVE_SUFFIXES:
        candidate = Path(f"{base}{suffix}")
        if candidate.is_file():
            return candidate
    return None


def _storyboard_modules(storyboard_path: str | Path, content_root: str | Path | None = None) -> list[Path]:
    """解析当前分镜真正引用的代码场景源文件，避免依赖全局生成清单的最后写入者。"""
    data = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    source_dir = Path(storyboard_path).resolve().parent
    found: dict[Path, None] = {}
    for _scene_path, _scene, module in code_scenes.iter_code_scenes(data):
        if module:
            resolved = code_scenes.resolve_module(source_dir, module)
            if resolved is not None:
                found[resolved.resolve()] = None
    return list(found)


def _manifest_modules(repo_root: Path | None = None) -> list[Path]:
    data = _manifest_data(repo_root)
    result: dict[Path, None] = {}
    for item in (data or {}).get("modules", []):
        raw = item.get("module") if isinstance(item, dict) else None
        if raw and Path(raw).is_file():
            result[Path(raw).resolve()] = None
    return list(result)


def build_inputs(
    repo_root: Path | None = None,
    *,
    storyboard_path: str | Path | None = None,
    content_root: str | Path | None = None,
    scene_modules: Iterable[Path] | None = None,
) -> list[Path]:
    """画面与编码的全部构建输入：从入口出发**沿引用可达**的文件。

    刻意不做「扫描整个 `src/`」：那样改一个没有任何画面用到的文件也会让所有
    成片判成「落后」，闸门立刻沦为噪音，而人一旦开始忽略它，它就不再是闸门。
    反面同样要防：可达性算少了会让「改了组件却判成当前」——所以入口、字体、
    依赖清单这些不被 import 的东西必须显式列出来。

    作品级代码场景的入口只有两个确定来源：目录里有分镜时按分镜解析，否则读
    `.gen/scene-manifest.json`。共享 composition（如金融专题，从不加载作品模块）
    应显式传 `scene_modules=()`：清单是全局最后写入者，会残留上一篇文章的模块。
    """
    web = contract_page.web_dir(repo_root)
    seen: dict[Path, None] = {}

    queue = [candidate for name in _ENTRY_ROOTS if (candidate := web / name).is_file()]
    if scene_modules is not None:
        queue.extend(scene_modules)
    elif storyboard_path:
        queue.extend(_storyboard_modules(storyboard_path, content_root))
    else:
        queue.extend(_manifest_modules(repo_root))
    generated_indexes = {
        (web / scene_manifest.GENERATED_MANIFEST).resolve(),
        (web / ".gen" / "active-tailwind.css").resolve(),
    }
    while queue:
        resolved = queue.pop().resolve()
        # 全局生成索引与 active-tailwind.css 都是从当前作品派生的临时文件，
        # 不同作品构建时会互相覆盖。真正的代码场景源文件与其导入会按分镜进入 queue。
        if resolved in generated_indexes:
            continue
        if resolved in seen:
            continue
        seen[resolved] = None
        for specifier in _imports_of(resolved):
            target = _resolve_import(specifier, resolved, web)
            if target is not None:
                queue.append(target)

    for name in _PACKAGE_FILES:
        candidate = web / name
        if candidate.is_file():
            seen[candidate.resolve()] = None
    # 字体取**源文件**而不是 `public/fonts/` 里的构建副本：副本是派生物，
    # 没构建过就不存在，那会让每一次复核都报「不见了」
    for font in contract_page.font_files(repo_root):
        seen[font.resolve()] = None
    return sorted(seen)


def build_input_fingerprint(
    repo_root: Path | None = None,
    *,
    storyboard_path: str | Path | None = None,
    content_root: str | Path | None = None,
    workspace_root: str | Path | None = None,
) -> dict:
    """成片溯源用的构建输入指纹。

    口径与页面路径一致（同样是 `{"files": {...}, "digest": ...}`），
    因此 `provenance_status` 的复核逻辑两条路径共用一套。
    """
    mounts = fingerprint_mounts(repo_root, workspace_root)
    root = contract_page.web_dir(repo_root)
    files = {
        assets.asset_key(path, root, mounts): file_digest(path)
        for path in build_inputs(repo_root, storyboard_path=storyboard_path, content_root=content_root)
    }
    ordered = dict(sorted(files.items()))
    return {"files": ordered, "digest": fingerprint(ordered)}
