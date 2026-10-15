"""合成性能观测：分阶段耗时、结构化报告、环境信息与进程树峰值内存。

设计约束（见 `openspec/changes/optimize-final-video-render/design.md`）：

- 逐帧渲染与编码在 Remotion 内部**重叠执行**，只记一段合并耗时，不拆成
  「渲染」与「编码」两段相加——那样总耗时会重复累计，报告反而不可信；
- 未执行的阶段记 ``None`` 并列入 ``skipped``，不写 0 冒充实测值：
  「跑过 0 秒」与「根本没跑」在报告里必须长得不一样；
- 报告与成片同级，落在作品 ``outputs/`` 下（已被 ``.gitignore`` 忽略），
  因此测出来的数不会进版本控制，也不需要人手工清理。
"""

from __future__ import annotations

import contextlib
import ctypes
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

#: 报告里固定出现的阶段，顺序即报告的书写顺序。
#: `cache` 是缓存准备（键计算、完整性复核、命中判定），`bundle` 是缺失时的重新打包。
#: `render` 已含编码，因此这里没有独立的 `encode`——两段在 Remotion 里是同一段时间。
STAGES: tuple[str, ...] = ("cache", "bundle", "metadata", "render", "mux", "probe")

#: 报告格式版本。字段或口径变化时递增，让旧报告一眼可辨。
REPORT_VERSION = 1

#: 性能报告后缀：`video.mp4` → `video.performance.json`，与成片同名同级。
REPORT_SUFFIX = ".performance.json"


@dataclass
class StageTimings:
    """按阶段记录单调时钟耗时；没跑过的阶段保持「跳过」。"""

    _seconds: dict[str, float | None] = field(default_factory=dict)

    def record(self, stage: str, seconds: float) -> None:
        if seconds < 0:  # pragma: no cover - 单调时钟不会回退
            raise ValueError(f"阶段 {stage} 的耗时不能为负：{seconds}")
        self._seconds[stage] = float(seconds)

    @contextlib.contextmanager
    def measure(self, stage: str) -> Iterator[None]:
        """把一段代码的耗时记到 `stage` 上，异常时同样记录。"""
        started = time.monotonic()
        try:
            yield
        finally:
            self.record(stage, time.monotonic() - started)

    def skip(self, *stages: str) -> None:
        for stage in stages:
            self._seconds[stage] = None

    def as_dict(self) -> dict[str, float | None]:
        """固定形状的读法：`:data:`STAGES` 全部出现，没跑的为 ``None``。"""
        return {stage: self._seconds.get(stage) for stage in STAGES}

    def skipped(self) -> list[str]:
        return [stage for stage in STAGES if self._seconds.get(stage) is None]

    def executed_seconds(self) -> float:
        return sum(value for value in self._seconds.values() if value is not None)


def report_path_for(output: str | Path) -> Path:
    """性能报告的落点：与成片同名同级。"""
    path = Path(output)
    return path.with_suffix(REPORT_SUFFIX)


def measure(timings: StageTimings | None, stage: str):
    """按需计时：`timings` 为 None 时什么都不记，调用方无需分支。"""
    return timings.measure(stage) if timings is not None else contextlib.nullcontext()


def write_report(path: str | Path, payload: dict) -> Path:
    """把报告写成 JSON。写失败如何处置由调用方决定：报告是附加信息，不牵动成片。"""
    target = Path(path)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def build_report(
    *,
    entry: str,
    output: str | Path,
    storyboard: str | Path | None,
    frames: int,
    fps: int,
    width: int,
    height: int,
    concurrency: int,
    timings: StageTimings,
    total_seconds: float,
    cache: dict | None = None,
    extra: dict | None = None,
) -> dict:
    """组装一份结构化性能报告。

    `entry` 标明数据来自哪个入口（`render` 是正式渲染，`benchmark` 是基准），
    因为正式门禁下的数字与内部 API 基准不同源，混着比会得出错误结论。
    """
    payload: dict = {
        "version": REPORT_VERSION,
        "entry": entry,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "output": str(Path(output).name) if output else None,
        "storyboard": str(storyboard) if storyboard else None,
        "frames": frames,
        "fps": fps,
        "width": width,
        "height": height,
        "concurrency": concurrency,
        "stages": timings.as_dict(),
        "skipped": timings.skipped(),
        "executedSeconds": round(timings.executed_seconds(), 3),
        "totalSeconds": round(total_seconds, 3),
        "environment": environment(),
    }
    if cache is not None:
        payload["cache"] = cache
    if extra:
        payload.update(extra)
    return payload


def node_version() -> str | None:
    """Node 版本；取不到时如实返回 None 而不是编一个。"""
    executable = shutil.which("node")
    if executable is None:
        return None
    return _first_line([executable, "--version"])


def ffmpeg_version() -> str | None:
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        return _first_line([get_ffmpeg_exe(), "-version"])
    except Exception:  # pragma: no cover - 缺 ffmpeg 时不影响渲染主流程
        return None


