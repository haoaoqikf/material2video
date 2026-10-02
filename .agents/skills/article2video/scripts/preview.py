#!/usr/bin/env python
"""预览入口：用本地 HTTP 服务在契约页打开画面，便于人工检查节奏与排版。

用法示例::

    uv run python .agents/skills/article2video/scripts/preview.py \
        --storyboard examples/buffer-smoothing/storyboard.json

契约页通过查询参数读取分镜 JSON，file:// 协议下会被同源策略拒绝，
因此预览必须走本地服务而不是双击 HTML。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2v.cli import main_preview  # noqa: E402  (路径注入后才能导入)

if __name__ == "__main__":
    raise SystemExit(main_preview())
