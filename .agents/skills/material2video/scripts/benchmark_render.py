#!/usr/bin/env python
"""渲染基准与成片验收入口。

skill bundle 需要可移植，因此脚本自行把同级目录加入 sys.path，
不依赖调用方的当前工作目录或已安装的包。

用法示例::

    # 三个固定示例的冷/热缓存与并发对照基准（报告写入作品 outputs/bench/）
    uv run python .agents/skills/material2video/scripts/benchmark_render.py benchmark

    # 全片有声渲染 + 跨并发未编码画面一致性验收
    uv run python .agents/skills/material2video/scripts/benchmark_render.py accept \
        --storyboard videos/compound-interest-leverage/storyboard.json \
        --media videos/compound-interest-leverage/outputs/media/media.json

产物（成片、截图、报告）全部落在作品 `outputs/` 下，已被 `.gitignore` 忽略。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from m2v.benchmark import main  # noqa: E402  (路径注入后才能导入)

if __name__ == "__main__":
    raise SystemExit(main())
