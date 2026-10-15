"""本地媒体的实测像素尺寸探测。

素材的留证尺寸必须是**所下载文件**的尺寸：图库返回的声明尺寸可能与实际文件不同
（平台裁切过的缩略图、取整后的缩放版本），而「素材长宽比与画布一致」这条契约只有
基于实测尺寸才可核验。这里复用依赖里已有的 ffmpeg（与成片验收同一可执行文件），
只读取流信息、不写任何文件，因此可以离线、确定性地重复执行。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError

#: ffmpeg 的流信息形如 ``Stream #0:0: Video: h264 ..., 1080x1920 [SAR 1:1 ...]``。
_STREAM_SIZE = re.compile(r"Video:.*?\s(\d{2,5})x(\d{2,5})[\s,\[]")


def probe_dimensions(path: Path) -> tuple[int, int]:
    """返回本地媒体的实测 ``(宽, 高)``；无法解析时抛出可读错误。

    ffmpeg 在没有指定输出时会以非零退出码结束，这是正常现象：流信息已经写进
    stderr，因此这里只看能否解析出尺寸，不把退出码当失败。
    """
    if not path.is_file():
        raise M2VError(f"素材文件不存在，无法读取尺寸：{path.name}")
    result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    line = next((item for item in result.stderr.splitlines()
                 if "Video:" in item and "Stream #" in item), "")
    match = _STREAM_SIZE.search(line)
    if match is None:
        detail = (result.stderr.strip().splitlines() or ["（无输出）"])[-1][:300]
        raise M2VError(f"无法读取素材尺寸：{path.name}（ffmpeg：{detail}）")
    return int(match.group(1)), int(match.group(2))
