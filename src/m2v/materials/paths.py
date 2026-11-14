"""工作根、下载暂存及模型共用的词法路径/链接防护；不导入数据库或网络。"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat

from .errors import MaterialError


def no_links(path: Path, *, stage: str = 'storage') -> Path:
    """先核验词法祖先，不能用 resolve 抹掉 junction；缺失目标也检查 lstat。

    这是本进程访问前的路径检查，不是针对同权限恶意进程竞态的 OS 沙箱。
    源文件可以是显式选中的普通硬链接；需要独立所有权的暂存调用方另外检查 nlink。
    """
    if re.search(r'[\x00-\x1f\x7f]', str(path)):
        raise MaterialError('invalid-request', '素材路径不能包含控制字符', stage=stage)
    absolute = Path(os.path.abspath(path))
    for part in (absolute, *absolute.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise MaterialError('security-blocked', '素材路径不能经过链接或目录联接', stage=stage)
    return absolute
