#!/usr/bin/env python
"""校验入口：检查分镜 JSON 的结构、时长与组件字段。

用法示例::

    uv run python .agents/skills/article2video/scripts/validate.py \
        examples/why-effort-fails/storyboard.json
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2v.cli import main_validate  # noqa: E402  (路径注入后才能导入)

if __name__ == "__main__":
    raise SystemExit(main_validate())
