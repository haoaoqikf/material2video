"""跨平台记录进程启动身份；未知身份不会授权回收。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

UNKNOWN = "unknown"
EXITED = "exited"


def _windows_start(pid: int) -> str:
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *[ctypes.POINTER(wintypes.FILETIME)] * 4]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        if ctypes.get_last_error() == 87:
            return EXITED
        return _windows_cim_start(pid)
    try:
        created, exited, kernel_time, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in (created, exited, kernel_time, user))):
            return UNKNOWN
        if exited.dwHighDateTime or exited.dwLowDateTime:
            return EXITED
        ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime
        return f"epoch:{(ticks - 116444736000000000) * 100}"
    finally:
        kernel.CloseHandle(handle)


def _windows_cim_start(pid: int) -> str:
    """CIM 可读取部分系统进程的启动时间，即使普通句柄访问被拒绝。"""
    command = (
        f"$item = Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'; "
        "if ($item.CreationDate) { ([DateTimeOffset]$item.CreationDate).ToUnixTimeMilliseconds() }"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, timeout=6, check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return f"epoch-ms:{int(result.stdout.strip())}"
    except (OSError, subprocess.SubprocessError, ValueError):
        return UNKNOWN


def process_start(pid: int) -> str:
    if pid <= 0:
        return UNKNOWN
    if sys.platform == "win32":
        return _windows_start(pid)
    if sys.platform.startswith("linux"):
        try:
            stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
            fields = stat.rsplit(")", 1)[1].split()
            if fields[0] == "Z":
                return EXITED
            boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
            return f"linux:{boot}:{fields[19]}"
        except FileNotFoundError:
            pass
        except (IndexError, OSError, UnicodeError):
            return UNKNOWN
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return EXITED
    except OSError:
        pass
    return UNKNOWN


def recording_ended(pid: int, marker: Path, *, legacy_before_ns: int | None = None) -> bool:
    """空标记来自旧运行时；仅可用明确晚于录制的启动时间排除旧持有者。"""
    start = process_start(pid)
    if start == EXITED:
        return True
    if start == UNKNOWN:
        return False
    try:
        expected = marker.read_text(encoding="ascii").strip() if marker.is_file() else ""
    except (OSError, UnicodeError):
        return False
    if start.startswith("epoch-ms:"):
        actual_ms = int(start.removeprefix("epoch-ms:"))
        if expected.startswith("epoch:") and expected.removeprefix("epoch:").isdigit():
            return actual_ms != int(expected.removeprefix("epoch:")) // 10**6
        if expected:
            return expected.startswith("epoch-ms:") and expected != start
        return legacy_before_ns is not None and actual_ms > legacy_before_ns // 10**6
    if expected:
        if expected.startswith("epoch-ms:") and start.startswith("epoch:"):
            return expected != f"epoch-ms:{int(start.removeprefix('epoch:')) // 10**6}"
        return expected.startswith(("epoch:", "linux:")) and expected != start
    if legacy_before_ns is not None and start.startswith("epoch:"):
        return int(start.removeprefix("epoch:")) > legacy_before_ns
    return False
