#!/usr/bin/env python
"""渲染入口：把动画网页逐帧渲染成 MP4。

skill bundle 需要可移植，因此脚本自行把同级目录加入 sys.path，
不依赖调用方的当前工作目录或已安装的包。

用法示例::

    uv run python .agents/skills/article2video/scripts/render.py \
        --page examples/why-effort-fails/index.html \
        --storyboard examples/why-effort-fails/storyboard.json \
        --out outputs/why-effort-fails.mp4
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2v.cli import main_render  # noqa: E402  (路径注入后才能导入)

if __name__ == "__main__":
    raise SystemExit(main_render())
