"""可取消的本地命令委托；流式读日志，退出时收回完整子进程树。"""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time
from typing import Callable

import psutil

from m2v.core.errors import M2VError


def environment(root: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'NODE_PATH', 'NODE_OPTIONS', 'VIRTUAL_ENV',
                'UV_PROJECT', 'UV_PROJECT_ENVIRONMENT', 'M2V_CONTENT_ROOT'):
        env.pop(key, None)
    # 外层uv/m2v环境不能通过PATH悄悄成为作品解释器或依赖来源。
    paths = os.get_exec_path(env)
    if sys.prefix != sys.base_prefix:
        prefix = Path(sys.prefix).resolve()
        paths = [value for value in paths if not Path(value).resolve().is_relative_to(prefix)]
    local_bin = root / '.venv' / ('Scripts' if os.name == 'nt' else 'bin')
    env['PATH'] = os.pathsep.join([str(local_bin), *paths])
    env['UV_PROJECT_ENVIRONMENT'] = str(root / '.venv')
    env['PYTHONUTF8'] = '1'
    return env


def run(argv: list[str], root: Path, *, timeout: float, on_line: Callable[[str], None],
        cancelled: threading.Event | None = None) -> int:
    """控制工具自己的启动屏障，作品执行只使用其本地命令和清洁环境。"""
    env = environment(root)
    job = None
    process = None
    reader = None
    events: queue.Queue = queue.Queue()
    descendants: dict[tuple[int, float], psutil.Process] = {}
    tree_stopped = False

    def stop_tree():
        nonlocal tree_stopped
        if tree_stopped:
            return
        if job:
            job.close()
        elif process and os.name != 'nt':
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            for (pid, created), child in descendants.items():
                with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                    if child.create_time() == created:
                        child.kill()
            psutil.wait_procs(list(descendants.values()), timeout=30)
        tree_stopped = True

    try:
        if os.name == 'nt':
            from .windows_job import Job
            job = Job()
        process = subprocess.Popen([sys.executable, str(Path(__file__).with_name('launch.py'))],
            cwd=root, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', bufsize=1,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0,
            start_new_session=os.name != 'nt')
        if job:
            job.assign(process.pid)
        process.stdin.write(json.dumps({'argv': argv}, ensure_ascii=True)+'\n')
        process.stdin.close()

        def read_lines():
            try:
                for line in process.stdout:
                    events.put(line.rstrip('\r\n'))
            finally:
                events.put(None)

        reader = threading.Thread(target=read_lines, daemon=True)
        reader.start()
        deadline = time.monotonic() + timeout
        parent = psutil.Process(process.pid)
        while True:
            if cancelled is not None and cancelled.is_set():
                raise M2VError('作品执行已取消，已终止本次进程树')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise M2VError(f'作品本地命令超时（{timeout:g}秒），已终止本次进程树')
            # 启动器等到作品主进程退出才退出。其后遗留的浏览器不能继续持有
            # stdout而令一次成功执行挂起；先回收后代，再把队列中的末尾日志读完。
            if process.poll() is not None:
                stop_tree()
            if os.name != 'nt':
                with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                    for child in parent.children(recursive=True):
                        descendants[(child.pid, child.create_time())] = child
            try:
                line = events.get(timeout=min(.1, remaining))
            except queue.Empty:
                continue
            if line is None:
                break
            on_line(line)
        return process.wait(timeout=max(.1, deadline-time.monotonic()))
    except (OSError, subprocess.SubprocessError) as exc:
        raise M2VError(f'作品本地进程执行失败：{exc}') from exc
    finally:
        try:
            stop_tree()
        finally:
            if process:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=30)
                if reader:
                    reader.join(timeout=5)
                if process.stdout:
                    process.stdout.close()
