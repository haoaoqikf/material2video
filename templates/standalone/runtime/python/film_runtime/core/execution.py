"""可选制作工具协议的声明校验，不执行命令或加载外部代码。"""
from __future__ import annotations

from pathlib import Path

from .errors import VideoError


def command(root: Path, project: dict, *, required: bool = False) -> list[str] | None:
    """协议只描述本地入口；不接入制作工具的工程可省略它。"""
    runtime = project.get('runtime')
    if runtime is None and not required:
        return None
    if (not isinstance(runtime, dict) or set(runtime) != {'version', 'command'}
            or type(runtime.get('version')) is not int or runtime['version'] != 1):
        raise VideoError('runtime必须为version=1及本地command参数数组')
    argv = runtime.get('command')
    if (not isinstance(argv, list) or len(argv) < 2
            or any(not isinstance(value, str) or not value.strip() or '\0' in value for value in argv)):
        raise VideoError('runtime.command必须是非空字符串参数数组，末项为本地入口')
    entry = Path(argv[-1])
    target = (root / entry).resolve()
    if (entry.is_absolute() or '\\' in argv[-1] or '..' in entry.parts
            or not target.is_relative_to(root.resolve()) or not target.is_file()):
        raise VideoError('runtime.command入口必须是作品内存在的相对路径，不能越界或借用主项目')
    # 可执行工具可从PATH恢复；其他参数不接受绝对文件路径，避免目录搬移失效。
    if any(Path(value).is_absolute() for value in argv):
        raise VideoError('runtime.command不能保存机器绝对路径')
    return list(argv)
