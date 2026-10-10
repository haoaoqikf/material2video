"""交付文件的访问权限修复与自检。

背景（Windows 实测）：``tempfile.TemporaryDirectory()`` 在 Windows 上会创建一个
**刻意收紧**的目录，ACL 只有 ``SYSTEM / Administrators / OWNER RIGHTS`` 且关闭继承。
文件在这个临时目录里生成、再 ``replace()`` 到最终位置，就会把这份 ACL 一起带走：
既拿不到父目录的继承权限，也没有 ``Authenticated Users``。

后果不是「文件读不了」——你自己的账号（管理员）能读能写——而是**以标准权限运行的
打包应用读不到**：Windows 11 新版「媒体播放器」打开成片时报
``0x80070005 你没有访问该文件的权限``。ffmpeg、浏览器上传都不受影响，
所以这个问题只在用户双击播放时才暴露。注意它在 ``%TEMP%`` 下不会复现，
因为那里的临时目录额外继承了一条宽松的 ``CREATOR OWNER``。

修法是让落到最终位置的文件重新遵循父目录的继承规则（``icacls /reset``），
而不是把产物复制到别处或手工改 ACL。
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# icacls 是 Windows 自带命令；单次调用不到 50ms，且只在交付文件上执行
_TIMEOUT_SECONDS = 20

# icacls 的授权行形如：`BUILTIN\Users:(I)(RX)` 或 `NT AUTHORITY\SYSTEM:(F)`。
# 首个授权行前面会带文件路径，因此用「非括号、非冒号」的字符集界定主体，
# 并把右侧所有括号标记整体捕获（`(I)(M)` 里真正授权的是后面的 `(M)`）。
_ACE_LINE = re.compile(r"(?P<principal>[^:()\r\n]+?):(?P<flags>(?:\([^)]*\))+)")
# 标准权限进程（打包应用）实际依赖的授权对象
_EVERYONE_PRINCIPALS = ("authenticated users", "users", "everyone")
_WRITE_RIGHTS = ("(F)", "(M)", "(W)", "(RW)")


def _icacls(*args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["icacls", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("调用 icacls 失败: %s", exc)
        return None


def _qualified_user() -> str:
    user = os.environ.get("USERNAME", "")
    domain = os.environ.get("USERDOMAIN", "")
    return f"{domain}\\{user}".lower() if user and domain else user.lower()


def has_usable_access(path: str | Path) -> bool:
    """判断文件是否已授权给「标准权限进程」访问。

    只解析 icacls 的授权行，不看整份输出：输出的第一行含文件路径，而用户名往往
    就在路径里（``C:\\Users\\<名>\\...``），按整份输出做子串匹配会一律误判为
    「权限正常」——这正是这个缺陷此前能悄悄漏过去的原因。
    """
    if os.name != "nt":
        return True
    target = Path(path)
    if not target.exists():
        return False
    completed = _icacls(str(target))
    if completed is None or completed.returncode:
        return False
    user = os.environ.get("USERNAME", "").lower()
    domain_user = _qualified_user()
    for match in _ACE_LINE.finditer(completed.stdout):
        # 首个授权行前面粘着文件路径，取最后一段作为授权对象
        principal = match.group("principal").strip().lower().split()[-1]
        if not principal or principal.endswith("owner rights"):
            continue
        granted = match.group("flags")
        if not any(right in granted for right in _WRITE_RIGHTS):
            continue
        if principal in _EVERYONE_PRINCIPALS or (user and principal in (user, domain_user)):
            return True
    return False


def grant_inherited_access(path: str | Path) -> bool:
    """让文件重新继承父目录的访问权限，返回是否执行成功。

    非 Windows 平台直接返回 True（POSIX 权限模型下不存在这个问题）。
    失败只记日志、不抛异常：权限修复失败不应该让一次成功的渲染作废，
    但会在日志里明确提示，便于用户手工处理。
    """
    if os.name != "nt":
        return True
    target = Path(path)
    if not target.exists():
        return False
    completed = _icacls(str(target), "/reset")
    if completed is None:
        return False
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "").strip()
        logger.warning("修复访问权限失败 %s: %s", target, detail[-300:])
        return False
    return True
