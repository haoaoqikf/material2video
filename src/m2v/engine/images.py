"""图像比较的中立工具；不依赖 lookdev 或采集编排，避免循环导入。"""
from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError


def psnr(first: Path, second: Path) -> float:
    """两张同尺寸图的 PSNR；完全相同时为无穷大。"""
    result = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(first), "-i", str(second),
                             "-lavfi", "psnr=stats_file=-", "-f", "null", "-"],
                            capture_output=True, text=True, timeout=120)
    match = re.search(r"psnr_avg:([\d.]+|inf)", result.stdout or "")
    if not match:
        raise M2VError(f"无法读取 PSNR：{(result.stderr or result.stdout)[-400:]}")
    return math.inf if match.group(1) == "inf" else float(match.group(1))
