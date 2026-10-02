#!/usr/bin/env python
"""渲染入口：把分镜逐帧渲染成 MP4。

skill bundle 需要可移植，因此脚本自行把同级目录加入 sys.path，
不依赖调用方的当前工作目录或已安装的包。

用法示例::

    uv run python .agents/skills/article2video/scripts/render.py \
        --storyboard examples/buffer-smoothing/storyboard.json

省略 --out 时按文章归属推导：无声写入 videos/<slug>/outputs/silent.mp4，提供 --media 时写入
videos/<slug>/outputs/voiced.mp4，配合 --limit-frames 时写入 videos/<slug>/outputs/previews/。
规则见 references/paths-and-outputs.md。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2v.cli import main_render  # noqa: E402  (路径注入后才能导入)

if __name__ == "__main__":
    raise SystemExit(main_render())