def remotion_version(web_dir: str | Path | None = None) -> str | None:
    """从已安装的 `@remotion/renderer` 读版本；依赖没装时返回 None。"""
    import m2v.engine.contract_page as contract_page

    try:
        directory = Path(web_dir) if web_dir is not None else contract_page.web_dir()
    except Exception:  # pragma: no cover - 仓库结构异常时不影响报告
        return None
    manifest = directory / "node_modules" / "@remotion" / "renderer" / "package.json"
    if not manifest.is_file():
        return None
    try:
        return str(json.loads(manifest.read_text(encoding="utf-8")).get("version"))
    except (OSError, ValueError):  # pragma: no cover - 依赖目录损坏
        return None


def environment(*, web_dir: str | Path | None = None) -> dict:
    """记录硬件与软件版本，让两次报告的数字有可比性。"""
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "cpuCount": os.cpu_count(),
        "memoryGiB": _total_memory_gib(),
        "python": platform.python_version(),
        "node": node_version(),
        "remotion": remotion_version(web_dir),
        "ffmpeg": ffmpeg_version(),
        "executable": sys.executable,
    }


def _first_line(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = (completed.stdout or completed.stderr).strip().splitlines()
    return text[0].strip() if text else None


def _total_memory_gib() -> float | None:
    """物理内存总量（GiB）。取不到时返回 None，不猜一个值。"""
    if os.name == "nt":
        class _MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        try:
            status = _MemoryStatusEx()
            status.dwLength = ctypes.sizeof(_MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return round(status.ullTotalPhys / 1024**3, 1)
        except (AttributeError, OSError):  # pragma: no cover - 非 Windows 或受限环境
            return None
        return None
    try:  # pragma: no cover - POSIX 分支
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3, 1)
    except (AttributeError, ValueError, OSError):
        return None


_PROBE_TIMEOUT_S = 30


def tree_memory_bytes(pid: int) -> int | None:
    """当前进程树的常驻内存之和（字节）。

    Windows 用一次 CIM 查询取全表再按父子关系做 BFS：逐 pid 递归调用
    `Get-Process` 会在子进程不断生灭时漏掉整棵子树。POSIX 用 `ps` 的 pid/ppid/rss。
    取不到时返回 None——报告里宁可缺一项，也不写一个假数。
    """
    if os.name == "nt":
        return _windows_tree_memory(pid)
    return _posix_tree_memory(pid)


def _windows_tree_memory(pid: int) -> int | None:
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$all = Get-CimInstance Win32_Process -Property ProcessId,ParentProcessId,WorkingSetSize;"
        "$ids = New-Object 'System.Collections.Generic.HashSet[int]';"
        f"[void]$ids.Add({int(pid)});"
        "$changed = $true;"
        "while ($changed) { $changed = $false;"
        "  foreach ($p in $all) {"
        "    if ($ids.Contains([int]$p.ParentProcessId) -and -not $ids.Contains([int]$p.ProcessId)) {"
        "      [void]$ids.Add([int]$p.ProcessId); $changed = $true } } }"
        "$sum = [int64]0;"
        "foreach ($p in $all) { if ($ids.Contains([int]$p.ProcessId)) { $sum += [int64]$p.WorkingSetSize } };"
        "[Console]::Out.Write($sum)"
    )
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:  # pragma: no cover - Windows 上通常都有其中一个
        return None
    try:
        completed = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_PROBE_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - 采样失败不致命
        return None
    text = (completed.stdout or "").strip()
    if not text.isdigit():
        return None
    return int(text)


def _posix_tree_memory(pid: int) -> int | None:  # pragma: no cover - POSIX 分支
    try:
        completed = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,rss="],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_PROBE_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    rows: list[tuple[int, int, int]] = []
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        try:
            rows.append((int(parts[0]), int(parts[1]), int(parts[2])))
        except ValueError:
            continue
    children: dict[int, list[int]] = {}
    rss: dict[int, int] = {}
    for child, parent, size in rows:
        children.setdefault(parent, []).append(child)
        rss[child] = size
    total = 0
    stack = [pid]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        total += rss.get(current, 0) * 1024
        stack.extend(children.get(current, ()))
    return total or None


class ProcessTreeMemorySampler:
    """在后台按固定间隔采样进程树内存，返回峰值。

    采样是**粗粒度**的：间隔内的瞬时峰值看不到，因此报告里读的是
    「观测到的峰值」而不是「理论峰值」；这一点在基准报告的方法说明里写清楚。
    """

    def __init__(
        self,
        pid: int,
        *,
        interval_s: float = 2.0,
        probe: Callable[[int], int | None] | None = None,
    ) -> None:
        self.pid = int(pid)
        self.interval_s = interval_s
        self._probe = probe or tree_memory_bytes
        self.peak: int | None = None
        self.samples = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:  # pragma: no cover - 只允许启动一次
            return
        self._thread = threading.Thread(target=self._loop, name="m2v-memory-sampler", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.sample_once()
            if self._stop.wait(self.interval_s):
                break

    def sample_once(self) -> int | None:
        value = self._probe(self.pid)
        if value is None:
            return None
        self.samples += 1
        if self.peak is None or value > self.peak:
            self.peak = value
        return value

    def stop(self) -> int | None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=self.interval_s + _PROBE_TIMEOUT_S)
            self._thread = None
        return self.peak

    def __enter__(self) -> ProcessTreeMemorySampler:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()
