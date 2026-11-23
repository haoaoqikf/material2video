"""不发送控制事件的跨平台进程存活检查。"""

from __future__ import annotations

import os
import sys


#: Win32 错误码：`OpenProcess` 打不开目标进程时，用来区分「进程不存在」。
_ERROR_INVALID_PARAMETER = 87


def _process_is_alive_after_open_failure(error: int) -> bool:
    """`OpenProcess` 失败后的存活判定：只有「pid 不存在」才算已退出。

    权限不足（`ERROR_ACCESS_DENIED`）或其它错误说明进程可能存在，一律按存活
    处理，避免误回收仍然有效的锁。
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
    WAIT_OBJECT_0 = 0x00000000

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
        # 只有已结束的进程会返回有信号状态。查询失败也按可能仍在运行处理。
        return kernel32.WaitForSingleObject(handle, 0) != WAIT_OBJECT_0
    finally:
        kernel32.CloseHandle(handle)


def process_is_alive(pid: int) -> bool:
    """判断锁持有进程是否仍存活，不把权限拒绝当成进程死亡。"""
    if pid <= 0:
        return True
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
