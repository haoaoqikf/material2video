"""渲染进程与环境：起 Node、按截止时间读行、把失败翻译成能定位的错误。

这是 `m2v.engine.remotion` 包的最底层，只做三件事：起进程、解析它报出来的行、
把超时与失败翻译成带命令的错误。打包（:mod:`m2v.engine.remotion.bundling`）与
渲染会话（:mod:`m2v.engine.remotion.session`）都建立在这一层上，因此超时常量与
stdout 协议前缀也放在这里，由上层按需取用。

两边靠 stdout 上**带前缀的行**通信，前缀与超时都属于渲染契约的一部分，改名会让
上层解析不到，因此都写死在 Python 侧。
"""

from __future__ import annotations

import contextlib
import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

from m2v.core.errors import M2VError

#: 渲染脚本相对 `web/` 的位置
RENDER_SCRIPT = "scripts/remotion-render.mjs"

METADATA_PREFIX = "__M2V_COMPOSITION__"
PROGRESS_PREFIX = "__M2V_PROGRESS__"
SESSION_PREFIX = "__M2V_SESSION__"
READY_PREFIX = "__M2V_READY__"
DONE_PREFIX = "__M2V_DONE__"
CONFIRM_PREFIX = "__M2V_CONFIRM__"
ABORT_PREFIX = "__M2V_ABORT__"

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


class RemotionError(M2VError):
    """Remotion 渲染失败：依赖缺失、打包失败或渲染失败。"""


def check_concurrency(value: int) -> int:
    """并发必须是正整数；非法取值在打包之前就报错。"""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RemotionError(f"渲染并发必须是正整数，收到 {value!r}")
    return value


#: 兼容内部旧写法
_check_concurrency = check_concurrency


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
        self._thread = threading.Thread(target=self._pump, name="m2v-line-reader", daemon=True)
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
